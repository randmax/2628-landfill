from __future__ import annotations

from pathlib import Path

import numpy as np

from src.models.image_record import ImageRecord, RadiometricSettings
from src.models.roi_result import RoiSettings
from src.storage.cache_store import CacheStore
from src.thermal.dji_sdk_wrapper import DjiThermalSdk
from src.thermal.geospatial import enrich_roi_georeference, resolve_thermal_gsd
from src.thermal.roi_analyzer import find_best_roi


class ThermalProcessor:
    """Coordinates SDK measurement, cache use, and ROI analysis."""

    def __init__(self, sdk: DjiThermalSdk, cache: CacheStore | None = None) -> None:
        self.sdk = sdk
        self.cache = cache

    def process_image(
        self,
        record: ImageRecord,
        radiometry: RadiometricSettings,
        roi_settings: RoiSettings,
    ) -> ImageRecord:
        """Process one image and update its record."""
        record.processing_status = "feldolgozas alatt"
        try:
            cache_key = self.cache.compute_key(record.filepath, radiometry, roi_settings, self.sdk.sdk_version()) if self.cache else None
            cached = self.cache.load(cache_key) if self.cache and cache_key else None
            if cached:
                matrix = np.load(cached["temperature_matrix"])
                record.roi_result = cached["roi_result"]
            else:
                measured = self.sdk.measure(record.filepath, radiometry)
                matrix = measured.data
                record.roi_result = find_best_roi(matrix, roi_settings)
                effective_gsd = resolve_thermal_gsd(roi_settings, record.metadata, matrix.shape[1])
                record.roi_result = enrich_roi_georeference(
                    record.roi_result,
                    record.metadata,
                    matrix.shape,
                    effective_gsd,
                )
                if self.cache and cache_key:
                    self.cache.save(cache_key, matrix, record.roi_result, record.filepath)
            if record.roi_result:
                effective_gsd = resolve_thermal_gsd(roi_settings, record.metadata, matrix.shape[1])
                record.roi_result = enrich_roi_georeference(
                    record.roi_result,
                    record.metadata,
                    matrix.shape,
                    effective_gsd,
                )
            valid = matrix[np.isfinite(matrix)]
            record.image_min_temperature = float(np.min(valid))
            record.image_max_temperature = float(np.max(valid))
            record.image_mean_temperature = float(np.mean(valid))
            record.radiometric_settings = radiometry
            record.cache_key = cache_key
            record.mark_processed()
        except Exception as exc:
            record.mark_error(str(exc))
        return record
