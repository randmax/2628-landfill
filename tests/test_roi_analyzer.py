import numpy as np
import pytest

from src.models.roi_result import RoiSettings
from src.thermal.roi_analyzer import find_best_roi


def test_find_known_hottest_roi() -> None:
    matrix = np.zeros((6, 6), dtype=np.float32)
    matrix[2:4, 3:5] = 10
    result = find_best_roi(matrix, RoiSettings(width=2, height=2, stride=1))
    assert (result.x, result.y) == (3, 2)
    assert result.mean_temperature == 10


def test_roi_larger_than_image_raises() -> None:
    matrix = np.ones((3, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="ROI"):
        find_best_roi(matrix, RoiSettings(width=4, height=2))


def test_nan_values_are_ignored_when_ratio_allows() -> None:
    matrix = np.array([[1, 2, np.nan], [1, 20, 20], [1, 20, 20]], dtype=np.float32)
    result = find_best_roi(matrix, RoiSettings(width=2, height=2, min_valid_ratio=0.75))
    assert (result.x, result.y) == (1, 1)
    assert result.mean_temperature == 20


def test_tie_prefers_roi_nearer_center() -> None:
    matrix = np.zeros((7, 7), dtype=np.float32)
    matrix[0:2, 0:2] = 5
    matrix[3:5, 3:5] = 5
    result = find_best_roi(matrix, RoiSettings(width=2, height=2))
    assert (result.x, result.y) == (3, 3)


def test_stride_limits_candidate_positions() -> None:
    matrix = np.zeros((5, 5), dtype=np.float32)
    matrix[1:3, 1:3] = 100
    matrix[2:4, 2:4] = 50
    result = find_best_roi(matrix, RoiSettings(width=2, height=2, stride=2))
    assert (result.x, result.y) == (2, 2)

