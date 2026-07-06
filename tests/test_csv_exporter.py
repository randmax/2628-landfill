from src.models.image_record import ImageRecord
from src.models.roi_result import RoiResult
from src.storage.csv_exporter import records_to_rows


def _record(name: str, value: float) -> ImageRecord:
    record = ImageRecord(name)
    record.processing_status = "sikeres"
    record.roi_result = RoiResult(0, 0, 2, 2, value, value, value, value, value, 1.0, "mean", value)
    return record


def test_csv_sorts_successful_records_descending() -> None:
    rows = records_to_rows([_record("cold.jpg", 1), _record("hot.jpg", 9)])
    assert [row["filename"] for row in rows[:2]] == ["hot.jpg", "cold.jpg"]
    assert [row["rank"] for row in rows[:2]] == [1, 2]


def test_failed_image_goes_to_csv_end() -> None:
    failed = ImageRecord("bad.jpg")
    failed.mark_error("nem tamogatott")
    rows = records_to_rows([failed, _record("hot.jpg", 9)])
    assert [row["filename"] for row in rows] == ["hot.jpg", "bad.jpg"]
    assert rows[-1]["error_message"] == "nem tamogatott"
