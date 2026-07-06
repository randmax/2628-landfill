import numpy as np

from src.models.image_record import RadiometricSettings
from src.models.roi_result import RoiResult, RoiSettings
from src.storage.cache_store import CacheStore


def test_cache_key_changes_when_roi_changes(tmp_path) -> None:
    source = tmp_path / "image.JPG"
    source.write_bytes(b"abc")
    cache = CacheStore(tmp_path / "cache")
    key1 = cache.compute_key(source, RadiometricSettings(), RoiSettings(width=2), "sdk")
    key2 = cache.compute_key(source, RadiometricSettings(), RoiSettings(width=3), "sdk")
    assert key1 != key2


def test_cache_save_and_load(tmp_path) -> None:
    source = tmp_path / "image.JPG"
    source.write_bytes(b"abc")
    cache = CacheStore(tmp_path / "cache")
    key = cache.compute_key(source, RadiometricSettings(), RoiSettings(), "sdk")
    roi = RoiResult(1, 2, 3, 4, 5, 1, 9, 5, 8, 1.0, "mean", 5)
    cache.save(key, np.ones((2, 2), dtype=np.float32), roi, source)
    loaded = cache.load(key)
    assert loaded is not None
    assert loaded["roi_result"].x == 1
    assert np.load(loaded["temperature_matrix"]).shape == (2, 2)

