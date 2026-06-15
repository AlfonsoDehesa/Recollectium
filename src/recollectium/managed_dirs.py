"""Helpers for marking and recognizing Recollectium-created directories."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_MANAGED_DIRECTORY_MARKER = ".recollectium-managed-directory.json"


def managed_directory_marker_path(path: Path) -> Path:
    """Return the marker file path for a managed directory."""
    return path / _MANAGED_DIRECTORY_MARKER


def ensure_managed_directory(path: Path, *, purpose: str | None = None) -> bool:
    """Create *path* and persist a marker only when the directory is new."""
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if existed:
        return False

    payload: dict[str, Any] = {
        "created_by": "recollectium",
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if purpose is not None:
        payload["purpose"] = purpose
    managed_directory_marker_path(path).write_text(
        json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
    )
    return True


def directory_was_created_by_recollectium(path: Path) -> bool:
    """Return whether *path* has a valid Recollectium directory marker."""
    marker = managed_directory_marker_path(path)
    if not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("created_by") == "recollectium"
