from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from src.metadata.metadata_reader import MetadataReader
from src.models.image_record import ImageRecord, RadiometricSettings
from src.models.roi_result import RoiSettings
from src.thermal.thermal_processor import ThermalProcessor


class ProcessingWorker(QObject):
    """Qt worker, amely a hosszú képfeldolgozást a GUI főszálán kívül futtatja."""

    record_started = Signal(int)
    record_finished = Signal(int, object)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(
        self,
        processor: ThermalProcessor,
        records: list[ImageRecord],
        indexes: list[int],
        radiometry: RadiometricSettings,
        roi_settings: RoiSettings,
        metadata_reader: MetadataReader | None = None,
    ) -> None:
        super().__init__()
        self.processor = processor
        self.records = records
        self.indexes = indexes
        self.radiometry = radiometry
        self.roi_settings = roi_settings
        self.metadata_reader = metadata_reader
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        """A kijelölt képeket sorban feldolgozza, közben állapotjelzéseket küld."""
        total = len(self.indexes)
        for done, index in enumerate(self.indexes, start=1):
            if self._cancelled:
                break
            self.record_started.emit(index)
            self._ensure_metadata(self.records[index])
            record = self.processor.process_image(self.records[index], self.radiometry, self.roi_settings)
            self.record_finished.emit(index, record)
            self.progress.emit(done, total)
        self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        """Request cancellation after the current SDK call returns."""
        self._cancelled = True

    def _ensure_metadata(self, record: ImageRecord) -> None:
        if not self.metadata_reader:
            return
        metadata = record.metadata
        has_any_geo = any(
            value is not None
            for value in (
                metadata.gps_latitude,
                metadata.gps_longitude,
                metadata.relative_altitude,
                metadata.absolute_altitude,
                metadata.gps_altitude,
            )
        )
        if has_any_geo or metadata.capture_time:
            return
        result = self.metadata_reader.read_batch([record.filepath])
        record.metadata = result.get(record.filepath) or result.get(str(record.filepath)) or record.metadata
