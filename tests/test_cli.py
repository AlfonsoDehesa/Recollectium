"""CLI tests for Recollectium Core."""

from __future__ import annotations

import io
import json
import os
import tomllib
from copy import deepcopy
from importlib.metadata import PackageNotFoundError
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from pytest import CaptureFixture

import recollectium.cli as cli_module
from recollectium.config import (
    DEFAULTS,
    RESPONSE_VERBOSITY_COMPACT,
    RESPONSE_VERBOSITY_VERBOSE,
)
from recollectium.cli import (
    _ReembeddingProgressReporter,
    _builtin_fastembed_provider_from_config,
    _emit_failure_payload,
    _emit_success,
    _extract_cli_output_override,
    _format_human_error,
    _format_human_output,
    _format_memory,
    _resolve_output_format,
    _set_cli_output_format,
    _supports_color,
    main,
)
from recollectium.errors import (
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
    EmbeddingReadinessTimeoutError,
    MigrationError,
    RecollectiumError,
    ServiceConflictError,
    ServiceError,
    ValidationError,
)
from recollectium.models import (
    ALL_MEMORY_TYPES,
    SPACE_USER,
    SPACE_WORKSPACE,
    USER_MEMORY_TYPES,
    WORKSPACE_MEMORY_TYPES,
)
from recollectium.storage import SQLiteMemoryStore
from recollectium.core import RecollectiumCore


class FakeEmbeddingProvider:
    """Lightweight fake embedding provider for CLI workspace tests."""

    def __init__(
        self, model_name: str | None = None, *, cache_dir: str | Path | None = None
    ) -> None:
        self.model_name = model_name
        self.cache_dir = str(cache_dir) if cache_dir is not None else None
        self.embedding_profile = {
            "provider": "fake",
            "model": "fake-model",
            "dimensions": 3,
            "version": "1",
            "profile": "fake-profile-v1",
            "max_tokens": 16,
            "chunk_tokens": 4,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }

    def embed(self, text: str) -> list[float]:
        size = float(len(text))
        first = float(ord(text[0])) if text else 0.0
        return [size, first, 1.0]

    def similarity(self, first: list[float], second: list[float]) -> float:
        return sum(a * b for a, b in zip(first, second, strict=True))

    def ensure_ready(self, *, timeout_seconds: float = 60.0) -> None:
        return None


def _run_cli(
    args: list[str],
    capsys: CaptureFixture[str],
    *,
    json_by_default: bool = True,
) -> tuple[int, str, str]:
    if (
        json_by_default
        and "--json" not in args
        and "--human-readable" not in args
        and "--compact" not in args
        and "--verbose" not in args
    ):
        args = ["--json", "--verbose", *args]
    exit_code = main(args)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


def _isolate_xdg_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))


def _mark_memory_profile_stale(db_path: Path, memory_id: str) -> None:
    stale_profile = {
        **FakeEmbeddingProvider().embedding_profile,
        "profile": "stale-profile",
    }
    SQLiteMemoryStore(db_path).update_memory(memory_id, embedding_profile=stale_profile)


def _run_help(args: list[str], capsys: CaptureFixture[str]) -> str:
    with pytest.raises(SystemExit) as exc_info:
        main(args)

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def test_cli_help_documents_commands_and_flags(capsys) -> None:
    top_level_help = _run_help(["--help"], capsys)
    assert "Recollectium Core local memory CLI" in top_level_help
    assert "Human-readable output is the default" in top_level_help
    assert "--json for structured JSON" in top_level_help
    assert "follow the" in top_level_help
    assert "selected output format" in top_level_help
    assert "--version" in top_level_help
    assert "--json" in top_level_help
    assert "--human-readable" in top_level_help
    assert "initialize Recollectium config" in top_level_help
    assert "add a user or workspace memory" in top_level_help
    assert "search memories for one workspace UID" in top_level_help
    assert "embedding-status" in top_level_help
    assert "embedding-refresh" in top_level_help
    assert "embedding-jobs-clear" in top_level_help
    assert "embedding-jobs" in top_level_help
    assert "db-status" in top_level_help
    assert "dev" in top_level_help
    assert "upgrade" in top_level_help
    assert "uninstall" in top_level_help
    assert "completion" in top_level_help


def test_cli_internal_parser_helpers_reject_invalid_threshold_and_count() -> None:
    with pytest.raises(
        cli_module.argparse.ArgumentTypeError, match="must be an integer >= 0"
    ):
        cli_module._parse_non_negative_int("-1")

    with pytest.raises(
        cli_module.argparse.ArgumentTypeError,
        match="must be model_recommended_default, none, or a number between 0.0 and 1.0",
    ):
        cli_module._parse_match_threshold("oops")

    with pytest.raises(
        cli_module.argparse.ArgumentTypeError,
        match="must be model_recommended_default, none, or a number between 0.0 and 1.0",
    ):
        cli_module._parse_match_threshold("1.5")

    assert cli_module._parse_non_negative_int("0") == 0
    assert cli_module._parse_match_threshold(" none ") is None
    assert (
        cli_module._parse_match_threshold("MODEL_RECOMMENDED_DEFAULT")
        == "model_recommended_default"
    )
    assert cli_module._parse_match_threshold("0.25") == 0.25


def test_cli_memory_type_completer_prefers_known_space() -> None:
    from recollectium.cli import _memory_type_choices_for_space, _memory_type_completer

    assert _memory_type_choices_for_space("user") == USER_MEMORY_TYPES
    assert _memory_type_choices_for_space("workspace") == WORKSPACE_MEMORY_TYPES
    assert _memory_type_choices_for_space(None) == ALL_MEMORY_TYPES
    assert _memory_type_choices_for_space("unknown") == ALL_MEMORY_TYPES

    assert _memory_type_completer("", SimpleNamespace(space="user")) == list(
        USER_MEMORY_TYPES
    )
    assert _memory_type_completer("d", SimpleNamespace(space="workspace")) == [
        "decision"
    ]
    assert _memory_type_completer("f", SimpleNamespace(space=None)) == ["fact"]


def test_cli_subcommand_help_documents_commands_and_flags(capsys) -> None:
    add_help = _run_help(["add", "--help"], capsys)
    assert "User memories must not" in add_help
    assert "include --workspace-uid" in add_help
    assert "Workspace memories require --workspace-uid" in add_help
    assert "Memory space: 'user'" in add_help
    assert "inline JSON" in add_help
    assert "@path/to/file.json" in add_help
    assert "confidence score from 0.0 to 1.0" in add_help

    search_help = _run_help(["search-workspace", "--help"], capsys)
    assert "Stable workspace UID" in search_help
    assert "searched" in search_help
    assert "Defaults to 20" in search_help

    update_help = _run_help(["update", "--help"], capsys)
    assert "regenerates" in update_help
    assert "embedding" in update_help
    assert "recollectium upgrade" in update_help

    upgrade_help = _run_help(["upgrade", "--help"], capsys)
    assert "--check" in upgrade_help
    assert "--dry-run" in upgrade_help
    assert "--install-method" in upgrade_help
    assert "--version" in upgrade_help
    assert "--main" in upgrade_help
    assert "--allow-main" in upgrade_help

    archive_help = _run_help(["archive", "--help"], capsys)
    assert "not hard-deleted" in archive_help

    serve_help = _run_help(["serve", "--help"], capsys)
    assert "blocking" in serve_help
    assert "local-first" in serve_help
    assert "127.0.0.1" in serve_help
    assert "/v1" in serve_help
    assert "--host" in serve_help
    assert "--port" in serve_help

    dev_help = _run_help(["dev", "--help"], capsys)
    assert "optimize-threshold" in dev_help

    dev_eval_help = _run_help(["dev", "eval", "--help"], capsys)
    normalized_dev_eval_help = " ".join(dev_eval_help.split())
    assert (
        "This seeded development benchmark helps developers judge a model's expected "
        "retrieval performance on Recollectium-style memory tasks. No combined score "
        "is reported." in normalized_dev_eval_help
    )
    assert (
        "Exact MRR: Checks whether known exact-memory queries rank the intended seeded "
        "memory first or near the top." in normalized_dev_eval_help
    )
    assert (
        "Semantic MRR: Checks whether paraphrased queries retrieve the intended seeded "
        "memory near the top." in normalized_dev_eval_help
    )
    assert (
        "Thematic Weighted Precision@10: Checks how much of the top 10 is relevant to "
        "the requested theme, weighted by fixture relevance grades."
        in normalized_dev_eval_help
    )
    assert (
        "Thematic Weighted Recall@10: Checks how much of the theme's expected relevant "
        "set appears in the top 10, weighted by fixture relevance grades."
        in normalized_dev_eval_help
    )
    assert (
        "Ranked-set NDCG@5: Checks whether graded expected results appear in the right "
        "order near the top 5." in normalized_dev_eval_help
    )

    optimize_help = _run_help(["dev", "optimize-threshold", "--help"], capsys)
    normalized_optimize_help = " ".join(optimize_help.split())
    assert "advisory by default" in normalized_optimize_help
    assert "seeded thematic query" in normalized_optimize_help
    assert "PR1 query" not in normalized_optimize_help
    assert "Metrics:" in normalized_optimize_help
    assert (
        "Weighted precision: Checks how much of the returned set is useful"
        in normalized_optimize_help
    )
    assert (
        "Weighted recall: Checks how much of the total useful labeled set the returned set captures"
        in normalized_optimize_help
    )
    assert (
        "Weighted F-beta: Combines weighted precision and weighted recall"
        in normalized_optimize_help
    )
    assert (
        "Exposure: Checks the share of the returned set that is confuser or unrelated"
        in normalized_optimize_help
    )
    assert "lower is better" in normalized_optimize_help
    assert "--verbose also shows the threshold sweep range" in normalized_optimize_help
    assert (
        "Average returned count: Checks how many memories are returned on average per seeded query at the threshold"
        in normalized_optimize_help
    )
    assert "--write-config" in optimize_help
    assert "--format" in optimize_help
    assert "--beta" in optimize_help
    top_level_help_2 = _run_help(["--help"], capsys)
    assert "--config" in top_level_help_2
    assert "--db" in top_level_help_2

    embedding_status_help = _run_help(["embedding-status", "--help"], capsys)
    assert "built-in local FastEmbed" in embedding_status_help
    assert "BAAI/bge-base-en-v1.5" in embedding_status_help
    assert "jinaai/jina-embeddings-v2-small-en" in embedding_status_help

    embedding_jobs_help = _run_help(["embedding-jobs", "--help"], capsys)
    assert "--job-id" in embedding_jobs_help
    assert "--state" in embedding_jobs_help
    assert "--limit" in embedding_jobs_help

    embedding_refresh_help = _run_help(["embedding-refresh", "--help"], capsys)
    assert "--space" in embedding_refresh_help
    assert "--workspace-uid" in embedding_refresh_help
    assert "--include-archived" in embedding_refresh_help

    embedding_jobs_clear_help = _run_help(["embedding-jobs-clear", "--help"], capsys)
    assert "--state" in embedding_jobs_clear_help
    assert "--yes" in embedding_jobs_clear_help

    db_status_help = _run_help(["db-status", "--help"], capsys)
    assert "migration status" in db_status_help
    assert "pending" in db_status_help
    assert "schema versions" in db_status_help

    uninstall_help = _run_help(["uninstall", "--help"], capsys)
    assert "preserving memories" in uninstall_help
    assert "--purge" in uninstall_help
    assert "--yes-delete-all-recollectium-data" in uninstall_help
    assert "--dry-run" in uninstall_help

    service_discover_help = _run_help(["service", "discover", "--help"], capsys)
    assert "machine-readable connection details" in service_discover_help
    assert "without creating a config file" in service_discover_help


def test_cli_no_args_prints_help(capsys) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Recollectium Core local memory CLI" in captured.out
    assert captured.err == ""


def test_cli_parser_without_command_prints_help(monkeypatch, capsys) -> None:
    class FakeArgs:
        version = False
        command = None

    class FakeParser:
        def parse_args(self, argv: object) -> FakeArgs:
            return FakeArgs()

        def print_help(self) -> None:
            print("fake help")

    monkeypatch.setattr("recollectium.cli._build_parser", lambda: FakeParser())

    assert main(["--not-real-for-fake-parser"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "fake help\n"


def test_cli_log_level_applies_to_missing_config_fallback(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    exit_code, stdout, stderr = _run_cli(
        ["--log-level", "debug", "config", "--path"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    assert "config.json" in stdout


def test_cli_logging_falls_back_after_os_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    def _fake_setup_logging(config: object) -> None:
        calls.append(config)
        if len(calls) == 1:
            raise OSError("disk unavailable")

    monkeypatch.setattr("recollectium.cli.setup_logging", _fake_setup_logging)

    from recollectium.cli import _setup_cli_logging

    _setup_cli_logging(tmp_path / "missing.json", log_level="debug")

    assert len(calls) == 2


def test_module_entrypoint_delegates_to_cli_main(monkeypatch) -> None:
    calls: list[object] = []

    def fake_main() -> int:
        calls.append(None)
        return 7

    monkeypatch.setattr("recollectium.cli.main", fake_main)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("recollectium.__main__", run_name="__main__")

    assert exc_info.value.code == 7
    assert calls == [None]


def test_cli_serve_passes_flags_to_service_runner(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "serve.db"
    call: dict[str, object] = {}

    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        call["host"] = host
        call["port"] = port
        call["db_path"] = db_path
        call["config_path"] = config_path
        call["log_level"] = log_level

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    exit_code = main(
        [
            "--config",
            str(config_path),
            "--db",
            str(db_path),
            "--log-level",
            "debug",
            "serve",
            "--host",
            "127.0.0.2",
            "--port",
            "9001",
        ]
    )

    assert exit_code == 0
    assert call["host"] == "127.0.0.2"
    assert call["port"] == 9001
    assert call["db_path"] == str(db_path)
    assert str(call["config_path"]) == str(config_path)
    assert call["log_level"] == "debug"


def test_cli_serve_uses_default_host_and_port_without_explicit_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call: dict[str, object] = {}

    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        call["host"] = host
        call["port"] = port
        call["db_path"] = db_path
        call["config_path"] = config_path
        call["log_level"] = log_level

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

    exit_code = main(["serve"])

    assert exit_code == 0
    assert call["host"] == "127.0.0.1"
    assert call["port"] == 8765
    assert call["db_path"] is None
    assert call["config_path"] is None
    assert call["log_level"] is None
    assert (tmp_path / "config" / "recollectium" / "config.json").exists()


def test_cli_serve_explicit_missing_config_fails_clearly(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        raise AssertionError("run_service should not run with a missing config")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)
    config_path = tmp_path / "missing" / "config.json"

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "serve"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"config file not found: {config_path}" in stderr

    with pytest.raises(AssertionError, match="missing config"):
        _fake_run_service(
            host="127.0.0.1",
            port=8765,
            db_path=None,
            config_path=str(config_path),
            log_level=None,
        )


def test_cli_serve_invalid_config_fails_clearly(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        raise AssertionError("run_service should not run with invalid config")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)
    config_path = tmp_path / "config.json"
    config_path.write_text('{"version": 1, "service": {"port": "bad"}}')

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "serve"], capsys
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError:" in stderr
    assert "service.port must be int" in stderr

    with pytest.raises(AssertionError, match="invalid config"):
        _fake_run_service(
            host="127.0.0.1",
            port=8765,
            db_path=None,
            config_path=str(config_path),
            log_level=None,
        )


def test_cli_serve_explicit_missing_config_fails_after_flag_overrides(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "missing" / "config.json"

    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        raise FileNotFoundError(f"config file not found: {config_path}")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "serve",
            "--host",
            "127.0.0.2",
            "--port",
            "9001",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"config file not found: {config_path}" in stderr


def test_cli_serve_invalid_config_fails_after_flag_overrides(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"

    def _fake_run_service(
        *,
        host: str,
        port: int,
        db_path: str | None,
        config_path: str | None,
        log_level: str | None,
        cli_structured_errors: bool = False,
    ) -> None:
        raise ValidationError("invalid JSON in config file")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "serve",
            "--host",
            "127.0.0.2",
            "--port",
            "9001",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError: invalid JSON in config file" in stderr


def test_cli_first_run_without_config_creates_default_config(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "first-run.db"), "list", "--limit", "1"], capsys
    )

    config_path = config_home / "recollectium" / "config.json"
    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout) == []
    assert json.loads(config_path.read_text(encoding="utf-8")) == DEFAULTS


def test_cli_explicit_missing_config_fails_for_normal_command(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    config_path = tmp_path / "missing" / "config.json"

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "--db",
            str(tmp_path / "explicit-missing.db"),
            "list",
            "--limit",
            "1",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"config file not found: {config_path}" in stderr


def test_cli_human_search_emits_reembedding_progress_to_stderr(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )
    db_path = tmp_path / "human-search-progress.db"

    add_code, add_out, add_err = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            SPACE_USER,
            "--type",
            "fact",
            "--content",
            "Hermes prefers live re-embedding progress",
        ],
        capsys,
    )
    assert add_code == 0
    assert add_err == ""
    memory_id = json.loads(add_out)["id"]
    _mark_memory_profile_stale(db_path, memory_id)

    search_code, search_out, search_err = _run_cli(
        [
            "--human-readable",
            "--db",
            str(db_path),
            "search-user",
            "live progress",
        ],
        capsys,
        json_by_default=False,
    )

    assert search_code == 0
    assert "1 result" in search_out
    assert "\r\x1b[2K" in search_err
    assert search_err.endswith("\r\x1b[2K")
    assert "Re-embedding" in search_err
    assert "1/1" in search_err
    assert "Status:" not in search_err
    assert "\n" not in search_err


def test_cli_human_embedding_refresh_emits_reembedding_progress_to_stderr(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )
    db_path = tmp_path / "human-refresh-progress.db"

    add_code, add_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            SPACE_USER,
            "--type",
            "fact",
            "--content",
            "Refresh stale embedding explicitly",
        ],
        capsys,
    )
    assert add_code == 0
    memory_id = json.loads(add_out)["id"]
    _mark_memory_profile_stale(db_path, memory_id)

    refresh_code, refresh_out, refresh_err = _run_cli(
        [
            "--human-readable",
            "--db",
            str(db_path),
            "embedding-refresh",
            "--space",
            SPACE_USER,
        ],
        capsys,
        json_by_default=False,
    )

    assert refresh_code == 0
    assert "Embedding refresh" in refresh_out
    assert "\r\x1b[2K" in refresh_err
    assert refresh_err.endswith("\r\x1b[2K")
    assert "Re-embedding" in refresh_err
    assert "1/1" in refresh_err
    assert "Status:" not in refresh_err
    assert "\n" not in refresh_err


def test_cli_json_search_reembedding_remains_parse_safe(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )
    db_path = tmp_path / "json-search-progress.db"

    add_code, add_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            SPACE_USER,
            "--type",
            "fact",
            "--content",
            "JSON output must stay parse-safe during refresh",
        ],
        capsys,
    )
    assert add_code == 0
    memory_id = json.loads(add_out)["id"]
    _mark_memory_profile_stale(db_path, memory_id)

    search_code, search_out, search_err = _run_cli(
        ["--db", str(db_path), "search-user", "parse-safe"],
        capsys,
    )

    assert search_code == 0
    payload = json.loads(search_out)
    assert payload[0]["memory"]["id"] == memory_id
    assert "Re-embedding memories" not in search_out
    assert "Re-embedding memories" not in search_err


def test_cli_human_workspace_search_emits_reembedding_progress_to_stderr(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )
    db_path = tmp_path / "human-workspace-search-progress.db"

    add_code, add_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            SPACE_WORKSPACE,
            "--workspace-uid",
            "recollectium",
            "--type",
            "fact",
            "--content",
            "Workspace search should show live re-embedding progress",
        ],
        capsys,
    )
    assert add_code == 0
    memory_id = json.loads(add_out)["id"]
    _mark_memory_profile_stale(db_path, memory_id)

    search_code, search_out, search_err = _run_cli(
        [
            "--human-readable",
            "--db",
            str(db_path),
            "search-workspace",
            "live progress",
            "--workspace-uid",
            "recollectium",
        ],
        capsys,
        json_by_default=False,
    )

    assert search_code == 0
    assert "1 result" in search_out
    assert "\r\x1b[2K" in search_err
    assert search_err.endswith("\r\x1b[2K")
    assert "Re-embedding" in search_err
    assert "1/1" in search_err
    assert "Status:" not in search_err
    assert "\n" not in search_err


class _OSErrorIsattyStream(io.StringIO):
    def isatty(self) -> bool:
        raise OSError("isatty unavailable")


def test_reembedding_progress_reporter_handles_isatty_errors() -> None:
    stream = _OSErrorIsattyStream()
    reporter = _ReembeddingProgressReporter(stream)

    with reporter:
        reporter(
            {
                "event": "failed",
                "reason": "search",
                "model": "fake-model",
                "total": 2,
                "processed": 1,
                "succeeded": 0,
                "failed": 1,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Re-embedding" in output
    assert "1/2" in output


def test_reembedding_progress_reporter_uses_single_line_for_tty() -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined,method-assign]
    reporter = _ReembeddingProgressReporter(stream)

    with reporter:
        reporter(
            {
                "event": "started",
                "reason": "force-refresh",
                "model": "fake-model",
                "total": 2,
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
            }
        )
        reporter(
            {
                "event": "progress",
                "reason": "force-refresh",
                "model": "fake-model",
                "total": 2,
                "processed": 1,
                "succeeded": 1,
                "failed": 0,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Re-embedding" in output
    assert "1/2" in output


def test_dev_eval_progress_reporter_handles_isatty_errors() -> None:
    stream = _OSErrorIsattyStream()
    reporter = cli_module._DevEvalProgressReporter(stream, min_render_interval=0)

    with reporter:
        reporter.phase("Checking embedding provider readiness")
        reporter(
            {
                "phase": "semantic_mrr",
                "bucket": "paraphrases",
                "label": "Semantic MRR paraphrases",
                "completed": 1,
                "total": 2,
            }
        )
        reporter(
            {
                "label": "Results phase",
                "completed": 0,
                "total": 0,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.count("\r") == 4
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "Checking" in output
    assert "Semantic" in output
    assert "1/2" in output
    assert "Results" in output


def test_live_progress_title_limit_returns_none_when_terminal_size_errors(
    monkeypatch,
) -> None:
    def raise_terminal_size_error(
        fallback: tuple[int, int],
    ) -> os.terminal_size:
        raise OSError("terminal size unavailable")

    monkeypatch.setattr(
        cli_module.shutil,
        "get_terminal_size",
        raise_terminal_size_error,
    )

    assert cli_module._live_progress_title_limit(io.StringIO()) is None


def test_live_progress_title_limit_returns_none_for_narrow_terminal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((59, 24)),
    )

    assert cli_module._live_progress_title_limit(io.StringIO()) is None


def test_compact_live_title_returns_untrimmed_label_within_limit() -> None:
    assert cli_module._compact_live_title("Short label", 20) == "Short label"
    assert cli_module._compact_live_title("Long label", 6) == "Long…"


def test_dev_eval_progress_reporter_uses_dynamic_line_for_narrow_terminal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((59, 24)),
    )
    stream = io.StringIO()
    reporter = cli_module._DevEvalProgressReporter(stream, min_render_interval=0)

    with reporter:
        reporter(
            {
                "label": "Exact MRR workspace memories",
                "completed": 49,
                "total": 90,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.count("\r") == 2
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "Exact MRR: workspace" in output
    assert "…" not in output
    assert "49/90" in output


def test_dev_eval_progress_reporter_keeps_curated_labels_whole_on_narrow_terminal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_module.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((59, 24)),
    )
    stream = io.StringIO()
    reporter = cli_module._DevEvalProgressReporter(stream, min_render_interval=0)

    with reporter:
        reporter.phase("Checking embedding provider readiness")
        reporter.phase("Preparing seeded development database")
        reporter.phase("Loading eval fixtures")
        reporter(
            {
                "label": "Exact MRR workspace memories",
                "completed": 49,
                "total": 90,
            }
        )
        reporter(
            {
                "label": "Thematic weighted workspace themes",
                "completed": 6,
                "total": 12,
            }
        )
        reporter(
            {
                "label": "Ranked-set NDCG@5 cases",
                "completed": 3,
                "total": 5,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Checking provider" in output
    assert "Preparing dev DB" in output
    assert "Loading fixtures" in output
    assert "Exact MRR: workspace" in output
    assert "Thematic metrics: workspace" in output
    assert "NDCG@5" in output
    assert "…" not in output


def test_dev_eval_progress_reporter_non_tty_label_uses_dynamic_line() -> None:
    """Captured non-TTY output should not emit one Status line per event."""
    stream = io.StringIO()
    reporter = cli_module._DevEvalProgressReporter(stream)

    with reporter:
        reporter(
            {
                "label": "Results phase",
                "completed": 0,
                "total": 0,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert output.count("\r") == 2
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "Results phase" in output
    assert "Status:" not in output


def test_dev_eval_progress_reporter_throttles_and_dedupes_high_frequency_updates() -> (
    None
):
    now = [0.0]

    def clock() -> float:
        return now[0]

    stream = io.StringIO()
    reporter = cli_module._DevEvalProgressReporter(
        stream,
        clock=clock,
        min_render_interval=0.25,
    )

    with reporter:
        first_event = {
            "label": "Semantic MRR paraphrases",
            "completed": 1,
            "total": 10,
        }
        reporter(first_event)
        now[0] = 0.3
        reporter(first_event)
        for completed in range(2, 10):
            reporter(
                {
                    "label": "Semantic MRR paraphrases",
                    "completed": completed,
                    "total": 10,
                }
            )
        reporter(
            {
                "label": "Semantic MRR paraphrases",
                "completed": 10,
                "total": 10,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.count("\r") == 4
    assert output.count("\x1b[2K") == 1
    assert output.count("1/10") == 1
    assert "10/10" in output
    assert "100% 10/10" in output
    assert output.endswith("\r\x1b[2K")


def test_dev_eval_progress_reporter_forces_first_count_after_phase() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    stream = io.StringIO()
    reporter = cli_module._DevEvalProgressReporter(
        stream,
        clock=clock,
        min_render_interval=0.25,
    )

    with reporter:
        reporter.phase("Preparing seeded development database")
        reporter(
            {
                "label": "Exact MRR user memories",
                "completed": 1,
                "total": 100,
            }
        )
        reporter(
            {
                "label": "Exact MRR user memories",
                "completed": 2,
                "total": 100,
            }
        )
        reporter(
            {
                "label": "Exact MRR user memories",
                "completed": 100,
                "total": 100,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert output.count("\r") == 4
    assert "Preparing dev DB" in output
    assert "1/100" in output
    assert "2/100" not in output
    assert "100% 100/100" in output
    assert output.endswith("\r\x1b[2K")


def test_dev_eval_progress_reporter_format_line_renders_full_bar_at_width() -> None:
    reporter = cli_module._DevEvalProgressReporter(io.StringIO())

    line = reporter._format_line("Finished", 100, 3, 3)

    assert "100% 3/3" in line
    assert "╺" not in line


def test_dev_eval_progress_reporter_bar_width_uses_fallback_when_terminal_size_errors(
    monkeypatch,
) -> None:
    def raise_terminal_size_error(
        fallback: tuple[int, int],
    ) -> os.terminal_size:
        raise OSError("terminal size unavailable")

    monkeypatch.setattr(
        cli_module.shutil,
        "get_terminal_size",
        raise_terminal_size_error,
    )
    reporter = cli_module._DevEvalProgressReporter(io.StringIO())

    assert reporter._bar_width("Short label", 1, 2) == 30


def test_dev_eval_progress_reporter_renders_single_tty_line_and_clears() -> None:
    class FakeTTYStream(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = FakeTTYStream()
    reporter = cli_module._DevEvalProgressReporter(stream, min_render_interval=0)

    with reporter:
        reporter.phase("Checking embedding provider readiness")
        reporter.phase("Preparing seeded development database")
        reporter(
            {
                "label": "Exact MRR user memories",
                "completed": 50,
                "total": 100,
            }
        )
        reporter(
            {
                "label": "Semantic MRR paraphrases",
                "completed": 570,
                "total": 570,
            }
        )
        reporter.phase("Loading eval fixtures")
        reporter(
            {
                "label": "Results phase",
                "completed": 0,
                "total": 0,
            }
        )
        reporter(
            {
                "label": "Start phase",
                "completed": 0,
                "total": 1,
            }
        )

    output = stream.getvalue()
    assert "\n" not in output
    assert output.count("\r") == 8
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "Exact MRR: user" in output
    assert "Semantic MRR" in output
    assert "50/100" in output
    completed_line = next(line for line in output.split("\r") if "Semantic MRR" in line)
    assert "100% 570/570" in completed_line
    assert "╺" not in completed_line
    assert "570/570" in output
    assert "Status:" not in output


def test_emit_human_progress_writes_status_line_and_flushes(monkeypatch) -> None:
    class FakeStdout(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.flushed = False

        def flush(self) -> None:
            self.flushed = True

    stream = FakeStdout()
    monkeypatch.setattr(cli_module.sys, "stdout", stream)

    cli_module._emit_human_progress("Checking embedding provider readiness")

    assert stream.getvalue() == "Status: Checking embedding provider readiness\n"
    assert stream.flushed is True


def test_dev_eval_progress_reporter_uses_one_dynamic_tty_line_across_updates() -> None:
    class FakeTTYStream(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = FakeTTYStream()
    reporter = cli_module._DevEvalProgressReporter(stream, min_render_interval=0)

    with reporter:
        reporter.phase("Checking embedding provider readiness")
        reporter.phase("Preparing seeded development database")
        reporter(
            {
                "label": "Exact MRR user memories",
                "completed": 50,
                "total": 100,
            }
        )
        reporter(
            {
                "label": "Semantic MRR paraphrases",
                "completed": 570,
                "total": 570,
            }
        )
        reporter.phase("Loading eval fixtures")

    output = stream.getvalue()
    assert "\n" not in output
    assert output.count("\r") == 6
    assert output.count("\x1b[2K") == 1
    assert output.endswith("\r\x1b[2K")
    assert "Checking provider" in output
    assert "Preparing dev DB" in output
    assert "Loading fixtures" in output


def test_cli_full_workflow(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )
    db_path = tmp_path / "cli.db"

    add_user_code, add_user_out, add_user_err = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "user",
            "--type",
            "preference",
            "--content",
            "I like short answers",
            "--metadata",
            '{"priority": "high"}',
        ],
        capsys,
    )
    assert add_user_code == 0
    assert add_user_err == ""
    user_memory = json.loads(add_user_out)
    user_memory_id = user_memory["id"]

    add_workspace_code, add_workspace_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "workspace",
            "--workspace-uid",
            "ws-123",
            "--type",
            "note",
            "--content",
            "The gearbox fails under load",
        ],
        capsys,
    )
    assert add_workspace_code == 0
    workspace_memory = json.loads(add_workspace_out)
    workspace_memory_id = workspace_memory["id"]

    search_user_code, search_user_out, _ = _run_cli(
        ["--db", str(db_path), "search-user", "short answers", "--limit", "5"],
        capsys,
    )
    assert search_user_code == 0
    search_user_payload = json.loads(search_user_out)
    assert len(search_user_payload) == 1
    assert search_user_payload[0]["memory"]["id"] == user_memory_id

    search_workspace_code, search_workspace_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "search-workspace",
            "mechanical stress issue",
            "--workspace-uid",
            "ws-123",
        ],
        capsys,
    )
    assert search_workspace_code == 0
    search_workspace_payload = json.loads(search_workspace_out)
    assert len(search_workspace_payload) == 1
    assert search_workspace_payload[0]["memory"]["id"] == workspace_memory_id

    list_code, list_out, _ = _run_cli(
        ["--db", str(db_path), "list", "--space", "workspace", "--limit", "10"],
        capsys,
    )
    assert list_code == 0
    list_payload = json.loads(list_out)
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == workspace_memory_id

    get_code, get_out, _ = _run_cli(
        ["--db", str(db_path), "get", user_memory_id], capsys
    )
    assert get_code == 0
    get_payload = json.loads(get_out)
    assert get_payload["id"] == user_memory_id

    update_code, update_out, _ = _run_cli(
        [
            "--db",
            str(db_path),
            "update",
            user_memory_id,
            "--content",
            "I prefer concise responses",
            "--confidence",
            "0.9",
        ],
        capsys,
    )
    assert update_code == 0
    update_payload = json.loads(update_out)
    assert update_payload["content"] == "I prefer concise responses"
    assert update_payload["confidence"] == 0.9

    archive_code, archive_out, _ = _run_cli(
        ["--db", str(db_path), "archive", user_memory_id],
        capsys,
    )
    assert archive_code == 0
    archive_payload = json.loads(archive_out)
    assert archive_payload["status"] == "archived"


def test_cli_reads_metadata_from_json_file(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli-file-metadata.db"
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"origin": "file"}', encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "file metadata memory",
            "--metadata",
            f"@{metadata_path}",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["metadata"] == {"origin": "file"}


def test_cli_db_status_reports_migration_state(tmp_path, capsys) -> None:
    db_path = tmp_path / "db-status.db"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "db-status"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["db_path"] == str(db_path)
    assert payload["current_version"] == 3
    assert payload["latest_version"] == 3
    assert payload["pending_versions"] == []
    assert payload["up_to_date"] is True


def test_cli_dev_help_documents_actions(capsys) -> None:
    dev_help = _run_help(["dev", "--help"], capsys)
    assert "seeded development" in dev_help
    assert "true" in dev_help
    assert "false" in dev_help
    assert "reset" in dev_help
    assert "eval" in dev_help

    eval_help = _run_help(["dev", "eval", "--help"], capsys)
    normalized_eval_help = " ".join(eval_help.split())
    assert (
        "This seeded development benchmark helps developers judge a model's expected "
        "retrieval performance on Recollectium-style memory tasks. No combined score "
        "is reported."
    ) in normalized_eval_help
    assert (
        "Exact MRR: Checks whether known exact-memory queries rank the intended "
        "seeded memory first or near the top."
    ) in normalized_eval_help
    assert (
        "Semantic MRR: Checks whether paraphrased queries retrieve the intended "
        "seeded memory near the top."
    ) in normalized_eval_help
    assert (
        "Thematic Weighted Precision@10: Checks how much of the top 10 is relevant "
        "to the requested theme, weighted by fixture relevance grades."
    ) in normalized_eval_help
    assert (
        "Thematic Weighted Recall@10: Checks how much of the theme's expected "
        "relevant set appears in the top 10, weighted by fixture relevance grades."
    ) in normalized_eval_help
    assert (
        "Ranked-set NDCG@5: Checks whether graded expected results appear in the "
        "right order near the top 5."
    ) in normalized_eval_help


def test_cli_dev_reset_resets_configured_seed_database(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "reset"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["database"] == str(dev_db)
    assert payload["user_memories"] == 100
    assert payload["workspace_memories"] == 90
    assert payload["workspaces"] == 3
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_true_and_false_switch_database_without_touching_regular_db(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "true"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "enabled"
    assert payload["use_seeded_database"] is True
    assert payload["database"] == str(dev_db)
    assert payload["workspace_memories"] == 90
    assert dev_db.exists()
    assert not regular_db.exists()
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert loaded["development"]["use_seeded_database"] is True

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "false"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload == {
        "status": "disabled",
        "use_seeded_database": False,
        "database": str(regular_db),
    }
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert loaded["development"]["use_seeded_database"] is False
    assert not regular_db.exists()


def test_cli_dev_eval_json_reports_all_metrics_without_touching_regular_db(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    assert payload["database"] == str(dev_db)
    assert payload["regular_database"] == str(regular_db)
    assert payload["regular_database_not_touched"] is True
    assert payload["preparation"]["seeded_database"] == "reset"
    assert payload["preparation"]["fixtures"] == "loaded"
    assert set(payload["metrics"]) == {
        "exact_mrr",
        "semantic_mrr",
        "thematic_weighted_precision_at_10",
        "thematic_weighted_recall_at_10",
        "ranked_set_ndcg_at_5",
    }
    assert "combined_score" not in payload
    assert "combined_score" not in payload["metrics"]
    assert payload["metrics"]["exact_mrr"]["targets"] == 190
    assert payload["metrics"]["exact_mrr"]["hit_at_1"] >= 0.0
    assert payload["metrics"]["exact_mrr"]["hit_at_3"] >= 0.0
    assert payload["metrics"]["semantic_mrr"]["queries"] == 570
    assert payload["metrics"]["thematic_weighted_precision_at_10"]["groups"] == 19
    assert payload["metrics"]["thematic_weighted_precision_at_10"]["limit"] == 10
    assert (
        payload["metrics"]["thematic_weighted_precision_at_10"]["protected_minimum"]
        == 0
    )
    assert (
        payload["metrics"]["thematic_weighted_precision_at_10"]["match_threshold"]
        == 0.0
    )
    assert payload["metrics"]["thematic_weighted_recall_at_10"]["groups"] == 19
    assert payload["metrics"]["ranked_set_ndcg_at_5"]["cases"] >= 12
    assert set(payload["diagnostics"]) == {
        "worst_exact",
        "worst_semantic",
        "worst_thematic",
        "worst_ranked_sets",
        "confusers",
    }
    assert "Status:" not in stdout
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_eval_human_output_defaults_to_concise_progress(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "eval", "--human-readable"],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert "\r\x1b[2K" in stderr
    assert stderr.endswith("\r\x1b[2K")
    assert "\n" not in stderr
    assert "Checking provider" in stderr
    assert "Preparing dev DB" in stderr
    assert "Exact MRR: workspace" in stderr
    assert "Thematic metrics: workspace" in stderr
    assert "NDCG@5" in stderr
    assert "…" not in stderr
    assert str(dev_db) not in stderr
    assert "Status:" not in stderr
    assert "Status: Checking embedding provider readiness" not in stdout
    assert "1/100" in stderr
    assert "90/90" in stderr
    assert "570/570" in stderr
    assert "1/10" in stderr
    assert "1/9" in stderr
    assert "15/15" in stderr
    assert "Seeded dev DB:" not in stdout
    assert "Regular DB:" not in stdout
    assert "Diagnostics" not in stdout
    assert "Results" not in stdout
    assert "Exact MRR: 0.063" in stdout
    assert "Semantic MRR: 0.061" in stdout
    assert "Thematic Weighted Precision@10: 0.281" in stdout
    assert "Thematic Weighted Recall@10: 0.211" in stdout
    assert "Ranked-set NDCG@5: 0.103" in stdout
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_eval_human_output_verbose_progress_uses_concise_label(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "--human-readable",
            "--verbose",
            "dev",
            "eval",
        ],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert "\r\x1b[2K" in stderr
    assert stderr.endswith("\r\x1b[2K")
    assert "Status:" not in stderr
    assert "Preparing dev DB" in stderr
    assert "Preparing seeded" not in stderr
    assert "…" not in stderr
    assert str(dev_db) not in stderr
    assert "Recollectium dev eval" in stdout
    assert f"Seeded dev DB: {dev_db}" in stdout


def test_cli_dev_eval_human_output_compact_hides_verbose_sections() -> None:
    output = _format_human_output(
        {
            "status": "ok",
            "database": "/tmp/dev.db",
            "regular_database": "/tmp/regular.db",
            "regular_database_not_touched": True,
            "preparation": {"seeded_database": "ready", "fixtures": "loaded"},
            "phases": {
                "exact_mrr": {
                    "user_memories": 1,
                    "workspace_memories": 1,
                    "total": 2,
                },
                "semantic_mrr": {"paraphrases": 6, "targets": 2},
                "thematic_weighted_at_10": {
                    "user_topics": 1,
                    "workspace_themes": 1,
                    "queries": 6,
                },
                "ranked_set_ndcg_at_5": {"cases": 2},
            },
            "metrics": {
                "exact_mrr": {"value": 1.0},
                "semantic_mrr": {"value": 1.0},
                "thematic_weighted_precision_at_10": {
                    "value": 1.0,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "thematic_weighted_recall_at_10": {
                    "value": 1.0,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "ranked_set_ndcg_at_5": {"value": 1.0},
            },
            "diagnostics": {
                "worst_exact": [],
                "worst_semantic": [],
                "worst_thematic": [],
                "worst_ranked_sets": [],
                "confusers": [],
            },
        },
        command="dev eval",
        response_verbosity=RESPONSE_VERBOSITY_COMPACT,
    )

    assert output.startswith("\nRecollectium dev eval\n  Exact MRR")
    assert "\nRecollectium dev eval\n\n" not in output
    assert "Exact MRR" in output
    assert "Semantic MRR" in output
    assert "Thematic Weighted Precision@10" in output
    assert "Thematic Weighted Recall@10" in output
    assert "Ranked-set NDCG@5" in output
    assert "Seeded dev DB" not in output
    assert "Regular DB" not in output
    assert "Preparing seeded development database" not in output
    assert "Loading eval fixtures" not in output
    assert "Results" not in output
    assert "Diagnostics" not in output
    assert "Worst exact target" not in output
    assert output.endswith("\n\n")


def test_cli_dev_eval_human_output_verbose_preserves_details() -> None:
    output = _format_human_output(
        {
            "status": "ok",
            "database": "/tmp/dev.db",
            "regular_database": "/tmp/regular.db",
            "regular_database_not_touched": True,
            "preparation": {"seeded_database": "ready", "fixtures": "loaded"},
            "phases": {
                "exact_mrr": {"user_memories": 1, "workspace_memories": 1, "total": 2},
                "semantic_mrr": {"paraphrases": 6, "targets": 2},
                "thematic_weighted_at_10": {
                    "user_topics": 1,
                    "workspace_themes": 1,
                    "queries": 6,
                },
                "ranked_set_ndcg_at_5": {"cases": 2},
            },
            "metrics": {
                "exact_mrr": {"value": 0.5},
                "semantic_mrr": {"value": 0.5},
                "thematic_weighted_precision_at_10": {
                    "value": 0.4,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "thematic_weighted_recall_at_10": {
                    "value": 0.6,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "ranked_set_ndcg_at_5": {"value": 0.3},
            },
            "diagnostics": {
                "worst_exact": [],
                "worst_semantic": [],
                "worst_thematic": [
                    {
                        "expected_group": "project_planning",
                        "weighted_precision": 0.2,
                        "weighted_recall": 0.3,
                        "returned_count": 2,
                        "query_index": 1,
                        "query": "planning q",
                    }
                ],
                "worst_ranked_sets": [
                    {
                        "case_id": "ranked-case",
                        "ndcg": 0.25,
                        "expected_memories": [
                            {"memory_id": "expected-a", "grade": 3},
                            {"memory_id": "expected-b", "grade": 2},
                        ],
                        "returned_top": [
                            {"memory_id": "actual-x", "grade": 0},
                            {"memory_id": "expected-b", "grade": 2},
                        ],
                    }
                ],
                "confusers": [],
            },
        },
        command="dev eval",
        response_verbosity=RESPONSE_VERBOSITY_VERBOSE,
    )

    assert "Seeded dev DB: /tmp/dev.db" in output
    assert "Regular DB: /tmp/regular.db" in output
    assert "Regular DB not touched: yes" in output
    assert "Preparing seeded development database... ready" in output
    assert "Loading eval fixtures... loaded" in output
    assert "Results" in output
    assert "Diagnostics" in output
    assert "Worst exact: none" in output
    assert "Worst semantic: none" in output
    assert "Worst thematic" in output
    assert "Expected group: project_planning" in output
    assert "Weighted precision: 0.2" in output
    assert "Case id: ranked-case" in output
    assert "Memory id: expected-a" in output
    assert "Memory id: actual-x" in output
    assert "Running exact MRR" not in output
    assert "Running semantic MRR" not in output
    assert "Running thematic weighted metrics" not in output
    assert "Running ranked-set NDCG@5" not in output
    assert output.endswith("\n\n")


def test_cli_dev_eval_human_output_verbose_includes_diagnostics_and_fallbacks() -> None:
    output = _format_human_output(
        {
            "status": "ok",
            "database": "/tmp/dev.db",
            "regular_database": "/tmp/regular.db",
            "regular_database_not_touched": True,
            "preparation": {"seeded_database": "ready", "fixtures": "loaded"},
            "phases": {
                "exact_mrr": {
                    "user_memories": 1,
                    "workspace_memories": 1,
                    "total": 2,
                },
                "semantic_mrr": {"paraphrases": 6, "targets": 2},
                "thematic_weighted_at_10": {
                    "user_topics": 1,
                    "workspace_themes": 1,
                    "queries": 6,
                },
                "ranked_set_ndcg_at_5": {"cases": 2},
            },
            "metrics": {
                "exact_mrr": {"value": 0.5},
                "semantic_mrr": {"value": 0.5},
                "thematic_weighted_precision_at_10": {
                    "value": 0.4,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "thematic_weighted_recall_at_10": {
                    "value": 0.6,
                    "limit": 10,
                    "protected_minimum": 0,
                    "match_threshold": 0.0,
                },
                "ranked_set_ndcg_at_5": {"value": 0.3},
            },
            "diagnostics": {
                "worst_exact": [
                    {"target_id": "exact-1", "rank": None},
                ],
                "worst_semantic": [
                    {
                        "target_id": "semantic-1",
                        "average_reciprocal_rank": 0.25,
                    }
                ],
                "worst_thematic": [],
                "worst_ranked_sets": [],
                "confusers": [],
            },
        },
        command="dev eval",
        response_verbosity=RESPONSE_VERBOSITY_VERBOSE,
    )

    assert "Diagnostics" in output
    assert "Target id: exact-1" in output
    assert "Target id: semantic-1" in output
    assert "Average reciprocal rank: 0.25" in output
    assert "Worst thematic: none" in output
    assert "Worst ranked sets: none" in output


def test_cli_dev_eval_human_progress_omits_reembedding_progress_when_unavailable(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)
    monkeypatch.setattr(
        cli_module, "_human_reembedding_progress_reporter", lambda _: None
    )

    seen: dict[str, Any] = {}

    def fake_run_seeded_dev_eval(*args: object, **kwargs: object) -> dict[str, object]:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return {
            "status": "ok",
            "database": str(dev_db),
            "regular_database": str(regular_db),
            "preparation": {"seeded_database": "ready", "fixtures": "loaded"},
            "metrics": {
                "exact_mrr": {"value": 0.1},
                "semantic_mrr": {"value": 0.2},
                "thematic_weighted_precision_at_10": {"value": 0.3},
                "thematic_weighted_recall_at_10": {"value": 0.4},
                "ranked_set_ndcg_at_5": {"value": 0.5},
            },
            "diagnostics": {
                "worst_exact": [],
                "worst_semantic": [],
                "worst_thematic": [],
                "worst_ranked_sets": [],
                "confusers": [],
            },
        }

    monkeypatch.setattr(cli_module, "_run_seeded_dev_eval", fake_run_seeded_dev_eval)

    exit_code, stdout, stderr = _run_cli(
        ["--human-readable", "--compact", "--config", str(config_path), "dev", "eval"],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert "Recollectium dev eval" in stdout
    assert "\r\x1b[2K" in stderr
    assert stderr.endswith("\r\x1b[2K")
    assert "Checking provider" in stderr
    assert "Status:" not in stderr
    assert seen["kwargs"]["eval_progress_reporter"] is not None
    assert "search_progress_reporter" not in seen["kwargs"]


def test_cli_dev_eval_json_progress_uses_reembedding_progress_when_available(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_xdg_dirs(tmp_path, monkeypatch)
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    class FakeReembeddingProgress:
        def __init__(self) -> None:
            self.entered = False
            self.exited = False

        def __enter__(self) -> FakeReembeddingProgress:
            self.entered = True
            return self

        def __exit__(self, *_: object) -> None:
            self.exited = True

    fake_reembedding_progress = FakeReembeddingProgress()
    monkeypatch.setattr(
        cli_module,
        "_human_reembedding_progress_reporter",
        lambda _: fake_reembedding_progress,
    )

    seen: dict[str, Any] = {}

    def fake_run_seeded_dev_eval(*args: object, **kwargs: object) -> dict[str, object]:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return {
            "status": "ok",
            "database": str(dev_db),
            "regular_database": str(regular_db),
            "preparation": {"seeded_database": "ready", "fixtures": "loaded"},
            "metrics": {
                "exact_mrr": {"value": 0.1},
                "semantic_mrr": {"value": 0.2},
                "thematic_weighted_precision_at_10": {"value": 0.3},
                "thematic_weighted_recall_at_10": {"value": 0.4},
                "ranked_set_ndcg_at_5": {"value": 0.5},
            },
            "diagnostics": {
                "worst_exact": [],
                "worst_semantic": [],
                "worst_thematic": [],
                "worst_ranked_sets": [],
                "confusers": [],
            },
        }

    monkeypatch.setattr(cli_module, "_run_seeded_dev_eval", fake_run_seeded_dev_eval)

    exit_code, stdout, stderr = _run_cli(
        ["--json", "--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 0
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    assert stderr == ""
    assert fake_reembedding_progress.entered is True
    assert fake_reembedding_progress.exited is True
    assert seen["kwargs"]["search_progress_reporter"] is fake_reembedding_progress


@pytest.mark.parametrize("output_mode", ["--json", "--human-readable"])
def test_cli_dev_eval_refuses_when_seeded_database_matches_regular_database(
    tmp_path, capsys, monkeypatch, output_mode
) -> None:
    config_path = tmp_path / "config.json"
    shared_db = tmp_path / "shared.db"
    shared_db.write_text("regular database marker", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(shared_db)},
                "development": {"seeded_database_path": str(shared_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructedShared(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructedShared
    )

    exit_code, stdout, stderr = _run_cli(
        [output_mode, "--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    if output_mode == "--json":
        payload = json.loads(stderr)
        assert payload["status"] == "unsafe_seeded_database_path"
        assert payload["seeded_database"] == str(shared_db)
        assert payload["regular_database"] == str(shared_db)
    else:
        assert "Seeded dev database path matches the regular database path." in stderr
        assert "Status: unsafe_seeded_database_path" in stderr
        assert f"Seeded database: {shared_db}" in stderr
        assert f"Regular database: {shared_db}" in stderr
    assert shared_db.read_text(encoding="utf-8") == "regular database marker"

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructedShared()


def test_cli_dev_eval_refuses_db_override_matching_seeded_database(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    configured_regular_db = tmp_path / "regular.db"
    shared_db = tmp_path / "dev.db"
    shared_db.write_text("regular database marker", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(configured_regular_db)},
                "development": {"seeded_database_path": str(shared_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructedDbOverride(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructedDbOverride
    )

    exit_code, stdout, stderr = _run_cli(
        ["--json", "--db", str(shared_db), "--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "unsafe_seeded_database_path"
    assert payload["seeded_database"] == str(shared_db)
    assert payload["regular_database"] == str(shared_db)
    assert shared_db.read_text(encoding="utf-8") == "regular database marker"
    assert not configured_regular_db.exists()

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructedDbOverride()


def test_cli_dev_eval_refuses_tilde_db_override_matching_seeded_database(
    tmp_path, capsys, monkeypatch
) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    config_path = tmp_path / "config.json"
    configured_regular_db = tmp_path / "regular.db"
    shared_db = home_dir / "shared.db"
    shared_db.write_text("regular database marker", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(configured_regular_db)},
                "development": {"seeded_database_path": str(shared_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructed(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructed
    )

    exit_code, stdout, stderr = _run_cli(
        ["--json", "--db", "~/shared.db", "--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "unsafe_seeded_database_path"
    assert payload["seeded_database"] == str(shared_db)
    assert payload["regular_database"] == str(shared_db)
    assert shared_db.read_text(encoding="utf-8") == "regular database marker"
    assert not configured_regular_db.exists()

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructed()


def test_cli_dev_eval_reports_db_override_as_regular_database(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    configured_regular_db = tmp_path / "regular.db"
    override_regular_db = tmp_path / "override.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(configured_regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "--db",
            str(override_regular_db),
            "--config",
            str(config_path),
            "dev",
            "eval",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["database"] == str(dev_db)
    assert payload["regular_database"] == str(override_regular_db)
    assert payload["regular_database_not_touched"] is True
    assert dev_db.exists()
    assert not configured_regular_db.exists()
    assert not override_regular_db.exists()


def test_cli_dev_eval_refuses_relative_regular_database_overlap(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    data_dir = tmp_path / "data"
    shared_db = data_dir / "shared.db"
    shared_db.parent.mkdir(parents=True)
    shared_db.write_text("regular database marker", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": "shared.db"},
                "directories": {"data": str(data_dir)},
                "development": {"seeded_database_path": str(shared_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructed(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructed
    )

    exit_code, stdout, stderr = _run_cli(
        ["--json", "--config", str(config_path), "dev", "eval"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "unsafe_seeded_database_path"
    assert payload["seeded_database"] == str(shared_db)
    assert payload["regular_database"] == str(shared_db)
    assert shared_db.read_text(encoding="utf-8") == "regular database marker"

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructed()


def test_cli_dev_optimize_threshold_progress_reporter_uses_single_line_and_clears() -> (
    None
):
    class FakeTTYStream(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = FakeTTYStream()
    reporter = cli_module._ThresholdOptimizationProgressReporter(stream)

    with pytest.raises(RuntimeError):
        with reporter:
            reporter.phase("Checking embedding provider readiness")
            reporter.start_scoring(2)
            reporter.advance_scoring(1, 0.5)
            reporter.phase("Writing CSV artifact: thresholds.csv")
            raise RuntimeError("boom")

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Checking provider" in output
    assert "Scoring thresholds" in output
    assert "1/2" in output
    assert "Writing CSV" in output
    assert "thresholds.csv" not in output
    assert "…" not in output


def test_cli_dev_optimize_threshold_progress_reporter_non_tty_uses_dynamic_line() -> (
    None
):
    stream = io.StringIO()
    reporter = cli_module._ThresholdOptimizationProgressReporter(stream)

    with reporter:
        reporter.phase("Preparing seeded development database: /tmp/dev.db")
        reporter.phase("Loading candidate pools")
        reporter.start_scoring(3)
        reporter.advance_scoring(1, 0.0)
        reporter.advance_scoring(3, 0.2)
        reporter.phase("Writing CSV sweep to stdout")
        reporter.phase("Unknown done")

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Preparing dev DB" in output
    assert "Loading candidates" in output
    assert "Scoring thresholds" in output
    assert "1/3" in output
    assert "3/3" in output
    assert "Writing CSV stdout" in output
    assert "Unknown done" in output
    assert "/tmp/dev.db" not in output
    assert "…" not in output


def test_cli_dev_optimize_threshold_progress_reporter_handles_isatty_oserror() -> None:
    class BadTTYStream(io.StringIO):
        def isatty(self) -> bool:
            raise OSError("no tty")

    stream = BadTTYStream()
    reporter = cli_module._ThresholdOptimizationProgressReporter(stream)

    with reporter:
        reporter.phase("Loading fixtures")

    output = stream.getvalue()
    assert "\n" not in output
    assert "Status:" not in output
    assert output.endswith("\r\x1b[2K")
    assert "Loading fixtures" in output


def test_cli_dev_optimize_threshold_csv_stdout_is_pure_and_reports_summary(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
            "--start",
            "0",
            "--end",
            "0.1",
            "--step",
            "0.1",
            "--human-readable",
        ],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert stdout.startswith("threshold,weighted_precision")
    assert "Status:" not in stdout
    assert "\r\x1b[2K" in stderr
    assert "Status:" not in stderr
    assert "Preparing dev DB" in stderr
    assert "Loading fixtures" in stderr
    assert "Loading candidates" in stderr
    assert "Scoring thresholds" in stderr
    assert "1/2" in stderr
    assert "2/2" in stderr
    assert "Writing CSV stdout" in stderr
    assert "Preparing seeded development database" not in stderr
    assert "Loading candidate pools" not in stderr
    assert "Scoring thresholds: 0/2 (ETA calculating)" not in stderr
    assert "Recommendation:" in stderr
    assert "Exposure:" in stderr
    assert "Result not applied. To apply recommendation, use:" in stderr
    assert "recollectium config set retrieval.match_threshold" in stderr
    assert "Apply:" not in stderr
    assert "Objective:" not in stderr
    assert "Current config:" not in stderr
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_optimize_threshold_json_csv_stdout_emits_json_payload_only(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--json",
            "--config",
            str(config_path),
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
            "--start",
            "0",
            "--end",
            "0.1",
            "--step",
            "0.1",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert not stdout.startswith("threshold,weighted_precision")
    payload = json.loads(stdout)
    assert payload["status"] == "ok"
    assert payload["artifact"] == {"format": "csv", "path": "stdout"}
    assert len(payload["optimization"]["rows"]) == 2
    assert payload["optimization"]["rows"][0]["threshold"] == 0.0
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_optimize_threshold_write_config_persists_numeric_threshold(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    output_csv = tmp_path / "thresholds.csv"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
            "--output",
            str(output_csv),
            "--write-config",
            "--start",
            "0",
            "--end",
            "0.1",
            "--step",
            "0.1",
        ],
        capsys,
    )

    assert exit_code == 0
    payload = json.loads(stdout)
    assert stderr == ""
    assert payload["status"] == "ok"
    assert payload["optimization"]["wrote_config"] is True
    assert payload["artifact"]["format"] == "csv"
    assert output_csv.exists()
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert isinstance(updated["retrieval"]["match_threshold"], float)
    assert updated["retrieval"]["match_threshold"] != "model_recommended_default"
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_optimize_threshold_human_readable_csv_writes_summary_and_artifact(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    output_csv = tmp_path / "thresholds.csv"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "--human-readable",
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
            "--output",
            str(output_csv),
            "--start",
            "0",
            "--end",
            "0.1",
            "--step",
            "0.1",
        ],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert "Recollectium dev optimize-threshold" in stdout
    assert stdout.startswith("\nRecollectium dev optimize-threshold")
    assert stdout.endswith("\n\n")
    assert "Thresholds:" not in stdout
    assert "Metrics:" in stdout
    assert "Exposure:" in stdout
    assert "Result not applied. To apply recommendation, use:" in stdout
    assert "Apply:" not in stdout
    assert "Objective:" not in stdout
    assert "Current config:" not in stdout
    assert "Writing CSV" in stderr
    assert "Writing CSV artifact:" not in stderr
    assert output_csv.exists()
    assert output_csv.read_text(encoding="utf-8").startswith("threshold,")
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_optimize_threshold_human_readable_png_writes_summary_and_artifact(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    output_png = tmp_path / "thresholds.png"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "--human-readable",
            "--verbose",
            "dev",
            "optimize-threshold",
            "--format",
            "png",
            "--output",
            str(output_png),
            "--write-config",
            "--start",
            "0",
            "--end",
            "0.1",
            "--step",
            "0.1",
        ],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert "Recollectium dev optimize-threshold" in stdout
    assert "Writing config" in stderr
    assert "Writing PNG" in stderr
    assert "Writing config:" not in stderr
    assert "Writing PNG artifact:" not in stderr
    assert "Recommendation:" in stdout
    assert "Thresholds:" in stdout
    assert "Recommendation result applied to config" in stdout
    assert "Result not applied" not in stdout
    assert "recollectium config set retrieval.match_threshold" not in stdout
    assert "Apply:" not in stdout
    assert "Objective:" not in stdout
    assert "Current config:" not in stdout
    assert output_png.exists()
    assert output_png.stat().st_size > 0
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert isinstance(updated["retrieval"]["match_threshold"], float)
    assert dev_db.exists()
    assert not regular_db.exists()


def test_cli_dev_optimize_threshold_validates_sweep_before_provider_setup(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    regular_db = tmp_path / "regular.db"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(regular_db)},
                "development": {"seeded_database_path": str(dev_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructed(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructed
    )

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
            "--beta",
            "0",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "validation_error"
    assert "beta must be > 0.0" in payload["detail"]
    assert not dev_db.exists()
    assert not regular_db.exists()

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructed()


@pytest.mark.parametrize("output_mode", ["--json", "--human-readable"])
def test_cli_dev_optimize_threshold_refuses_when_seeded_database_matches_regular_database(
    tmp_path, capsys, monkeypatch, output_mode
) -> None:
    config_path = tmp_path / "config.json"
    shared_db = tmp_path / "shared.db"
    shared_db.write_text("regular database marker", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(shared_db)},
                "development": {"seeded_database_path": str(shared_db)},
            }
        ),
        encoding="utf-8",
    )

    class ProviderMustNotBeConstructed(FakeEmbeddingProvider):
        def __init__(self) -> None:
            raise AssertionError("provider should not be constructed")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", ProviderMustNotBeConstructed
    )

    exit_code, stdout, stderr = _run_cli(
        [
            output_mode,
            "--config",
            str(config_path),
            "dev",
            "optimize-threshold",
            "--format",
            "csv",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    if output_mode == "--json":
        payload = json.loads(stderr)
        assert payload["status"] == "unsafe_seeded_database_path"
        assert payload["seeded_database"] == str(shared_db)
        assert payload["regular_database"] == str(shared_db)
    else:
        assert "Seeded dev database path matches the regular database path." in stderr
        assert "Status: unsafe_seeded_database_path" in stderr
        assert str(shared_db) in stderr
    assert shared_db.read_text(encoding="utf-8") == "regular database marker"

    with pytest.raises(AssertionError, match="provider should not be constructed"):
        ProviderMustNotBeConstructed()


def test_cli_dev_reset_resolves_relative_seed_database_path(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    data_dir = tmp_path / "data"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": "regular.db"},
                "directories": {"data": str(data_dir)},
                "development": {"seeded_database_path": "dev.db"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_module, "BuiltinFastEmbedProvider", FakeEmbeddingProvider)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "reset"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["database"] == str(data_dir / "dev.db")
    assert (data_dir / "dev.db").exists()


def test_cli_dev_reports_config_and_embedding_errors(
    tmp_path, capsys, monkeypatch
) -> None:
    missing_config = tmp_path / "missing.json"

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(missing_config), "dev", "reset"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert json.loads(stderr)["status"] == "config_missing"

    invalid_config = tmp_path / "invalid.json"
    invalid_config.write_text(
        json.dumps({"development": {"use_seeded_database": "yes"}}),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(invalid_config), "dev", "reset"],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert json.loads(stderr)["status"] == "validation_error"

    class FailingEmbeddingProvider(FakeEmbeddingProvider):
        def ensure_ready(self, *, timeout_seconds: float = 60.0) -> None:
            raise EmbeddingProviderUnavailableError("fake provider unavailable")

    valid_config = tmp_path / "valid.json"
    valid_config.write_text(
        json.dumps({"development": {"seeded_database_path": str(tmp_path / "dev.db")}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", FailingEmbeddingProvider
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(valid_config), "dev", "reset"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert json.loads(stderr)["status"] == "embedding_provider_unavailable"


def test_cli_dev_true_does_not_persist_config_when_embedding_fails(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    config_path.write_text(
        json.dumps({"development": {"seeded_database_path": str(dev_db)}}),
        encoding="utf-8",
    )

    class FailingEmbeddingProvider(FakeEmbeddingProvider):
        def ensure_ready(self, *, timeout_seconds: float = 60.0) -> None:
            raise EmbeddingProviderUnavailableError("fake provider unavailable")

    monkeypatch.setattr(
        cli_module, "BuiltinFastEmbedProvider", FailingEmbeddingProvider
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "true"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert json.loads(stderr)["status"] == "embedding_provider_unavailable"
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert "use_seeded_database" not in loaded["development"]
    assert not dev_db.exists()


def test_cli_dev_refuses_to_switch_or_reset_while_service_is_running(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    dev_db = tmp_path / "dev.db"
    config_path.write_text(
        json.dumps({"development": {"seeded_database_path": str(dev_db)}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_module,
        "check_running_service",
        lambda _config: {"type": "api", "pid": 12345},
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "true"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "service_running"
    assert payload["hint"].startswith("Stop or restart the service")
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert "use_seeded_database" not in loaded["development"]

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "reset"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert json.loads(stderr)["status"] == "service_running"
    assert not dev_db.exists()


def test_cli_dev_reports_service_status_errors(tmp_path, capsys, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"development": {"seeded_database_path": str(tmp_path / "dev.db")}}),
        encoding="utf-8",
    )

    def raise_service_error(_config):
        raise ServiceError("bad pid file")

    monkeypatch.setattr(cli_module, "check_running_service", raise_service_error)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "dev", "true"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert json.loads(stderr)["status"] == "service_error"


def test_cli_human_readable_flag_formats_failure_output(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "config",
            "set",
            "logging.level",
            "trace",
            "--human-readable",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert stderr.startswith("Config is invalid.\n")
    assert "Status: config_invalid" in stderr
    assert "Detail: ValidationError: logging.level must be one of" in stderr
    with pytest.raises(json.JSONDecodeError):
        json.loads(stderr)


def test_cli_human_readable_config_formats_failure_output(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "cli_output": "human_readable",
                "service": {"port": "not-an-int"},
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "config", "get", "service.port"],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 2
    assert stdout == ""
    assert stderr.startswith("Config is invalid.\n")
    assert "Status: config_invalid" in stderr
    assert "service.port must be int" in stderr


def test_cli_json_flag_formats_failure_output_as_json(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "cli_output": "human_readable",
                "service": {"port": "not-an-int"},
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "config", "get", "service.port", "--json"],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "config_invalid"
    assert "service.port must be int" in payload["detail"]


def test_cli_human_readable_flag_formats_success_output(tmp_path, capsys) -> None:
    db_path = tmp_path / "human-status.db"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "db-status", "--human-readable"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout.startswith("Db status\n")
    assert "Db path:" in stdout
    assert "Up to date: true" in stdout
    assert "\x1b[" not in stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(stdout)


class _TTYBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class _NonTTYBuffer(io.StringIO):
    def isatty(self) -> bool:
        return False


class _BrokenTTYBuffer(io.StringIO):
    def isatty(self) -> bool:
        raise OSError("tty unavailable")


def test_cli_color_detection_handles_non_tty_streams() -> None:
    assert _supports_color(object()) is False
    assert _supports_color(_BrokenTTYBuffer()) is False


def test_cli_human_output_uses_rich_as_direct_dependency() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert cli_module.Console.__module__.startswith("rich.")
    assert cli_module.Text.__module__.startswith("rich.")
    assert any(dependency.partition(">=")[0] == "rich" for dependency in dependencies)


def test_cli_human_readable_success_uses_color_on_tty(monkeypatch) -> None:
    stream = _TTYBuffer()
    monkeypatch.setattr("sys.stdout", stream)

    _emit_success(
        {"up_to_date": True, "pending_versions": []},
        output_format="human_readable",
        command="db-status",
    )

    output = stream.getvalue()
    assert output.startswith("\x1b[1;36mDb status\x1b[0m\n")
    assert "\x1b[1mUp to date:\x1b[0m true" in output
    assert "\x1b[" in output


def test_cli_human_readable_success_does_not_color_non_tty(monkeypatch) -> None:
    stream = _NonTTYBuffer()
    monkeypatch.setattr("sys.stdout", stream)

    _emit_success(
        {"up_to_date": True},
        output_format="human_readable",
        command="db-status",
    )

    output = stream.getvalue()
    assert output.startswith("Db status\n")
    assert "\x1b[" not in output


def test_cli_human_readable_errors_use_color_on_tty(monkeypatch) -> None:
    stream = _TTYBuffer()
    monkeypatch.setattr("sys.stderr", stream)
    _set_cli_output_format("human_readable")

    try:
        _emit_failure_payload(
            {
                "status": "config_invalid",
                "message": "Config is invalid.",
                "detail": "ValidationError: bad value",
                "hint": "Fix the config file.",
            }
        )
    finally:
        _set_cli_output_format("json")

    output = stream.getvalue()
    assert output.startswith("\x1b[1;31mConfig is invalid.\x1b[0m\n")
    assert "\x1b[1mStatus:\x1b[0m config_invalid" in output
    assert "\x1b[33mFix the config file.\x1b[0m" in output


def test_cli_human_readable_is_default_output(tmp_path, capsys) -> None:
    db_path = tmp_path / "default-human-status.db"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "db-status"], capsys, json_by_default=False
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout.startswith("Db status\n")
    with pytest.raises(json.JSONDecodeError):
        json.loads(stdout)


def test_cli_output_config_controls_success_output(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "configured-human.db"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "cli_output": "human_readable",
                "database": {"path": str(db_path)},
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "db-status"],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout.startswith("Db status\n")


def test_cli_json_flag_overrides_human_readable_config(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "configured-json.db"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "cli_output": "human_readable",
                "database": {"path": str(db_path)},
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "db-status", "--json"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["db_path"] == str(db_path)


def test_cli_output_flags_work_before_command(tmp_path, capsys) -> None:
    db_path = tmp_path / "before-command.db"

    human_code, human_out, human_err = _run_cli(
        ["--human-readable", "--db", str(db_path), "db-status"], capsys
    )
    assert human_code == 0
    assert human_err == ""
    assert human_out.startswith("Db status\n")

    json_code, json_out, json_err = _run_cli(
        ["--json", "--db", str(db_path), "db-status"], capsys
    )
    assert json_code == 0
    assert json_err == ""
    assert json.loads(json_out)["db_path"] == str(db_path)


def test_cli_output_flag_literals_can_follow_double_dash(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "config",
            "set",
            "logging.level",
            "--",
            "--json",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "logging.level must be one of" in stderr
    assert "--json" in stderr


def test_cli_output_flags_are_mutually_exclusive(capsys) -> None:
    exit_code, stdout, stderr = _run_cli(
        ["db-status", "--json", "--human-readable"], capsys
    )

    assert exit_code == 2
    assert stdout == ""
    assert stderr.startswith("Choose either --json or --human-readable, not both.\n")
    assert "Status: validation_error" in stderr


def test_completion_complete_line_stays_json_under_human_output_config(
    tmp_path, capsys
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"version": 1, "cli_output": "human_readable"}), encoding="utf-8"
    )

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "completion",
            "--complete-line",
            "recollectium c",
            "--point",
            "14",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert isinstance(json.loads(stdout), list)


def test_cli_human_formatter_covers_command_shapes() -> None:
    memory = {
        "id": 123,
        "space": "workspace",
        "workspace_uid": "demo",
        "type": "decision",
        "status": "active",
        "source": "test",
        "confidence": 0.9,
        "sensitivity": "normal",
        "content": "Use SQLite.",
        "metadata": {"ticket": "R-1"},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "archived_at": "2026-01-03T00:00:00Z",
    }

    assert _format_human_output(None) == "Done\n"
    assert _format_human_output([]) == "No results\n"
    assert "- plain" in _format_human_output(["plain", 2])
    assert "1. Memory 123" in _format_human_output([{"memory": memory, "score": 0.75}])
    assert '1. {"name": "demo"}' in _format_human_output([{"name": "demo"}])
    assert _format_human_output(3, label="count") == "count: 3\n"
    assert _format_human_output("ok") == "ok\n"
    assert "Memory added" in _format_human_output(memory, command="add")
    assert "Memory updated" in _format_human_output(memory, command="update")
    assert "Memory archived" in _format_human_output(memory, command="archive")
    # Compact archive projection (id + status only, no content) → short output
    assert (
        _format_human_output({"id": 456, "status": "archived"}, command="archive")
        == "Memory archived.\n"
    )
    # Compact archive with just status (no id, no content) → short output
    assert (
        _format_human_output({"status": "archived"}, command="archive")
        == "Memory archived.\n"
    )
    # Verbose archive (full memory dict with content + archived status) → detailed output
    archived_memory = {**memory, "status": "archived"}
    verbose_output = _format_human_output(archived_memory, command="archive")
    assert "Memory archived" in verbose_output
    assert "Use SQLite." in verbose_output  # content present
    assert "decision" in verbose_output  # type present
    # Compact add projection → short output
    assert (
        _format_human_output({"id": 789, "status": "saved"}, command="add")
        == "Memory saved!\n"
    )
    # Compact update projection → short output
    assert (
        _format_human_output({"id": 789, "status": "updated"}, command="update")
        == "Memory updated.\n"
    )
    assert "cli_output: human_readable" in _format_human_output(
        "human_readable", command="config get", label="cli_output"
    )
    assert 'embedding: {"model": "demo"}' in _format_human_output(
        {"model": "demo"}, command="config get", label="embedding"
    )
    assert "Config updated:" in _format_human_output(
        {"key": "cli_output", "value": "json"}, command="config set"
    )
    assert "Config key removed:" in _format_human_output(
        {"key": "cli_output"}, command="config unset"
    )
    assert "Exit code: 2" in _format_human_error(
        {
            "status": "validation_error",
            "message": "Input validation failed.",
            "detail": "bad value",
            "hint": "try again",
            "exit_code": 2,
        }
    )
    assert "Config initialized:" in _format_human_output(
        {"path": "/tmp/config.json"}, command="config init"
    )
    assert "Config reset to defaults:" in _format_human_output(
        {"path": "/tmp/config.json"}, command="config reset"
    )
    assert "Config doctor" in _format_human_output(
        {"status": "ok", "checks": {"config": "/tmp/config.json"}},
        command="config doctor",
    )
    assert "Effective configuration" in _format_human_output(
        {
            "nested": {"key": "value"},
            "items": [{"name": "one"}, "two"],
            "empty": [],
        },
        command="config",
    )
    assert "Recollectium initialized" in _format_human_output(
        {"database": "/tmp/recollectium.db"}, command="init"
    )
    assert "Workspace result" in _format_human_output(
        {"canonical_uid": "demo"}, command="workspace resolve"
    )
    assert "Service result" in _format_human_output(
        {"status": "running"}, command="service status"
    )
    assert "Embedding status" in _format_human_output(
        {"provider": "builtin-fastembed"}, command="embedding-status"
    )
    assert "Result" in _format_human_output({"ok": True})


def test_cli_human_formatter_colors_config_command_shapes() -> None:
    assert _format_human_output(
        "human_readable", command="config get", label="cli_output", color=True
    ).startswith("\x1b[1mcli_output:\x1b[0m human_readable")
    assert _format_human_output(
        {"model": "demo"}, command="config get", label="embedding", color=True
    ).startswith('\x1b[1membedding:\x1b[0m {"model": "demo"}')
    assert _format_human_output(
        {"key": "cli_output", "value": "json"}, command="config set", color=True
    ).startswith("\x1b[1;36mConfig updated:\x1b[0m cli_output = json")
    assert _format_human_output(
        {"key": "cli_output"}, command="config unset", color=True
    ).startswith("\x1b[1;36mConfig key removed:\x1b[0m cli_output")
    assert _format_human_output(
        {"path": "/tmp/config.json"}, command="config init", color=True
    ).startswith("\x1b[1;36mConfig initialized:\x1b[0m /tmp/config.json")
    assert _format_human_output(
        {"path": "/tmp/config.json"}, command="config reset", color=True
    ).startswith("\x1b[1;36mConfig reset to defaults:\x1b[0m /tmp/config.json")


def test_cli_output_helpers_cover_sys_argv_and_invalid_config_shapes(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("sys.argv", ["recollectium", "list", "--human-readable"])
    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(None)
    )
    assert cleaned == ["list"]
    assert output_format == "human_readable"
    assert response_verbosity is None
    assert output_conflict is False
    assert verbosity_conflict is False

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(["--human-readable", "list", "--json"])
    )
    assert cleaned == ["list"]
    assert output_format == "json"
    assert response_verbosity is None
    assert output_conflict is True
    assert verbosity_conflict is False

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(["config", "set", "logging.level", "--", "--json"])
    )
    assert cleaned == ["config", "set", "logging.level", "--", "--json"]
    assert output_format is None
    assert response_verbosity is None
    assert output_conflict is False
    assert verbosity_conflict is False

    config_path = tmp_path / "config.json"
    config_path.write_text('{"version": 1, "cli_output": "invalid"}', encoding="utf-8")
    assert (
        _resolve_output_format(config_path=config_path, explicit=True, override=None)
        == "human_readable"
    )
    config_path.write_text("{bad", encoding="utf-8")
    assert (
        _resolve_output_format(config_path=config_path, explicit=True, override=None)
        == "human_readable"
    )


def test_cli_verbosity_extraction_conflicts_order_and_literals(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["recollectium", "list", "--compact"])
    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(None)
    )
    assert cleaned == ["list"]
    assert output_format is None
    assert response_verbosity == RESPONSE_VERBOSITY_COMPACT
    assert output_conflict is False
    assert verbosity_conflict is False

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(["--verbose", "list"])
    )
    assert cleaned == ["list"]
    assert output_format is None
    assert response_verbosity == RESPONSE_VERBOSITY_VERBOSE
    assert output_conflict is False
    assert verbosity_conflict is False

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(["list", "--compact", "--verbose"])
    )
    assert cleaned == ["list"]
    assert response_verbosity == RESPONSE_VERBOSITY_VERBOSE
    assert output_conflict is False
    assert verbosity_conflict is True

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(["list", "--verbose", "--compact"])
    )
    assert cleaned == ["list"]
    assert response_verbosity == RESPONSE_VERBOSITY_COMPACT
    assert output_conflict is False
    assert verbosity_conflict is True

    cleaned, output_format, response_verbosity, output_conflict, verbosity_conflict = (
        _extract_cli_output_override(
            ["config", "set", "response_verbosity", "--", "--verbose"]
        )
    )
    assert cleaned == ["config", "set", "response_verbosity", "--", "--verbose"]
    assert output_format is None
    assert response_verbosity is None
    assert output_conflict is False
    assert verbosity_conflict is False


def test_cli_human_readable_verbosity_conflict_uses_human_error(capsys) -> None:
    exit_code, stdout, stderr = _run_cli(
        ["--human-readable", "--compact", "--verbose", "list"],
        capsys,
        json_by_default=False,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "Choose either --compact or --verbose, not both." in stderr
    assert not stderr.lstrip().startswith("{")


def test_cli_json_verbosity_compact_vs_verbose_memory_shapes(tmp_path, capsys) -> None:
    db_path = tmp_path / "verbosity.db"

    compact_add_code, compact_add_out, compact_add_err = _run_cli(
        [
            "--json",
            "--compact",
            "--db",
            str(db_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "verbosity shape memory",
        ],
        capsys,
    )
    assert compact_add_code == 0
    assert compact_add_err == ""
    compact_add = json.loads(compact_add_out)
    assert set(compact_add) == {"id", "status"}
    assert compact_add["status"] == "saved"

    verbose_search_code, verbose_search_out, verbose_search_err = _run_cli(
        [
            "--json",
            "--verbose",
            "--db",
            str(db_path),
            "search-user",
            "verbosity",
        ],
        capsys,
    )
    assert verbose_search_code == 0
    assert verbose_search_err == ""
    verbose_search = json.loads(verbose_search_out)
    assert set(verbose_search[0]) >= {"memory", "score", "rank"}
    assert verbose_search[0]["memory"]["id"] == compact_add["id"]

    compact_search_code, compact_search_out, compact_search_err = _run_cli(
        [
            "--json",
            "--compact",
            "--db",
            str(db_path),
            "search-user",
            "verbosity",
        ],
        capsys,
    )
    assert compact_search_code == 0
    assert compact_search_err == ""
    compact_search = json.loads(compact_search_out)
    assert set(compact_search[0]) == {"id", "content", "match"}
    assert compact_search[0]["id"] == compact_add["id"]
    assert compact_search[0]["content"] == "verbosity shape memory"
    assert isinstance(compact_search[0]["match"], float)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("add", "Memory saved!\n"),
        ("update", "Memory updated.\n"),
        ("archive", "Memory archived.\n"),
    ],
)
def test_cli_human_compact_projects_mutations_to_short_messages(
    command: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)

    _emit_success(
        {
            "id": "mem-1",
            "content": "compact human mutation",
            "type": "fact",
            "space": "user",
            "metadata": {"source": "test"},
            "created_at": "2026-01-01T00:00:00Z",
        },
        output_format="human_readable",
        command=command,
        response_verbosity=RESPONSE_VERBOSITY_COMPACT,
    )

    assert stream.getvalue() == expected


def test_cli_compact_human_search_output_includes_match_score() -> None:
    """Compact human search results should display the match score."""
    payload = {
        "id": "mem-search-1",
        "content": "a searchable fact",
        "match": 0.87,
    }
    lines = _format_memory(payload)
    assert any("score=0.87" in line for line in lines)


def test_cli_human_verbose_preserves_detailed_mutation_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = io.StringIO()
    monkeypatch.setattr("sys.stdout", stream)

    _emit_success(
        {
            "id": "mem-1",
            "content": "verbose human mutation",
            "type": "fact",
            "space": "user",
            "metadata": {"source": "test"},
            "created_at": "2026-01-01T00:00:00Z",
        },
        output_format="human_readable",
        command="add",
        response_verbosity=RESPONSE_VERBOSITY_VERBOSE,
    )

    output = stream.getvalue()
    assert output.startswith("Memory added\n")
    assert "Memory mem-1 (fact)" in output
    assert "Content: verbose human mutation" in output
    assert 'Metadata: {"source": "test"}' in output


def test_cli_response_verbosity_flag_overrides_config_without_mutation(
    tmp_path, capsys, monkeypatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"version": 1, "cli_output": "json", "response_verbosity": "verbose"}
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "override.db"
    monkeypatch.setattr(
        "recollectium.core.BuiltinFastEmbedProvider", FakeEmbeddingProvider
    )

    add_code, add_out, add_err = _run_cli(
        [
            "--config",
            str(config_path),
            "--compact",
            "--db",
            str(db_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "runtime compact override",
        ],
        capsys,
        json_by_default=False,
    )

    assert add_code == 0
    assert add_err == ""
    assert set(json.loads(add_out)) == {"id", "status"}
    assert (
        json.loads(config_path.read_text(encoding="utf-8"))["response_verbosity"]
        == "verbose"
    )


def test_cli_config_human_readable_setup_commands(tmp_path, capsys) -> None:
    config_path = tmp_path / "config.json"

    init_code, init_out, init_err = _run_cli(
        ["--config", str(config_path), "config", "init", "--human-readable"], capsys
    )
    assert init_code == 0
    assert init_err == ""
    assert "Config initialized:" in init_out

    set_code, set_out, set_err = _run_cli(
        [
            "--config",
            str(config_path),
            "config",
            "set",
            "cli_output",
            "human_readable",
            "--human-readable",
        ],
        capsys,
    )
    assert set_code == 0
    assert set_err == ""
    assert "Config updated: cli_output = human_readable" in set_out

    unset_code, unset_out, unset_err = _run_cli(
        [
            "--config",
            str(config_path),
            "config",
            "unset",
            "cli_output",
            "--human-readable",
        ],
        capsys,
    )
    assert unset_code == 0
    assert unset_err == ""
    assert "Config key removed: cli_output" in unset_out


def test_cli_db_status_missing_explicit_config_errors(tmp_path, capsys) -> None:
    config_path = tmp_path / "nonexistent" / "config.json"

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "db-status"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"config file not found: {config_path}" in stderr


def test_cli_db_status_invalid_config_errors(tmp_path, capsys) -> None:
    config_path = tmp_path / "bad.json"
    config_path.write_text('{"version": 1, "database": {"path": 3}}')

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "db-status"],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError:" in stderr
    assert "database.path must be str" in stderr


def test_cli_db_status_invalid_default_config_errors(
    tmp_path, capsys, monkeypatch
) -> None:
    config_home = tmp_path / "config"
    config_path = config_home / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"version": 1, "database": {"path": 3}}')
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    exit_code, stdout, stderr = _run_cli(["db-status"], capsys)

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError:" in stderr
    assert "database.path must be str" in stderr


def test_cli_rejects_invalid_metadata_json_and_non_object(
    tmp_path: Path, capsys
) -> None:
    invalid_json_path = tmp_path / "invalid.json"
    invalid_json_path.write_text("{", encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "bad-json.db"),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "bad json memory",
            "--metadata",
            f"@{invalid_json_path}",
        ],
        capsys,
    )
    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "metadata_invalid"
    assert "metadata must be valid JSON" in payload["detail"]

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "bad-type.db"),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "bad metadata memory",
            "--metadata",
            "[]",
        ],
        capsys,
    )
    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "metadata_invalid"
    assert "metadata must be a JSON object" in payload["detail"]


def test_cli_validation_error_returns_2(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli.db"

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "workspace",
            "--type",
            "note",
            "--content",
            "Missing workspace",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError:" in stderr
    assert "workspace_uid is required" in stderr


def test_cli_not_found_returns_1(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli.db"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "get", "missing-id"],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "NotFoundError:" in stderr


def test_cli_embedding_error_returns_clear_message(
    tmp_path, capsys, monkeypatch
) -> None:
    class UnavailableCore:
        def __init__(self, *args, **kwargs) -> None:
            raise EmbeddingProviderUnavailableError("FastEmbed is unavailable")

    monkeypatch.setattr("recollectium.cli.RecollectiumCore", UnavailableCore)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "provider.db"), "embedding-status"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingProviderUnavailableError: FastEmbed is unavailable" in stderr


def test_cli_model_unavailable_error_returns_guidance(
    tmp_path, capsys, monkeypatch
) -> None:
    class UnavailableCore:
        def __init__(self, *args, **kwargs) -> None:
            raise EmbeddingModelUnavailableError("failed to load embedding model")

    monkeypatch.setattr("recollectium.cli.RecollectiumCore", UnavailableCore)

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "model.db"),
            "add",
            "--space",
            "user",
            "--type",
            "note",
            "--content",
            "test",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingModelUnavailableError: failed to load embedding model" in stderr
    assert "recollectium init" in stderr


def test_cli_readiness_timeout_error_returns_guidance(
    tmp_path, capsys, monkeypatch
) -> None:
    class TimeoutCore:
        def __init__(self, *args, **kwargs) -> None:
            raise EmbeddingReadinessTimeoutError("startup timed out")

    monkeypatch.setattr("recollectium.cli.RecollectiumCore", TimeoutCore)

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "timeout.db"),
            "add",
            "--space",
            "user",
            "--type",
            "note",
            "--content",
            "test",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingReadinessTimeoutError: startup timed out" in stderr
    assert "recollectium init" in stderr


def test_cli_update_with_content_gates_model_readiness(
    tmp_path, capsys, monkeypatch
) -> None:
    """Update --content triggers embedding readiness gate."""
    import recollectium.cli as cli_mod

    readiness_called = []

    class TrackingCore:
        def __init__(self, *args, **kwargs) -> None:
            self.store = type(
                "FakeStore",
                (),
                {
                    "get_memory": lambda *a, **kw: {
                        "id": "m1",
                        "space": "user",
                        "type": "note",
                        "content": "old",
                        "status": "active",
                        "embedding_profile": {
                            "provider": "fake",
                            "model": "x",
                            "dimensions": 3,
                            "version": "1",
                            "profile": "p",
                            "max_tokens": 16,
                            "chunk_tokens": 4,
                            "chunk_overlap_tokens": 0,
                            "query_prompt_policy": "raw",
                        },
                        "embedding": [1.0, 2.0, 3.0],
                    },
                    "update_memory": lambda *a, **kw: None,
                },
            )()

        def update_memory(self, memory_id, **kwargs):
            return {
                "id": memory_id,
                "space": "user",
                "type": "note",
                "content": kwargs.get("content", "old"),
            }

        def _ensure_model_ready(self):
            readiness_called.append(True)

    monkeypatch.setattr(cli_mod, "RecollectiumCore", TrackingCore)

    # update with --content should gate
    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "udb.db"), "update", "m1", "--content", "new content"],
        capsys,
    )
    assert exit_code == 0
    assert len(readiness_called) == 1


def test_cli_update_metadata_only_skips_readiness_gate(
    tmp_path, capsys, monkeypatch
) -> None:
    """Update without --content skips the embedding readiness gate."""
    import recollectium.cli as cli_mod

    readiness_called = []

    class TrackingCore:
        def __init__(self, *args, **kwargs) -> None:
            self.store = type(
                "FakeStore",
                (),
                {
                    "get_memory": lambda *a, **kw: {
                        "id": "m1",
                        "space": "user",
                        "type": "note",
                        "content": "old",
                        "status": "active",
                        "embedding_profile": {
                            "provider": "fake",
                            "model": "x",
                            "dimensions": 3,
                            "version": "1",
                            "profile": "p",
                            "max_tokens": 16,
                            "chunk_tokens": 4,
                            "chunk_overlap_tokens": 0,
                            "query_prompt_policy": "raw",
                        },
                        "embedding": [1.0, 2.0, 3.0],
                    },
                    "update_memory": lambda *a, **kw: None,
                },
            )()

        def update_memory(self, memory_id, **kwargs):
            return {"id": memory_id, "space": "user", "type": "note", "content": "old"}

        def _ensure_model_ready(self):
            readiness_called.append(True)

    monkeypatch.setattr(cli_mod, "RecollectiumCore", TrackingCore)

    # update with --source only should skip gate
    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "udb2.db"), "update", "m1", "--source", "new-source"],
        capsys,
    )
    assert exit_code == 0
    assert len(readiness_called) == 0

    TrackingCore()._ensure_model_ready()


def test_cli_embedding_generation_error_returns_1(
    tmp_path, capsys, monkeypatch
) -> None:
    class FailingCore:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def active_embedding_status(self) -> dict[str, object]:
            raise EmbeddingGenerationError("provider returned no vector")

    monkeypatch.setattr("recollectium.cli.RecollectiumCore", FailingCore)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "generation.db"), "embedding-status"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingGenerationError: provider returned no vector" in stderr


def test_cli_fetches_one_embedding_job(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    db_path = tmp_path / "cli-job.db"
    store = SQLiteMemoryStore(db_path)
    store.create_embedding_job(
        job_id="job-1",
        state="completed",
        total_count=1,
        processed_count=1,
        succeeded_count=1,
        failed_count=0,
        provider="test",
        model="fake",
        embedding_profile={"provider": "test", "model": "fake", "dimensions": 3},
    )

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "embedding-jobs", "--job-id", "job-1"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["id"] == "job-1"


def test_cli_embedding_maintenance_prepares_model_and_refreshes(
    tmp_path, capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod

    calls: list[str] = []
    config_path = tmp_path / "config.json"
    db_path = tmp_path / "maintenance.db"

    class FakeProvider:
        embedding_profile = {
            "provider": "fake",
            "model": "fake-model",
            "dimensions": 3,
            "version": "1",
            "profile": "fake-profile",
            "max_tokens": 16,
            "chunk_tokens": 4,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }

        def ensure_ready(self) -> None:
            calls.append("ensure_ready")

    class FakeStore:
        def __init__(self, path) -> None:
            self.db_path = path

    class FakeCore:
        def __init__(self, *, db_path, config_path=None, log_level=None) -> None:
            calls.append(f"core:{db_path}")
            self.config = cli_mod.RecollectiumConfig(config_path, log_level=log_level)
            self.store = FakeStore(db_path)
            self.embedding_provider = FakeProvider()

        def _ensure_model_ready(self) -> None:
            calls.append("model_state")

        def refresh_stale_embeddings(self, *, include_archived=False, **kwargs):
            calls.append(f"refresh:{include_archived}")
            return {
                "refreshed": True,
                "stale_count": 2,
                "job": {"id": "job-1", "state": "completed"},
                "status_path": "/v1/embedding/jobs/job-1",
            }

    monkeypatch.setattr(
        cli_mod, "SQLiteMemoryStore", lambda path: calls.append(f"store:{path}")
    )
    monkeypatch.setattr(cli_mod, "RecollectiumCore", FakeCore)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "--db", str(db_path), "embedding-maintenance"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "embedding_maintenance_completed"
    assert payload["database"] == str(db_path)
    assert payload["model_prepared"] is True
    assert payload["embedding_refresh"]["stale_count"] == 2
    assert calls == [
        f"store:{db_path}",
        f"core:{db_path}",
        "ensure_ready",
        "model_state",
        "refresh:True",
    ]


def test_cli_embedding_maintenance_provider_without_ready_uses_healthcheck(
    tmp_path, capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod

    calls: list[str] = []
    db_path = tmp_path / "maintenance-fallback.db"

    class FallbackProvider:
        embedding_profile = {
            "provider": "fake",
            "model": "fallback",
            "dimensions": 3,
            "version": "1",
            "profile": "fallback-profile",
            "max_tokens": 16,
            "chunk_tokens": 4,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }

        def embed(self, text: str) -> list[float]:
            calls.append(f"embed:{text}")
            return [0.0, 0.0, 0.0]

    class FakeCore:
        def __init__(self, *, db_path, config_path=None, log_level=None) -> None:
            self.config = cli_mod.RecollectiumConfig(config_path, log_level=log_level)
            self.store = type("FakeStore", (), {"db_path": db_path})()
            self.embedding_provider = FallbackProvider()

        def _ensure_model_ready(self) -> None:
            calls.append("model_state")

        def refresh_stale_embeddings(self, *, include_archived=False, **kwargs):
            calls.append(f"refresh:{include_archived}")
            return {"refreshed": False, "stale_count": 0, "job": None}

    monkeypatch.setattr(cli_mod, "SQLiteMemoryStore", lambda path: None)
    monkeypatch.setattr(cli_mod, "RecollectiumCore", FakeCore)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "embedding-maintenance"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["status"] == "embedding_maintenance_completed"
    assert calls == ["embed:healthcheck", "model_state", "refresh:True"]


def test_run_installed_embedding_maintenance_builds_fresh_process_command(
    tmp_path, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult

    calls: list[tuple[list[str], int]] = []

    class FakeRunner:
        def run(self, command, *, timeout_seconds, cwd=None):
            calls.append((command, timeout_seconds))
            assert cwd is None
            return CommandResult(0, '{"status":"ok"}', "")

    monkeypatch.setattr(cli_mod, "SubprocessCommandRunner", FakeRunner)
    monkeypatch.setattr(cli_mod.sys, "executable", "/tmp/python")

    result = cli_mod._run_installed_embedding_maintenance(
        config_path=tmp_path / "config.json",
        explicit=True,
        db_path=str(tmp_path / "memory.db"),
        log_level="debug",
        timeout_seconds=42,
    )

    assert result.returncode == 0
    assert calls == [
        (
            [
                "/tmp/python",
                "-m",
                "recollectium",
                "--json",
                "--config",
                str(tmp_path / "config.json"),
                "--db",
                str(tmp_path / "memory.db"),
                "--log-level",
                "debug",
                "embedding-maintenance",
            ],
            42,
        )
    ]


def test_cli_embedding_maintenance_error_paths_return_structured_json(
    capsys, monkeypatch, tmp_path
) -> None:
    import recollectium.cli as cli_mod

    cases = [
        (FileNotFoundError("missing config"), "config_missing"),
        (ValidationError("bad config"), "config_invalid"),
        (
            EmbeddingProviderUnavailableError("offline"),
            "embedding_provider_unavailable",
        ),
        (MigrationError("boom"), "migration_error"),
        (RecollectiumError("failed"), "operation_failed"),
    ]
    for exc, status in cases:
        monkeypatch.setattr(
            cli_mod,
            "_run_embedding_maintenance",
            lambda *a, _exc=exc, **kw: (_ for _ in ()).throw(_exc),
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(tmp_path / f"{status}.json"), "embedding-maintenance"],
            capsys,
        )
        assert exit_code != 0
        assert stdout == ""
        assert json.loads(stderr)["status"] == status


def test_cli_unknown_command_defensive_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeArgs:
        command = "mystery"
        db_path = None
        config_path = None
        log_level = None

    class FakeParser:
        def parse_args(self, argv: object) -> FakeArgs:
            return FakeArgs()

        def error(self, message: str) -> None:
            assert message == "unknown command: mystery"

    class FakeCore:
        def __init__(
            self,
            *,
            db_path: object,
            config_path: object = None,
            log_level: object = None,
            auto_startup_reembedding: bool = True,
        ) -> None:
            assert db_path is None

    monkeypatch.setattr("recollectium.cli._build_parser", lambda: FakeParser())
    monkeypatch.setattr("recollectium.cli.RecollectiumCore", FakeCore)

    assert main(["mystery"]) == 2


def test_cli_db_status_with_valid_config(tmp_path, capsys) -> None:
    """db-status uses resolved_database_path from config when available."""
    config_path = tmp_path / "config.json"
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text(
        json.dumps({"version": 1}),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "db-status"], capsys
    )
    assert exit_code == 0
    payload = json.loads(stdout)
    assert "db_path" in payload


def test_cli_parse_config_value_plain_string(tmp_path, capsys) -> None:
    """config set with a non-JSON value falls back to string."""
    config_path = tmp_path / "config.json"
    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "config", "set", "logging.level", "debug"],
        capsys,
    )
    assert exit_code == 0
    loaded = json.loads(config_path.read_text())
    assert loaded["logging"]["level"] == "debug"


def test_builtin_fastembed_provider_from_config_resolves_cache_dir(
    tmp_path: Path,
) -> None:
    config = deepcopy(DEFAULTS)
    config["directories"] = {"cache": str(tmp_path / "cache")}

    provider = _builtin_fastembed_provider_from_config(config)

    assert provider.cache_dir == str(tmp_path / "cache" / "models")


def test_cli_embedding_status_and_jobs_output_json(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli-embedding.db"

    add_code, _, add_err = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "user",
            "--type",
            "fact",
            "--content",
            "Local embedding status smoke",
        ],
        capsys,
    )
    assert add_code == 0
    assert add_err == ""

    status_code, status_out, status_err = _run_cli(
        ["--db", str(db_path), "embedding-status"],
        capsys,
    )
    assert status_code == 0
    assert status_err == ""
    status_payload = json.loads(status_out)
    assert status_payload["embedding_profile"]["provider"] == "builtin-fastembed"
    assert status_payload["provider_status"] == "configured"
    assert status_payload["model_status"] == "managed_by_recollectium_cache"
    assert status_payload["model_cache_path"].endswith("recollectium/models")
    assert status_payload["runtime"] == {
        "name": "fastembed",
        "threads": 1,
        "parallel": None,
    }
    assert status_payload["embedding_jobs_status_path"] == "/v1/embedding/jobs"
    assert isinstance(status_payload["recent_embedding_jobs"], list)

    SQLiteMemoryStore(db_path).create_embedding_job(
        job_id="job-1",
        state="completed",
        total_count=1,
        processed_count=1,
        succeeded_count=1,
        failed_count=0,
        provider="builtin-fastembed",
        model="fake-model",
        embedding_profile={"provider": "builtin-fastembed", "model": "fake-model"},
    )

    jobs_code, jobs_out, jobs_err = _run_cli(
        ["--db", str(db_path), "embedding-jobs"],
        capsys,
    )
    assert jobs_code == 0
    assert jobs_err == ""
    jobs_payload = json.loads(jobs_out)
    assert isinstance(jobs_payload, list)
    if jobs_payload:
        job_id = jobs_payload[0]["id"]

        one_job_code, one_job_out, one_job_err = _run_cli(
            ["--db", str(db_path), "embedding-jobs", "--job-id", job_id],
            capsys,
        )
        assert one_job_code == 0
        assert one_job_err == ""
        one_job_payload = json.loads(one_job_out)
        assert one_job_payload["id"] == job_id

    state_code, state_out, state_err = _run_cli(
        [
            "--db",
            str(db_path),
            "embedding-jobs",
            "--state",
            "completed",
            "--limit",
            "1",
        ],
        capsys,
    )
    assert state_code == 0
    assert state_err == ""
    state_payload = json.loads(state_out)
    assert isinstance(state_payload, list)


def test_cli_embedding_refresh_and_jobs_clear_output_json(tmp_path, capsys) -> None:
    db_path = tmp_path / "cli-embedding-refresh.db"

    refresh_code, refresh_out, refresh_err = _run_cli(
        ["--db", str(db_path), "embedding-refresh", "--space", "user"],
        capsys,
    )
    assert refresh_code == 0
    assert refresh_err == ""
    refresh_payload = json.loads(refresh_out)
    assert refresh_payload == {
        "refreshed": False,
        "stale_count": 0,
        "job": None,
        "status_path": "/v1/embedding/jobs",
    }

    clear_without_yes_code, clear_without_yes_out, clear_without_yes_err = _run_cli(
        ["--db", str(db_path), "embedding-jobs-clear", "--state", "pending"],
        capsys,
    )
    assert clear_without_yes_code == 1
    assert clear_without_yes_out == ""
    assert json.loads(clear_without_yes_err)["status"] == "confirmation_required"

    clear_code, clear_out, clear_err = _run_cli(
        [
            "--db",
            str(db_path),
            "embedding-jobs-clear",
            "--state",
            "pending",
            "--yes",
        ],
        capsys,
    )
    assert clear_code == 0
    assert clear_err == ""
    assert json.loads(clear_out) == {"deleted_count": 0, "states": ["pending"]}


# ---------------------------------------------------------------------------
# Config command tests
# ---------------------------------------------------------------------------


class TestConfigCommand:
    def test_directory_writable_returns_false_for_file_path(self, tmp_path) -> None:
        from recollectium.cli import _directory_writable

        non_directory = tmp_path / "not-a-dir"
        non_directory.write_text("x", encoding="utf-8")

        assert _directory_writable(non_directory) is False

    def test_config_prints_effective_json(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1}),
            encoding="utf-8",
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config"], capsys
        )
        assert exit_code == 0
        assert stderr == ""
        payload = json.loads(stdout)
        assert payload["service"]["port"] == 8765

    def test_config_validate_success(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1}),
            encoding="utf-8",
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "--validate"], capsys
        )
        assert exit_code == 0
        assert stderr == ""

    def test_config_validate_failure(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text("{bad", encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "--validate"], capsys
        )
        assert exit_code == 2
        assert "invalid JSON" in stderr

    def test_config_validate_missing_file(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "nonexistent.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "--validate"], capsys
        )
        assert exit_code == 1
        assert "config file not found" in stderr

    def test_config_validate_default_creates_file(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

        exit_code, stdout, stderr = _run_cli(["config", "--validate"], capsys)

        config_path = config_home / "recollectium" / "config.json"
        assert exit_code == 0
        assert stdout == ""
        assert stderr == ""
        assert config_path.exists()

    def test_config_path_flag(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "--path"], capsys
        )
        assert exit_code == 0
        assert stderr == ""
        assert str(config_path) in stdout

    def test_config_path_writes_structured_log_without_creating_config(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        state_home = tmp_path / "state"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

        exit_code, stdout, stderr = _run_cli(["config", "--path"], capsys)

        config_path = config_home / "recollectium" / "config.json"
        log_file = state_home / "recollectium" / "logs" / "recollectium.log"
        assert exit_code == 0
        assert stderr == ""
        assert str(config_path) in stdout
        assert not config_path.exists()
        payload = json.loads(log_file.read_text(encoding="utf-8").splitlines()[-1])
        assert payload["event"] == "cli.command"
        assert payload["context"] == {"command": "config"}

    def test_config_defaults(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "--defaults"], capsys
        )
        assert exit_code == 0
        assert stderr == ""
        payload = json.loads(stdout)
        assert payload["version"] == 1
        assert payload["service"]["port"] == 8765

    def test_config_get_value(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1, "service": {"port": 9999}}),
            encoding="utf-8",
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "get", "service.port"], capsys
        )
        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == 9999

    def test_config_get_missing_key(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "get", "nonexistent"], capsys
        )
        assert exit_code == 1
        assert "not found" in stderr

    def test_config_get_missing_explicit_file_errors(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "missing.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "get", "service.port"], capsys
        )

        assert exit_code == 1
        assert stdout == ""
        assert f"config file not found: {config_path}" in stderr

    def test_config_get_invalid_config_errors(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text("{bad", encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "get", "service.port"], capsys
        )

        assert exit_code == 2
        assert stdout == ""
        assert "ValidationError: invalid JSON" in stderr

    def test_config_set_creates_file(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "set", "service.port", "9090"],
            capsys,
        )
        assert exit_code == 0
        assert config_path.exists()
        loaded = json.loads(config_path.read_text())
        assert loaded["service"]["port"] == 9090
        assert "version" in loaded

    def test_config_set_parses_json_values(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "set", "service.port", "9090"],
            capsys,
        )
        assert exit_code == 0
        loaded = json.loads(config_path.read_text())
        assert loaded["service"]["port"] == 9090
        assert isinstance(loaded["service"]["port"], int)

    @pytest.mark.parametrize(
        "model_name",
        ["BAAI/bge-base-en-v1.5", "jinaai/jina-embeddings-v2-small-en"],
    )
    def test_config_set_accepts_supported_embedding_models(
        self, tmp_path, capsys, model_name: str
    ) -> None:
        config_path = tmp_path / "config.json"
        exit_code, stdout, stderr = _run_cli(
            [
                "--config",
                str(config_path),
                "config",
                "set",
                "embedding.model",
                model_name,
            ],
            capsys,
        )
        assert exit_code == 0
        assert stderr == ""
        loaded = json.loads(config_path.read_text())
        assert loaded["embedding"]["model"] == model_name

    def test_config_set_rejects_unknown_embedding_model(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        exit_code, stdout, stderr = _run_cli(
            [
                "--config",
                str(config_path),
                "config",
                "set",
                "embedding.model",
                "unknown-model",
            ],
            capsys,
        )
        assert exit_code == 2
        assert stdout == ""
        assert "embedding.model must be one of" in stderr
        assert "BAAI/bge-base-en-v1.5" in stderr
        assert "jinaai/jina-embeddings-v2-small-en" in stderr

    def test_config_set_can_enable_seeded_dev_database(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        exit_code, stdout, stderr = _run_cli(
            [
                "--config",
                str(config_path),
                "config",
                "set",
                "development.use_seeded_database",
                "true",
            ],
            capsys,
        )
        assert exit_code == 0
        assert stderr == ""
        loaded = json.loads(config_path.read_text())
        assert loaded["development"]["use_seeded_database"] is True

    def test_config_set_preserves_existing_keys(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1, "logging": {"level": "debug"}}),
            encoding="utf-8",
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "set", "service.port", "8080"],
            capsys,
        )
        assert exit_code == 0
        loaded = json.loads(config_path.read_text())
        assert loaded["logging"]["level"] == "debug"
        assert loaded["service"]["port"] == 8080

    def test_config_unset_removes_key(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1, "service": {"host": "0.0.0.0", "port": 8765}}),
            encoding="utf-8",
        )
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "unset", "service.host"], capsys
        )
        assert exit_code == 0
        loaded = json.loads(config_path.read_text())
        assert "host" not in loaded["service"]
        assert loaded["service"]["port"] == 8765

    def test_config_unset_missing_key(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "unset", "nonexistent"], capsys
        )
        assert exit_code == 1
        assert "not found" in stderr

    def test_config_unset_missing_file(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "nonexistent.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "unset", "service.port"], capsys
        )
        assert exit_code == 1
        assert "config file not found" in stderr

    def test_config_init_creates_file(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "recollectium" / "config.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "init"], capsys
        )
        assert exit_code == 0
        assert config_path.exists()
        loaded = json.loads(config_path.read_text())
        assert loaded["version"] == 1

    def test_config_init_without_force_existing(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1, "custom": "data"}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "init"], capsys
        )
        assert exit_code == 1
        assert "already exists" in stderr
        # File should NOT be overwritten
        loaded = json.loads(config_path.read_text())
        assert loaded.get("custom") == "data"

    def test_config_init_force_overwrites(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1, "custom": "data"}', encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "init", "--force"], capsys
        )
        assert exit_code == 0
        loaded = json.loads(config_path.read_text())
        assert "custom" not in loaded
        assert loaded["version"] == 1

    def test_config_explicit_missing_file_errors(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "nonexistent" / "config.json"
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config"], capsys
        )
        assert exit_code == 1
        assert stdout == ""
        assert f"config file not found: {config_path}" in stderr

    def test_config_no_args_invalid_config_errors(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text("{bad", encoding="utf-8")
        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config"], capsys
        )

        assert exit_code == 2
        assert stdout == ""
        assert "ValidationError: invalid JSON" in stderr

    def test_config_default_no_args_creates_file(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

        exit_code, stdout, stderr = _run_cli(["config"], capsys)

        config_path = config_home / "recollectium" / "config.json"
        assert exit_code == 0
        assert stderr == ""
        assert config_path.exists()
        payload = json.loads(stdout)
        assert payload["service"]["port"] == 8765

    def test_config_default_get_creates_file(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

        exit_code, stdout, stderr = _run_cli(["config", "get", "service.port"], capsys)

        config_path = config_home / "recollectium" / "config.json"
        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == 8765
        assert config_path.exists()

    def test_config_path_and_defaults_do_not_create_default_file(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

        path_code, path_stdout, path_stderr = _run_cli(["config", "--path"], capsys)
        defaults_code, defaults_stdout, defaults_stderr = _run_cli(
            ["config", "--defaults"], capsys
        )

        config_path = config_home / "recollectium" / "config.json"
        assert path_code == 0
        assert path_stderr == ""
        assert str(config_path) in path_stdout
        assert defaults_code == 0
        assert defaults_stderr == ""
        assert json.loads(defaults_stdout) == DEFAULTS
        assert not config_path.exists()

    def test_config_doctor_success_and_default_creation(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_home = tmp_path / "config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

        exit_code, stdout, stderr = _run_cli(["config", "doctor"], capsys)

        config_path = config_home / "recollectium" / "config.json"
        assert exit_code == 0
        assert stderr == ""
        assert config_path.exists()
        payload = json.loads(stdout)
        assert payload["status"] == "ok"
        assert payload["checks"]["config"] == str(config_path)
        assert "data" in payload["checks"]
        assert "cache" in payload["checks"]
        assert "logs" in payload["checks"]
        assert "runtime" in payload["checks"]

    def test_config_doctor_explicit_missing_file_errors(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "missing" / "config.json"

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "doctor"], capsys
        )

        assert exit_code == 1
        assert stdout == ""
        assert f"config file not found: {config_path}" in stderr

    def test_config_doctor_invalid_embedding_settings_fail_validation(
        self, tmp_path, capsys
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "embedding": {
                        "provider": "custom-provider",
                        "model": "custom-model",
                    },
                }
            ),
            encoding="utf-8",
        )

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "doctor"], capsys
        )

        assert exit_code == 2
        assert stdout == ""
        assert "ValidationError:" in stderr
        assert "embedding.provider only supports" in stderr

    def test_config_doctor_reports_directory_writability_failure(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"version": 1}), encoding="utf-8")
        monkeypatch.setattr("recollectium.cli._directory_writable", lambda _path: False)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "doctor"], capsys
        )

        assert exit_code == 1
        assert stdout == ""
        assert "FAIL data directory is not writable:" in stderr
        assert "FAIL cache directory is not writable:" in stderr
        assert "FAIL logs directory is not writable:" in stderr
        assert "FAIL runtime directory is not writable:" in stderr
        assert "FAIL database parent directory is not writable:" in stderr

    def test_config_doctor_reports_missing_and_nondirectory_paths(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        state_home = tmp_path / "state"
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        non_dir = tmp_path / "not-a-dir"
        non_dir.write_text("x", encoding="utf-8")
        monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

        fake_cfg = SimpleNamespace(
            config_file_path=tmp_path / "config.json",
            xdg_dirs={
                "data": tmp_path / "missing-data",
                "cache": non_dir,
                "logs": existing_dir,
                "runtime": existing_dir,
            },
            resolved_database_path=(tmp_path / "missing-db-parent" / "recollectium.db"),
        )
        monkeypatch.setattr(
            "recollectium.cli._load_effective_config", lambda _path, explicit: fake_cfg
        )

        exit_code, stdout, stderr = _run_cli(["config", "doctor"], capsys)

        assert exit_code == 1
        assert stdout == ""
        assert "FAIL data directory missing:" in stderr
        assert "FAIL cache path is not a directory:" in stderr
        assert "FAIL database parent directory missing:" in stderr
        log_file = state_home / "recollectium" / "logs" / "recollectium.log"
        payloads = [
            json.loads(line)
            for line in log_file.read_text(encoding="utf-8").splitlines()
        ]
        doctor_failures = [
            payload
            for payload in payloads
            if payload["event"] == "config.doctor_failed"
        ]
        assert {payload["message"] for payload in doctor_failures} >= {
            f"data directory missing: {tmp_path / 'missing-data'}",
            f"cache path is not a directory: {non_dir}",
            f"database parent directory missing: {tmp_path / 'missing-db-parent'}",
        }

    def test_config_doctor_reports_database_parent_not_directory(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        shared_dir = tmp_path / "dirs"
        shared_dir.mkdir()
        db_parent_file = tmp_path / "db-parent-file"
        db_parent_file.write_text("x", encoding="utf-8")

        fake_cfg = SimpleNamespace(
            config_file_path=tmp_path / "config.json",
            xdg_dirs={
                "data": shared_dir,
                "cache": shared_dir,
                "logs": shared_dir,
                "runtime": shared_dir,
            },
            resolved_database_path=db_parent_file / "recollectium.db",
        )
        monkeypatch.setattr(
            "recollectium.cli._load_effective_config", lambda _path, explicit: fake_cfg
        )

        exit_code, stdout, stderr = _run_cli(["config", "doctor"], capsys)

        assert exit_code == 1
        assert "FAIL database parent path is not a directory:" in stderr

    # -- edit ---------------------------------------------------------------

    def test_config_edit_creates_file_and_opens_editor(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_path = tmp_path / "recollectium" / "config.json"
        editor_calls: list[list[str]] = []

        def _fake_call(args, **kwargs) -> int:
            editor_calls.append(args)
            return 0

        monkeypatch.setattr("subprocess.call", _fake_call)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "edit"], capsys
        )

        assert exit_code == 0
        assert stderr == ""
        assert config_path.exists()
        loaded = json.loads(config_path.read_text())
        assert loaded["version"] == 1
        assert len(editor_calls) == 1
        assert editor_calls[0][0] == "vi"
        assert editor_calls[0][1] == str(config_path)

    def test_config_edit_opens_existing_config(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1, "logging": {"level": "debug"}}),
            encoding="utf-8",
        )
        editor_calls: list[list[str]] = []

        def _fake_call(args, **kwargs) -> int:
            editor_calls.append(args)
            return 0

        monkeypatch.setattr("subprocess.call", _fake_call)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "edit"], capsys
        )

        assert exit_code == 0
        assert stderr == ""
        # File should not be overwritten
        loaded = json.loads(config_path.read_text())
        assert loaded["logging"]["level"] == "debug"
        assert len(editor_calls) == 1
        assert editor_calls[0][1] == str(config_path)

    def test_config_edit_respects_editor_env(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")
        monkeypatch.setenv("EDITOR", "nano")

        editor_calls: list[list[str]] = []

        def _fake_call(args, **kwargs) -> int:
            editor_calls.append(args)
            return 0

        monkeypatch.setattr("subprocess.call", _fake_call)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "edit"], capsys
        )

        assert exit_code == 0
        assert editor_calls[0][0] == "nano"

    def test_config_edit_editor_not_found(self, tmp_path, capsys, monkeypatch) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")

        def _fake_call(args, **kwargs) -> int:
            raise FileNotFoundError("no such editor")

        monkeypatch.setattr("subprocess.call", _fake_call)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "edit"], capsys
        )

        assert exit_code == 1
        assert "editor not found" in stderr

    def test_config_edit_returns_editor_exit_code(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text('{"version": 1}', encoding="utf-8")

        def _fake_call(args, **kwargs) -> int:
            return 42

        monkeypatch.setattr("subprocess.call", _fake_call)

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "edit"], capsys
        )

        assert exit_code == 42

    # -- reset --------------------------------------------------------------

    def test_config_reset_creates_file_when_missing(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "recollectium" / "config.json"

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "reset"], capsys
        )

        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == {"path": str(config_path)}
        assert config_path.exists()
        loaded = json.loads(config_path.read_text())
        assert loaded["version"] == 1
        assert loaded["service"]["port"] == 8765

    def test_config_reset_overwrites_existing(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_text(
            json.dumps({"version": 1, "logging": {"level": "debug"}, "custom": "data"}),
            encoding="utf-8",
        )

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "reset"], capsys
        )

        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == {"path": str(config_path)}
        loaded = json.loads(config_path.read_text())
        assert "custom" not in loaded
        assert loaded["logging"]["level"] == "info"  # back to default

    def test_config_reset_prints_message(self, tmp_path, capsys) -> None:
        config_path = tmp_path / "config.json"

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "config", "reset"], capsys
        )

        assert exit_code == 0
        assert stderr == ""
        assert json.loads(stdout) == {"path": str(config_path)}

    def test_config_help_shows_actions(self, capsys) -> None:
        help_text = _run_help(["config", "--help"], capsys)
        assert "inspect, validate, and edit" in help_text.lower()
        assert "get" in help_text
        assert "set" in help_text
        assert "unset" in help_text
        assert "init" in help_text
        assert "doctor" in help_text
        assert "edit" in help_text
        assert "reset" in help_text
        assert "--validate" in help_text
        assert "--path" in help_text
        assert "--defaults" in help_text


def test_cli_version_prints_package_version(capsys, monkeypatch) -> None:
    monkeypatch.setattr("recollectium.cli.package_version", lambda _name: "1.2.3")

    exit_code, stdout, stderr = _run_cli(["--version"], capsys)

    assert exit_code == 0
    assert stdout == "recollectium 1.2.3\n"
    assert stderr == ""


def test_cli_version_uses_source_fallback(capsys, monkeypatch) -> None:
    def _missing_package(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("recollectium.cli.package_version", _missing_package)
    monkeypatch.setattr("recollectium.cli.__version__", "0.1.0-dev")

    exit_code, stdout, stderr = _run_cli(["--version"], capsys)

    assert exit_code == 0
    assert stdout == "recollectium 0.1.0-dev\n"
    assert stderr == ""


def test_cli_version_without_command_does_not_require_subcommand(capsys) -> None:
    exit_code, stdout, stderr = _run_cli(["--version"], capsys)

    assert exit_code == 0
    assert stdout.startswith("recollectium ")
    assert stderr == ""


def test_cli_init_creates_runtime_files_and_downloads_model(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    ready_calls: list[object] = []

    def _fake_ensure_ready(self) -> None:
        ready_calls.append(self)

    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        _fake_ensure_ready,
    )

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    payload = json.loads(stdout)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    db_path = tmp_path / "data" / "recollectium" / "recollectium.db"
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "initialized"
    assert payload["config"] == str(config_path)
    assert payload["database"] == str(db_path)
    assert payload["embedding_model"] == "BAAI/bge-base-en-v1.5"
    assert config_path.exists()
    assert db_path.exists()
    assert (tmp_path / "cache" / "recollectium").is_dir()
    assert (tmp_path / "state" / "recollectium" / "logs").is_dir()
    assert ready_calls


def test_cli_init_explicit_missing_config_creates_file(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "custom" / "config.json"
    ready_calls: list[object] = []

    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        lambda self: ready_calls.append(self),
    )

    exit_code, stdout, stderr = _run_cli(["--config", str(config_path), "init"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["config"] == str(config_path)
    assert config_path.exists()
    assert ready_calls


def test_cli_init_accepts_db_after_subcommand(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    db_path = tmp_path / "custom.db"
    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        lambda self: None,
    )

    exit_code, stdout, stderr = _run_cli(["init", "--db", str(db_path)], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["database"] == str(db_path)
    assert db_path.exists()


def test_cli_init_reports_validation_error(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"version": 1, "logging": {"level": "bad"}}))

    exit_code, stdout, stderr = _run_cli(["--config", str(config_path), "init"], capsys)

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError:" in stderr


def test_cli_init_reports_file_not_found_from_handler(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_file_not_found(*args, **kwargs) -> int:
        raise FileNotFoundError("config disappeared")

    monkeypatch.setattr("recollectium.cli._handle_init_command", _raise_file_not_found)

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "config disappeared" in stderr


def test_cli_init_reports_model_readiness_error(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    def _raise_readiness_error(self) -> None:
        raise EmbeddingProviderUnavailableError("model unavailable")

    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        _raise_readiness_error,
    )

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingProviderUnavailableError: model unavailable" in stderr


def test_cli_init_reports_readiness_timeout_error(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    def _raise_timeout(self) -> None:
        raise EmbeddingReadinessTimeoutError("startup timed out")

    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        _raise_timeout,
    )

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingReadinessTimeoutError: startup timed out" in stderr
    assert "recollectium init" in stderr


def test_cli_init_reports_model_unavailable_error(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    def _raise_model_error(self) -> None:
        raise EmbeddingModelUnavailableError("model not found")

    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        _raise_model_error,
    )

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "EmbeddingModelUnavailableError: model not found" in stderr
    assert "recollectium init" in stderr

    with pytest.raises(EmbeddingModelUnavailableError, match="model not found"):
        _raise_model_error(None)


def test_cli_init_reports_generic_recollectium_error(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_recollectium_error(*args: object, **kwargs: object) -> int:
        raise RecollectiumError("init failed")

    monkeypatch.setattr(
        "recollectium.cli._handle_init_command", _raise_recollectium_error
    )

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "RecollectiumError: init failed" in stderr


def test_cli_update_without_memory_id_requires_memory_id(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _unexpected_core(*args, **kwargs):
        raise AssertionError("missing memory id should not initialise RecollectiumCore")

    monkeypatch.setattr("recollectium.cli.RecollectiumCore", _unexpected_core)

    exit_code, stdout, stderr = _run_cli(["update"], capsys)

    payload = json.loads(stderr)
    assert exit_code == 2
    assert stdout == ""
    assert payload["status"] == "validation_error"
    assert "recollectium upgrade" in payload["hint"]

    with pytest.raises(
        AssertionError, match="missing memory id should not initialise RecollectiumCore"
    ):
        _unexpected_core()


def _set_xdg_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))


def test_cli_service_discover_not_running_does_not_create_config(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)

    exit_code, stdout, stderr = _run_cli(["service", "discover"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 1
    assert stderr == ""
    assert payload["status"] == "not_running"
    assert payload["service"] is None
    assert "service start api" in payload["next_step"]
    assert not (tmp_path / "config" / "recollectium" / "config.json").exists()


def test_cli_service_discover_running_returns_success(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)

    def _fake_discover(config: object) -> dict[str, object]:
        return {
            "status": "running",
            "service": {"type": "api", "pid": 123},
            "paths": {},
        }

    monkeypatch.setattr("recollectium.cli.discover_service", _fake_discover)

    exit_code, stdout, stderr = _run_cli(["service", "discover"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["status"] == "running"


def test_cli_service_discover_invalid_config_exits_two(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"service": {"port": "bad"}}), encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "service", "discover"], capsys
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError" in stderr


def test_cli_service_discover_explicit_missing_config_exits_one(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    missing_path = tmp_path / "missing.json"

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(missing_path), "service", "discover"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"config file not found: {missing_path}" in stderr


def test_cli_service_discover_service_error_exits_two(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)

    def _raise_service_error(config: object) -> dict[str, object]:
        raise ServiceError("corrupted PID file")

    monkeypatch.setattr("recollectium.cli.discover_service", _raise_service_error)

    exit_code, stdout, stderr = _run_cli(["service", "discover"], capsys)

    assert exit_code == 2
    assert stdout == ""
    assert "corrupted PID file" in stderr


def test_cli_uninstall_preserves_data_and_uses_install_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    db_path = tmp_path / "data" / "recollectium" / "recollectium.db"
    model_cache_path = tmp_path / "cache" / "recollectium" / "models"
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    config_path.parent.mkdir(parents=True)
    db_path.parent.mkdir(parents=True)
    model_cache_path.mkdir(parents=True)
    metadata_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    db_path.write_text("preserved", encoding="utf-8")
    (model_cache_path / "model.bin").write_text("derived", encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "install_method": "bootstrap",
                "source_ref": "main",
                "managed_path_edits": ["profile path edit"],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "recollectium.cli.RecollectiumCore", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    run_calls: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        assert model_cache_path.exists()
        run_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("recollectium.cli.subprocess.run", _fake_run)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "uninstalled"
    assert payload["data"]["preserved"] is True
    assert payload["data"]["memories_preserved"] is True
    assert payload["data"]["config_preserved"] is True
    assert payload["data"]["derived_artifacts_removed"] is True
    assert payload["data"]["paths"]["database"] == str(db_path)
    assert payload["data"]["paths"]["model_cache"] == str(model_cache_path)
    assert payload["data"]["model_cache"]["deleted"] == [
        {"path": str(model_cache_path), "deleted": True}
    ]
    assert payload["package"]["install_method"] == "bootstrap"
    assert payload["package"]["source_ref"] == "main"
    assert payload["package"]["recommended"] == "uv tool uninstall recollectium"
    assert payload["package"]["uninstall"]["status"] == "removed"
    assert payload["package"]["managed_path_edits"] == ["profile path edit"]
    assert run_calls == [["uv", "tool", "uninstall", "recollectium"]]
    assert config_path.exists()
    assert db_path.read_text(encoding="utf-8") == "preserved"
    assert not model_cache_path.exists()


def test_cli_uninstall_uses_bootstrap_legacy_state_metadata_path(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "legacy-state"))
    monkeypatch.setattr(
        "recollectium.cli.user_state_dir",
        lambda _app_name: str(tmp_path / "platform-state"),
    )
    metadata_path = tmp_path / "legacy-state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap", "source_ref": "ci"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    monkeypatch.setattr(
        "recollectium.cli.subprocess.run",
        lambda _cmd, **_kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["package"]["install_method"] == "bootstrap"
    assert payload["package"]["source_ref"] == "ci"


def test_cli_uninstall_uses_windows_bootstrap_metadata_path(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    monkeypatch.setattr(
        "recollectium.cli.user_state_dir",
        lambda _app_name: str(tmp_path / "platform-state"),
    )
    metadata_path = tmp_path / "local-app-data" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap", "source_ref": "ci"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    monkeypatch.setattr(
        "recollectium.cli.subprocess.Popen",
        lambda *_args, **_kwargs: SimpleNamespace(pid=1234),
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["package"]["install_method"] == "bootstrap"
    assert payload["package"]["source_ref"] == "ci"
    assert payload["package"]["uninstall"]["status"] == "scheduled"


def test_cli_uninstall_purge_closes_log_handlers_before_deleting_logs(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    shutdown_called = False

    original_rmtree = shutil.rmtree

    def _shutdown() -> None:
        nonlocal shutdown_called
        shutdown_called = True

    def _assert_shutdown_before_delete(path: Path) -> None:
        if path == tmp_path / "state" / "recollectium" / "logs":
            assert shutdown_called
        original_rmtree(path)

    monkeypatch.setattr("recollectium.cli.logging.shutdown", _shutdown)
    monkeypatch.setattr(
        "recollectium.cli.shutil.rmtree", _assert_shutdown_before_delete
    )

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--purge", "--yes-delete-all-recollectium-data"], capsys
    )

    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert json.loads(stdout)["data"]["purge"]["deleted"]
    assert shutdown_called


def test_cli_uninstall_removes_managed_completion_block(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text(
        "before\n"
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n"
        "after\n",
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert bashrc.read_text(encoding="utf-8") == "before\nafter\n"
    assert payload["shell_completion"]["removed"] == [
        {"path": str(bashrc), "removed": True, "blocks": 1}
    ]


def test_cli_uninstall_dry_run_preserves_managed_completion_block(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bashrc = tmp_path / ".bashrc"
    content = (
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n"
    )
    bashrc.write_text(content, encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(["uninstall", "--dry-run"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert bashrc.read_text(encoding="utf-8") == content
    assert payload["shell_completion"]["removed"] == []
    assert any(
        item["path"] == str(bashrc) and item["reason"] == "dry_run"
        for item in payload["shell_completion"]["skipped"]
    )


def test_cli_uninstall_removes_completion_block_from_install_metadata_path(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    custom_rc = tmp_path / "custom" / "recollectium-shell-setup"
    custom_rc.parent.mkdir()
    custom_rc.write_text(
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n",
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(
            {
                "managed_path_edits": [
                    f'{custom_rc}: eval "$(recollectium completion --source bash)"'
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert custom_rc.read_text(encoding="utf-8") == "\n"
    assert payload["shell_completion"]["removed"] == [
        {"path": str(custom_rc), "removed": True, "blocks": 1}
    ]


def test_cli_uninstall_removes_powershell_completion_from_structured_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    profile = tmp_path / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "before\n"
        "# >>> recollectium completion >>>\n"
        "if (Get-Command recollectium -ErrorAction SilentlyContinue) {\n"
        "    Invoke-Expression ((& recollectium completion --source powershell) -join [Environment]::NewLine)\n"
        "}\n"
        "# <<< recollectium completion <<<\n"
        "after\n",
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(
            {
                "managed_completion_edits": [
                    {
                        "shell": "powershell",
                        "path": str(profile),
                        "source_command": "recollectium completion --source powershell",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert profile.read_text(encoding="utf-8") == "before\nafter\n"
    assert payload["shell_completion"]["removed"] == [
        {"path": str(profile), "removed": True, "blocks": 1}
    ]


def test_cli_uninstall_ignores_invalid_structured_completion_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"managed_completion_edits": ["not structured"]}),
        encoding="utf-8",
    )

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["shell_completion"]["removed"] == []


def test_cli_uninstall_bootstrap_reports_package_removal_without_starting_handoff(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap", "managed_path_edits": []}),
        encoding="utf-8",
    )
    run_calls: list[tuple[list[str], dict[str, Any]]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        run_calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("recollectium.cli.subprocess.run", _fake_run)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "uninstalled"
    assert payload["package"]["uninstall"]["status"] == "removed"
    assert (
        payload["package"]["uninstall"]["command"] == "uv tool uninstall recollectium"
    )
    assert run_calls[0][0] == ["uv", "tool", "uninstall", "recollectium"]
    assert run_calls[0][1]["check"] is False


def test_cli_uninstall_dry_run_does_not_start_bootstrap_package_removal(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap", "managed_path_edits": []}),
        encoding="utf-8",
    )
    run_calls: list[list[str]] = []
    monkeypatch.setattr(
        "recollectium.cli.subprocess.run",
        lambda cmd, **kwargs: run_calls.append(cmd),
    )

    exit_code, stdout, stderr = _run_cli(["uninstall", "--dry-run"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "dry_run"
    assert payload["package"]["uninstall"]["status"] == "dry_run"
    assert (
        payload["package"]["uninstall"]["command"] == "uv tool uninstall recollectium"
    )
    assert run_calls == []


@pytest.mark.parametrize(
    ("install_method", "expected_command"),
    [
        ("pip", f"{sys.executable} -m pip uninstall -y recollectium"),
        ("pipx", "pipx uninstall recollectium"),
        ("uv_tool", "uv tool uninstall recollectium"),
    ],
)
def test_cli_uninstall_dry_run_detects_package_manager_without_install_metadata(
    install_method: str,
    expected_command: str,
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setenv("RECOLLECTIUM_INSTALL_METHOD", install_method)
    run_calls: list[list[str]] = []
    monkeypatch.setattr(
        "recollectium.cli.subprocess.run",
        lambda cmd, **kwargs: run_calls.append(cmd),
    )

    exit_code, stdout, stderr = _run_cli(["uninstall", "--dry-run"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "dry_run"
    assert payload["data"]["preserved"] is True
    assert payload["package"]["install_method"] == install_method
    assert payload["package"]["recommended"] == expected_command
    assert payload["package"]["uninstall"]["status"] == "dry_run"
    assert payload["package"]["uninstall"]["command"] == expected_command
    assert run_calls == []


@pytest.mark.parametrize(
    ("install_method", "expected_argv"),
    [
        ("pip", [sys.executable, "-m", "pip", "uninstall", "-y", "recollectium"]),
        ("pipx", ["pipx", "uninstall", "recollectium"]),
        ("uv_tool", ["uv", "tool", "uninstall", "recollectium"]),
    ],
)
def test_cli_uninstall_detects_package_manager_without_install_metadata_for_removal(
    install_method: str,
    expected_argv: list[str],
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setenv("RECOLLECTIUM_INSTALL_METHOD", install_method)
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    run_calls: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        run_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("recollectium.cli.subprocess.run", _fake_run)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "uninstalled"
    assert payload["data"]["preserved"] is True
    assert payload["package"]["install_method"] == install_method
    assert payload["package"]["uninstall"]["status"] == "removed"
    assert payload["package"]["uninstall"]["argv"] == expected_argv
    assert run_calls == [expected_argv]


@pytest.mark.parametrize(
    ("install_method", "expected"),
    [
        ("bootstrap", "uv tool uninstall recollectium"),
        ("uv_tool", "uv tool uninstall recollectium"),
        ("pip", f"{sys.executable} -m pip uninstall -y recollectium"),
        ("pipx", "pipx uninstall recollectium"),
        (
            "source",
            "Remove the source checkout from your shell PATH or deactivate the editable install manually.",
        ),
        (
            "unknown",
            "Install method unknown; inspect how Recollectium was installed and use the matching package manager manually.",
        ),
        (
            "dev_source",
            "Install method unknown; inspect how Recollectium was installed and use the matching package manager manually.",
        ),
    ],
)
def test_cli_uninstall_package_instructions_use_canonical_install_methods(
    install_method: str, expected: str
) -> None:
    from recollectium.cli import _uninstall_package_instructions

    payload = _uninstall_package_instructions({"install_method": install_method})

    expected_method = install_method if install_method != "dev_source" else "unknown"
    assert payload["install_method"] == expected_method
    assert payload["recommended"] == expected
    if expected_method in {"bootstrap", "uv_tool", "pip", "pipx"}:
        assert payload["uninstall"] == {"status": "supported", "command": expected}
    else:
        assert payload["uninstall"] == {"status": "unsupported", "hint": expected}
    assert "source" in payload["commands"]
    assert "unknown" in payload["commands"]
    assert "dev_source" not in payload["commands"]


def test_cli_uninstall_bootstrap_command_uses_windows_uv_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.cli import _package_uninstall_command

    uv_path = tmp_path / "local-app-data" / "uv" / "uv.exe"
    uv_path.parent.mkdir(parents=True)
    uv_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    monkeypatch.setattr("recollectium.cli.shutil.which", lambda _name: None)

    command = _package_uninstall_command("bootstrap")

    assert command == [str(uv_path), "tool", "uninstall", "recollectium"]


def test_cli_uninstall_pip_command_uses_running_interpreter() -> None:
    from recollectium.cli import _package_uninstall_command

    command = _package_uninstall_command("pip")

    assert command == [sys.executable, "-m", "pip", "uninstall", "-y", "recollectium"]


def test_cli_uninstall_completion_cleanup_skips_duplicate_metadata_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.cli import _remove_completion_blocks

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text("", encoding="utf-8")

    payload = _remove_completion_blocks(
        {
            "managed_path_edits": [
                123,
                f'{bashrc}: eval "$(recollectium completion --source bash)"',
            ]
        },
        dry_run=True,
    )

    paths = [item["path"] for item in payload["targets"]]
    assert paths.count(str(bashrc)) == 1


def test_cli_uninstall_completion_cleanup_reports_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.cli import _remove_completion_blocks

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text("", encoding="utf-8")
    original_read_text = Path.read_text

    def _raise_for_bashrc(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == bashrc:
            raise OSError("cannot read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_for_bashrc)

    payload = _remove_completion_blocks(None, dry_run=False)

    assert any(
        item["path"] == str(bashrc) and item["reason"] == "read_error: cannot read"
        for item in payload["skipped"]
    )

    other_path = tmp_path / "other.rc"
    other_path.write_text("echo hi\n", encoding="utf-8")
    assert _raise_for_bashrc(other_path) == "echo hi\n"


def test_cli_uninstall_completion_cleanup_reports_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.cli import _remove_completion_blocks

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text(
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n",
        encoding="utf-8",
    )
    original_write_text = Path.write_text

    def _raise_for_bashrc(path: Path, *args: Any, **kwargs: Any) -> int:
        if path == bashrc:
            raise OSError("cannot write")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _raise_for_bashrc)

    payload = _remove_completion_blocks(None, dry_run=False)

    assert any(
        item["path"] == str(bashrc) and item["reason"] == "write_error: cannot write"
        for item in payload["skipped"]
    )

    other_path = tmp_path / "other.rc"
    assert _raise_for_bashrc(other_path, "echo hi\n") == 8


def test_cli_uninstall_stops_running_service(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    stopped_configs: list[object] = []

    def _fake_stop(config: object) -> int:
        stopped_configs.append(config)
        return 123

    monkeypatch.setattr("recollectium.cli.stop_service", _fake_stop)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["service"] == {"status": "stopped", "pid": 123}
    assert stopped_configs


def test_cli_uninstall_rejects_destructive_yes_without_purge(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--yes-delete-all-recollectium-data"], capsys
    )

    assert exit_code == 2
    assert stdout == ""
    assert "requires --purge" in stderr


def test_cli_uninstall_reports_explicit_missing_config(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(tmp_path / "missing.json"), "uninstall"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert "config file not found" in stderr


def test_cli_uninstall_reports_invalid_config(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"logging": {"level": "bad"}}), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "uninstall"], capsys
    )

    assert exit_code == 2
    assert stdout == ""
    assert "ValidationError" in stderr


def test_cli_uninstall_reports_service_stop_error(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_service_error(_config: object) -> None:
        raise ServiceError("service stop failed")

    monkeypatch.setattr("recollectium.cli.stop_service", _raise_service_error)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "service stop failed" in stderr


def test_cli_uninstall_ignores_unreadable_install_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text("not json", encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["package"]["install_method"] == "source"
    assert payload["package"]["uninstall"]["status"] == "unsupported"


def test_cli_uninstall_falls_back_to_detection_for_non_object_install_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(json.dumps(["bootstrap"]), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["package"]["install_method"] == "source"
    assert payload["package"]["uninstall"]["status"] == "unsupported"


def test_cli_uninstall_purge_dry_run_lists_targets_without_deleting(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    data_dir = tmp_path / "data" / "recollectium"
    cache_dir = tmp_path / "cache" / "recollectium"
    logs_dir = tmp_path / "state" / "recollectium" / "logs"
    runtime_dir = tmp_path / "runtime" / "recollectium"
    for directory in (config_path.parent, data_dir, cache_dir, logs_dir, runtime_dir):
        directory.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    (data_dir / "recollectium.db").write_text("memory", encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(["uninstall", "--purge", "--dry-run"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["service"] == {
        "status": "dry_run",
        "note": "service would be stopped",
    }
    assert payload["data"]["preserved"] is False
    assert payload["data"]["purge"]["dry_run"] is True
    assert payload["data"]["purge"]["deleted"] == []
    assert config_path.exists()
    assert (data_dir / "recollectium.db").exists()


def test_cli_uninstall_purge_cancelled_by_confirmation(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    stopped = False

    def _stop_service(_config: Any) -> None:
        nonlocal stopped
        stopped = True

    bashrc = tmp_path / ".bashrc"
    bashrc.write_text(
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("recollectium.cli.stop_service", _stop_service)
    monkeypatch.setattr(
        "recollectium.cli.subprocess.run",
        lambda _cmd, **_kwargs: pytest.fail("package removal should not run"),
    )
    monkeypatch.setattr("sys.stdin.readline", lambda: "no\n")

    exit_code, stdout, stderr = _run_cli(["uninstall", "--purge"], capsys)

    assert exit_code == 1
    assert stdout == ""
    assert "purge cancelled" in stderr
    assert not stopped
    assert "recollectium completion --source bash" in bashrc.read_text(encoding="utf-8")

    _stop_service(object())


def test_cli_uninstall_purge_accepts_interactive_confirmation(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    monkeypatch.setattr("sys.stdin.readline", lambda: "delete all recollectium data\n")

    exit_code, stdout, stderr = _run_cli(["uninstall", "--purge"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert str(config_path) in stderr
    assert payload["data"]["purge"]["deleted"]


def test_cli_uninstall_purge_deletes_recollectium_owned_paths(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    data_dir = tmp_path / "data" / "recollectium"
    cache_dir = tmp_path / "cache" / "recollectium"
    logs_dir = tmp_path / "state" / "recollectium" / "logs"
    runtime_dir = tmp_path / "runtime" / "recollectium"
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    for directory in (config_path.parent, data_dir, cache_dir, logs_dir, runtime_dir):
        directory.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    (data_dir / "recollectium.db").write_text("memory", encoding="utf-8")
    metadata_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--purge", "--yes-delete-all-recollectium-data"], capsys
    )

    payload = json.loads(stdout)
    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert payload["data"]["purge"]["deleted"]
    assert not config_path.parent.exists()
    assert not data_dir.exists()
    assert not cache_dir.exists()
    assert not logs_dir.exists()
    assert not runtime_dir.exists()
    assert (tmp_path / "config").exists()
    assert (tmp_path / "data").exists()


def test_cli_uninstall_purge_deletes_macos_application_support_install_metadata(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    application_support_dir = (
        tmp_path / "Library" / "Application Support" / "recollectium"
    )
    config_path = application_support_dir / "config.json"
    logs_dir = application_support_dir / "logs"
    metadata_path = application_support_dir / "install.json"
    macos_dirs = {
        "config": application_support_dir,
        "data": application_support_dir,
        "cache": application_support_dir,
        "logs": logs_dir,
        "runtime": application_support_dir,
    }
    config_path.parent.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap"}), encoding="utf-8"
    )
    monkeypatch.setattr(
        "recollectium.cli._resolve_xdg_dirs", lambda _overrides: macos_dirs
    )
    monkeypatch.setattr(
        "recollectium.cli.user_state_dir",
        lambda _app_name: str(metadata_path.parent),
    )
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--purge", "--yes-delete-all-recollectium-data"], capsys
    )

    payload = json.loads(stdout)
    skipped = payload["data"]["purge"]["skipped"]
    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert not metadata_path.exists()
    assert (
        sum(
            item["path"] == str(metadata_path)
            for item in payload["data"]["purge"]["deleted"]
        )
        == 1
    )
    assert not any(item["path"] == str(metadata_path) for item in skipped)


def test_cli_uninstall_purge_reports_delete_errors(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    def _raise_remove(_path: Path) -> None:
        raise OSError("delete failed")

    monkeypatch.setattr("recollectium.cli.shutil.rmtree", _raise_remove)

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--purge", "--yes-delete-all-recollectium-data"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    assert "delete failed" in stderr


def test_cli_uninstall_purge_skips_shared_cache_override(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    shared_cache = tmp_path / "recollectium" / "shared-cache"
    model_cache = shared_cache / "models"
    model_cache.mkdir(parents=True)
    (model_cache / "model.bin").write_text("derived", encoding="utf-8")
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_data = deepcopy(DEFAULTS)
    config_data["directories"] = {"cache": str(shared_cache)}
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        ["uninstall", "--purge", "--yes-delete-all-recollectium-data"], capsys
    )

    payload = json.loads(stdout)
    skipped = payload["data"]["purge"]["skipped"]
    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert f"  {shared_cache}\n" not in stderr
    assert str(model_cache) in stderr
    assert shared_cache.exists()
    assert not model_cache.exists()
    assert any(
        item["path"] == str(shared_cache) and item["reason"] == "not_recollectium_owned"
        for item in skipped
    )
    assert any(
        item["path"] == str(model_cache) for item in payload["data"]["purge"]["deleted"]
    )


def test_cli_uninstall_purge_skips_explicit_config_outside_recollectium_dir(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "uninstall",
            "--purge",
            "--yes-delete-all-recollectium-data",
        ],
        capsys,
    )

    payload = json.loads(stdout)
    assert exit_code == 0
    assert "permanently deleted" in stderr
    assert str(config_path) not in stderr
    assert config_path.exists()
    assert any(
        item["path"] == str(config_path) and item["reason"] == "not_recollectium_owned"
        for item in payload["data"]["purge"]["skipped"]
    )


def test_cli_uninstall_purge_skips_duplicate_targets(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    duplicate_dir = tmp_path / "data" / "recollectium"
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    duplicate_dir.mkdir(parents=True)
    config_path.parent.mkdir(parents=True)
    config_data = deepcopy(DEFAULTS)
    config_data["directories"] = {
        "data": str(duplicate_dir),
        "cache": str(duplicate_dir),
    }
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(["uninstall", "--purge", "--dry-run"], capsys)

    payload = json.loads(stdout)
    paths = [item["path"] for item in payload["data"]["purge"]["targets"]]
    assert exit_code == 0
    assert stderr == ""
    assert paths.count(str(duplicate_dir)) == 1


def test_cli_uninstall_purge_marks_suspicious_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _delete_purge_target

    monkeypatch.setattr(Path, "home", lambda: Path.cwd())

    payload = _delete_purge_target(Path.cwd(), dry_run=True)

    assert payload == {
        "path": str(Path.cwd()),
        "deleted": False,
        "reason": "suspicious_path",
    }


def test_cli_reinstall_after_safe_uninstall_reuses_existing_config_and_database(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    monkeypatch.setattr(
        "recollectium.cli.BuiltinFastEmbedProvider.ensure_ready",
        lambda self: None,
    )

    assert _run_cli(["init"], capsys)[0] == 0
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    db_path = tmp_path / "data" / "recollectium" / "recollectium.db"
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    config_data["service"]["port"] = 9090
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    db_size = db_path.stat().st_size

    assert _run_cli(["uninstall"], capsys)[0] == 0
    assert _run_cli(["init"], capsys)[0] == 0

    reloaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert reloaded["service"]["port"] == 9090
    assert db_path.stat().st_size == db_size


def test_cli_uninstall_dry_run_without_purge_prints_instructions(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    model_cache_path = tmp_path / "cache" / "recollectium" / "models"
    config_path.parent.mkdir(parents=True)
    model_cache_path.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")

    exit_code, stdout, stderr = _run_cli(["uninstall", "--dry-run"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["status"] == "dry_run"
    assert payload["data"]["preserved"] is True
    assert payload["data"]["derived_artifacts_removed"] is False
    assert payload["data"]["model_cache"]["skipped"] == [
        {"path": str(model_cache_path), "deleted": False, "reason": "dry_run"}
    ]
    assert payload["service"]["status"] == "dry_run"
    assert model_cache_path.exists()


def test_cli_uninstall_removes_model_cache_inside_custom_cache_dir(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    custom_cache = tmp_path / "shared-cache"
    model_cache_path = custom_cache / "models"
    model_cache_path.mkdir(parents=True)
    (custom_cache / "keep.txt").write_text("keep", encoding="utf-8")
    (model_cache_path / "model.bin").write_text("derived", encoding="utf-8")
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    config_path.parent.mkdir(parents=True)
    config_data = deepcopy(DEFAULTS)
    config_data["directories"] = {"cache": str(custom_cache)}
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["data"]["model_cache"]["deleted"] == [
        {"path": str(model_cache_path), "deleted": True}
    ]
    assert custom_cache.exists()
    assert (custom_cache / "keep.txt").exists()
    assert not model_cache_path.exists()


def test_cli_uninstall_reports_model_cache_cleanup_failure_after_package_removal(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    config_path = tmp_path / "config" / "recollectium" / "config.json"
    model_cache_path = tmp_path / "cache" / "recollectium" / "models"
    metadata_path = tmp_path / "state" / "recollectium" / "install.json"
    config_path.parent.mkdir(parents=True)
    model_cache_path.mkdir(parents=True)
    metadata_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(DEFAULTS), encoding="utf-8")
    metadata_path.write_text(
        json.dumps({"install_method": "bootstrap", "source_ref": "main"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    run_calls: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        run_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def _fail_rmtree(path: Path) -> None:
        assert run_calls == [["uv", "tool", "uninstall", "recollectium"]]
        raise OSError("permission denied")

    monkeypatch.setattr("recollectium.cli.subprocess.run", _fake_run)
    monkeypatch.setattr("recollectium.cli.shutil.rmtree", _fail_rmtree)

    exit_code, stdout, stderr = _run_cli(["uninstall"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 1
    assert stderr == ""
    assert payload["status"] == "uninstalled_with_warnings"
    assert payload["package"]["uninstall"]["status"] == "removed"
    assert payload["data"]["derived_artifacts_removed"] is False
    assert payload["data"]["model_cache"]["status"] == "failed"
    assert payload["data"]["model_cache"]["skipped"] == [
        {
            "path": str(model_cache_path),
            "deleted": False,
            "reason": "cleanup_error: permission denied",
        }
    ]
    assert model_cache_path.exists()


def test_cli_uninstall_dry_run_does_not_stop_service(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_xdg_home(monkeypatch, tmp_path)
    stop_calls: list[object] = []

    def _record_stop(config: object) -> int:
        stop_calls.append(config)
        return 123

    monkeypatch.setattr("recollectium.cli.stop_service", _record_stop)

    _run_cli(["uninstall", "--dry-run"], capsys)
    assert stop_calls == []

    _run_cli(["uninstall", "--purge", "--dry-run"], capsys)
    assert stop_calls == []

    _record_stop(object())


def test_cli_uninstall_config_is_recollectium_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _UninstallConfig
    from recollectium.config import RecollectiumConfig

    conf = _UninstallConfig(
        effective_config={},
        xdg_dirs={},
        config_path=tmp_path / "cfg.json",
        database_path=tmp_path / "db.db",
    )
    assert isinstance(conf, RecollectiumConfig)


class TestMcpStdioErrorPaths:
    def test_mcp_stdio_file_not_found(self, tmp_path, capsys) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_data = dict(DEFAULTS)
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        with patch("recollectium.cli.RecollectiumCore") as mock_core:
            mock_core.side_effect = FileNotFoundError("no database found")
            exit_code, stdout, stderr = _run_cli(
                ["--config", str(config_path), "mcp-stdio"],
                capsys,
            )

        assert exit_code == 1
        assert stdout == ""
        assert "no database found" in stderr

    def test_mcp_stdio_validation_error(self, tmp_path, capsys) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_data = dict(DEFAULTS)
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        with patch("recollectium.cli.RecollectiumCore") as mock_core:
            mock_core.side_effect = ValidationError("bad config value")
            exit_code, stdout, stderr = _run_cli(
                ["--config", str(config_path), "mcp-stdio"],
                capsys,
            )

        assert exit_code == 2
        assert stdout == ""
        assert "ValidationError: bad config value" in stderr

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (
                EmbeddingReadinessTimeoutError("startup timed out"),
                "EmbeddingReadinessTimeoutError: startup timed out",
            ),
            (
                EmbeddingModelUnavailableError("model not found"),
                "EmbeddingModelUnavailableError: model not found",
            ),
            (
                EmbeddingProviderUnavailableError("provider unavailable"),
                "EmbeddingProviderUnavailableError: provider unavailable",
            ),
        ],
    )
    def test_mcp_stdio_readiness_errors_return_guidance(
        self, tmp_path, capsys, error: Exception, expected: str
    ) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_data = dict(DEFAULTS)
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        class FakeCore:
            def _ensure_model_ready(self) -> None:
                raise error

        with patch("recollectium.cli.RecollectiumCore", return_value=FakeCore()):
            exit_code, stdout, stderr = _run_cli(
                ["--config", str(config_path), "mcp-stdio"],
                capsys,
            )

        assert exit_code == 1
        assert stdout == ""
        assert expected in stderr
        assert "recollectium init" in stderr

    def test_mcp_stdio_happy_path_returns_zero(self, tmp_path, capsys) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_data = dict(DEFAULTS)
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        class FakeMCP:
            async def run_stdio_async(self) -> None:
                pass

        with (
            patch("recollectium.cli.RecollectiumCore"),
            patch("recollectium.cli.create_mcp_server", return_value=FakeMCP()),
        ):
            exit_code, stdout, stderr = _run_cli(
                ["--config", str(config_path), "mcp-stdio"],
                capsys,
            )

        assert exit_code == 0

    def test_mcp_stdio_runtime_error(self, tmp_path, capsys) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_data = dict(DEFAULTS)
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        class FakeMCP:
            def run_stdio_async(self) -> None:
                raise RuntimeError("stdio transport broken")

        with (
            patch("recollectium.cli.RecollectiumCore"),
            patch("recollectium.cli.create_mcp_server", return_value=FakeMCP()),
        ):
            exit_code, stdout, stderr = _run_cli(
                ["--config", str(config_path), "mcp-stdio"],
                capsys,
            )

        assert exit_code == 1
        assert stdout == ""
        assert "stdio transport broken" in stderr


class TestServiceStatusCorruptConfig:
    def test_status_validation_error_on_bad_config(self, tmp_path, capsys) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.json"

        config_data = dict(DEFAULTS)
        config_data["logging"] = {"level": "invalid"}
        config_data["directories"] = {
            "data": str(tmp_path / "data"),
            "cache": str(tmp_path / "cache"),
            "logs": str(tmp_path / "logs"),
            "runtime": str(tmp_path / "run"),
        }
        config_path.write_text(json.dumps(config_data))

        exit_code, stdout, stderr = _run_cli(
            ["--config", str(config_path), "service", "status"],
            capsys,
        )

        assert exit_code == 2
        assert stdout == ""
        assert "logging.level must be one of" in stderr


# ---------------------------------------------------------------------------
#  shell completion tests
# ---------------------------------------------------------------------------


def test_cli_completion_help_prints_human_readable_instructions(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "bash"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "Add this line to your shell rc file" in stdout
    assert 'eval "$(recollectium completion --source bash)"' in stdout
    assert "recollectium completion --install bash" in stdout


def test_cli_completion_default_prints_human_readable_instructions(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "zsh"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "Add this line to your shell rc file" in stdout
    assert 'eval "$(recollectium completion --source zsh)"' in stdout
    assert "recollectium completion --install zsh" in stdout


def test_cli_completion_default_prints_human_readable_instructions_fish(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "fish"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "Add this line to your shell rc file" in stdout
    assert 'eval "$(recollectium completion --source fish)"' in stdout
    assert "recollectium completion --install fish" in stdout


def test_cli_completion_powershell_prints_human_readable_instructions(
    capsys: CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "powershell"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "$PROFILE.CurrentUserCurrentHost" in stdout
    assert (
        "Invoke-Expression ((& recollectium completion --source powershell) -join [Environment]::NewLine)"
        in stdout
    )
    assert "recollectium completion --install powershell" in stdout
    assert "$PROFILE.CurrentUserAllHosts" in stdout


def test_cli_completion_source_bash_prints_shellcode(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "--source", "bash"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "register-python-argcomplete" in stdout or "complete " in stdout
    assert "recollectium" in stdout


def test_cli_completion_source_zsh_prints_shellcode(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "--source", "zsh"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert len(stdout) > 0


def test_cli_completion_source_fish_prints_shellcode(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, stdout, stderr = _run_cli(["completion", "--source", "fish"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert len(stdout) > 0


def test_cli_completion_source_powershell_prints_dynamic_wrapper(
    capsys: CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = _run_cli(
        ["completion", "--source", "powershell"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Register-ArgumentCompleter" in stdout
    assert "recollectium completion --complete-line" in stdout
    assert "CompletionResult" in stdout


def test_cli_completion_dynamic_helper_completes_commands(
    capsys: CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = _run_cli(
        ["completion", "--complete-line", "recollectium conf"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout) == ["config"]


def test_cli_completion_dynamic_helper_completes_config_keys(
    capsys: CaptureFixture[str],
) -> None:
    exit_code, stdout, stderr = _run_cli(
        ["completion", "--complete-line", "recollectium config get log"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout) == [
        "logging.level",
        "logging.format",
        "logging.max_bytes",
        "logging.backup_count",
    ]


def test_cli_completion_auto_detect_shell(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")

    exit_code, stdout, stderr = _run_cli(["completion", "--source"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "recollectium" in stdout


def test_cli_completion_unknown_shell_returns_validation_error(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("PSModulePath", raising=False)

    exit_code, stdout, stderr = _run_cli(["completion"], capsys)

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "validation_error"
    assert payload["message"] == "Could not detect a supported shell."


def test_cli_completion_auto_detect_non_standard_shell_returns_validation_error(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHELL", "/bin/tcsh")
    monkeypatch.delenv("PSModulePath", raising=False)

    exit_code, stdout, stderr = _run_cli(["completion"], capsys)

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "validation_error"
    assert payload["message"] == "Could not detect a supported shell."


def test_cli_completion_auto_detect_powershell_from_environment(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setenv("PSModulePath", "C:/Users/example/Documents/PowerShell/Modules")

    exit_code, stdout, stderr = _run_cli(["completion", "--source"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert "Register-ArgumentCompleter" in stdout


def test_cli_completion_auto_detect_with_source(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHELL", "/bin/zsh")

    exit_code, stdout, stderr = _run_cli(["completion", "--source"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert len(stdout) > 0


def test_cli_completion_install_yes_writes_rc_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "installed"
    assert payload["rc_file"] == str(rc_path)
    assert payload["shell"] == "bash"
    content = rc_path.read_text(encoding="utf-8")
    assert "# >>> recollectium completion >>>" in content
    assert 'eval "$(recollectium completion --source bash)"' in content
    assert "# <<< recollectium completion <<<" in content


def test_cli_completion_install_powershell_uses_current_user_current_host_profile(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    monkeypatch.setenv("RECOLLECTIUM_POWERSHELL_PROFILE", str(profile))

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "powershell", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "installed"
    assert payload["shell"] == "powershell"
    assert payload["rc_file"] == str(profile)
    assert payload["profile"] == str(profile)
    assert payload["updated"] is False
    content = profile.read_text(encoding="utf-8")
    assert "Get-Command recollectium" in content
    assert "recollectium completion --source powershell" in content
    assert "-join [Environment]::NewLine" in content
    assert "Register-ArgumentCompleter" not in content
    assert "recollectium completion --complete-line" not in content


def test_cli_completion_install_powershell_dedups_existing_source_line(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "recollectium completion --source powershell\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RECOLLECTIUM_POWERSHELL_PROFILE", str(profile))

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "powershell", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "already_installed"
    assert payload["profile"] == str(profile)
    assert payload["updated"] is False


def test_cli_completion_install_powershell_reports_current_managed_block(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        "# >>> recollectium completion >>>\n"
        "if (Get-Command recollectium -ErrorAction SilentlyContinue) {\n"
        "    Invoke-Expression ((& recollectium completion --source powershell) -join [Environment]::NewLine)\n"
        "}\n"
        "# <<< recollectium completion <<<\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RECOLLECTIUM_POWERSHELL_PROFILE", str(profile))

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "powershell", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "already_installed"
    assert payload["profile"] == str(profile)
    assert payload["updated"] is False


def test_cli_completion_install_refreshes_existing_managed_block(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(
        "before\n"
        "# >>> recollectium completion >>>\n"
        "old completion\n"
        "# <<< recollectium completion <<<\n"
        "after\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "updated"
    content = rc_path.read_text(encoding="utf-8")
    assert "old completion" not in content
    assert content.count("# >>> recollectium completion >>>") == 1
    assert 'eval "$(recollectium completion --source bash)"' in content


def test_cli_completion_install_reports_already_installed_for_current_managed_block(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(
        "# >>> recollectium completion >>>\n"
        'eval "$(recollectium completion --source bash)"\n'
        "# <<< recollectium completion <<<\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "already_installed"
    assert (
        rc_path.read_text(encoding="utf-8").count("# >>> recollectium completion >>>")
        == 1
    )


def test_cli_completion_install_dedup_when_already_present(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(
        'eval "$(recollectium completion --source bash)"\n', encoding="utf-8"
    )
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "already_installed"
    occurrences = rc_path.read_text(encoding="utf-8").count(
        "recollectium completion --source"
    )
    assert occurrences == 1


def test_cli_completion_install_unknown_shell(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("recollectium.cli._COMPLETION_RC_FILES", {"bash": ".bashrc"})
    monkeypatch.setenv("SHELL", "/bin/zsh")

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "zsh", "--yes"], capsys
    )

    assert exit_code == 1
    assert "No rc file mapping" in stderr


def test_cli_completion_install_refuses_without_confirm_in_non_tty(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)
    monkeypatch.setattr("sys.stdin.readline", lambda: "no\n")

    exit_code, stdout, stderr = _run_cli(["completion", "--install", "bash"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "operation_failed"
    assert payload["message"] == "Completion installation cancelled."


def test_cli_completion_install_accepts_confirm(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)
    monkeypatch.setattr("sys.stdin.readline", lambda: "yes\n")

    exit_code, stdout, stderr = _run_cli(["completion", "--install", "bash"], capsys)

    assert exit_code == 0
    payload = json.loads(stdout)
    assert payload["status"] == "installed"
    assert payload["rc_file"] == str(rc_path)


def test_cli_completion_unreadable_rc_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.mkdir()
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 1
    assert "Could not read rc file" in stderr


def test_cli_completion_unwritable_rc_file(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_path = tmp_path / ".bashrc"
    rc_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)

    original_write_text = Path.write_text

    def _fake_write_text(self: Path, *args: Any, **kwargs: Any) -> int:
        if self == rc_path:
            raise OSError("Permission denied")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _fake_write_text)

    exit_code, stdout, stderr = _run_cli(
        ["completion", "--install", "bash", "--yes"], capsys
    )

    assert exit_code == 1
    assert "Could not write to" in stderr

    assert _fake_write_text(tmp_path / "other.rc", "echo hi\n", encoding="utf-8") == 8


def test_cli_completion_help_includes_completion(
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    top_level = _run_help(["--help"], capsys)
    assert "completion" in top_level

    completion_help = _run_help(["completion", "--help"], capsys)
    assert "--source" in completion_help
    assert "--install" in completion_help
    assert "--yes" in completion_help
    assert "bash" in completion_help
    assert "zsh" in completion_help
    assert "fish" in completion_help


def test_cli_completion_does_not_interfere_with_normal_commands(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """argcomplete.autocomplete(parser) must be a silent no-op for normal invocations."""
    _set_xdg_home(monkeypatch, tmp_path)
    exit_code, stdout, stderr = _run_cli(["--version"], capsys)
    assert exit_code == 0
    assert "recollectium" in stdout
    assert stderr == ""


def test_cli_completion_config_key_completer_registered(
    capsys: CaptureFixture[str],
) -> None:
    config_get_help = _run_help(["config", "get", "--help"], capsys)
    assert "key" in config_get_help

    config_set_help = _run_help(["config", "set", "--help"], capsys)
    assert "key" in config_set_help

    config_unset_help = _run_help(["config", "unset", "--help"], capsys)
    assert "key" in config_unset_help


# -- workspace CLI --------------------------------------------------------


def test_workspace_list_empty_database(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace list on a fresh database returns an empty array."""
    db_path = tmp_path / "test.db"
    SQLiteMemoryStore(db_path)
    exit_code, out, err = _run_cli(
        ["--db", str(db_path), "workspace", "list"],
        capsys,
    )
    assert exit_code == 0
    assert json.loads(out) == []


def test_workspace_list_returns_sorted_uids(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace list returns distinct workspace UIDs sorted."""

    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space="workspace", type="fact", content="a", workspace_uid="project-b"
    )
    core.add_memory(
        space="workspace", type="fact", content="b", workspace_uid="project-a"
    )

    exit_code, out, err = _run_cli(
        ["--db", str(tmp_path / "test.db"), "workspace", "list"],
        capsys,
    )
    assert exit_code == 0
    assert json.loads(out) == ["project-a", "project-b"]


def test_workspace_rename_moves_memories(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace rename migrates memories and prints result."""

    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="old-ws")
    core.add_memory(space="workspace", type="fact", content="b", workspace_uid="old-ws")

    exit_code, out, err = _run_cli(
        [
            "--db",
            str(tmp_path / "test.db"),
            "workspace",
            "rename",
            "old-ws",
            "new-ws",
        ],
        capsys,
    )
    assert exit_code == 0
    result = json.loads(out)
    assert result["old_uid"] == "old-ws"
    assert result["new_uid"] == "new-ws"
    assert result["memories_updated"] == 2


def test_workspace_rename_nonexistent_fails(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace rename with nonexistent old_uid returns error."""
    db_path = tmp_path / "test.db"
    SQLiteMemoryStore(db_path)

    exit_code, out, err = _run_cli(
        [
            "--db",
            str(db_path),
            "workspace",
            "rename",
            "nonexistent",
            "new",
        ],
        capsys,
    )
    assert exit_code == 1
    assert "no workspace memories found" in err.lower()


def test_workspace_rename_noop_same_uid(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace rename to same UID after normalization is a no-op."""

    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(space="workspace", type="fact", content="a", workspace_uid="my-ws")

    # "MY-WS" normalizes to "my-ws" — same as stored
    exit_code, out, err = _run_cli(
        [
            "--db",
            str(tmp_path / "test.db"),
            "workspace",
            "rename",
            "MY-WS",
            "my-ws",
        ],
        capsys,
    )
    assert exit_code == 0
    result = json.loads(out)
    assert result["memories_updated"] == 0


def test_config_set_rejects_invalid_value(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """config set with an invalid value fails with validation error."""
    # workspace.uid_normalization only accepts 'normalize' or 'exact'
    exit_code, out, err = _run_cli(
        ["config", "set", "workspace.uid_normalization", "bogus"],
        capsys,
    )
    assert exit_code == 2
    assert "ValidationError" in err or "normalize, exact" in err


def test_workspace_rename_empty_uid_fails(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """workspace rename with whitespace-only UID returns validation error."""
    db_path = tmp_path / "test.db"
    SQLiteMemoryStore(db_path)
    exit_code, out, err = _run_cli(
        ["--db", str(db_path), "workspace", "rename", "   ", "valid"],
        capsys,
    )
    assert exit_code == 2
    assert "empty string" in err.lower() or "validation" in err.lower()


def test_workspace_alias_cli_commands_round_trip(tmp_path, capsys) -> None:
    db_path = tmp_path / "workspace-alias-cli.db"
    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "workspace",
            "--type",
            "fact",
            "--workspace-uid",
            "Canonical",
            "--content",
            "a",
        ],
        capsys,
    )
    assert exit_code == 0
    assert stderr == ""

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "workspace", "alias", "add", "Canonical", "Legacy"],
        capsys,
    )
    assert exit_code == 0
    assert json.loads(stdout)["alias"]["alias_uid"] == "legacy"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "workspace", "resolve", "Legacy"], capsys
    )
    assert exit_code == 0
    assert json.loads(stdout)["canonical_uid"] == "canonical"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "workspace", "list", "--include-aliases"], capsys
    )
    assert exit_code == 0
    assert json.loads(stdout) == [{"workspace_uid": "canonical", "aliases": ["legacy"]}]

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "workspace",
            "alias",
            "list",
            "--workspace",
            "Canonical",
        ],
        capsys,
    )
    assert exit_code == 0
    assert json.loads(stdout)[0]["alias_uid"] == "legacy"

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "workspace", "alias", "remove", "Legacy"], capsys
    )
    assert exit_code == 0
    assert json.loads(stdout)["alias_uid"] == "legacy"


def test_workspace_alias_cli_migrate_existing_conflict(tmp_path, capsys) -> None:
    db_path = tmp_path / "workspace-alias-cli-conflict.db"
    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "add",
            "--space",
            "workspace",
            "--type",
            "fact",
            "--workspace-uid",
            "Legacy",
            "--content",
            "a",
        ],
        capsys,
    )
    assert exit_code == 0

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(db_path), "workspace", "alias", "add", "Canonical", "Legacy"],
        capsys,
    )
    assert exit_code == 1
    assert "Use --migrate-existing" in stderr

    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(db_path),
            "workspace",
            "alias",
            "add",
            "Canonical",
            "Legacy",
            "--migrate-existing",
        ],
        capsys,
    )
    assert exit_code == 0
    assert json.loads(stdout)["migrated_memories"] == 1


def test_cli_uninstall_package_applies_success_and_failure_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _remove_installed_package

    completed = subprocess.CompletedProcess(
        ["uv", "tool", "uninstall", "recollectium"],
        3,
        "removed stdout",
        "removed stderr",
    )
    monkeypatch.setattr(cli_module.subprocess, "run", lambda *args, **kwargs: completed)

    payload = _remove_installed_package({"install_method": "uv_tool"}, dry_run=False)

    assert payload["uninstall"]["status"] == "failed"
    assert payload["uninstall"]["stdout"] == "removed stdout"
    assert payload["uninstall"]["stderr"] == "removed stderr"
    assert "package removal failed" in payload["uninstall"]["hint"]


def test_cli_uninstall_package_reports_missing_package_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _remove_installed_package

    def raise_missing(
        *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("missing uv")

    monkeypatch.setattr(cli_module.subprocess, "run", raise_missing)

    payload = _remove_installed_package({"install_method": "uv_tool"}, dry_run=False)

    assert payload["uninstall"]["status"] == "failed"
    assert payload["uninstall"]["returncode"] == 127
    assert "missing uv" in payload["uninstall"]["stderr"]


def test_cli_uninstall_package_reports_missing_windows_powershell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _remove_installed_package

    def raise_missing(command: list[str]) -> dict[str, object]:
        raise FileNotFoundError("missing powershell")

    monkeypatch.setattr(cli_module.sys, "platform", "win32")
    monkeypatch.setattr(cli_module, "_schedule_windows_package_removal", raise_missing)

    payload = _remove_installed_package({"install_method": "uv_tool"}, dry_run=False)

    assert payload["uninstall"]["status"] == "failed"
    assert payload["uninstall"]["returncode"] == 127
    assert "missing powershell" in payload["uninstall"]["stderr"]


def test_cli_resolve_executable_uses_windows_path_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from recollectium.cli import _resolve_executable

    monkeypatch.setattr(cli_module.sys, "platform", "win32")
    monkeypatch.setattr(cli_module, "_safe_which", lambda name: f"C:/Tools/{name}.exe")

    assert _resolve_executable("uv") == "C:/Tools/uv.exe"


def test_cli_recollectium_owned_path_detection(tmp_path: Path) -> None:
    from recollectium.cli import _is_recollectium_owned_path

    assert _is_recollectium_owned_path(tmp_path / "recollectium" / "data") is True
    assert (
        _is_recollectium_owned_path(tmp_path / "Recollectium" / "config.json") is True
    )
    assert _is_recollectium_owned_path(tmp_path / "other" / "config.json") is False
    assert _is_recollectium_owned_path(tmp_path / "other" / "notes.txt") is False


def test_cli_upgrade_ignores_config_errors_during_apply(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )

    def raise_config(*args: object, **kwargs: object) -> object:
        raise ValidationError("bad config")

    monkeypatch.setattr(cli_mod, "RecollectiumConfig", raise_config)
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "ok", "")
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "updated"
    assert payload["services_to_restart"] == []


def test_cli_upgrade_version_selector_targets_release(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(cli_mod, "write_install_metadata_update", lambda plan: None)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--version", "1.2.3"], capsys)

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "updated"
    assert payload["target_kind"] == "release"
    assert payload["target_ref"] == "v1.2.3"
    assert payload["command"] == [
        "uv",
        "tool",
        "install",
        "--force",
        "recollectium==1.2.3",
    ]


def test_cli_upgrade_main_check_resolves_remote_ref(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, MainRefInfo

    calls: list[tuple[str, str, int, bool]] = []
    commit = "a" * 40
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("--main must not fetch releases")
        ),
    )

    def _resolve_main_ref(
        *, repo, install_method, runner, source_root, timeout_seconds, non_mutating
    ):
        calls.append((repo, install_method, timeout_seconds, non_mutating))
        return MainRefInfo(remote_commit=commit)

    monkeypatch.setattr(cli_mod, "resolve_main_ref", _resolve_main_ref)
    monkeypatch.setattr(
        cli_mod,
        "write_install_metadata_update",
        lambda plan: (_ for _ in ()).throw(
            AssertionError("check must not write metadata")
        ),
    )

    exit_code, stdout, stderr = _run_cli(
        ["upgrade", "--check", "--main", "--repo", "owner/repo", "--timeout", "7"],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    assert calls == [("owner/repo", "uv_tool", 7, True)]
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["target_kind"] == "main"
    assert payload["target_commit"] == commit
    assert payload["will_update_metadata"] is False


def test_cli_upgrade_main_lookup_error_uses_main_message(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseLookupError

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")

    def _resolve_main_ref(*args, **kwargs):
        raise ReleaseLookupError("offline", reason="main_lookup_failed")

    monkeypatch.setattr(cli_mod, "resolve_main_ref", _resolve_main_ref)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check", "--main"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "network_error"
    assert payload["message"] == "Could not resolve Recollectium main from GitHub."
    assert payload["reason"] == "main_lookup_failed"


def test_cli_upgrade_version_latest_check_is_non_mutating(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod,
        "write_install_metadata_update",
        lambda plan: (_ for _ in ()).throw(
            AssertionError("check must not write metadata")
        ),
    )

    exit_code, stdout, stderr = _run_cli(
        ["upgrade", "--check", "--version", "latest"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["target_kind"] == "latest_release"
    assert payload["will_update_metadata"] is False


def test_cli_upgrade_rejects_version_main(capsys) -> None:
    exit_code, stdout, stderr = _run_cli(["upgrade", "--version", "main"], capsys)

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "validation_error"
    assert "--main" in payload["detail"]


def test_cli_upgrade_rejects_mutually_exclusive_targets(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run_cli(["upgrade", "--version", "latest", "--main"], capsys)

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "not allowed with argument" in captured.err


def test_cli_update_without_memory_id_points_to_upgrade(capsys) -> None:
    exit_code, stdout, stderr = _run_cli(["update"], capsys)

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "validation_error"
    assert "recollectium upgrade" in payload["hint"]


def test_cli_upgrade_check_prints_non_mutating_plan(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod,
        "RecollectiumConfig",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("--check must not create or load default config")
        ),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check"], capsys)

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["install_method"] == "uv_tool"
    assert payload["latest_version"] == "9.9.9"
    assert payload["command"] == ["uv", "tool", "upgrade", "recollectium"]
    assert payload["services_to_restart"] == []


def test_cli_upgrade_applies_and_reports_service_restart_failure(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    fake_config = object()
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "check_running_service",
        lambda cfg: {"type": "api", "pid": 123, "process_start_time": 456},
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(cli_mod, "stop_service", lambda cfg: 123)

    def _raise_start(*args, **kwargs):
        raise ServiceError("restart failed")

    monkeypatch.setattr(cli_mod, "start_service", _raise_start)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--force"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "service_error"
    assert payload["service_restart_errors"] == [
        {"type": "api", "error": "restart failed"}
    ]


def test_cli_upgrade_success_preserves_raw_embedding_maintenance_stdout(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(
        cli_mod,
        "_run_installed_embedding_maintenance",
        lambda **kw: CommandResult(0, "not-json", ""),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["embedding_maintenance"] == {"raw_stdout": "not-json"}


def test_cli_upgrade_embedding_maintenance_failure_attempts_service_restore(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    calls: list[str] = []
    fake_config = object()
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(
        cli_mod, "check_running_service", lambda cfg: {"type": "api", "pid": 1}
    )
    monkeypatch.setattr(cli_mod, "stop_service", lambda cfg: calls.append("stop"))
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(
        cli_mod,
        "_run_installed_embedding_maintenance",
        lambda **kw: CommandResult(3, "", "maintenance failed"),
    )

    def _restart(*args, **kwargs):
        calls.append("restart")
        raise ServiceError("restart failed")

    monkeypatch.setattr(cli_mod, "start_service", _restart)

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 3
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "embedding_maintenance_failed"
    assert payload["service_restart_errors"] == [
        {"type": "api", "error": "restart failed"}
    ]
    assert calls == ["stop", "restart"]


def test_cli_upgrade_release_lookup_error_with_repo_uses_main_fallback(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, MainRefInfo, ReleaseLookupError

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("bootstrap", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "bootstrap")

    def _raise(*args, **kwargs):
        raise ReleaseLookupError("missing", reason="no_latest_release")

    monkeypatch.setattr(cli_mod, "fetch_latest_release", _raise)
    fallback_commit = "b" * 40

    def _resolve_main_ref(
        *, repo, install_method, runner, source_root, timeout_seconds, non_mutating
    ):
        assert (repo, install_method, non_mutating) == ("owner/repo", "bootstrap", True)
        return MainRefInfo(remote_commit=fallback_commit)

    monkeypatch.setattr(cli_mod, "resolve_main_ref", _resolve_main_ref)

    exit_code, stdout, stderr = _run_cli(
        ["upgrade", "--check", "--repo", "owner/repo"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["latest_tag"] == "main"
    assert payload["target_commit"] == fallback_commit
    assert "owner/repo/" + fallback_commit + "/install.sh" in payload["command"][-1]
    assert payload["reason"] == "main_fallback_allowed"


def test_cli_upgrade_release_lookup_main_fallback_failure_returns_main_message(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseLookupError

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("bootstrap", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "bootstrap")

    def _raise_release(*args, **kwargs):
        raise ReleaseLookupError("missing", reason="no_latest_release")

    def _raise_main(*args, **kwargs):
        raise ReleaseLookupError("offline", reason="main_lookup_failed")

    monkeypatch.setattr(cli_mod, "fetch_latest_release", _raise_release)
    monkeypatch.setattr(cli_mod, "resolve_main_ref", _raise_main)

    exit_code, stdout, stderr = _run_cli(
        ["upgrade", "--check", "--repo", "owner/repo"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "network_error"
    assert payload["message"] == "Could not resolve Recollectium main from GitHub."
    assert payload["reason"] == "main_lookup_failed"


def test_cli_upgrade_release_lookup_error_returns_json_stderr(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseLookupError

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")

    def _raise(*args, **kwargs):
        raise ReleaseLookupError("offline", reason="release_lookup_failed")

    monkeypatch.setattr(cli_mod, "fetch_latest_release", _raise)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "network_error"
    assert payload["reason"] == "release_lookup_failed"


def test_cli_upgrade_unknown_install_method_returns_usage_error(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("unknown", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "unknown")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 2
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "unsupported_install_method"


def test_cli_upgrade_plan_network_error_returns_json_stderr(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("pip", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "pip")
    monkeypatch.setattr(cli_mod, "fetch_latest_release", lambda client, *, repo: None)

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "network_error"
    assert payload["detail"] == "no_latest_release"


def test_cli_upgrade_apply_failure_returns_command_exit(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(126, "", "bad")
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "update_failed"
    assert payload["stderr"] == "bad"


def test_cli_upgrade_success_restarts_running_service(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    calls: list[str] = []
    fake_config = object()
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(
        cli_mod, "check_running_service", lambda cfg: {"type": "mcp", "pid": 1}
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(cli_mod, "stop_service", lambda cfg: calls.append("stop") or 1)
    monkeypatch.setattr(
        cli_mod, "start_service", lambda *a, **kw: calls.append("start") or 2
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert calls == ["stop", "start"]
    payload = json.loads(stdout)
    assert payload["status"] == "updated"
    assert payload["services_to_restart"] == ["mcp"]


def test_cli_upgrade_success_runs_installed_embedding_maintenance(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    maintenance_calls: list[dict[str, object]] = []
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )

    def _maintenance(**kwargs):
        maintenance_calls.append(kwargs)
        return CommandResult(
            0,
            json.dumps(
                {
                    "status": "embedding_maintenance_completed",
                    "model_prepared": True,
                    "embedding_refresh": {"refreshed": False, "stale_count": 0},
                }
            ),
            "",
        )

    monkeypatch.setattr(cli_mod, "_run_installed_embedding_maintenance", _maintenance)

    exit_code, stdout, stderr = _run_cli(
        ["--db", "/tmp/recollectium.db", "upgrade"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "updated"
    assert (
        payload["embedding_maintenance"]["status"] == "embedding_maintenance_completed"
    )
    assert len(maintenance_calls) == 1
    assert isinstance(maintenance_calls[0]["config_path"], Path)
    assert maintenance_calls[0] == {
        "config_path": maintenance_calls[0]["config_path"],
        "explicit": False,
        "db_path": "/tmp/recollectium.db",
        "log_level": None,
        "timeout_seconds": 600,
    }


def test_cli_upgrade_check_does_not_run_embedding_maintenance(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod,
        "_run_installed_embedding_maintenance",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["status"] == "dry_run"


def test_cli_upgrade_embedding_maintenance_failure_reports_json(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "done", "")
    )
    monkeypatch.setattr(
        cli_mod,
        "_run_installed_embedding_maintenance",
        lambda **kwargs: CommandResult(7, "", "model download failed"),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 7
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "embedding_maintenance_failed"
    assert payload["stderr"] == "model download failed"


def test_cli_upgrade_ignores_config_errors_when_checking_services(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: object())

    def _raise_config(*args, **kwargs):
        raise ServiceError("pid file broken")

    monkeypatch.setattr(cli_mod, "check_running_service", _raise_config)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check"], capsys)

    assert exit_code == 0
    assert stderr == ""
    assert json.loads(stdout)["services_to_restart"] == []

    with pytest.raises(ServiceError, match="pid file broken"):
        _raise_config()


def test_cli_upgrade_service_stop_failure_blocks_package_update(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    fake_config = object()
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(
        cli_mod, "check_running_service", lambda cfg: {"type": "api", "pid": 1}
    )

    def _raise_stop(cfg):
        raise ServiceError("stop failed")

    def _unexpected_apply(*args, **kwargs):
        raise AssertionError("package update should not run after stop failure")

    monkeypatch.setattr(cli_mod, "stop_service", _raise_stop)
    monkeypatch.setattr(cli_mod, "apply_update", _unexpected_apply)

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["service_stop_errors"] == [{"type": "api", "error": "stop failed"}]

    with pytest.raises(
        AssertionError, match="package update should not run after stop failure"
    ):
        _unexpected_apply()


def test_cli_upgrade_apply_failure_attempts_service_restore(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    calls: list[str] = []
    fake_config = object()
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(
        cli_mod, "check_running_service", lambda cfg: {"type": "api", "pid": 1}
    )
    monkeypatch.setattr(cli_mod, "stop_service", lambda cfg: calls.append("stop") or 1)
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(7, "", "bad")
    )
    monkeypatch.setattr(
        cli_mod, "start_service", lambda *a, **kw: calls.append("start") or 2
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 7
    assert stdout == ""
    assert calls == ["stop", "start"]
    assert json.loads(stderr)["status"] == "update_failed"


def test_cli_upgrade_apply_failure_reports_service_restore_failure(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    fake_config = object()
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "RecollectiumConfig", lambda *a, **kw: fake_config)
    monkeypatch.setattr(
        cli_mod, "check_running_service", lambda cfg: {"type": "api", "pid": 1}
    )
    monkeypatch.setattr(cli_mod, "stop_service", lambda cfg: 1)
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(3, "", "bad")
    )

    def _raise_start(*args, **kwargs):
        raise ServiceError("restore failed")

    monkeypatch.setattr(cli_mod, "start_service", _raise_start)

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 3
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "update_failed"
    assert payload["service_restart_errors"] == [
        {"type": "api", "error": "restore failed"}
    ]


def test_workspace_resolve_validation_error(tmp_path, capsys) -> None:
    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "workspace-resolve-error.db"),
            "workspace",
            "resolve",
            "",
        ],
        capsys,
    )

    assert exit_code == 2
    assert stdout == ""
    assert "workspace uid must be a non-empty string" in stderr.lower()


def test_workspace_alias_remove_not_found_error(tmp_path, capsys) -> None:
    exit_code, stdout, stderr = _run_cli(
        [
            "--db",
            str(tmp_path / "workspace-alias-missing.db"),
            "workspace",
            "alias",
            "remove",
            "missing",
        ],
        capsys,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "workspace alias not found" in stderr.lower()


def test_cli_upgrade_source_without_checkout_returns_structured_failure(
    tmp_path, capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(cli_mod, "find_source_checkout_root", lambda start: None)
    monkeypatch.setattr(
        "recollectium.update.find_source_checkout_root", lambda start: None
    )
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("source", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "source")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )

    exit_code, stdout, stderr = _run_cli(
        ["upgrade", "--install-method", "source"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "update_failed"
    assert payload["detail"] == "source_checkout_not_found"
    assert payload["returncode"] == 1


def test_cli_upgrade_apply_failure_includes_structured_error_fields(
    capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(cli_mod, "check_running_service", lambda cfg: None)
    monkeypatch.setattr(
        cli_mod,
        "apply_update",
        lambda *a, **kw: CommandResult(9, "", "package manager failed"),
    )

    exit_code, stdout, stderr = _run_cli(["upgrade"], capsys)

    assert exit_code == 9
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "update_failed"
    assert payload["returncode"] == 9
    assert payload["message"] == "Recollectium package upgrade failed."
    assert payload["detail"] == "package manager failed"
    assert payload["hint"]


def test_cli_upgrade_check_existing_config_error_stays_non_mutating(
    tmp_path, capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod,
        "RecollectiumConfig",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    exit_code, stdout, stderr = _run_cli(
        ["--config", str(config_path), "upgrade", "--check"], capsys
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["services_to_restart"] == []


def test_cli_upgrade_check_explicit_config_creates_no_xdg_directories(
    tmp_path, capsys, monkeypatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo

    xdg_root = tmp_path / "xdg"
    xdg_env = {
        "XDG_CACHE_HOME": xdg_root / "cache",
        "XDG_CONFIG_HOME": xdg_root / "config",
        "XDG_DATA_HOME": xdg_root / "data",
        "XDG_RUNTIME_DIR": xdg_root / "runtime",
        "XDG_STATE_HOME": xdg_root / "state",
    }
    for name, path in xdg_env.items():
        monkeypatch.setenv(name, str(path))

    config_path = tmp_path / "explicit-config.json"
    config_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("bootstrap", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "bootstrap")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )

    def _unexpected_config(*args, **kwargs):
        raise AssertionError(
            "upgrade --check must not load config or discover services"
        )

    monkeypatch.setattr(cli_mod, "RecollectiumConfig", _unexpected_config)

    exit_code, stdout, stderr = _run_cli(
        [
            "--config",
            str(config_path),
            "upgrade",
            "--check",
            "--install-method",
            "bootstrap",
            "--repo",
            "owner/repo",
        ],
        capsys,
    )

    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout)
    assert payload["status"] == "dry_run"
    assert payload["services_to_restart"] == []
    assert not any((path / "recollectium").exists() for path in xdg_env.values())
    assert not (xdg_env["XDG_STATE_HOME"] / "recollectium" / "logs").exists()

    with pytest.raises(
        AssertionError, match="must not load config or discover services"
    ):
        _unexpected_config()


def test_write_tty_writes_to_controlling_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import recollectium.cli as cli_mod

    writes: list[str] = []
    flushes: list[bool] = []

    class FakeTty:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def write(self, text: str) -> None:
            writes.append(text)

        def flush(self) -> None:
            flushes.append(True)

    monkeypatch.setattr(cli_mod.Path, "open", lambda *args, **kwargs: FakeTty())

    assert cli_mod._write_tty("prompt") is True
    assert writes == ["prompt"]
    assert flushes == [True]


def test_write_tty_returns_false_when_terminal_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import recollectium.cli as cli_mod

    def _raise(*args, **kwargs):
        raise OSError("no tty")

    monkeypatch.setattr(cli_mod.Path, "open", _raise)

    assert cli_mod._write_tty("prompt") is False


def test_completion_install_interactive_prompt_uses_tty_not_stderr(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod

    prompts: list[str] = []

    monkeypatch.setattr("recollectium.cli.Path.home", lambda: tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdin.readline", lambda: "no\n")
    monkeypatch.setattr(
        cli_mod, "_write_tty", lambda text: prompts.append(text) or True
    )

    exit_code, stdout, stderr = _run_cli(["completion", "--install", "bash"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "operation_failed"
    assert prompts
    assert "Will append" in prompts[0]


def test_uninstall_purge_interactive_prompt_uses_tty_not_stderr(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod

    prompts: list[str] = []

    _set_xdg_home(monkeypatch, tmp_path)
    monkeypatch.setattr("recollectium.cli.stop_service", lambda _config: None)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdin.readline", lambda: "no\n")
    monkeypatch.setattr(
        cli_mod, "_write_tty", lambda text: prompts.append(text) or True
    )

    exit_code, stdout, stderr = _run_cli(["uninstall", "--purge"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "purge_cancelled"
    assert prompts == [
        "Type 'delete all recollectium data' to permanently delete Recollectium data: "
    ]


def test_init_migration_error_returns_structured_json(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.errors import MigrationError

    def _raise(*args, **kwargs):
        raise MigrationError("boom")

    monkeypatch.setattr(cli_mod, "SQLiteMemoryStore", _raise)

    exit_code, stdout, stderr = _run_cli(["init"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "migration_error"
    assert payload["message"] == "Database migration failed."


def test_db_status_migration_error_returns_structured_json(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.errors import MigrationError

    def _raise(*args, **kwargs):
        raise MigrationError("status boom")

    monkeypatch.setattr(cli_mod, "SQLiteMemoryStore", _raise)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "db-status.db"), "db-status"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "migration_error"
    assert payload["message"] == "Database migration status failed."


def test_core_migration_error_returns_structured_json(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.errors import MigrationError

    def _raise(*args, **kwargs):
        raise MigrationError("core boom")

    monkeypatch.setattr(cli_mod, "RecollectiumCore", _raise)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "core.db"), "get", "missing"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "migration_error"
    assert payload["message"] == "Database migration failed."


def test_core_recollectium_error_returns_operation_failed_json(
    tmp_path: Path, capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import recollectium.cli as cli_mod
    from recollectium.errors import RecollectiumError

    def _raise(*args, **kwargs):
        raise RecollectiumError("domain boom")

    monkeypatch.setattr(cli_mod, "RecollectiumCore", _raise)

    exit_code, stdout, stderr = _run_cli(
        ["--db", str(tmp_path / "core-error.db"), "get", "missing"], capsys
    )

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "operation_failed"
    assert payload["detail"] == "RecollectiumError: domain boom"


def test_cli_serve_service_error_returns_structured_json(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.errors import ServiceError

    def _fake_run_service(**kwargs: object) -> None:
        raise ServiceError("serve boom")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    exit_code, stdout, stderr = _run_cli(["serve"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "service_error"
    assert payload["detail"] == "ServiceError: serve boom"


def test_cli_serve_embedding_error_returns_structured_json(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.errors import EmbeddingGenerationError

    def _fake_run_service(**kwargs: object) -> None:
        assert kwargs["cli_structured_errors"] is True
        raise EmbeddingGenerationError("model readiness failed")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    exit_code, stdout, stderr = _run_cli(["serve"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "embedding_error"
    assert payload["detail"] == "EmbeddingGenerationError: model readiness failed"


def test_cli_serve_recollectium_error_returns_structured_json(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from recollectium.errors import RecollectiumError

    def _fake_run_service(**kwargs: object) -> None:
        raise RecollectiumError("serve domain boom")

    monkeypatch.setattr("recollectium.cli.run_service", _fake_run_service)

    exit_code, stdout, stderr = _run_cli(["serve"], capsys)

    assert exit_code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["status"] == "operation_failed"
    assert payload["detail"] == "RecollectiumError: serve domain boom"


def test_cli_install_metadata_detection_error_paths(
    tmp_path: Path, monkeypatch
) -> None:
    import recollectium.cli as cli_mod

    metadata_path = tmp_path / "install.json"
    metadata_path.write_text("{", encoding="utf-8")

    def raise_attribute_error() -> object:
        raise AttributeError("broken metadata")

    monkeypatch.setattr(cli_mod, "load_install_metadata", raise_attribute_error)
    payload = cli_mod._load_install_metadata(metadata_path)
    assert payload == {"install_method": "unknown"}

    monkeypatch.setattr(cli_mod, "load_install_metadata", raise_attribute_error)
    enriched = cli_mod._metadata_with_detected_install_method({"source_ref": "v1.0.0"})
    assert enriched == {"source_ref": "v1.0.0", "install_method": "unknown"}


def test_cli_upgrade_metadata_write_warning(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import CommandResult, InstallMetadata, ReleaseInfo

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata("uv_tool", None, None, None),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")
    monkeypatch.setattr(
        cli_mod,
        "fetch_latest_release",
        lambda client, *, repo: ReleaseInfo("9.9.9", "v9.9.9", None),
    )
    monkeypatch.setattr(
        cli_mod, "apply_update", lambda *a, **kw: CommandResult(0, "ok", "")
    )

    def fail_metadata_write(plan: object) -> None:
        raise OSError("metadata unwritable")

    monkeypatch.setattr(cli_mod, "write_install_metadata_update", fail_metadata_write)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--force"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["metadata_updated"] is False
    assert payload["metadata_warning"] == "metadata unwritable"


def test_cli_rewrites_upgrade_version_equals_selector() -> None:
    import recollectium.cli as cli_mod

    assert cli_mod._rewrite_upgrade_version_selector(
        ["upgrade", "--version=1.2.3"]
    ) == ["upgrade", "--target-version=1.2.3"]


def test_cli_upgrade_latest_uses_metadata_target_repo(capsys, monkeypatch) -> None:
    import recollectium.cli as cli_mod
    from recollectium.update import InstallMetadata, ReleaseInfo, TrackingTarget

    monkeypatch.setattr(cli_mod, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(
        cli_mod,
        "load_install_metadata",
        lambda: InstallMetadata(
            "uv_tool",
            None,
            None,
            None,
            tracking_target=TrackingTarget(
                "latest_release", "latest", repo="Metadata/Repo"
            ),
        ),
    )
    monkeypatch.setattr(cli_mod, "detect_install_method", lambda metadata: "uv_tool")

    def fake_fetch(client: object, *, repo: str) -> ReleaseInfo:
        assert repo == "Metadata/Repo"
        return ReleaseInfo("9.9.9", "v9.9.9", None)

    monkeypatch.setattr(cli_mod, "fetch_latest_release", fake_fetch)

    exit_code, stdout, stderr = _run_cli(["upgrade", "--check"], capsys)

    payload = json.loads(stdout)
    assert exit_code == 0
    assert stderr == ""
    assert payload["target_kind"] == "latest_release"
    assert payload["target_source"] == "metadata"


class _FakeServiceConfig:
    def __init__(self, config_path: Path, log_level: str | None = None) -> None:
        self.config_path = config_path
        self.log_level = log_level
        self.effective_config = {"service": {"host": "127.0.0.1", "port": 8765}}


@pytest.mark.parametrize("service_action", ["start", "stop", "status", "restart"])
def test_cli_service_command_rejects_missing_config(
    tmp_path, capsys, monkeypatch, service_action: str
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    def fake_output_format(*args: object, **kwargs: object) -> str:
        return cli_module.CLI_OUTPUT_JSON

    def fake_verbosity(*args: object, **kwargs: object) -> str:
        return RESPONSE_VERBOSITY_COMPACT

    class MissingConfig(_FakeServiceConfig):
        def __init__(self, config_path: Path, log_level: str | None = None) -> None:
            raise FileNotFoundError("config missing")

    monkeypatch.setattr(cli_module, "_resolve_output_format", fake_output_format)
    monkeypatch.setattr(cli_module, "_resolve_response_verbosity", fake_verbosity)
    monkeypatch.setattr(cli_module, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(cli_module, "RecollectiumConfig", MissingConfig)

    argv = ["--config", str(config_path), "--json", "service", service_action]
    if service_action == "start":
        argv.append("api")
    elif service_action == "restart":
        argv.extend(["--type", "api"])

    exit_code, stdout, stderr = _run_cli(argv, capsys, json_by_default=False)

    assert exit_code == 1
    assert stdout == ""
    assert "config missing" in stderr


@pytest.mark.parametrize("service_action", ["start", "stop", "status", "restart"])
def test_cli_service_command_rejects_invalid_config(
    tmp_path, capsys, monkeypatch, service_action: str
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    def fake_output_format(*args: object, **kwargs: object) -> str:
        return cli_module.CLI_OUTPUT_JSON

    def fake_verbosity(*args: object, **kwargs: object) -> str:
        return RESPONSE_VERBOSITY_COMPACT

    class InvalidConfig(_FakeServiceConfig):
        def __init__(self, config_path: Path, log_level: str | None = None) -> None:
            raise ValidationError("config invalid")

    monkeypatch.setattr(cli_module, "_resolve_output_format", fake_output_format)
    monkeypatch.setattr(cli_module, "_resolve_response_verbosity", fake_verbosity)
    monkeypatch.setattr(cli_module, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(cli_module, "RecollectiumConfig", InvalidConfig)

    argv = ["--config", str(config_path), "--json", "service", service_action]
    if service_action == "start":
        argv.append("api")
    elif service_action == "restart":
        argv.extend(["--type", "api"])

    exit_code, stdout, stderr = _run_cli(argv, capsys, json_by_default=False)

    assert exit_code == 2
    assert stdout == ""
    assert "config invalid" in stderr


@pytest.mark.parametrize("service_action", ["start", "stop", "status", "restart"])
def test_cli_service_command_success_and_runtime_errors(
    tmp_path, capsys, monkeypatch, service_action: str
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    state: dict[str, object] = {
        "start": "ok",
        "stop": 1234,
        "running": {"type": "service-a", "pid": 42},
        "raw_pid_info": {"type": "service-a", "pid": 42},
    }

    def fake_output_format(*args: object, **kwargs: object) -> str:
        return cli_module.CLI_OUTPUT_JSON

    def fake_verbosity(*args: object, **kwargs: object) -> str:
        return RESPONSE_VERBOSITY_COMPACT

    def fake_start_service(
        cfg: object,
        service_type: str,
        *,
        db_path: object = None,
        log_level: str | None = None,
    ) -> int:
        mode = state["start"]
        if mode == "conflict":
            raise ServiceConflictError("start conflict")
        if mode == "service_error":
            raise ServiceError("start boom")
        if mode == "value_error":
            raise ValueError("bad service request")
        return 4321

    def fake_stop_service(cfg: object) -> int | None:
        value = state["stop"]
        if value is None:
            return None
        assert isinstance(value, int)
        return value

    def fake_get_pid_file_path(cfg: object) -> Path:
        return tmp_path / "service.pid"

    def fake_read_pid_file(path: Path) -> dict[str, object] | None:
        raw = state["raw_pid_info"]
        return raw if isinstance(raw, dict) else None

    def fake_check_running_service(cfg: object) -> dict[str, object] | None:
        running = state["running"]
        return running if isinstance(running, dict) else None

    monkeypatch.setattr(cli_module, "_resolve_output_format", fake_output_format)
    monkeypatch.setattr(cli_module, "_resolve_response_verbosity", fake_verbosity)
    monkeypatch.setattr(cli_module, "_setup_cli_logging", lambda *a, **kw: None)
    monkeypatch.setattr(cli_module, "RecollectiumConfig", _FakeServiceConfig)
    monkeypatch.setattr(cli_module, "start_service", fake_start_service)
    monkeypatch.setattr(cli_module, "stop_service", fake_stop_service)
    monkeypatch.setattr(cli_module, "get_pid_file_path", fake_get_pid_file_path)
    monkeypatch.setattr(cli_module, "read_pid_file", fake_read_pid_file)
    monkeypatch.setattr(cli_module, "check_running_service", fake_check_running_service)

    def invoke(extra_args: list[str]) -> tuple[int, str, str]:
        return _run_cli(
            ["--config", str(config_path), "--json", "service", *extra_args],
            capsys,
            json_by_default=False,
        )

    if service_action == "start":
        code, stdout, stderr = invoke(["start", "api"])
        assert code == 0
        assert "started" in stdout
        state["start"] = "conflict"
        code, stdout, stderr = invoke(["start", "api"])
        assert code == 1
        assert stdout == ""
        assert "start conflict" in stderr
        state["start"] = "service_error"
        code, stdout, stderr = invoke(["start", "api"])
        assert code == 1
        assert stdout == ""
        assert "start boom" in stderr
        state["start"] = "value_error"
        code, stdout, stderr = invoke(["start", "api"])
        assert code == 2
        assert stdout == ""
        assert "validation_error" in stderr
        return

    if service_action == "stop":
        state["stop"] = 9876
        code, stdout, stderr = invoke(["stop"])
        assert code == 0
        assert "stopped" in stdout
        state["stop"] = None
        code, stdout, stderr = invoke(["stop"])
        assert code == 0
        assert "no_service_running" in stdout
        return

    if service_action == "status":
        state["running"] = {"type": "service-a", "pid": 42}
        code, stdout, stderr = invoke(["status"])
        assert code == 0
        assert "running" in stdout
        state["running"] = None
        state["raw_pid_info"] = {"type": "service-a", "pid": 42}
        code, stdout, stderr = invoke(["status"])
        assert code == 0
        assert "last_service" in stdout
        return

    assert service_action == "restart"
    state["running"] = {"type": "service-a", "pid": 42}
    code, stdout, stderr = invoke(["restart", "--type", "api"])
    assert code == 0
    assert "restarted" in stdout
    state["running"] = None
    state["raw_pid_info"] = {"type": "service-b", "pid": 77}
    code, stdout, stderr = invoke(["restart"])
    assert code == 0
    assert "restarted" in stdout
    state["raw_pid_info"] = None
    code, stdout, stderr = invoke(["restart", "--type", "api"])
    assert code == 0
    assert "restarted" in stdout
    code, stdout, stderr = invoke(["restart"])
    assert code == 1
    assert stdout == ""
    assert "No running service found" in stderr
    state["running"] = {"type": "service-a", "pid": 42}
    state["start"] = "conflict"
    code, stdout, stderr = invoke(["restart", "--type", "api"])
    assert code == 1
    assert stdout == ""
    assert "start conflict" in stderr
    state["running"] = None
    state["raw_pid_info"] = {"type": "service-a", "pid": 42}
    state["start"] = "service_error"
    code, stdout, stderr = invoke(["restart"])
    assert code == 1
    assert stdout == ""
    assert "start boom" in stderr
    state["start"] = "value_error"
    code, stdout, stderr = invoke(["restart", "--type", "api"])
    assert code == 2
    assert stdout == ""
    assert "validation_error" in stderr
