from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.models.image_record import RadiometricSettings
from src.models.image_record import ImageRecord
from src.models.roi_result import RoiSettings


class SettingsPanel(QWidget):
    """Right-side controls for ROI and radiometric settings."""

    settings_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        camera_box = QGroupBox("Kamera / termál kép")
        camera_layout = QVBoxLayout(camera_box)
        self.camera_info = QLabel("Feldolgozás után jelenik meg a termál GSD, magasság és felbontás.")
        self.camera_info.setWordWrap(True)
        self.camera_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        camera_layout.addWidget(self.camera_info)
        layout.addWidget(camera_box)

        roi_box = QGroupBox("ROI-beállítások")
        roi_layout = QVBoxLayout(roi_box)
        roi_form = QFormLayout()
        self.square_roi = QCheckBox("Négyzetes ROI")
        self.square_roi.setToolTip("Bekapcsolva a ROI szélessége és magassága azonos értékre áll.")
        self.square_roi.setChecked(True)
        self.roi_width = QSpinBox()
        self.roi_width.setRange(1, 10000)
        self.roi_width.setValue(20)
        self.roi_width.setSuffix(" px")
        self.roi_height = QSpinBox()
        self.roi_height.setRange(1, 10000)
        self.roi_height.setValue(20)
        self.roi_height.setSuffix(" px")
        self.stride = QSpinBox()
        self.stride.setRange(1, 10000)
        self.stride.setValue(1)
        self.stride.setSuffix(" px")
        self.valid_ratio = QDoubleSpinBox()
        self.valid_ratio.setRange(1, 100)
        self.valid_ratio.setValue(95)
        self.valid_ratio.setSuffix(" %")
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Átlaghőmérséklet", "95. percentilis", "Maximumhőmérséklet"])
        roi_form.addRow(self._field_label("Négyzetes ROI", "A szélesség és magasság összekapcsolása."), self.square_roi)
        roi_form.addRow(self._field_label("ROI szélesség", "A keresőablak vízszintes mérete pixelben."), self.roi_width)
        roi_form.addRow(self._field_label("ROI magasság", "A keresőablak függőleges mérete pixelben."), self.roi_height)
        roi_form.addRow(self._field_label("Lépésköz", "Ennyi pixelenként mozdul tovább a ROI a képen."), self.stride)
        roi_form.addRow(
            self._field_label("Érvényes pixelek", "Minimum arány, amely alatt a ROI nem vehető figyelembe."),
            self.valid_ratio,
        )
        roi_form.addRow(
            self._field_label("Rangsorolás", "Ez alapján választjuk ki a képen belüli legmelegebb ROI-t."),
            self.metric_combo,
        )
        roi_layout.addLayout(roi_form)
        layout.addWidget(roi_box)

        spatial_box = QGroupBox("Térbeli és GPS beállítások")
        spatial_layout = QVBoxLayout(spatial_box)
        spatial_form = QFormLayout()
        self.auto_thermal_gsd = QCheckBox("Automatikus termál GSD becslés")
        self.auto_thermal_gsd.setChecked(True)
        self.auto_thermal_gsd.setToolTip("Relatív magasság + termál látószög alapján becsült hőkamerás m/pixel érték.")
        self.thermal_hfov = QDoubleSpinBox()
        self.thermal_hfov.setRange(1.0, 179.0)
        self.thermal_hfov.setDecimals(1)
        self.thermal_hfov.setSingleStep(0.5)
        self.thermal_hfov.setValue(61.0)
        self.thermal_hfov.setSuffix(" °")
        self.gsd = QDoubleSpinBox()
        self.gsd.setRange(0.001, 10.0)
        self.gsd.setDecimals(3)
        self.gsd.setSingleStep(0.01)
        self.gsd.setValue(0.05)
        self.gsd.setSuffix(" m/termál px")
        spatial_form.addRow(
            self._field_label("Auto GSD", "Bekapcsolva képenként a relatív magasságból becsüli a termál GSD-t."),
            self.auto_thermal_gsd,
        )
        spatial_form.addRow(
            self._field_label("Termál HFOV", "A hőkamera vízszintes látószöge fokban. Csak automatikus GSD becslésnél számít."),
            self.thermal_hfov,
        )
        spatial_form.addRow(
            self._field_label("Kézi termál GSD", "Fallback érték, ha nincs relatív magasság vagy kikapcsolod az automatikus becslést."),
            self.gsd,
        )
        spatial_layout.addLayout(spatial_form)
        layout.addWidget(spatial_box)

        self.rad_box = QGroupBox("DJI SDK hőmérséklet-korrekciók")
        self.rad_box.setCheckable(True)
        self.rad_box.setChecked(False)
        rad_layout = QVBoxLayout(self.rad_box)
        rad_form = QFormLayout()
        self.emissivity = QDoubleSpinBox()
        self.emissivity.setRange(0.1, 1.0)
        self.emissivity.setDecimals(2)
        self.emissivity.setSingleStep(0.01)
        self.emissivity.setValue(0.95)
        self.distance = QDoubleSpinBox()
        self.distance.setRange(1, 25)
        self.distance.setValue(25)
        self.distance.setSuffix(" m")
        self.humidity = QDoubleSpinBox()
        self.humidity.setRange(1, 100)
        self.humidity.setValue(50)
        self.humidity.setSuffix(" %")
        self.reflection = QDoubleSpinBox()
        self.reflection.setRange(-40, 100)
        self.reflection.setValue(20)
        self.reflection.setSuffix(" °C")
        self.ambient = QDoubleSpinBox()
        self.ambient.setRange(-40, 80)
        self.ambient.setValue(20)
        self.ambient.setSuffix(" °C")
        rad_form.addRow(
            self._field_label("Emisszivitás", "A felület hősugárzási tényezője; 0.95 jó általános kiindulás."),
            self.emissivity,
        )
        rad_form.addRow(
            self._field_label("SDK tárgytávolság", "DJI SDK korrekciós paraméter, jelen SDK-ban 1-25 m. Nem a repülési magasság."),
            self.distance,
        )
        rad_form.addRow(
            self._field_label("Páratartalom", "Relatív páratartalom, amelyet az SDK a hőmérséklet-korrekcióhoz használ."),
            self.humidity,
        )
        rad_form.addRow(
            self._field_label("Visszavert hőm.", "A környezetből visszaverődő hősugárzás becsült hőmérséklete."),
            self.reflection,
        )
        rad_form.addRow(
            self._field_label("Környezeti hőm.", "A levegő becsült hőmérséklete a mérés idején."),
            self.ambient,
        )
        rad_layout.addLayout(rad_form)
        layout.addWidget(self.rad_box)

        display_box = QGroupBox("Megjelenítés")
        display_layout = QVBoxLayout(display_box)
        display_form = QFormLayout()
        self.show_box = QCheckBox("Bounding box megjelenítése")
        self.show_box.setToolTip("A megtalált ROI kerete külön grafikai rétegként jelenik meg.")
        self.show_box.setChecked(True)
        self.show_label = QCheckBox("Hőmérsékleti felirat megjelenítése")
        self.show_label.setToolTip("A ROI mellett megjeleníti az átlag, maximum és P95 értékeket.")
        self.show_label.setChecked(True)
        self.palette = QComboBox()
        self.palette.addItems(["inferno", "grayscale", "iron", "turbo", "hot"])
        display_form.addRow(self._field_label("Paletta", "A hőtérkép megjelenítési színskálája."), self.palette)
        display_form.addRow(self._field_label("Bounding box", "Kapcsolja a ROI keretének láthatóságát."), self.show_box)
        display_form.addRow(self._field_label("Felirat", "Kapcsolja a ROI hőmérsékleti címkéjét."), self.show_label)
        display_layout.addLayout(display_form)
        layout.addWidget(display_box)
        layout.addStretch(1)

        self.square_roi.toggled.connect(self._sync_square)
        self.roi_width.valueChanged.connect(self._sync_square)
        for widget in (
            self.roi_width,
            self.roi_height,
            self.stride,
            self.gsd,
            self.thermal_hfov,
            self.valid_ratio,
            self.emissivity,
            self.distance,
            self.humidity,
            self.reflection,
            self.ambient,
        ):
            widget.valueChanged.connect(lambda _value=None: self.settings_changed.emit())
        for widget in (self.metric_combo, self.palette):
            widget.currentIndexChanged.connect(lambda _index=None: self.settings_changed.emit())
        for widget in (self.show_box, self.show_label, self.square_roi, self.auto_thermal_gsd, self.rad_box):
            widget.toggled.connect(lambda _checked=None: self.settings_changed.emit())

    def roi_settings(self) -> RoiSettings:
        """Return validated ROI settings from controls."""
        metric_map = {
            "Átlaghőmérséklet": "mean",
            "95. percentilis": "p95",
            "Maximumhőmérséklet": "max",
        }
        return RoiSettings(
            width=self.roi_width.value(),
            height=self.roi_height.value(),
            stride=self.stride.value(),
            min_valid_ratio=self.valid_ratio.value() / 100.0,
            ranking_metric=metric_map[self.metric_combo.currentText()],
            gsd_m_per_px=self.gsd.value(),
            auto_thermal_gsd=self.auto_thermal_gsd.isChecked(),
            thermal_hfov_deg=self.thermal_hfov.value(),
        )

    def radiometric_settings(self) -> RadiometricSettings:
        """Return radiometric settings from controls."""
        if not self.rad_box.isChecked():
            return RadiometricSettings()
        return RadiometricSettings(
            emissivity=self.emissivity.value(),
            distance=self.distance.value(),
            humidity=self.humidity.value(),
            reflected_temperature=self.reflection.value(),
            ambient_temperature=self.ambient.value(),
        )

    def set_camera_info(self, record: ImageRecord | None) -> None:
        """Update camera/thermal metadata summary for the selected image."""
        if record is None or record.roi_result is None:
            self.camera_info.setText("Feldolgozás után jelenik meg a termál GSD, magasság és felbontás.")
            return
        roi = record.roi_result
        rel_alt = roi.relative_altitude if roi.relative_altitude is not None else record.metadata.relative_altitude
        abs_alt = roi.absolute_altitude
        resolution = (
            f"{roi.thermal_width_px} x {roi.thermal_height_px} px"
            if roi.thermal_width_px and roi.thermal_height_px
            else "nincs adat"
        )
        gsd = f"{roi.gsd_m_per_px:.4f} m/termál px" if roi.gsd_m_per_px is not None else "nincs adat"
        rel = f"{rel_alt:.2f} m" if rel_alt is not None else "nincs adat"
        absolute = f"{abs_alt:.2f} m" if abs_alt is not None else "nincs adat"
        self.camera_info.setText(
            f"Termál GSD: {gsd}\n"
            f"Relatív magasság: {rel}\n"
            f"Abszolút magasság: {absolute}\n"
            f"Termál felbontás: {resolution}"
        )

    def _sync_square(self) -> None:
        if self.square_roi.isChecked():
            self.roi_height.setValue(self.roi_width.value())

    @staticmethod
    def _info_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            "QLabel { color: #374151; background: #f3f4f6; border: 1px solid #d1d5db; "
            "border-radius: 4px; padding: 6px; }"
        )
        return label

    @staticmethod
    def _field_label(text: str, tooltip: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(text)
        info = QLabel("i")
        info.setToolTip(tooltip)
        info.setAlignment(Qt.AlignCenter)
        info.setFixedSize(16, 16)
        info.setStyleSheet(
            "QLabel { color: #1d4ed8; border: 1px solid #93c5fd; border-radius: 8px; "
            "font-weight: bold; background: #eff6ff; }"
        )
        layout.addWidget(label)
        layout.addWidget(info)
        layout.addStretch(1)
        return widget
