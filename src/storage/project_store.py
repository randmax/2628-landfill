from __future__ import annotations

import json
from pathlib import Path

from src.models.image_record import ImageRecord


class ProjectStore:
    """JSON project persistence."""

    def save(self, path: str | Path, records: list[ImageRecord]) -> None:
        """Save project records to JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "records": [record.to_dict() for record in records]}
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str | Path) -> list[ImageRecord]:
        """Load project records from JSON."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return [ImageRecord.from_dict(item) for item in payload.get("records", [])]

