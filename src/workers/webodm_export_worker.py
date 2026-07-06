from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from src.metadata.metadata_reader import MetadataReader
from src.models.image_record import ImageRecord, RadiometricSettings
from src.thermal.webodm_exporter import WebOdmRadiometricExporter


class WebOdmExportWorker(QObject):
    """Qt worker a WebODM radiometrikus TIFF export háttérben futtatásához."""

    record_started = Signal(int)
    record_finished = Signal(int, object)
    progress = Signal(int, int)
    finished = Signal(list)

    def __init__(
        self,
        exporter: WebOdmRadiometricExporter,
        records: list[ImageRecord],
        output_dir: str,
        radiometry: RadiometricSettings,
        metadata_reader: MetadataReader | None = None,
    ) -> None:
        super().__init__()
        self.exporter = exporter
        self.records = records
        self.output_dir = output_dir
        self.radiometry = radiometry
        self.metadata_reader = metadata_reader
        self._cancelled = False
        self.results = []

    @Slot()
    def run(self) -> None:
        """Export records sequentially."""
        total = len(self.records)
        for done, record in enumerate(self.records, start=1):
            if self._cancelled:
                break
            self.record_started.emit(done - 1)
            self._ensure_metadata(record)
            result = self.exporter.export_record(record, self._output_path(), self.radiometry)
            self.results.append(result)
            self.record_finished.emit(done - 1, result)
            self.progress.emit(done, total)
        self.exporter.write_manifest(self._output_path() / "webodm_radiometric_manifest.csv", self.results)
        self.exporter.write_geo_txt(self._output_path() / "webodm_geo.txt", self.results)
        self.finished.emit(self.results)

    @Slot()
    def cancel(self) -> None:
        """Request cancellation after the current image finishes."""
        self._cancelled = True

    def _output_path(self):
        from pathlib import Path

        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_metadata(self, record: ImageRecord) -> None:
        if not self.metadata_reader:
            return
        metadata = record.metadata
        if metadata.capture_time or metadata.gps_latitude is not None or metadata.gps_longitude is not None:
            return
        result = self.metadata_reader.read_batch([record.filepath])
        record.metadata = result.get(record.filepath) or result.get(str(record.filepath)) or record.metadata
