from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.metadata.metadata_reader import MetadataReader
from src.models.image_record import ImageRecord
from src.storage.cache_store import CacheStore
from src.storage.csv_exporter import export_csv
from src.storage.project_store import ProjectStore
from src.thermal.dji_sdk_wrapper import DjiSdkError, DjiThermalSdk
from src.thermal.palette_renderer import render_temperature
from src.thermal.thermal_processor import ThermalProcessor
from src.thermal.webodm_exporter import WebOdmRadiometricExporter
from src.workers.processing_worker import ProcessingWorker
from src.workers.webodm_export_worker import WebOdmExportWorker
from src.gui.image_viewer import ImageViewer
from src.gui.result_table import ResultTable
from src.gui.settings_panel import SettingsPanel


IMAGE_PATTERNS = ("*.JPG", "*.JPEG", "*.jpg", "*.jpeg")
THERMAL_SUFFIXES = ("_T", "_R")


class MainWindow(QMainWindow):
    """A Térmonitor-thermal fő PySide6 ablaka."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Térmonitor-thermal")
        self.resize(1500, 900)
        self.records: list[ImageRecord] = []
        self.current_dir: Path | None = None
        self.current_index = -1
        self.view_mode = "thermal"
        self.cache = CacheStore("cache")
        self.project_store = ProjectStore()
        self.metadata_reader = MetadataReader()
        self.worker: ProcessingWorker | WebOdmExportWorker | None = None
        self.thread: QThread | None = None
        self.sdk: DjiThermalSdk | None = None
        self.processor: ThermalProcessor | None = None

        try:
            self.sdk = DjiThermalSdk()
            self.processor = ThermalProcessor(self.sdk, self.cache)
        except DjiSdkError as exc:
            logging.exception("SDK betoltesi hiba")
            QMessageBox.warning(self, "SDK hiba", f"A DJI SDK nem toltheto be:\n{exc}")

        self._build_ui()
        self._refresh_stats()

    def _build_ui(self) -> None:
        actions = self._create_actions()
        self._build_menus(actions)

        toolbar = QToolBar("Eszközök")
        self.addToolBar(toolbar)
        for group in (
            ("choose_directory", "scan_directory"),
            ("process_current", "process_all", "export_webodm_radiometric", "cancel_processing"),
            ("toggle_view_mode",),
            ("export_results", "open_output_dir"),
        ):
            for key in group:
                toolbar.addAction(actions[key])
            toolbar.addSeparator()

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.dir_label = QLabel("Nincs munkakönyvtár")
        self.stats_label = QLabel("")
        self.image_list = QListWidget()
        self.image_list.currentRowChanged.connect(self.select_image)
        left_layout.addWidget(self.dir_label)
        left_layout.addWidget(self.stats_label)
        left_layout.addWidget(self.image_list)

        viewer_panel = QWidget()
        viewer_layout = QVBoxLayout(viewer_panel)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        self.viewer = ImageViewer()
        viewer_layout.addWidget(self.viewer, 1)
        image_nav = QHBoxLayout()
        image_nav.addStretch(1)
        self.previous_image_button = QPushButton("Előző kép")
        self.previous_image_button.clicked.connect(self.previous_image)
        self.next_image_button = QPushButton("Következő kép")
        self.next_image_button.clicked.connect(self.next_image)
        self.clear_points_button = QPushButton("Mérési pontok törlése")
        self.clear_points_button.clicked.connect(self.clear_temperature_points)
        image_nav.addWidget(self.previous_image_button)
        image_nav.addWidget(self.next_image_button)
        image_nav.addWidget(self.clear_points_button)
        image_nav.addStretch(1)
        viewer_layout.addLayout(image_nav)

        right_tabs = QTabWidget()
        self.settings_panel = SettingsPanel()
        self.results = ResultTable()
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        settings_scroll.setWidget(self.settings_panel)
        right_tabs.addTab(settings_scroll, "Beállítások")
        right_tabs.addTab(self.results, "Találatok")
        self.results.cellDoubleClicked.connect(self._open_result_row)
        self.settings_panel.settings_changed.connect(self._refresh_current_image)

        splitter.addWidget(left)
        splitter.addWidget(viewer_panel)
        splitter.addWidget(right_tabs)
        splitter.setSizes([320, 850, 360])
        self.setCentralWidget(splitter)

        status = QStatusBar()
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 0, 8, 0)
        self.operation_label = QLabel("Kész")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(260)
        bottom_layout.addWidget(self.operation_label)
        bottom_layout.addWidget(self.progress)
        status.addPermanentWidget(bottom, 1)
        self.setStatusBar(status)

    def _create_actions(self) -> dict[str, QAction]:
        action_specs = {
            "choose_directory": ("Munkakönyvtár kiválasztása", self.choose_directory),
            "scan_directory": ("Képek beolvasása", self.scan_directory),
            "save_project": ("Projekt mentése", self.save_project),
            "load_project": ("Projekt betöltése", self.load_project),
            "process_current": ("Aktuális kép feldolgozása", self.process_current),
            "process_all": ("Összes kép feldolgozása", self.process_all),
            "export_webodm_radiometric": ("WebODM radiometrikus TIFF export", self.export_webodm_radiometric),
            "cancel_processing": ("Feldolgozás leállítása", self.cancel_processing),
            "previous_image": ("Előző kép", self.previous_image),
            "next_image": ("Következő kép", self.next_image),
            "toggle_view_mode": ("Hőkép / RGB nézet váltása", self.toggle_view_mode),
            "export_results": ("CSV exportálása", self.export_results),
            "open_output_dir": ("Kimeneti könyvtár megnyitása", self.open_output_dir),
            "clear_cache": ("Cache törlése", self.clear_cache),
        }
        actions = {}
        for key, (text, slot) in action_specs.items():
            action = QAction(text, self)
            action.triggered.connect(slot)
            actions[key] = action
        return actions

    def _build_menus(self, actions: dict[str, QAction]) -> None:
        file_menu = self.menuBar().addMenu("Fájl és projekt")
        self._add_menu_actions(file_menu, actions, ("choose_directory", "scan_directory"))
        file_menu.addSeparator()
        self._add_menu_actions(file_menu, actions, ("save_project", "load_project"))

        processing_menu = self.menuBar().addMenu("Feldolgozás")
        self._add_menu_actions(processing_menu, actions, ("process_current", "process_all"))
        processing_menu.addSeparator()
        self._add_menu_actions(processing_menu, actions, ("export_webodm_radiometric",))
        processing_menu.addSeparator()
        self._add_menu_actions(processing_menu, actions, ("cancel_processing",))

        navigation_menu = self.menuBar().addMenu("Navigáció")
        self._add_menu_actions(navigation_menu, actions, ("toggle_view_mode",))
        navigation_menu.addSeparator()
        self._add_menu_actions(navigation_menu, actions, ("previous_image", "next_image"))

        results_menu = self.menuBar().addMenu("Eredmények")
        self._add_menu_actions(results_menu, actions, ("export_results", "open_output_dir"))

        maintenance_menu = self.menuBar().addMenu("Karbantartás")
        self._add_menu_actions(maintenance_menu, actions, ("clear_cache",))

    @staticmethod
    def _add_menu_actions(menu: QMenu, actions: dict[str, QAction], keys: tuple[str, ...]) -> None:
        for key in keys:
            menu.addAction(actions[key])

    def choose_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Munkakönyvtár kiválasztása")
        if folder:
            self.current_dir = Path(folder)
            self.dir_label.setText(str(self.current_dir))
            self.scan_directory()

    def scan_directory(self) -> None:
        """Gyors képlistázás: metaadatot itt még nem olvasunk, hogy a GUI ne fagyjon meg."""
        if not self.current_dir:
            return
        paths: list[Path] = []
        for pattern in IMAGE_PATTERNS:
            paths.extend(self.current_dir.rglob(pattern))
        paths = sorted(set(paths))
        thermal_paths = [path for path in paths if _is_thermal_image(path)]
        rgb_by_key = {_image_pair_key(path): path for path in paths if _is_rgb_image(path)}
        self.records = []
        for path in thermal_paths:
            key = _image_pair_key(path)
            rgb_path = rgb_by_key.get(key) or _guess_rgb_pair(path)
            self.records.append(
                ImageRecord(
                    filepath=str(path),
                    rgb_filepath=str(rgb_path) if rgb_path and rgb_path.exists() else None,
                )
            )
        paired = sum(1 for record in self.records if record.rgb_filepath)
        self.operation_label.setText(f"Betöltve: {len(self.records)} hőkép, RGB pár: {paired}")
        self._refresh_list()
        self._refresh_stats()
        if self.records:
            self.image_list.setCurrentRow(0)

    def process_current(self) -> None:
        if self.current_index >= 0:
            self._start_processing([self.current_index])

    def process_all(self) -> None:
        self._start_processing(list(range(len(self.records))))

    def export_webodm_radiometric(self) -> None:
        """A betöltött R-JPEG képeket float32 Celsius TIFF-ként exportálja WebODM-hez."""
        if not self.sdk:
            QMessageBox.warning(self, "SDK hiba", "A DJI SDK nem érhető el, az export nem indítható.")
            return
        if not self.records:
            QMessageBox.information(self, "WebODM export", "Előbb olvass be R-JPEG képeket.")
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "WebODM radiometrikus TIFF export könyvtára",
            str(Path("output") / "webodm_radiometric_tiff"),
        )
        if not folder:
            return
        exporter = WebOdmRadiometricExporter(self.sdk, self.metadata_reader)
        self.thread = QThread(self)
        self.worker = WebOdmExportWorker(
            exporter,
            self.records,
            folder,
            self.settings_panel.radiometric_settings(),
            self.metadata_reader,
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.record_started.connect(self._webodm_record_started)
        self.worker.record_finished.connect(self._webodm_record_finished)
        self.worker.progress.connect(self._progress_changed)
        self.worker.finished.connect(self._webodm_export_finished)
        thread = self.thread
        worker = self.worker
        self.worker.finished.connect(lambda _results, thread=thread: thread.quit())
        self.worker.finished.connect(lambda _results, worker=worker: worker.deleteLater())
        self.thread.finished.connect(self.thread.deleteLater)
        self.progress.setValue(0)
        self.progress.setMaximum(len(self.records))
        self.thread.start()

    def _start_processing(self, indexes: list[int]) -> None:
        """Elindítja a ROI-elemzést háttérszálon a megadott képekre."""
        if not self.processor:
            QMessageBox.warning(self, "SDK hiba", "A DJI SDK nem érhető el, a feldolgozás nem indítható.")
            return
        if not indexes:
            return
        self.thread = QThread(self)
        self.worker = ProcessingWorker(
            self.processor,
            self.records,
            indexes,
            self.settings_panel.radiometric_settings(),
            self.settings_panel.roi_settings(),
            self.metadata_reader,
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.record_started.connect(self._record_started)
        self.worker.record_finished.connect(self._record_finished)
        self.worker.progress.connect(self._progress_changed)
        self.worker.finished.connect(self._processing_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.progress.setValue(0)
        self.progress.setMaximum(len(indexes))
        self.thread.start()

    def cancel_processing(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.operation_label.setText("Leállítás kérése...")

    def select_image(self, index: int) -> None:
        self.current_index = index
        if index < 0 or index >= len(self.records):
            return
        self._show_record(self.records[index])
        self.settings_panel.set_camera_info(self.records[index])

    def previous_image(self) -> None:
        if self.current_index > 0:
            self.image_list.setCurrentRow(self.current_index - 1)

    def next_image(self) -> None:
        if self.current_index < len(self.records) - 1:
            self.image_list.setCurrentRow(self.current_index + 1)

    def toggle_view_mode(self) -> None:
        """Váltás a radiometrikus hőkép és a hozzá tartozó RGB kép között."""
        self.view_mode = "rgb" if self.view_mode == "thermal" else "thermal"
        self.operation_label.setText("RGB nézet" if self.view_mode == "rgb" else "Hőkép nézet")
        self._refresh_current_image()

    def clear_temperature_points(self) -> None:
        self.viewer.clear_measurements()
        self.operation_label.setText("Mérési pontok törölve.")

    def export_results(self) -> None:
        full, hotspots = export_csv(self.records, "output")
        QMessageBox.information(self, "CSV export", f"Elkészült:\n{full}\n{hotspots}")

    def open_output_dir(self) -> None:
        os.startfile(str(Path("output").resolve()))

    def clear_cache(self) -> None:
        self.cache.clear()
        QMessageBox.information(self, "Cache", "A cache törölve.")

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Projekt mentése", "output/project.json", "JSON (*.json)")
        if path:
            self.project_store.save(path, self.records)

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Projekt betöltése", "output", "JSON (*.json)")
        if path:
            self.records = self.project_store.load(path)
            self._refresh_list()
            self._refresh_stats()
            self.results.set_records(self.records)

    def _record_started(self, index: int) -> None:
        self.records[index].processing_status = "feldolgozás alatt"
        self._refresh_list_item(index)
        self.operation_label.setText(f"Feldolgozás: {self.records[index].filename}")

    def _record_finished(self, index: int, record: ImageRecord) -> None:
        self.records[index] = record
        self._refresh_list_item(index)
        self._refresh_stats()
        self.results.set_records(self.records)
        self.project_store.save("output/autosave_project.json", self.records)
        if index == self.current_index:
            self._show_record(record)
            self.settings_panel.set_camera_info(record)

    def _progress_changed(self, done: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _processing_finished(self) -> None:
        self.operation_label.setText("Kész")
        self.worker = None
        self.thread = None

    def _webodm_record_started(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.operation_label.setText(f"WebODM export: {self.records[index].filename}")

    def _webodm_record_finished(self, _index: int, _result: object) -> None:
        return

    def _webodm_export_finished(self, results: list) -> None:
        ok = sum(1 for result in results if getattr(result, "status", "") == "sikeres")
        bad = len(results) - ok
        self.operation_label.setText("Kész")
        self.worker = None
        self.thread = None
        QMessageBox.information(
            self,
            "WebODM export",
            "Radiometrikus TIFF export kész.\n"
            f"Sikeres: {ok}\n"
            f"Hibás: {bad}\n"
            "Manifest: webodm_radiometric_manifest.csv",
        )

    def _show_record(self, record: ImageRecord) -> None:
        """Megjeleníti az aktuális képet, feldolgozás után radiometrikus előnézettel."""
        if self.view_mode == "rgb":
            if record.rgb_filepath:
                img = cv2.imread(record.rgb_filepath)
                if img is not None:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.viewer.set_image(rgb)
                    self.viewer.set_temperature_matrix(None)
                    self.viewer.set_roi(None)
                    return
            self.operation_label.setText("Ehhez a hőképhez nem található RGB pár.")
        matrix = self._matrix_for_record(record)
        if matrix is not None:
            rgb = render_temperature(matrix, self.settings_panel.palette.currentText())
            self.viewer.set_image(rgb)
            self.viewer.set_temperature_matrix(matrix)
            if record.roi_result:
                self.viewer.set_roi(record.roi_result, self.settings_panel.show_box.isChecked(), self.settings_panel.show_label.isChecked())
            else:
                self._show_roi_preview(matrix.shape[1], matrix.shape[0])
            return
        img = cv2.imread(record.filepath)
        if img is not None:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self.viewer.set_image(rgb)
            self.viewer.set_temperature_matrix(None)
            self._show_roi_preview(rgb.shape[1], rgb.shape[0])

    def _show_roi_preview(self, image_w: int, image_h: int) -> None:
        """Feldolgozás előtt is láthatóvá teszi az aktív ROI méretét."""
        settings = self.settings_panel.roi_settings()
        roi_w = min(settings.width, image_w)
        roi_h = min(settings.height, image_h)
        label = (
            f"ROI előnézet: {roi_w} x {roi_h} termál px | "
            f"{roi_w * settings.gsd_m_per_px:.2f} x {roi_h * settings.gsd_m_per_px:.2f} m"
        )
        self.viewer.set_roi_preview(roi_w, roi_h, label)

    def _refresh_current_image(self) -> None:
        if 0 <= self.current_index < len(self.records):
            self._show_record(self.records[self.current_index])

    def _matrix_for_record(self, record: ImageRecord) -> np.ndarray | None:
        if not record.cache_key:
            return None
        matrix_path = Path("cache") / record.cache_key / "temperature_matrix.npy"
        if matrix_path.exists():
            return np.load(matrix_path)
        return None

    def _refresh_list(self) -> None:
        self.image_list.clear()
        for record in self.records:
            item = QListWidgetItem(f"{record.filename}  [{record.processing_status}]")
            self.image_list.addItem(item)

    def _refresh_list_item(self, index: int) -> None:
        item = self.image_list.item(index)
        if item:
            record = self.records[index]
            item.setText(f"{record.filename}  [{record.processing_status}]")

    def _refresh_stats(self) -> None:
        total = len(self.records)
        ok = sum(1 for r in self.records if r.processing_status == "sikeres")
        bad = sum(1 for r in self.records if r.processing_status == "hibas")
        pending = total - ok - bad
        paired = sum(1 for r in self.records if r.rgb_filepath)
        self.stats_label.setText(
            f"Hőképek: {total} | RGB pár: {paired} | feldolgozott: {ok} | hibás: {bad} | várakozik: {pending}"
        )

    def _open_result_row(self, row: int, _column: int) -> None:
        item = self.results.item(row, 1)
        if not item:
            return
        filepath = item.data(256)
        for index, record in enumerate(self.records):
            if record.filepath == filepath:
                self.image_list.setCurrentRow(index)
                break


def _image_pair_key(path: Path) -> str:
    """DJI fájlnévből párosítási kulcsot képez, elsősorban a képsorszám alapján."""
    match = re.search(r"DJI_(\d+)_(\d{4})_[A-Z]\.jpe?g$", path.name, flags=re.IGNORECASE)
    if match:
        return match.group(2)
    stem = path.stem
    for suffix in (*THERMAL_SUFFIXES, "_V"):
        if stem.upper().endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _is_thermal_image(path: Path) -> bool:
    return (
        bool(re.search(r"_[TR]\.jpe?g$", path.name, flags=re.IGNORECASE))
        or path.parent.name.upper().endswith("_T")
        or "THERMAL" in path.parent.name.upper()
    )


def _is_rgb_image(path: Path) -> bool:
    return bool(re.search(r"_V\.jpe?g$", path.name, flags=re.IGNORECASE)) or "RGB" in path.parent.name.upper()


def _guess_rgb_pair(thermal_path: Path) -> Path | None:
    """Tipikus M3T könyvtárstruktúrában megpróbálja kitalálni az RGB párt."""
    rgb_name = re.sub(r"_[TR](\.jpe?g)$", r"_V\1", thermal_path.name, flags=re.IGNORECASE)
    candidates = [
        thermal_path.with_name(rgb_name),
        thermal_path.parent.parent / "M3T_RGB" / rgb_name,
        thermal_path.parent.parent / "RGB" / rgb_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    key = _image_pair_key(thermal_path)
    # Egyes DJI mentéseknél az RGB timestamp eltérhet, ilyenkor a képsorszám a biztos kapocs.
    for folder in (thermal_path.parent.parent / "M3T_RGB", thermal_path.parent.parent / "RGB"):
        if not folder.exists():
            continue
        matches = sorted(folder.glob(f"DJI_*_{key}_V.JPG")) + sorted(folder.glob(f"DJI_*_{key}_V.jpg"))
        if matches:
            return matches[0]
    return None
