from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from src.models.image_record import ImageRecord


class ResultTable(QTableWidget):
    """Sortable hotspot table."""

    HEADERS = [
        "Sorrend",
        "Képnév",
        "ROI átlag °C",
        "ROI maximum °C",
        "P95 °C",
        "Kép maximum °C",
        "ROI szélesség m",
        "ROI magasság m",
        "ROI közép GPS szélesség",
        "ROI közép GPS hosszúság",
        "Relatív magasság m",
        "Abszolút magasság m",
        "Állapot",
    ]

    def __init__(self) -> None:
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSortingEnabled(True)

    def set_records(self, records: list[ImageRecord]) -> None:
        """Refresh table rows from processed records."""
        self.setSortingEnabled(False)
        processed = [r for r in records if r.roi_result is not None]
        processed.sort(key=lambda r: r.roi_result.ranking_value if r.roi_result else -1, reverse=True)
        self.setRowCount(len(processed))
        for row, record in enumerate(processed):
            roi = record.roi_result
            values = [
                row + 1,
                record.filename,
                f"{roi.mean_temperature:.2f}" if roi else "",
                f"{roi.max_temperature:.2f}" if roi else "",
                f"{roi.p95_temperature:.2f}" if roi else "",
                f"{record.image_max_temperature:.2f}" if record.image_max_temperature is not None else "",
                _format_float(roi.width_m if roi else None, 2),
                _format_float(roi.height_m if roi else None, 2),
                _format_float(roi.center_latitude if roi else None, 7),
                _format_float(roi.center_longitude if roi else None, 7),
                _format_float(_first_not_none(roi.relative_altitude if roi else None, record.metadata.relative_altitude), 2),
                _format_float(
                    _first_not_none(
                        roi.absolute_altitude if roi else None,
                        record.metadata.absolute_altitude,
                        record.metadata.gps_altitude,
                    ),
                    2,
                ),
                record.processing_status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(256, record.filepath)
                self.setItem(row, col, item)
        self.setSortingEnabled(True)


def _format_float(value: float | None, decimals: int) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None
