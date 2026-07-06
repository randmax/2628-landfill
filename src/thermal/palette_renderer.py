from __future__ import annotations

import cv2
import numpy as np


PALETTES = {
    "grayscale": None,
    "inferno": cv2.COLORMAP_INFERNO,
    "iron": cv2.COLORMAP_JET,
    "turbo": cv2.COLORMAP_TURBO,
    "hot": cv2.COLORMAP_HOT,
}


def render_temperature(
    matrix: np.ndarray,
    palette: str = "inferno",
    scale_mode: str = "auto",
    manual_min: float | None = None,
    manual_max: float | None = None,
) -> np.ndarray:
    """Render a float32 Celsius matrix into RGB uint8 pixels."""
    valid = matrix[np.isfinite(matrix)]
    if valid.size == 0:
        return np.zeros((*matrix.shape, 3), dtype=np.uint8)
    if scale_mode == "manual" and manual_min is not None and manual_max is not None:
        low, high = manual_min, manual_max
    elif scale_mode == "percentile":
        low, high = np.percentile(valid, [2, 98])
    else:
        low, high = float(np.min(valid)), float(np.max(valid))
    if high <= low:
        high = low + 1.0
    normalized = np.clip((matrix - low) / (high - low), 0, 1)
    gray = np.nan_to_num(normalized * 255, nan=0.0).astype(np.uint8)
    cmap = PALETTES.get(palette, cv2.COLORMAP_INFERNO)
    if cmap is None:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    bgr = cv2.applyColorMap(gray, cmap)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

