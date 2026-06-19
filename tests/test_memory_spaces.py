"""Tests for memory-space resolution and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from recollectium.errors import ValidationError
from recollectium.memory_spaces import (
    DEFAULT_MEMORY_SPACE_KEY,
    MAX_MEMORY_SPACE_KEY_LENGTH,
    MemorySpaceResolver,
    validate_memory_space_key,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("default", "default"),
        ("  hermes-default-profile  ", "hermes-default-profile"),
        ("profile_01:workspace.alpha", "profile_01:workspace.alpha"),
    ],
)
def test_validate_memory_space_key_accepts_valid_values(
    value: str, expected: str
) -> None:
    assert validate_memory_space_key(value) == expected


@pytest.mark.parametrize(
    "value, message",
    [
        ("", "must not be empty"),
        ("   ", "must not be empty"),
        ("a\x00b", "must not contain NUL"),
        ("a/b", "path separators"),
        ("a\\b", "path separators"),
        (".", "must not be '.' or '..'"),
        ("..", "must not be '.' or '..'"),
        ("-leading-dash", "must start with a letter or number"),
        ("hello world", "may only contain ASCII letters"),
        ("x" * (MAX_MEMORY_SPACE_KEY_LENGTH + 1), "at most 128 characters"),
    ],
)
def test_validate_memory_space_key_rejects_invalid_values(
    value: str, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_memory_space_key(value)


def test_resolver_maps_keys_under_database_folder_and_updates_manifest(
    tmp_path: Path,
) -> None:
    resolver = MemorySpaceResolver(tmp_path / "memory-spaces")

    default_resolution = resolver.resolve()
    custom_resolution = resolver.resolve("hermes-default-profile")

    assert default_resolution.key == DEFAULT_MEMORY_SPACE_KEY
    assert default_resolution.is_default is True
    assert default_resolution.db_path.parent == resolver.database_folder
    assert default_resolution.db_path.name.startswith("default--")
    assert default_resolution.db_path.suffix == ".db"

    assert custom_resolution.key == "hermes-default-profile"
    assert custom_resolution.is_default is False
    assert custom_resolution.db_path.parent == resolver.database_folder
    assert custom_resolution.db_path.name.startswith("hermes-default-profile--")
    assert re.fullmatch(
        r"hermes-default-profile--[0-9a-f]{12}\.db", custom_resolution.db_path.name
    )

    manifest_path = resolver.database_folder / "memory-spaces.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert (
        manifest["spaces"][DEFAULT_MEMORY_SPACE_KEY]["filename"]
        == default_resolution.db_path.name
    )
    assert (
        manifest["spaces"]["hermes-default-profile"]["filename"]
        == custom_resolution.db_path.name
    )


def test_list_spaces_uses_manifest_entries(tmp_path: Path) -> None:
    resolver = MemorySpaceResolver(tmp_path / "memory-spaces")
    default_resolution = resolver.resolve()
    custom_resolution = resolver.resolve("team-workspace")

    infos = resolver.list_spaces()

    assert [info.key for info in infos] == [DEFAULT_MEMORY_SPACE_KEY, "team-workspace"]
    assert infos[0].db_path == default_resolution.db_path
    assert infos[0].is_default is True
    assert infos[0].exists is False
    assert infos[1].db_path == custom_resolution.db_path
    assert infos[1].is_default is False
    assert infos[1].exists is False
    assert all(info.created_at for info in infos)
    assert all(info.updated_at for info in infos)
