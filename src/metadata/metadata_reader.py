from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

from src.models.image_record import ImageMetadata


class MetadataReader:
    """Metaadat-olvasó: elsőként ExifToolt használ, nélküle gyors XMP/Pillow fallbacket."""

    def __init__(self, exiftool_path: str | None = None) -> None:
        self.exiftool_path = exiftool_path or shutil.which("exiftool")

    @property
    def exiftool_available(self) -> bool:
        """Return whether ExifTool can be executed."""
        return bool(self.exiftool_path)

    def read_batch(self, paths: list[str | Path]) -> dict[str, ImageMetadata]:
        """Több kép metaadatait olvassa be, lehetőség szerint egy ExifTool hívással."""
        if not paths:
            return {}
        if self.exiftool_available:
            return self._read_exiftool(paths)
        return {str(path): self._read_pillow(path) for path in paths}

    def _read_exiftool(self, paths: list[str | Path]) -> dict[str, ImageMetadata]:
        command = [self.exiftool_path or "exiftool", "-json", "-n", *[str(p) for p in paths]]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return {str(path): ImageMetadata() for path in paths}
        rows: list[dict[str, Any]] = json.loads(result.stdout)
        output = {}
        for row in rows:
            source = row.get("SourceFile")
            output[str(source)] = ImageMetadata(
                capture_time=_first_value(row, "DateTimeOriginal", "CreateDate"),
                gps_latitude=_float_or_none(_first_value(row, "GPSLatitude", "GpsLatitude", "Latitude")),
                gps_longitude=_float_or_none(_first_value(row, "GPSLongitude", "GpsLongitude", "Longitude")),
                gps_altitude=_float_or_none(_first_value(row, "GPSAltitude", "GpsAltitude")),
                relative_altitude=_float_or_none(_first_value(row, "RelativeAltitude", "relativeAltitude")),
                absolute_altitude=_float_or_none(_first_value(row, "AbsoluteAltitude", "absoluteAltitude")),
                gimbal_pitch=_float_or_none(_first_value(row, "GimbalPitchDegree", "GimbalPitch")),
                gimbal_roll=_float_or_none(_first_value(row, "GimbalRollDegree", "GimbalRoll")),
                gimbal_yaw=_float_or_none(_first_value(row, "GimbalYawDegree", "GimbalYaw")),
                flight_yaw=_float_or_none(_first_value(row, "FlightYawDegree", "FlightYaw")),
                rtk_status=_string_or_none(_first_value(row, "RtkFlag", "RTKFlag", "RtkStd")),
            )
        return output

    def _read_pillow(self, path: str | Path) -> ImageMetadata:
        xmp_metadata = self._read_xmp(path)
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                tags = {ExifTags.TAGS.get(key, key): value for key, value in exif.items()}
                xmp_metadata.capture_time = xmp_metadata.capture_time or str(
                    tags.get("DateTimeOriginal") or tags.get("DateTime") or ""
                ) or None
                return xmp_metadata
        except Exception:
            return xmp_metadata

    def _read_xmp(self, path: str | Path) -> ImageMetadata:
        """DJI XMP mezők gyors keresése a JPEG elejében és végében."""
        try:
            data = _read_metadata_text(path)
        except Exception:
            return ImageMetadata()
        return ImageMetadata(
            capture_time=_xmp_value(data, ("CreateDate", "DateTimeOriginal")),
            gps_latitude=_float_or_none(_xmp_value(data, ("GpsLatitude", "GPSLatitude", "Latitude"))),
            gps_longitude=_float_or_none(_xmp_value(data, ("GpsLongitude", "GPSLongitude", "Longitude"))),
            gps_altitude=_float_or_none(_xmp_value(data, ("GpsAltitude", "GPSAltitude"))),
            relative_altitude=_float_or_none(_xmp_value(data, ("RelativeAltitude", "relativeAltitude"))),
            absolute_altitude=_float_or_none(_xmp_value(data, ("AbsoluteAltitude", "absoluteAltitude"))),
            gimbal_pitch=_float_or_none(_xmp_value(data, ("GimbalPitchDegree", "GimbalPitch"))),
            gimbal_roll=_float_or_none(_xmp_value(data, ("GimbalRollDegree", "GimbalRoll"))),
            gimbal_yaw=_float_or_none(_xmp_value(data, ("GimbalYawDegree", "GimbalYaw"))),
            flight_yaw=_float_or_none(_xmp_value(data, ("FlightYawDegree", "FlightYaw"))),
            rtk_status=_xmp_value(data, ("RtkFlag", "RTKFlag", "RtkStd")),
        )


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if row.get(key) not in (None, ""):
            return row[key]
    return None


def _string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _xmp_value(text: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        patterns = (
            rf'(?:drone-dji:|exif:|tiff:|xmp:)?{re.escape(name)}="([^"]+)"',
            rf"<(?:drone-dji:|exif:|tiff:|xmp:)?{re.escape(name)}>([^<]+)</",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return None


def _read_metadata_text(path: str | Path, chunk_size: int = 512 * 1024) -> str:
    """Csak a JPEG elejét és végét olvassa, hogy sok kép esetén se fagyjon a program."""
    source = Path(path)
    size = source.stat().st_size
    with source.open("rb") as handle:
        head = handle.read(chunk_size)
        if size > chunk_size:
            handle.seek(max(0, size - chunk_size))
            tail = handle.read(chunk_size)
        else:
            tail = b""
    return (head + b"\n" + tail).decode("utf-8", errors="ignore")
