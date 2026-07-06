from __future__ import annotations

import csv
from pathlib import Path

from src.models.image_record import ImageRecord


CSV_COLUMNS = [
    "rank",
    "filename",
    "filepath",
    "capture_time",
    "gps_latitude",
    "gps_longitude",
    "relative_altitude_m",
    "absolute_altitude_m",
    "roi_x",
    "roi_y",
    "roi_center_x_px",
    "roi_center_y_px",
    "roi_width_px",
    "roi_height_px",
    "roi_width_m",
    "roi_height_m",
    "roi_center_latitude",
    "roi_center_longitude",
    "roi_relative_altitude_m",
    "roi_absolute_altitude_m",
    "thermal_gsd_m_per_px",
    "roi_mean_c",
    "roi_max_c",
    "roi_min_c",
    "roi_median_c",
    "roi_p95_c",
    "image_max_c",
    "image_mean_c",
    "valid_pixel_ratio",
    "ranking_metric",
    "ranking_value",
    "processing_status",
    "error_message",
]


def records_to_rows(records: list[ImageRecord]) -> list[dict[str, object]]:
    """Convert records to ranked CSV rows."""
    rows = [_record_to_row(record) for record in records]
    ok = [row for row in rows if row["processing_status"] == "sikeres" and row["ranking_value"] is not None]
    bad = [row for row in rows if row not in ok]
    ok.sort(key=lambda item: item["ranking_value"], reverse=True)
    ranked = []
    for idx, row in enumerate(ok, start=1):
        row["rank"] = idx
        ranked.append(row)
    for row in bad:
        row["rank"] = ""
        ranked.append(row)
    return ranked


def records_to_dataframe(records: list[ImageRecord]) -> list[dict[str, object]]:
    """Backward-compatible alias returning ranked row dictionaries."""
    return records_to_rows(records)


def export_csv(records: list[ImageRecord], output_dir: str | Path) -> tuple[Path, Path]:
    """Write full and hotspots-only CSV files with UTF-8 BOM."""
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    rows = records_to_rows(records)
    full_path = folder / "thermal_results_sorted.csv"
    hotspots_path = folder / "thermal_hotspots_sorted.csv"
    _write_csv(full_path, rows)
    _write_csv(hotspots_path, [row for row in rows if row["processing_status"] == "sikeres"])
    return full_path, hotspots_path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _record_to_row(record: ImageRecord) -> dict[str, object]:
    roi = record.roi_result
    md = record.metadata
    return {
        "rank": "",
        "filename": record.filename,
        "filepath": record.filepath,
        "capture_time": md.capture_time,
        "gps_latitude": md.gps_latitude,
        "gps_longitude": md.gps_longitude,
        "relative_altitude_m": md.relative_altitude,
        "absolute_altitude_m": md.absolute_altitude,
        "roi_x": roi.x if roi else None,
        "roi_y": roi.y if roi else None,
        "roi_center_x_px": roi.center_x_px if roi else None,
        "roi_center_y_px": roi.center_y_px if roi else None,
        "roi_width_px": roi.width if roi else None,
        "roi_height_px": roi.height if roi else None,
        "roi_width_m": roi.width_m if roi else None,
        "roi_height_m": roi.height_m if roi else None,
        "roi_center_latitude": roi.center_latitude if roi else None,
        "roi_center_longitude": roi.center_longitude if roi else None,
        "roi_relative_altitude_m": roi.relative_altitude if roi else None,
        "roi_absolute_altitude_m": roi.absolute_altitude if roi else None,
        "thermal_gsd_m_per_px": roi.gsd_m_per_px if roi else None,
        "roi_mean_c": roi.mean_temperature if roi else None,
        "roi_max_c": roi.max_temperature if roi else None,
        "roi_min_c": roi.min_temperature if roi else None,
        "roi_median_c": roi.median_temperature if roi else None,
        "roi_p95_c": roi.p95_temperature if roi else None,
        "image_max_c": record.image_max_temperature,
        "image_mean_c": record.image_mean_temperature,
        "valid_pixel_ratio": roi.valid_pixel_ratio if roi else None,
        "ranking_metric": roi.ranking_metric if roi else None,
        "ranking_value": roi.ranking_value if roi else None,
        "processing_status": record.processing_status,
        "error_message": record.error_message,
    }
