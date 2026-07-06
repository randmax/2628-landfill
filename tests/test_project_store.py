from src.models.image_record import ImageRecord
from src.models.roi_result import RoiResult
from src.storage.project_store import ProjectStore


def test_project_save_and_load(tmp_path) -> None:
    record = ImageRecord("a.jpg")
    record.roi_result = RoiResult(1, 2, 3, 4, 5, 1, 9, 5, 8, 1.0, "mean", 5)
    record.mark_processed()
    path = tmp_path / "project.json"
    store = ProjectStore()
    store.save(path, [record])
    loaded = store.load(path)
    assert loaded[0].filename == "a.jpg"
    assert loaded[0].roi_result.x == 1
    assert loaded[0].processing_status == "sikeres"

