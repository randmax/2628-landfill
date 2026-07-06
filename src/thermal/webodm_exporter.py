from __future__ import annotations

import csv
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.metadata.metadata_reader import MetadataReader
from src.models.image_record import ImageRecord, RadiometricSettings
from src.thermal.dji_sdk_wrapper import DjiThermalSdk


@dataclass
class WebOdmExportResult:
    """Result of converting one R-JPEG to a WebODM-friendly radiometric TIFF."""

    source_path: str
    output_path: str
    status: str
    error_message: str = ""
    min_c: float | None = None
    max_c: float | None = None
    mean_c: float | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    altitude_m: float | None = None


class WebOdmRadiometricExporter:
    """DJI R-JPEG képek exportja WebODM-kompatibilis radiometrikus TIFF csomagba."""

    def __init__(
        self,
        sdk: DjiThermalSdk,
        metadata_reader: MetadataReader | None = None,
        exiftool_path: str | None = None,
    ) -> None:
        self.sdk = sdk
        self.metadata_reader = metadata_reader
        self.exiftool_path = exiftool_path or shutil.which("exiftool")

    def export_records(
        self,
        records: list[ImageRecord],
        output_dir: str | Path,
        radiometry: RadiometricSettings,
        cancel_requested=None,
    ) -> list[WebOdmExportResult]:
        """Export all records and write a manifest CSV."""
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        results: list[WebOdmExportResult] = []
        for record in records:
            if cancel_requested and cancel_requested():
                break
            self._ensure_metadata(record)
            results.append(self.export_record(record, folder, radiometry))
        self.write_manifest(folder / "webodm_radiometric_manifest.csv", results)
        self.write_geo_txt(folder / "webodm_geo.txt", results)
        return results

    def export_record(
        self,
        record: ImageRecord,
        output_dir: Path,
        radiometry: RadiometricSettings,
    ) -> WebOdmExportResult:
        """Egy képet egycsatornás float32 TIFF-be ment, ahol a pixelérték Celsius."""
        try:
            self._ensure_metadata(record)
            measured = self.sdk.measure(record.filepath, radiometry)
            matrix = measured.data.astype(np.float32, copy=False)
            output_path = output_dir / f"{Path(record.filepath).stem}_thermal_celsius_float32.tif"
            # Fontos: itt a radiometrikus mátrixot mentjük, nem a megjelenítéshez készült
            # 8 bites színezett képet. Így a hőmérsékleti információ megmarad.
            if not cv2.imwrite(str(output_path), matrix):
                raise RuntimeError("A TIFF mentése nem sikerült.")
            self._copy_metadata(record.filepath, output_path)
            valid = matrix[np.isfinite(matrix)]
            metadata = record.metadata
            return WebOdmExportResult(
                source_path=record.filepath,
                output_path=str(output_path),
                status="sikeres",
                min_c=float(np.min(valid)) if valid.size else None,
                max_c=float(np.max(valid)) if valid.size else None,
                mean_c=float(np.mean(valid)) if valid.size else None,
                gps_latitude=metadata.gps_latitude,
                gps_longitude=metadata.gps_longitude,
                altitude_m=_first_not_none(metadata.absolute_altitude, metadata.gps_altitude, metadata.relative_altitude),
            )
        except Exception as exc:
            return WebOdmExportResult(
                source_path=record.filepath,
                output_path="",
                status="hibás",
                error_message=str(exc),
            )

    def _copy_metadata(self, source_path: str | Path, output_path: str | Path) -> None:
        """ExifTool esetén megpróbálja az eredeti DJI metaadatokat átmásolni."""
        if not self.exiftool_path:
            return
        command = [
            self.exiftool_path,
            "-overwrite_original",
            "-TagsFromFile",
            str(source_path),
            "-all:all",
            "-unsafe",
            str(output_path),
        ]
        subprocess.run(command, capture_output=True, text=True, check=False)

    def _ensure_metadata(self, record: ImageRecord) -> None:
        if not self.metadata_reader:
            return
        md = record.metadata
        if md.gps_latitude is not None and md.gps_longitude is not None:
            return
        result = self.metadata_reader.read_batch([record.filepath])
        record.metadata = result.get(record.filepath) or result.get(str(record.filepath)) or record.metadata

    @staticmethod
    def write_manifest(path: str | Path, results: list[WebOdmExportResult]) -> None:
        """Write a UTF-8 BOM manifest that documents radiometric TIFF semantics."""
        fields = [
            "source_path",
            "output_path",
            "status",
            "error_message",
            "pixel_unit",
            "dtype",
            "min_c",
            "max_c",
            "mean_c",
            "gps_latitude",
            "gps_longitude",
            "altitude_m",
        ]
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "source_path": result.source_path,
                        "output_path": result.output_path,
                        "status": result.status,
                        "error_message": result.error_message,
                        "pixel_unit": "Celsius",
                        "dtype": "float32",
                        "min_c": result.min_c,
                        "max_c": result.max_c,
                        "mean_c": result.mean_c,
                        "gps_latitude": result.gps_latitude,
                        "gps_longitude": result.gps_longitude,
                        "altitude_m": result.altitude_m,
                    }
                )

    @staticmethod
    def write_geo_txt(path: str | Path, results: list[WebOdmExportResult]) -> None:
        """Write a simple EPSG:4326 geolocation sidecar for ODM/WebODM-style workflows."""
        lines = ["EPSG:4326"]
        for result in results:
            if (
                result.status == "sikeres"
                and result.output_path
                and result.gps_latitude is not None
                and result.gps_longitude is not None
            ):
                altitude = result.altitude_m if result.altitude_m is not None else 0.0
                lines.append(
                    f"{Path(result.output_path).name} {result.gps_longitude:.10f} {result.gps_latitude:.10f} {altitude:.3f}"
                )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None
