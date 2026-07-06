from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from src.models.roi_result import RoiResult, RoiSettings


def _window_sums(values: np.ndarray, window_h: int, window_w: int) -> np.ndarray:
    padded = np.pad(values, ((1, 0), (1, 0)), mode="constant", constant_values=0)
    integral = padded.cumsum(axis=0).cumsum(axis=1)
    return (
        integral[window_h:, window_w:]
        - integral[:-window_h, window_w:]
        - integral[window_h:, :-window_w]
        + integral[:-window_h, :-window_w]
    )


def find_best_roi(matrix: np.ndarray, settings: RoiSettings) -> RoiResult:
    """Megkeresi a legmelegebb érvényes ROI-t vektorizált NumPy műveletekkel."""
    if matrix.ndim != 2:
        raise ValueError("A homersekleti matrix ketdimenzios kell legyen.")
    settings.validate_for_shape(matrix.shape)

    data = matrix.astype(np.float32, copy=False)
    valid = np.isfinite(data)
    safe = np.where(valid, data, 0.0).astype(np.float64, copy=False)
    valid_f = valid.astype(np.float64)
    h, w = settings.height, settings.width

    # Átlag szerinti kereséshez integrálképet használunk, így a teljes képen való
    # végigcsúsztatás nem lassú, egymásba ágyazott Python ciklusokkal történik.
    counts = _window_sums(valid_f, h, w)
    valid_ratio = counts / float(h * w)
    candidate_mask = valid_ratio >= settings.min_valid_ratio
    if not np.any(candidate_mask):
        raise ValueError("Nincs eleg ervenyes pixelt tartalmazo ROI.")

    means = _window_sums(safe, h, w) / np.maximum(counts, 1)
    means = means[:: settings.stride, :: settings.stride]
    valid_ratio = valid_ratio[:: settings.stride, :: settings.stride]
    candidate_mask = candidate_mask[:: settings.stride, :: settings.stride]

    if settings.ranking_metric == "mean":
        scores = means
    else:
        windows = sliding_window_view(data, (h, w))[:: settings.stride, :: settings.stride]
        masked_windows = np.where(np.isfinite(windows), windows, np.nan)
        if settings.ranking_metric == "p95":
            scores = np.nanpercentile(masked_windows, 95, axis=(-2, -1))
        elif settings.ranking_metric == "max":
            scores = np.nanmax(masked_windows, axis=(-2, -1))
        else:
            raise ValueError("Ismeretlen rangsorolasi metrika.")

    scores = np.where(candidate_mask, scores, -np.inf)
    max_score = float(np.nanmax(scores))
    tied = np.argwhere(np.isclose(scores, max_score, rtol=0, atol=1e-6))
    best_y_i, best_x_i = _break_ties(data, tied, settings, max_score)
    y = int(best_y_i * settings.stride)
    x = int(best_x_i * settings.stride)

    roi = data[y : y + h, x : x + w]
    valid_roi = roi[np.isfinite(roi)]
    return RoiResult(
        x=x,
        y=y,
        width=w,
        height=h,
        mean_temperature=float(np.mean(valid_roi)),
        min_temperature=float(np.min(valid_roi)),
        max_temperature=float(np.max(valid_roi)),
        median_temperature=float(np.median(valid_roi)),
        p95_temperature=float(np.percentile(valid_roi, 95)),
        valid_pixel_ratio=float(valid_ratio[best_y_i, best_x_i]),
        ranking_metric=settings.ranking_metric,
        ranking_value=max_score,
    )


def _break_ties(
    data: np.ndarray, tied: np.ndarray, settings: RoiSettings, score: float
) -> tuple[int, int]:
    """Döntetlen esetén a nagyobb maximum, majd a képközéphez közelebbi ROI nyer."""
    image_h, image_w = data.shape
    center_y = image_h / 2.0
    center_x = image_w / 2.0
    best: tuple[float, float, int, int] | None = None
    for y_i, x_i in tied:
        y = int(y_i * settings.stride)
        x = int(x_i * settings.stride)
        roi = data[y : y + settings.height, x : x + settings.width]
        valid_roi = roi[np.isfinite(roi)]
        roi_max = float(np.max(valid_roi)) if valid_roi.size else -np.inf
        roi_cy = y + settings.height / 2.0
        roi_cx = x + settings.width / 2.0
        distance = (roi_cy - center_y) ** 2 + (roi_cx - center_x) ** 2
        key = (-roi_max, distance, y, x)
        if best is None or key < best:
            best = (key[0], key[1], y_i, x_i)
    if best is None:
        raise ValueError(f"Nincs ervenyes ROI a(z) {score} pontszamhoz.")
    return int(best[2]), int(best[3])
