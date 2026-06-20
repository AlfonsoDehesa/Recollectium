"""Cross-platform CI smoke coverage for the installed Recollectium CLI.

This helper exercises the installed command surface in isolated temp state so CI
can verify memory-space routing, database placement, and public CLI boundaries
without duplicating shell logic across platforms.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_CONTENT = "CI install smoke default memory"
ALT_MEMORY_CONTENT = "CI install smoke alt memory"
ALT_MEMORY_SPACE = "ci-alt"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        print("usage: ci_install_smoke.py", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(
        prefix="recollectium-install-smoke-"
    ) as smoke_root:
        _exercise_install_smoke(Path(smoke_root))
    return 0


def _resolve_recollectium_command() -> list[str]:
    command = shutil.which("recollectium")
    if command:
        return [command]

    uv = shutil.which("uv")
    if uv:
        completed = _run_command([uv, "tool", "dir", "--bin"])
        executable = Path(completed.stdout.strip()) / (
            "recollectium.exe" if os.name == "nt" else "recollectium"
        )
        if executable.exists():
            return [str(executable)]

    tool_bin_dir = os.environ.get("UV_TOOL_BIN_DIR")
    if tool_bin_dir:
        executable = Path(tool_bin_dir) / (
            "recollectium.exe" if os.name == "nt" else "recollectium"
        )
        if executable.exists():
            return [str(executable)]

    raise RuntimeError(
        "recollectium executable was not found on PATH or in the uv tool bin directory"
    )


def _run_command(
    args: list[str], *, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _smoke_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "nt":
        env.update(
            {
                "APPDATA": str(root / "appdata"),
                "LOCALAPPDATA": str(root / "localappdata"),
                "USERPROFILE": str(root / "userprofile"),
                "HOME": str(root / "home"),
                "TEMP": str(root / "temp"),
                "TMP": str(root / "temp"),
            }
        )
    else:
        env.update(
            {
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "xdg-config"),
                "XDG_DATA_HOME": str(root / "xdg-data"),
                "XDG_CACHE_HOME": str(root / "xdg-cache"),
                "XDG_STATE_HOME": str(root / "xdg-state"),
                "XDG_RUNTIME_DIR": str(root / "xdg-runtime"),
            }
        )
    return env


def _run_json(args: list[str], *, env: dict[str, str]) -> Any:
    completed = _run_command(args, env=env)
    if completed.stderr:
        raise RuntimeError(
            f"unexpected stderr from {' '.join(args)}:\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def _run_json_allow_failure(
    args: list[str], *, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    completed = _run_command(args, env=env, check=False)
    if completed.stdout:
        raise RuntimeError(
            f"unexpected stdout from {' '.join(args)}:\n{completed.stdout}"
        )
    return completed


def _exercise_install_smoke(root: Path) -> None:
    env = _smoke_env(root)
    recollectium = _resolve_recollectium_command()

    config_path = root / "config" / "config.json"
    database_folder = root / "database"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    database_folder.mkdir(parents=True, exist_ok=True)
    config_payload = {
        "version": 1,
        "database": {
            "folder": str(database_folder),
            "default_memory_space": "default",
        },
    }
    config_path.write_text(
        json.dumps(config_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    default_add = _run_json(
        [
            *recollectium,
            "--config",
            str(config_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            DEFAULT_MEMORY_CONTENT,
            "--json",
        ],
        env=env,
    )
    alt_add = _run_json(
        [
            *recollectium,
            "--config",
            str(config_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            ALT_MEMORY_CONTENT,
            "--memory-space",
            ALT_MEMORY_SPACE,
            "--json",
        ],
        env=env,
    )

    assert default_add["status"] == "saved", default_add
    assert alt_add["status"] == "saved", alt_add

    default_search = _run_json(
        [
            *recollectium,
            "--config",
            str(config_path),
            "search-user",
            DEFAULT_MEMORY_CONTENT,
            "--type",
            "fact",
            "--json",
        ],
        env=env,
    )
    assert len(default_search) == 1, default_search
    assert default_search[0]["content"] == DEFAULT_MEMORY_CONTENT, default_search
    assert default_search[0]["id"] == default_add["id"], default_search

    alt_search = _run_json(
        [
            *recollectium,
            "--config",
            str(config_path),
            "search-user",
            ALT_MEMORY_CONTENT,
            "--type",
            "fact",
            "--memory-space",
            ALT_MEMORY_SPACE,
            "--json",
        ],
        env=env,
    )
    assert len(alt_search) == 1, alt_search
    assert alt_search[0]["content"] == ALT_MEMORY_CONTENT, alt_search
    assert alt_search[0]["id"] == alt_add["id"], alt_search

    db_status = _run_json(
        [
            *recollectium,
            "--config",
            str(config_path),
            "db-status",
            "--memory-space",
            ALT_MEMORY_SPACE,
            "--json",
            "--verbose",
        ],
        env=env,
    )
    assert db_status["memory_space_key"] == ALT_MEMORY_SPACE, db_status
    assert db_status["memory_space_is_default"] is False, db_status
    memory_space_db_path = Path(db_status["memory_space_db_path"])
    assert memory_space_db_path.is_relative_to(database_folder), db_status

    raw_db = _run_json_allow_failure(
        [*recollectium, "--db", str(root / "raw.db"), "db-status"], env=env
    )
    assert raw_db.returncode == 2, raw_db
    assert "invalid choice" in raw_db.stderr, raw_db


if __name__ == "__main__":
    raise SystemExit(main())
