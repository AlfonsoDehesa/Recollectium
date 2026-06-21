"""Memory-space key validation and database path resolution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from recollectium.errors import ValidationError

DEFAULT_MEMORY_SPACE_KEY = "default"
MAX_MEMORY_SPACE_KEY_LENGTH = 128

_MEMORY_SPACE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MANIFEST_FILENAME = "memory-spaces.json"
_MANIFEST_VERSION = 1
_SLUG_MAX_LENGTH = 48
_HASH_PREFIX_LENGTH = 12


@dataclass(frozen=True)
class MemorySpaceResolution:
    """Resolved path for a memory-space key."""

    key: str
    db_path: Path
    is_default: bool


@dataclass(frozen=True)
class MemorySpaceInfo:
    """Descriptive information about a known memory space."""

    key: str
    db_path: Path
    is_default: bool
    exists: bool
    created_at: str | None = None
    updated_at: str | None = None


def validate_memory_space_key(value: str) -> str:
    """Normalize and validate a memory-space key.

    The caller must pass a string. The returned key is stripped of leading
    and trailing whitespace.
    """

    if not isinstance(value, str):
        raise ValidationError(
            f"memory space key must be a string (got {type(value).__name__})"
        )

    normalized = value.strip()
    if not normalized:
        raise ValidationError("memory space key must not be empty or whitespace")
    if len(normalized) > MAX_MEMORY_SPACE_KEY_LENGTH:
        raise ValidationError(
            f"memory space key must be at most {MAX_MEMORY_SPACE_KEY_LENGTH} characters"
        )
    if "\x00" in normalized:
        raise ValidationError("memory space key must not contain NUL bytes")
    if "/" in normalized or "\\" in normalized:
        raise ValidationError(
            "memory space key must not contain path separators (/ or \\)"
        )
    if normalized in {".", ".."}:
        raise ValidationError("memory space key must not be '.' or '..'")
    if not _MEMORY_SPACE_KEY_RE.fullmatch(normalized):
        raise ValidationError(
            "memory space key may only contain ASCII letters, numbers, dot, underscore, hyphen, and colon, and must start with a letter or number"
        )
    return normalized


class MemorySpaceResolver:
    """Resolve memory-space keys to SQLite database files under one folder."""

    def __init__(
        self, database_folder: Path, default_key: str = DEFAULT_MEMORY_SPACE_KEY
    ) -> None:
        self.database_folder = Path(database_folder).expanduser()
        self.default_key = validate_memory_space_key(default_key)
        self._manifest_path = self.database_folder / _MANIFEST_FILENAME

    def resolve(self, memory_space_key: str | None = None) -> MemorySpaceResolution:
        """Resolve *memory_space_key* to a safe database path."""

        key = (
            self.default_key
            if memory_space_key is None
            else validate_memory_space_key(memory_space_key)
        )
        db_path = resolve_memory_space_database_path(
            self.database_folder, key, default_key=self.default_key
        )
        self.database_folder.mkdir(parents=True, exist_ok=True)
        self._update_manifest(key, db_path)
        return MemorySpaceResolution(
            key=key, db_path=db_path, is_default=key == self.default_key
        )

    def list_spaces(self) -> list[MemorySpaceInfo]:
        """Return known memory spaces recorded in the manifest."""

        manifest = self._load_manifest()
        spaces_obj = manifest.get("spaces")
        if not isinstance(spaces_obj, dict):
            raise ValidationError("memory space manifest spaces must be an object")
        infos: list[MemorySpaceInfo] = []
        for key, entry in sorted(spaces_obj.items()):
            validate_memory_space_key(key)
            if not isinstance(entry, dict):
                raise ValidationError(
                    f"memory space manifest entry for {key!r} must be an object"
                )
            filename = entry.get("filename")
            if not isinstance(filename, str):
                raise ValidationError(
                    f"memory space manifest entry for {key!r} must include a filename"
                )
            safe_filename = _validate_manifest_filename(filename)
            db_path = self.database_folder / safe_filename
            created_at = entry.get("created_at")
            updated_at = entry.get("updated_at")
            infos.append(
                MemorySpaceInfo(
                    key=key,
                    db_path=db_path,
                    is_default=key == self.default_key,
                    exists=db_path.exists(),
                    created_at=created_at if isinstance(created_at, str) else None,
                    updated_at=updated_at if isinstance(updated_at, str) else None,
                )
            )
        return infos

    def _load_manifest(self) -> dict[str, object]:
        if not self._manifest_path.exists():
            return {"version": _MANIFEST_VERSION, "spaces": {}}
        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"invalid JSON in memory space manifest {self._manifest_path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ValidationError(
                f"memory space manifest {self._manifest_path} must be a JSON object"
            )
        version = payload.get("version")
        if not isinstance(version, int) or version != _MANIFEST_VERSION:
            raise ValidationError(
                f"memory space manifest {self._manifest_path} must have version {_MANIFEST_VERSION}"
            )
        spaces = payload.get("spaces")
        if not isinstance(spaces, dict):
            raise ValidationError(
                f"memory space manifest {self._manifest_path} must contain a spaces object"
            )
        return payload

    def _update_manifest(self, key: str, db_path: Path) -> None:
        manifest = self._load_manifest()
        spaces = manifest.get("spaces")
        if not isinstance(spaces, dict):
            raise ValidationError("memory space manifest spaces must be an object")

        now = _utc_timestamp()
        entry = spaces.get(key)
        created_at = now
        if isinstance(entry, dict) and isinstance(entry.get("created_at"), str):
            created_at = entry["created_at"]
        spaces[key] = {
            "filename": db_path.name,
            "created_at": created_at,
            "updated_at": now,
        }
        manifest["version"] = _MANIFEST_VERSION
        _write_json_atomic(self._manifest_path, manifest)


def _database_filename(key: str) -> str:
    slug = _slugify(key)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:_HASH_PREFIX_LENGTH]
    return f"{slug}--{digest}.db"


def resolve_memory_space_database_path(
    database_folder: Path,
    memory_space_key: str | None = None,
    *,
    default_key: str = DEFAULT_MEMORY_SPACE_KEY,
) -> Path:
    """Return the deterministic database path for a memory-space key."""

    database_folder = Path(database_folder).expanduser()
    resolved_database_folder = database_folder.resolve(strict=False)
    key = (
        default_key
        if memory_space_key is None
        else validate_memory_space_key(memory_space_key)
    )
    db_path = (resolved_database_folder / _database_filename(key)).resolve(strict=False)
    if not db_path.is_relative_to(resolved_database_folder):
        raise ValidationError(
            "resolved memory space database path escaped the configured database folder"
        )
    return db_path


def _validate_manifest_filename(filename: str) -> str:
    path = Path(filename)
    if path.is_absolute() or path.name != filename or filename in {".", ".."}:
        raise ValidationError(
            f"memory space manifest filename must be a safe basename (got {filename!r})"
        )
    if "/" in filename or "\\" in filename or "\x00" in filename:
        raise ValidationError(
            f"memory space manifest filename must not contain path separators (got {filename!r})"
        )
    return filename


def _slugify(key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "space"
    slug = slug[:_SLUG_MAX_LENGTH].rstrip("-")
    return slug or "space"


def _utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
