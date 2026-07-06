from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.models.image_record import RadiometricSettings
from src.models.roi_result import RoiResult, RoiSettings


class CacheStore:
    """File based per-image processing cache."""

    def __init__(self, root: str | Path = "cache") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def compute_key(
        self,
        filepath: str | Path,
        radiometry: RadiometricSettings,
        roi_settings: RoiSettings,
        sdk_version: str,
    ) -> str:
        """Compute a cache key from file stats and processing settings."""
        path = Path(filepath)
        stat = path.stat()
        payload = {
            "name": path.name,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "radiometry": radiometry.to_dict(),
            "roi": roi_settings.to_dict(),
            "sdk": sdk_version,
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def load(self, key: str) -> dict[str, Any] | None:
        """Load cached paths and ROI result if all files exist."""
        folder = self.root / key
        result_path = folder / "result.json"
        matrix_path = folder / "temperature_matrix.npy"
        if not result_path.exists() or not matrix_path.exists():
            return None
        data = json.loads(result_path.read_text(encoding="utf-8"))
        return {
            "temperature_matrix": matrix_path,
            "roi_result": RoiResult(**data["roi_result"]),
        }

    def save(self, key: str, matrix: np.ndarray, roi_result: RoiResult, source: str | Path) -> None:
        """Save matrix and ROI result under the given cache key."""
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "temperature_matrix.npy", matrix.astype(np.float32, copy=False))
        payload = {"source": str(source), "roi_result": roi_result.to_dict()}
        (folder / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear(self) -> None:
        """Delete cache contents below the cache root."""
        for child in self.root.iterdir():
            if child.is_dir():
                for item in child.iterdir():
                    item.unlink()
                child.rmdir()
            else:
                child.unlink()

