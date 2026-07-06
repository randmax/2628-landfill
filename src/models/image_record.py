from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.roi_result import RoiResult


@dataclass
class RadiometricSettings:
    """Parameters passed to the DJI DIRP measurement pipeline."""

    emissivity: float = 0.95
    distance: float = 25.0
    humidity: float = 50.0
    reflected_temperature: float = 20.0
    ambient_temperature: float = 20.0

    def to_dict(self) -> dict[str, float]:
        """Return a JSON serializable representation."""
        return asdict(self)


@dataclass
class ImageMetadata:
    """Useful EXIF/XMP metadata extracted from an image."""

    capture_time: str | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    gps_altitude: float | None = None
    relative_altitude: float | None = None
    absolute_altitude: float | None = None
    gimbal_pitch: float | None = None
    gimbal_roll: float | None = None
    gimbal_yaw: float | None = None
    flight_yaw: float | None = None
    rtk_status: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON serializable representation."""
        return asdict(self)


@dataclass
class ImageRecord:
    """Project state for one source image."""

    filepath: str
    processing_status: str = "feldolgozatlan"
    error_message: str = ""
    metadata: ImageMetadata = field(default_factory=ImageMetadata)
    image_min_temperature: float | None = None
    image_max_temperature: float | None = None
    image_mean_temperature: float | None = None
    roi_result: RoiResult | None = None
    radiometric_settings: RadiometricSettings = field(default_factory=RadiometricSettings)
    processed_at: str | None = None
    cache_key: str | None = None

    @property
    def filename(self) -> str:
        """Return the base filename."""
        return Path(self.filepath).name

    def mark_processed(self) -> None:
        """Set successful processing status and timestamp."""
        self.processing_status = "sikeres"
        self.error_message = ""
        self.processed_at = datetime.now().isoformat(timespec="seconds")

    def mark_error(self, message: str) -> None:
        """Set failed status with a user-facing message."""
        self.processing_status = "hibas"
        self.error_message = message
        self.processed_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON serializable representation."""
        data = asdict(self)
        data["filename"] = self.filename
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageRecord":
        """Create a record from stored JSON data."""
        metadata = ImageMetadata(**data.get("metadata", {}))
        settings = RadiometricSettings(**data.get("radiometric_settings", {}))
        roi_data = data.get("roi_result")
        roi = RoiResult(**roi_data) if roi_data else None
        return cls(
            filepath=data["filepath"],
            processing_status=data.get("processing_status", "feldolgozatlan"),
            error_message=data.get("error_message", ""),
            metadata=metadata,
            image_min_temperature=data.get("image_min_temperature"),
            image_max_temperature=data.get("image_max_temperature"),
            image_mean_temperature=data.get("image_mean_temperature"),
            roi_result=roi,
            radiometric_settings=settings,
            processed_at=data.get("processed_at"),
            cache_key=data.get("cache_key"),
        )
