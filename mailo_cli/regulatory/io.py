"""I/O helpers for reviewed regulatory-change fixtures."""

import json
from pathlib import Path

from .models import RegulatoryChangeSet


def load_change_set(path: str | Path) -> RegulatoryChangeSet:
    """Load and validate a reviewed regulatory change-set JSON document."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("regulatory change-set root must be a JSON object")
    return RegulatoryChangeSet.from_dict(data)
