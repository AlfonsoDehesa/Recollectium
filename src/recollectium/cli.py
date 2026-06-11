"""CLI entrypoint for Recollectium Core."""

from __future__ import annotations

import argparse
import argcomplete
import contextlib
from argcomplete.completers import ChoicesCompleter
from copy import deepcopy
import inspect
import json
import logging
import os
import re
import shutil
from importlib.metadata import PackageNotFoundError, version as package_version
import subprocess
import sys
import tempfile
import time
from io import StringIO
from pathlib import Path
from typing import Any, Iterator, NoReturn, Sequence, cast

from rich.console import Console
from rich.text import Text

from platformdirs import user_state_dir

from recollectium import (
    __version__,
    NotFoundError,
    RecollectiumCore,
    RecollectiumError,
    ValidationError,
)
from recollectium.errors import (
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
    EmbeddingReadinessTimeoutError,
    MigrationError,
)
from recollectium.config import (
    CLI_OUTPUT_HUMAN_READABLE,
    CLI_OUTPUT_JSON,
    DEFAULTS,
    RESPONSE_VERBOSITY_COMPACT,
    RESPONSE_VERBOSITY_VERBOSE,
    RecollectiumConfig,
    SUPPORTED_EMBEDDING_MODELS,
    _apply_explicit_null_overrides,
    _deep_merge,
    _resolve_xdg_dirs,
    _validate_config_value,
    get_config_value,
    load_config_file,
    resolve_model_cache_path,
    set_config_value,
    unset_config_value,
)
from recollectium.cli_progress import (
    SingleLineProgressReporter,
    SingleLineStatusSpinner,
)
from recollectium.dev_eval import (
    ExactMRRReport,
    RankedSetNDCGReport,
    SemanticMRRReport,
    evaluate_exact_mrr_for_core,
    evaluate_ranked_set_ndcg_for_core,
    evaluate_semantic_mrr_for_core,
)
from recollectium.dev_eval_thematic_weighted import (
    ThematicWeightedReport,
    evaluate_thematic_weighted_metrics_for_core,
)
from recollectium.dev_optimize_threshold import (
    build_threshold_optimization_report,
    build_threshold_search_bundles,
    generate_threshold_values,
    report_summary_lines,
    score_runtime_row,
    ThresholdOptimizationError,
    threshold_cases_from_fixture,
    threshold_rows_to_csv,
    validate_threshold_sweep_parameters,
    write_threshold_csv,
    write_threshold_png,
)
from recollectium.dev_seed import (
    DEV_SEED_TOPIC_COUNT,
    DEV_SEED_TOTAL_WORKSPACE_MEMORIES,
    DEV_SEED_USER_MEMORY_COUNT,
    DEV_SEED_WORKSPACE_COUNT,
    ensure_seeded_dev_database,
    reset_seeded_dev_database,
    seeded_dev_database_is_initialized,
)
import recollectium.embeddings as embeddings_module
from recollectium.embeddings import BuiltinFastEmbedProvider
from recollectium.logging import setup_logging
from recollectium.models import (
    ALL_MEMORY_TYPES,
    SPACE_USER,
    SPACE_WORKSPACE,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    SearchResult,
    USER_MEMORY_TYPES,
    WORKSPACE_MEMORY_TYPES,
)
from recollectium.retrieval import resolve_retrieval_policy
from recollectium.mcp_server import create_mcp_server
from recollectium.retrieval import UNSET
from recollectium.service import run_service
from recollectium.representations import (
    OPERATION_DEV_EVAL,
    OPERATION_DEV_MODE,
    OPERATION_DEV_OPTIMIZE_THRESHOLD,
    OPERATION_DEV_RESET,
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_MAINTENANCE,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_LIFECYCLE_INIT,
    OPERATION_LIFECYCLE_UNINSTALL,
    OPERATION_LIFECYCLE_UPGRADE,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_GET,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_SERVICE_DISCOVER,
    OPERATION_SERVICE_LIFECYCLE,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    project_payload,
    validate_response_verbosity,
)
from recollectium.errors import ServiceConflictError, ServiceError
from recollectium.service_manager import (
    check_running_service,
    discover_service,
    get_pid_file_path,
    read_pid_file,
    service_discovery_payload,
    start_service,
    stop_service,
)
from recollectium.storage import SQLiteMemoryStore
from recollectium.update import (
    CommandResult,
    GitHubReleaseClient,
    ReleaseInfo,
    ReleaseLookupError,
    SubprocessCommandRunner,
    TargetSelectorError,
    apply_update,
    build_update_plan,
    detect_install_method,
    fetch_latest_release,
    find_source_checkout_root,
    load_install_metadata,
    plan_to_dict,
    resolve_main_ref,
    select_tracking_target,
    write_install_metadata_update,
)

_log = logging.getLogger(__name__)
_INSTALL_METADATA_FILE = "install.json"
_PURGE_CONFIRMATION = "delete all recollectium data"

_COMPLETABLE_CONFIG_KEYS = [
    "version",
    "cli_output",
    "response_verbosity",
    "retrieval.protected_minimum",
    "retrieval.match_threshold",
    "database.path",
    "embedding.provider",
    "embedding.model",
    "service.host",
    "service.port",
    "logging.level",
    "logging.format",
    "logging.max_bytes",
    "logging.backup_count",
    "directories.data",
    "directories.cache",
    "directories.logs",
    "directories.runtime",
    "development.use_seeded_database",
    "development.seeded_database_path",
    "workspace.uid_normalization",
]
_SUPPORTED_EMBEDDING_MODELS_HELP = ", ".join(sorted(SUPPORTED_EMBEDDING_MODELS))
_ARGPARSE_JSON_ERRORS = False


def _frame_human_output(text: str) -> str:
    """Frame final human-readable CLI output with leading and trailing space."""
    return "\n" + text.strip("\n") + "\n\n" if text else "\n\n"


class _HumanFramedArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that frames argparse human help and error output."""

    def format_help(self) -> str:
        return _frame_human_output(super().format_help())

    def error(self, message: str) -> NoReturn:
        if _ARGPARSE_JSON_ERRORS:
            self.exit(
                2,
                json.dumps(
                    {
                        "status": "validation_error",
                        "message": message,
                    },
                    sort_keys=True,
                )
                + "\n",
            )
        self.exit(
            2,
            _frame_human_output(
                f"{argparse.ArgumentParser.format_usage(self)}{self.prog}: error: {message}"
            ),
        )


def _memory_type_choices_for_space(space: Any | None) -> tuple[str, ...]:
    if space == SPACE_USER:
        return USER_MEMORY_TYPES
    if space == SPACE_WORKSPACE:
        return WORKSPACE_MEMORY_TYPES
    return ALL_MEMORY_TYPES


def _memory_type_completer(prefix: str, parsed_args: Any, **_: Any) -> list[str]:
    choices = _memory_type_choices_for_space(getattr(parsed_args, "space", None))
    return [choice for choice in choices if choice.startswith(prefix)]


class _CliLoggingConfig:
    def __init__(self, *, effective_config: dict[str, Any], log_dir: Path) -> None:
        self.effective_config = effective_config
        self.xdg_dirs = {"logs": log_dir}


class _UninstallConfig(RecollectiumConfig):
    def __init__(
        self,
        *,
        effective_config: dict[str, Any],
        xdg_dirs: dict[str, Path],
        config_path: Path,
        database_path: Path,
    ) -> None:
        self._effective_config = effective_config
        self._xdg_dirs = xdg_dirs
        self._config_file_path = config_path
        self._resolved_db_path = database_path


class _UninstallPlan:
    def __init__(
        self,
        *,
        config: _UninstallConfig,
        config_path: Path,
        database_path: Path,
        install_metadata_path: Path,
        model_cache_path: Path,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.database_path = database_path
        self.install_metadata_path = install_metadata_path
        self.model_cache_path = model_cache_path


class _MetadataInvalidError(ValidationError):
    """Raised when CLI --metadata is malformed or not an object."""


def _parse_metadata(raw_metadata: str | None) -> dict[str, object] | None:
    if raw_metadata is None:
        return None

    payload = raw_metadata
    if raw_metadata.startswith("@"):
        metadata_path = Path(raw_metadata[1:])
        payload = metadata_path.read_text(encoding="utf-8")

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise _MetadataInvalidError(f"metadata must be valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise _MetadataInvalidError("metadata must be a JSON object")
    return parsed


def _parse_non_negative_int(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except ValueError as exc:  # pragma: no cover - argparse error path
        raise argparse.ArgumentTypeError("must be an integer >= 0") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be an integer >= 0")
    return parsed


def _parse_match_threshold(raw_value: str) -> float | str | None:
    normalized = raw_value.strip()
    lowered = normalized.lower()
    if lowered in {"none", "null"}:
        return None
    if lowered == "model_recommended_default":
        return "model_recommended_default"
    try:
        parsed = float(normalized)
    except ValueError as exc:  # pragma: no cover - argparse error path
        raise argparse.ArgumentTypeError(
            "must be model_recommended_default, none, or a number between 0.0 and 1.0"
        ) from exc
    if parsed < 0.0 or parsed > 1.0:
        raise argparse.ArgumentTypeError(
            "must be model_recommended_default, none, or a number between 0.0 and 1.0"
        )
    return parsed


def _write_tty(text: str) -> bool:
    """Write interactive prompt text to the controlling TTY, not stdout/stderr."""
    try:
        with Path("/dev/tty").open("w", encoding="utf-8") as tty:
            tty.write(text)
            tty.flush()
    except OSError:
        return False
    return True


def _to_payload(data: Any) -> Any:
    if isinstance(data, SearchResult):
        return data.to_dict()
    if hasattr(data, "to_dict"):
        return data.to_dict()
    if isinstance(data, list):
        return [_to_payload(item) for item in data]
    return data


def _json_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


_RICH_BOLD = "bold"
_RICH_HEADING = "bold cyan"
_RICH_BLUE_HEADING = "bold blue"
_RICH_SUCCESS = "bold green"
_RICH_ERROR = "bold red"
_RICH_HINT = "yellow"
_RICH_WARNING = "yellow"


def _supports_color(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _style(text: str, style: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    stream = StringIO()
    console = Console(
        file=stream,
        force_terminal=True,
        color_system="standard",
        legacy_windows=False,
        soft_wrap=True,
        width=120,
    )
    console.print(Text(text, style=style), end="")
    return stream.getvalue()


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").capitalize()


def _format_label(label: str, *, color: bool) -> str:
    return _style(f"{label}:", _RICH_BOLD, enabled=color)


def _format_mapping_lines(
    mapping: dict[str, Any], *, indent: int = 0, color: bool = False
) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in mapping.items():
        label = _humanize_key(str(key))
        if isinstance(value, dict):
            lines.append(f"{prefix}{_format_label(label, color=color)}")
            lines.extend(_format_mapping_lines(value, indent=indent + 2, color=color))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{_format_label(label, color=color)} none")
            else:
                lines.append(f"{prefix}{_format_label(label, color=color)}")
                for item in value:
                    if isinstance(item, dict):
                        lines.extend(
                            _format_mapping_lines(item, indent=indent + 2, color=color)
                        )
                    else:
                        lines.append(f"{' ' * (indent + 2)}- {_json_scalar(item)}")
        elif value is not None:
            lines.append(
                f"{prefix}{_format_label(label, color=color)} {_json_scalar(value)}"
            )
    return lines


def _memory_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "memory" in payload and isinstance(payload["memory"], dict):
        return payload["memory"]
    return payload


def _format_memory(
    payload: dict[str, Any], *, index: int | None = None, color: bool = False
) -> list[str]:
    memory = _memory_payload(payload)
    title_prefix = f"{index}. " if index is not None else ""
    memory_id = memory.get("id", "unknown")
    type_value = memory.get("type")
    status = memory.get("status")
    score = payload.get("score", payload.get("match", memory.get("score")))
    headline = f"{title_prefix}Memory {memory_id}"
    details = [str(item) for item in (type_value, status) if item]
    if details:
        headline += f" ({', '.join(details)})"
    if score is not None:
        headline += f" score={score}"
    lines = [_style(headline, _RICH_HEADING, enabled=color)]
    for key in ("space", "workspace_uid", "source", "confidence", "sensitivity"):
        if memory.get(key) is not None:
            lines.append(
                f"  {_format_label(_humanize_key(key), color=color)} "
                f"{_json_scalar(memory[key])}"
            )
    content = memory.get("content")
    if content is not None:
        lines.append(f"  {_format_label('Content', color=color)} {content}")
    metadata = memory.get("metadata")
    if metadata:
        lines.append(
            f"  {_format_label('Metadata', color=color)} "
            f"{json.dumps(metadata, sort_keys=True)}"
        )
    for key in ("created_at", "updated_at", "archived_at"):
        if memory.get(key):
            lines.append(
                f"  {_format_label(_humanize_key(key), color=color)} {memory[key]}"
            )
    return lines


def _format_dev_eval_metric_lines(
    metrics: dict[str, Any], *, color: bool = False
) -> list[str]:
    return [
        f"  {_format_label('Exact MRR', color=color)} {metrics['exact_mrr']['value']:.3f}",
        f"  {_format_label('Semantic MRR', color=color)} {metrics['semantic_mrr']['value']:.3f}",
        f"  {_format_label('Thematic Weighted Precision@10', color=color)} {metrics['thematic_weighted_precision_at_10']['value']:.3f}",
        f"  {_format_label('Thematic Weighted Recall@10', color=color)} {metrics['thematic_weighted_recall_at_10']['value']:.3f}",
        f"  {_format_label('Ranked-set NDCG@5', color=color)} {metrics['ranked_set_ndcg_at_5']['value']:.3f}",
    ]


def _format_dev_eval_output(
    payload: dict[str, Any],
    *,
    color: bool = False,
    verbose: bool = False,
) -> str:
    lines = ["", _style("Recollectium dev eval", _RICH_HEADING, enabled=color)]
    if not verbose:
        lines.extend(_format_dev_eval_metric_lines(payload["metrics"], color=color))
        return "\n".join(lines) + "\n\n"

    lines.extend(
        [
            "",
            f"Seeded dev DB: {payload['database']}",
            f"Regular DB: {payload['regular_database']}",
            "Regular DB not touched: yes",
            f"Preparing seeded development database... {payload['preparation']['seeded_database']}",
            f"Loading eval fixtures... {payload['preparation']['fixtures']}",
            "",
            "Results",
        ]
    )
    lines.extend(_format_dev_eval_metric_lines(payload["metrics"], color=color))
    lines.append("")
    lines.append("Diagnostics")
    lines.extend(_format_mapping_lines(payload["diagnostics"], indent=2, color=color))
    return "\n".join(lines) + "\n\n"


def _upgrade_target_phrase(payload: dict[str, Any]) -> str:
    kind = payload.get("target_kind")
    if kind == "main":
        return "main"
    if kind == "latest_release":
        return "the latest release"
    if kind == "release":
        return f"version {payload.get('target_ref') or payload.get('latest_tag') or payload.get('target_selector')}"
    return str(
        payload.get("target_ref")
        or payload.get("target_selector")
        or "the selected target"
    )


def _upgrade_target_value(payload: dict[str, Any]) -> str | None:
    if payload.get("target_kind") == "main":
        commit = payload.get("target_commit") or payload.get("current_commit")
        return str(commit)[:7] if isinstance(commit, str) and commit else None
    if payload.get("target_kind") == "release":
        return None
    value = payload.get("target_ref") or payload.get("latest_tag")
    return str(value) if value else None


def _upgrade_previous_phrase(payload: dict[str, Any]) -> str | None:
    kind = payload.get("previous_target_kind")
    if kind == "main":
        return "main"
    if kind == "latest_release":
        return "the latest release"
    if kind == "release":
        return f"version {payload.get('previous_target_ref') or payload.get('previous_target_selector')}"
    return None


def _format_upgrade_sentence(payload: dict[str, Any], *, color: bool = False) -> str:
    status = payload.get("status")
    target_phrase = _upgrade_target_phrase(payload)
    target_value = _upgrade_target_value(payload)
    suffix = f": {target_value}." if target_value else "."
    previous = _upgrade_previous_phrase(payload)

    if status == "up_to_date":
        if payload.get("target_kind") == "main":
            sentence = f"Recollectium main is already up to date{suffix}"
        elif payload.get("target_kind") == "latest_release":
            sentence = f"Recollectium is already on the latest release{suffix}"
        else:
            sentence = f"Recollectium is already on {target_phrase}{suffix}"
        return _style(sentence, _RICH_HINT, enabled=color) + "\n"

    verb = "would switch" if status == "dry_run" else "switched"
    if previous and previous != target_phrase and payload.get("target_source") == "cli":
        sentence = f"Recollectium {verb} from {previous} to {target_phrase}{suffix}"
    elif status == "dry_run":
        sentence = f"Recollectium would update to {target_phrase}{suffix}"
    elif payload.get("target_kind") == "latest_release":
        sentence = f"Recollectium was updated to the latest release{suffix}"
    elif payload.get("target_kind") == "main":
        sentence = f"Recollectium was updated to main{suffix}"
    else:
        sentence = f"Recollectium was updated to {target_phrase}{suffix}"
    return _style(sentence, _RICH_SUCCESS, enabled=color) + "\n"


def _uninstall_data_state_sentence(payload: dict[str, Any], *, dry_run: bool) -> str:
    data = payload.get("data")
    data_payload = data if isinstance(data, dict) else {}
    data_status = data_payload.get("status")
    if isinstance(data_status, str):
        if data_status in {"preserved", "would_preserve"}:
            return "Data would be preserved." if dry_run else "Data preserved."
        if data_status in {"deleted", "would_delete"}:
            return (
                "All Recollectium data would be deleted."
                if dry_run
                else "All Recollectium data was deleted."
            )
    data_preserved = bool(data_payload.get("preserved", True))
    if data_preserved:
        return "Data would be preserved." if dry_run else "Data preserved."
    if dry_run:
        return "All Recollectium data would be deleted."
    return "All Recollectium data was deleted."


def _format_uninstall_sentence(payload: dict[str, Any], *, color: bool = False) -> str:
    package = payload.get("package")
    package_payload = package if isinstance(package, dict) else {}
    uninstall = package_payload.get("uninstall")
    uninstall_payload = uninstall if isinstance(uninstall, dict) else {}
    status = payload.get("status")
    package_status = uninstall_payload.get("status")
    data_sentence = _uninstall_data_state_sentence(payload, dry_run=status == "dry_run")

    if package_status == "unsupported" or (
        status == "dry_run" and "command" not in uninstall_payload
    ):
        return (
            "Recollectium could not uninstall itself from this install method. "
            f"Manual removal is required. {data_sentence}\n"
        )

    if status == "dry_run":
        return f"Recollectium would be uninstalled. {data_sentence}\n"

    if status in {"uninstalled", "uninstalled_with_warnings"}:
        sentence = f"Uninstalled. {data_sentence}"
        return _style(sentence, _RICH_SUCCESS, enabled=color) + "\n"

    if status == "package_removal_unsupported":
        return (
            "Recollectium could not uninstall itself from this install method. "
            f"Manual removal is required. {data_sentence}\n"
        )

    return f"Uninstall did not complete. {data_sentence} Rerun with --verbose for details.\n"


def _embedding_count_noun(count: int) -> str:
    return "embedding" if count == 1 else "embeddings"


def _format_human_output(
    payload: Any,
    *,
    command: str | None = None,
    label: str | None = None,
    color: bool = False,
    response_verbosity: str | None = None,
) -> str:
    payload = _to_payload(payload)
    verbosity = response_verbosity or _CURRENT_RESPONSE_VERBOSITY
    if (
        command == "add"
        and isinstance(payload, dict)
        and payload.get("status") == "saved"
        and "content" not in payload
    ):
        memory_id = payload.get("id")
        message = (
            f"Memory saved: {memory_id}" if memory_id is not None else "Memory saved!"
        )
        return _style(message, _RICH_SUCCESS, enabled=color) + "\n"
    if (
        command == "update"
        and isinstance(payload, dict)
        and payload.get("status") == "updated"
        and "content" not in payload
    ):
        memory_id = payload.get("id")
        message = (
            f"Memory updated: {memory_id}"
            if memory_id is not None
            else "Memory updated."
        )
        return _style(message, _RICH_SUCCESS, enabled=color) + "\n"
    if (
        command == "archive"
        and isinstance(payload, dict)
        and payload.get("status") == "archived"
        and "content" not in payload
    ):
        memory_id = payload.get("id")
        message = (
            f"Memory archived: {memory_id}"
            if memory_id is not None
            else "Memory archived."
        )
        return _style(message, _RICH_SUCCESS, enabled=color) + "\n"
    if payload is None:
        return "Done\n"
    if isinstance(payload, list):
        if not payload:
            return "No results\n"
        if all(isinstance(item, dict) for item in payload):
            blocks = [
                _style(
                    f"{len(payload)} result{'s' if len(payload) != 1 else ''}",
                    _RICH_HEADING,
                    enabled=color,
                )
            ]
            for index, item in enumerate(payload, start=1):
                if "content" in item or "memory" in item:
                    blocks.append(
                        "\n".join(_format_memory(item, index=index, color=color))
                    )
                else:
                    blocks.append(f"{index}. {json.dumps(item, sort_keys=True)}")
            return "\n\n".join(blocks) + "\n"
        return "\n".join(f"- {_json_scalar(item)}" for item in payload) + "\n"
    if command == "config get" and label is not None:
        return f"{_format_label(label, color=color)} {_json_scalar(payload)}\n"
    if not isinstance(payload, dict):
        if label:
            return f"{label}: {_json_scalar(payload)}\n"
        return f"{_json_scalar(payload)}\n"

    if command in {"add", "get", "update", "archive"} or "content" in payload:
        title = "Memory"
        if command == "add":
            title = "Memory added"
        elif command == "update":
            title = "Memory updated"
        elif command == "archive":
            title = "Memory archived"
        return (
            "\n".join(
                [
                    _style(title, _RICH_HEADING, enabled=color),
                    *_format_memory(payload, color=color),
                ]
            )
            + "\n"
        )

    if command == "config set":
        if payload.get("status") == "skipped":
            return (
                _style(
                    "Config already has that value. Changes were skipped.",
                    _RICH_WARNING,
                    enabled=color,
                )
                + "\n"
            )
        heading = _style("Config updated:", _RICH_HEADING, enabled=color)
        return (
            f"{heading} {payload.get('key')} = {_json_scalar(payload.get('value'))}\n"
        )
    if command == "config unset":
        if payload.get("status") == "skipped":
            return (
                _style(
                    "Config key is already unset. Changes were skipped.",
                    _RICH_WARNING,
                    enabled=color,
                )
                + "\n"
            )
        heading = _style("Config key removed:", _RICH_HEADING, enabled=color)
        return f"{heading} {payload.get('key')}\n"
    if command == "config init":
        if verbosity == RESPONSE_VERBOSITY_COMPACT:
            return _style("Config file is ready.", _RICH_SUCCESS, enabled=color) + "\n"
        heading = _style("Config initialized:", _RICH_HEADING, enabled=color)
        return f"{heading} {payload.get('path')}\n"
    if command == "config reset":
        heading = _style("Config reset to defaults:", _RICH_HEADING, enabled=color)
        if verbosity == RESPONSE_VERBOSITY_COMPACT:
            return f"{heading} {payload.get('path')}\n"
        lines = [f"{heading} {payload.get('path')}"]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"
    if command == "config doctor":
        if verbosity == RESPONSE_VERBOSITY_COMPACT and payload.get("status") == "ok":
            return (
                _style("Config doctor found no problems.", _RICH_SUCCESS, enabled=color)
                + "\n"
            )
        lines = [_style("Config doctor", _RICH_HEADING, enabled=color)]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"
    if command == "config --validate":
        if verbosity == RESPONSE_VERBOSITY_COMPACT:
            return (
                _style("Current config is valid.", _RICH_SUCCESS, enabled=color) + "\n"
            )
        config_payload = payload.get("config")
        lines = [
            _style(
                "Current config is valid. Config tested:", _RICH_HEADING, enabled=color
            )
        ]
        if isinstance(config_payload, dict):
            lines.extend(_format_mapping_lines(config_payload, indent=2, color=color))
        return "\n".join(lines) + "\n"
    if command == "config":
        return (
            _style("Effective configuration", _RICH_HEADING, enabled=color)
            + "\n"
            + "\n".join(_format_mapping_lines(payload, indent=2, color=color))
            + "\n"
        )

    if command == "dev eval":
        if verbosity == RESPONSE_VERBOSITY_VERBOSE:
            return _format_dev_eval_output(payload, color=color, verbose=True)
        return _format_dev_eval_output(payload, color=color, verbose=False)

    if command == "upgrade" and verbosity == RESPONSE_VERBOSITY_COMPACT:
        return _format_upgrade_sentence(payload, color=color)

    if command == "uninstall" and verbosity == RESPONSE_VERBOSITY_COMPACT:
        return _format_uninstall_sentence(payload, color=color)

    if command == "init":
        if verbosity == RESPONSE_VERBOSITY_COMPACT:
            if payload.get("already_initialized") is True:
                message = "Recollectium is already initialized: No changes needed."
            else:
                refresh = payload.get("embedding_refresh")
                if isinstance(refresh, dict) and refresh.get("refreshed") is True:
                    stale_count = refresh.get("stale_count")
                    message = (
                        "Recollectium is ready and refreshed "
                        f"{stale_count} stale {_embedding_count_noun(stale_count)}."
                        if isinstance(stale_count, int)
                        else "Recollectium is ready and embeddings were refreshed."
                    )
                elif payload.get("refreshed") is True:
                    stale_count = payload.get("stale_count")
                    message = (
                        "Recollectium is ready and refreshed "
                        f"{stale_count} stale {_embedding_count_noun(stale_count)}."
                        if isinstance(stale_count, int)
                        else "Recollectium is ready and embeddings were refreshed."
                    )
                else:
                    message = (
                        "Recollectium is ready with no embeddings needing refresh."
                    )
            return _style(message, _RICH_SUCCESS, enabled=color) + "\n"
        lines = [_style("Recollectium initialized", _RICH_HEADING, enabled=color)]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"

    if command and command.startswith("workspace"):
        lines = [_style("Workspace result", _RICH_HEADING, enabled=color)]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"

    if command and command.startswith("service"):
        lines = [_style("Service result", _RICH_HEADING, enabled=color)]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"

    if command in {
        "db-status",
        "embedding-status",
        "embedding-maintenance",
        "embedding-jobs",
        "embedding-refresh",
        "embedding-jobs-clear",
        "upgrade",
        "uninstall",
        "completion",
    }:
        heading = _humanize_key(command)
        lines = [_style(heading, _RICH_HEADING, enabled=color)]
        lines.extend(_format_mapping_lines(payload, indent=2, color=color))
        return "\n".join(lines) + "\n"

    lines = [_style(_humanize_key(command or "result"), _RICH_HEADING, enabled=color)]
    lines.extend(_format_mapping_lines(payload, indent=2, color=color))
    return "\n".join(lines) + "\n"


def _operation_for_command(command: str | None, payload: Any = None) -> str | None:
    if command == "init":
        return OPERATION_LIFECYCLE_INIT
    if command == "embedding-maintenance":
        return OPERATION_EMBEDDING_MAINTENANCE
    if command == "upgrade":
        return OPERATION_LIFECYCLE_UPGRADE
    if command == "uninstall":
        return OPERATION_LIFECYCLE_UNINSTALL
    if command in {"dev true", "dev false"}:
        return OPERATION_DEV_MODE
    if command == "dev reset":
        return OPERATION_DEV_RESET
    if command == "dev eval":
        return OPERATION_DEV_EVAL
    if command == "dev optimize-threshold":
        return OPERATION_DEV_OPTIMIZE_THRESHOLD
    if command == "service discover":
        return OPERATION_SERVICE_DISCOVER
    if command in {
        "service start",
        "service stop",
        "service status",
        "service restart",
    }:
        return OPERATION_SERVICE_LIFECYCLE
    if command == "add":
        return OPERATION_MEMORIES_ADD
    if command == "update":
        return OPERATION_MEMORIES_UPDATE
    if command == "archive":
        return OPERATION_MEMORIES_ARCHIVE
    if command == "search-user":
        return OPERATION_MEMORIES_SEARCH_USER
    if command == "search-workspace":
        return OPERATION_MEMORIES_SEARCH_WORKSPACE
    if command == "list":
        return OPERATION_MEMORIES_LIST
    if command == "get":
        return OPERATION_MEMORIES_GET
    if command == "embedding-status":
        return OPERATION_EMBEDDING_STATUS
    if command == "embedding-refresh":
        return OPERATION_EMBEDDING_REFRESH
    if command == "embedding-jobs-clear":
        return OPERATION_EMBEDDING_JOBS_CLEAR
    if command == "embedding-jobs":
        return (
            OPERATION_EMBEDDING_JOBS_GET
            if isinstance(payload, dict)
            else OPERATION_EMBEDDING_JOBS_LIST
        )
    if command == "workspace list":
        return OPERATION_WORKSPACES_LIST
    if command == "workspace resolve":
        return OPERATION_WORKSPACES_RESOLVE
    if command == "workspace alias add":
        return OPERATION_WORKSPACES_ALIASES_ADD
    if command == "workspace alias list":
        return OPERATION_WORKSPACES_ALIASES_LIST
    if command == "workspace alias remove":
        return OPERATION_WORKSPACES_ALIASES_REMOVE
    if command == "workspace alias":
        if isinstance(payload, list):
            return OPERATION_WORKSPACES_ALIASES_LIST
        if isinstance(payload, dict) and "migrated_memories" in payload:
            return OPERATION_WORKSPACES_ALIASES_ADD
        return OPERATION_WORKSPACES_ALIASES_REMOVE
    if command == "workspace rename":
        return OPERATION_WORKSPACES_RENAME
    return None


_CURRENT_RESPONSE_VERBOSITY = RESPONSE_VERBOSITY_COMPACT


def _set_response_verbosity(verbosity: str) -> None:
    global _CURRENT_RESPONSE_VERBOSITY
    _CURRENT_RESPONSE_VERBOSITY = verbosity


def _should_preserve_full_payload_for_compact_human(
    *, output_format: str, verbosity: str, command: str | None
) -> bool:
    """Return whether compact human formatters need the unprojected payload.

    Compact JSON should still be projected, and generic compact human responses
    (notably memory mutations/lists/searches) should retain their concise slice-1
    behavior. Specialized lifecycle sentence renderers inspect fields omitted from
    compact JSON, so they must format from the full payload.
    """

    return (
        output_format == CLI_OUTPUT_HUMAN_READABLE
        and verbosity == RESPONSE_VERBOSITY_COMPACT
        and command in {"upgrade", "uninstall"}
    )


def _emit_success(
    payload: Any,
    *,
    output_format: str,
    command: str | None = None,
    label: str | None = None,
    json_indent: int | None = None,
    response_verbosity: str | None = None,
) -> None:
    payload = _to_payload(payload)
    verbosity = response_verbosity or _CURRENT_RESPONSE_VERBOSITY
    operation = _operation_for_command(command, payload)
    if (
        output_format != CLI_OUTPUT_HUMAN_READABLE
        or verbosity == RESPONSE_VERBOSITY_COMPACT
    ) and not _should_preserve_full_payload_for_compact_human(
        output_format=output_format, verbosity=verbosity, command=command
    ):
        payload = project_payload(
            payload,
            verbosity=verbosity,
            operation=operation,
        )
    if output_format == CLI_OUTPUT_HUMAN_READABLE:
        sys.stdout.write(
            _frame_human_output(
                _format_human_output(
                    payload,
                    command=command,
                    label=label,
                    color=_supports_color(sys.stdout),
                    response_verbosity=verbosity,
                )
            )
        )
        return
    print(json.dumps(payload, indent=json_indent, sort_keys=True))


def _emit_human_progress(message: str) -> None:
    sys.stdout.write(f"Status: {message}\n")
    sys.stdout.flush()


def _live_progress_title_limit(stream: Any) -> int | None:
    """Return a safe live-title length for terminal progress bars.

    Some terminals and log bridges turn long live-updating lines into a stream
    of wrapped blank rows. Keep the live title short enough to fit comfortably
    on common 80-column terminals, and disable the live bar entirely if the
    detected width is too narrow.
    """

    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except OSError:
        return None
    if columns < 60:
        return None
    return max(12, min(24, columns - 60))


def _compact_live_title(text: str, limit: int | None) -> str:
    compact = " ".join(text.split())
    if limit is None or len(compact) <= limit:
        return compact
    return compact[: max(1, limit - 1)].rstrip() + "…"


_DEV_EVAL_PROGRESS_LABELS = {
    "Checking embedding provider readiness": "Checking provider",
    "Checking provider": "Checking provider",
    "Preparing seeded development database": "Preparing dev DB",
    "Seeded user memories": "Seed user memories",
    "Seeded workspace memories": "Seed workspace memories",
    "Loading eval fixtures": "Loading fixtures",
    "Running exact MRR": "Exact MRR",
    "Running semantic MRR": "Semantic MRR",
    "Running thematic weighted metrics": "Thematic metrics",
    "Running ranked-set NDCG@5": "NDCG@5",
    "Exact MRR user memories": "Exact MRR: user",
    "Exact MRR workspace memories": "Exact MRR: workspace",
    "Semantic MRR paraphrases": "Semantic MRR",
    "Thematic weighted user topics": "Thematic metrics: user",
    "Thematic weighted workspace themes": "Thematic metrics: workspace",
    "Thematic Precision user topics": "Thematic metrics: user",
    "Thematic Precision workspace themes": "Thematic metrics: workspace",
    "Ranked-set NDCG@5 cases": "NDCG@5",
}

_REEMBEDDING_PROGRESS_LABELS = {
    "Re-embedding memories": "Re-embedding",
}

_THRESHOLD_OPTIMIZATION_PROGRESS_LABELS = {
    "Checking embedding provider readiness": "Checking provider",
    "Preparing seeded development database": "Preparing dev DB",
    "Seeded user memories": "Seed user memories",
    "Seeded workspace memories": "Seed workspace memories",
    "Loading fixtures": "Loading fixtures",
    "Loading candidate pools": "Loading candidates",
    "Scoring thresholds": "Scoring thresholds",
    "Writing config": "Writing config",
    "Writing PNG artifact": "Writing PNG",
    "Writing CSV artifact": "Writing CSV",
    "Writing CSV sweep to stdout": "Writing CSV stdout",
}

_DEV_SEED_PROGRESS_LABELS = {
    "Seeded user memories": "Seed user memories",
    "Seeded workspace memories": "Seed workspace memories",
}


class _ReembeddingProgressReporter:
    """Translate re-embedding progress events to a single-line renderer."""

    def __init__(self, stream: Any) -> None:
        title_limit = _live_progress_title_limit(stream)
        self._progress = SingleLineProgressReporter(
            stream,
            labels=_REEMBEDDING_PROGRESS_LABELS,
            title_limit=12 if title_limit is None else title_limit,
        )
        self._started = False

    def __enter__(self) -> _ReembeddingProgressReporter:
        self._ensure_started()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        self._progress.finish()

    def _ensure_started(self) -> None:
        if self._started:
            return
        self._progress.__enter__()
        self._started = True

    def __call__(self, event: dict[str, Any]) -> None:
        self._ensure_started()
        self._progress.update(
            "Re-embedding memories",
            completed=int(event.get("processed") or 0),
            total=int(event.get("total") or 0),
        )


def _stderr_supports_live_progress() -> bool:
    try:
        return bool(sys.stderr.isatty())
    except (OSError, ValueError):
        return False


def _human_reembedding_progress_reporter(
    output_format: str,
) -> _ReembeddingProgressReporter | None:
    if output_format != CLI_OUTPUT_HUMAN_READABLE:
        return None
    if not _stderr_supports_live_progress():
        return None
    return _ReembeddingProgressReporter(sys.stderr)


class _DevSeedProgressReporter:
    """Translate seeded dev database insertion progress to a single-line renderer."""

    def __init__(self, stream: Any) -> None:
        title_limit = _live_progress_title_limit(stream)
        self._progress = SingleLineProgressReporter(
            stream,
            labels=_DEV_SEED_PROGRESS_LABELS,
            title_limit=12 if title_limit is None else title_limit,
        )

    def __enter__(self) -> _DevSeedProgressReporter:
        self._progress.__enter__()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        self._progress.finish()

    def __call__(self, event: dict[str, object]) -> None:
        completed = event.get("completed")
        total = event.get("total")
        self._progress.update(
            str(event.get("label") or "Seeded dev memories"),
            completed=completed if isinstance(completed, int) else 0,
            total=total if isinstance(total, int) else 0,
        )


class _DevSeedProgressContext:
    """No-op context wrapper for optional seeded dev database progress."""

    def __init__(self, reporter: _DevSeedProgressReporter | None) -> None:
        self.reporter = reporter

    def __enter__(self) -> _DevSeedProgressReporter | None:
        if self.reporter is not None:
            self.reporter.__enter__()
        return self.reporter

    def __exit__(self, *_: object) -> None:
        if self.reporter is not None:
            self.reporter.finish()


def _human_dev_seed_progress_context(output_format: str) -> _DevSeedProgressContext:
    if output_format != CLI_OUTPUT_HUMAN_READABLE:
        return _DevSeedProgressContext(None)
    if not _stderr_supports_live_progress():
        return _DevSeedProgressContext(None)
    return _DevSeedProgressContext(_DevSeedProgressReporter(sys.stderr))


def _call_with_optional_progress_callback(
    callback: Any,
    *args: object,
    progress_callback: object | None,
) -> Any:
    if progress_callback is None or not _callable_accepts_cli_readiness_keyword(
        callback, "progress_callback"
    ):
        return callback(*args)
    return callback(*args, progress_callback=progress_callback)


def _refresh_stale_embeddings_with_progress(
    core: RecollectiumCore,
    *,
    space: str | None = None,
    workspace_uid: str | None = None,
    include_archived: bool,
    output_format: str,
) -> dict[str, Any]:
    """Run stale-embedding refresh with optional human TTY progress."""
    refresh_kwargs: dict[str, Any] = {
        "space": space,
        "workspace_uid": workspace_uid,
        "include_archived": include_archived,
    }
    progress_reporter = _human_reembedding_progress_reporter(output_format)
    if progress_reporter is None:
        return core.refresh_stale_embeddings(**refresh_kwargs)
    with progress_reporter:
        return core.refresh_stale_embeddings(
            **refresh_kwargs,
            progress_callback=progress_reporter,
        )


class _ModelReadinessProgressReporter:
    """Render model readiness as an indeterminate, honest status spinner."""

    def __init__(
        self,
        stream: Any,
        *,
        model_name: str | None,
        cached_model_artifact: bool | None,
    ) -> None:
        self._model_name = model_name
        self._cached_model_artifact = cached_model_artifact
        self._spinner = SingleLineStatusSpinner(
            stream,
            title=self._title(),
            details=self._details(),
        )
        self._started = False

    def __enter__(self) -> _ModelReadinessProgressReporter:
        self._ensure_started()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        self._spinner.finish()

    def _ensure_started(self) -> None:
        if self._started:
            return
        self._spinner.__enter__()
        self._started = True

    def __call__(self, event: dict[str, Any]) -> None:
        _ = event
        self._ensure_started()

    def _title(self) -> str:
        if self._model_name:
            return f"Preparing model {self._model_name}"
        return "Preparing embedding model"

    def _details(self) -> tuple[str, ...]:
        if self._cached_model_artifact is True:
            return (
                "verifying cached model",
                "checking local cache",
                "using Recollectium model cache",
            )
        if self._cached_model_artifact is False:
            return (
                "downloading model files if needed",
                "checking local cache",
                "this can take a minute the first time",
                "using Recollectium model cache",
            )
        return (
            "checking model readiness",
            "checking local cache",
            "downloading model files if needed",
            "this can take a minute the first time",
        )


def _human_model_readiness_progress_reporter(
    output_format: str,
    *,
    model_name: str | None = None,
    cached_model_artifact: bool | None = None,
) -> _ModelReadinessProgressReporter | None:
    if output_format != CLI_OUTPUT_HUMAN_READABLE:
        return None
    if not _stderr_supports_live_progress():
        return None
    return _ModelReadinessProgressReporter(
        sys.stderr,
        model_name=model_name,
        cached_model_artifact=cached_model_artifact,
    )


def _human_upgrade_progress_context(
    output_format: str,
) -> contextlib.AbstractContextManager[object]:
    if output_format != CLI_OUTPUT_HUMAN_READABLE:
        return contextlib.nullcontext()
    if not _stderr_supports_live_progress():
        return contextlib.nullcontext()
    return SingleLineStatusSpinner(
        sys.stderr,
        title="Upgrade in progress",
        details=("running package update",),
    )


def _model_readiness_context(provider: object) -> tuple[str | None, bool | None]:
    model_name_value = getattr(provider, "model_name", None)
    model_name = model_name_value if isinstance(model_name_value, str) else None
    has_cached_model_artifact = getattr(provider, "has_cached_model_artifact", None)
    if not callable(has_cached_model_artifact):
        return model_name, None
    try:
        cached_model_artifact = bool(has_cached_model_artifact())
    except (OSError, ValueError):
        cached_model_artifact = None
    return model_name, cached_model_artifact


@contextlib.contextmanager
def _suppress_cli_readiness_provider_output() -> Iterator[None]:
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            yield


def _ensure_cli_model_ready(core: RecollectiumCore, *, output_format: str) -> None:
    ensure_ready = core._ensure_model_ready
    with _suppress_cli_readiness_provider_output():
        model_name, cached_model_artifact = _model_readiness_context(
            getattr(core, "embedding_provider", None)
        )
    progress_reporter = _human_model_readiness_progress_reporter(
        output_format,
        model_name=model_name,
        cached_model_artifact=cached_model_artifact,
    )
    if progress_reporter is None:
        with _suppress_cli_readiness_provider_output():
            if _callable_accepts_cli_readiness_keyword(
                ensure_ready, "suppress_provider_output"
            ):
                ensure_ready(suppress_provider_output=True)
            else:
                ensure_ready()
        return
    with progress_reporter, _suppress_cli_readiness_provider_output():
        if _callable_accepts_cli_readiness_keyword(ensure_ready, "progress_callback"):
            kwargs: dict[str, object] = {"progress_callback": progress_reporter}
            if _callable_accepts_cli_readiness_keyword(
                ensure_ready, "suppress_provider_output"
            ):
                kwargs["suppress_provider_output"] = True
            cast(Any, ensure_ready)(**kwargs)
        else:
            ensure_ready()


def _ensure_cli_provider_ready(
    provider: BuiltinFastEmbedProvider,
    *,
    config_path: Path | None,
    log_level: str | None,
    output_format: str,
) -> None:
    if not isinstance(provider, embeddings_module.BuiltinFastEmbedProvider):
        _ensure_cli_custom_provider_ready(provider, output_format=output_format)
        return
    readiness_core = cast(RecollectiumCore, object.__new__(RecollectiumCore))
    readiness_core.config = RecollectiumConfig(config_path, log_level=log_level)
    readiness_core.embedding_provider = provider
    readiness_core._embedding_provider_managed_by_recollectium = True
    _ensure_cli_model_ready(readiness_core, output_format=output_format)


def _ensure_cli_custom_provider_ready(provider: object, *, output_format: str) -> None:
    with _suppress_cli_readiness_provider_output():
        model_name, cached_model_artifact = _model_readiness_context(provider)
    progress_reporter = _human_model_readiness_progress_reporter(
        output_format,
        model_name=model_name,
        cached_model_artifact=cached_model_artifact,
    )
    with contextlib.ExitStack() as stack:
        if progress_reporter is not None:
            stack.enter_context(progress_reporter)
        stack.enter_context(_suppress_cli_readiness_provider_output())
        provider_ready = getattr(provider, "ensure_ready", None)
        if callable(provider_ready):
            provider_ready()
        else:
            cast(Any, provider).embed("healthcheck")


def _callable_accepts_cli_readiness_keyword(callback: Any, keyword: str) -> bool:
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return False
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD or name == keyword
        for name, parameter in signature.parameters.items()
    )


class _ThresholdOptimizationProgressReporter:
    """Translate threshold optimizer updates to a single-line renderer."""

    def __init__(self, stream: Any) -> None:
        title_limit = _live_progress_title_limit(stream)
        self._progress = SingleLineProgressReporter(
            stream,
            labels=_THRESHOLD_OPTIMIZATION_PROGRESS_LABELS,
            title_limit=12 if title_limit is None else title_limit,
        )
        self._started = False
        self._scoring_total = 0

    def __enter__(self) -> _ThresholdOptimizationProgressReporter:
        self._ensure_started()
        return self

    def _ensure_started(self) -> None:
        if self._started:
            return
        self._progress.__enter__()
        self._started = True

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        self._progress.finish()

    def phase(self, message: str) -> None:
        self._ensure_started()
        self._progress.phase(self._phase_label(message))

    def start_scoring(self, total: int) -> None:
        self._ensure_started()
        self._scoring_total = total
        self._progress.update("Scoring thresholds", completed=0, total=total)

    def advance_scoring(self, completed: int, threshold: float) -> None:
        _ = threshold
        self._ensure_started()
        self._progress.update(
            "Scoring thresholds",
            completed=completed,
            total=self._scoring_total,
        )

    def __call__(self, event: dict[str, object]) -> None:
        completed = event.get("completed")
        total = event.get("total")
        self._ensure_started()
        self._progress.update(
            str(event.get("label") or "Seeded dev memories"),
            completed=completed if isinstance(completed, int) else 0,
            total=total if isinstance(total, int) else 0,
        )

    def _phase_label(self, message: str) -> str:
        for prefix in _THRESHOLD_OPTIMIZATION_PROGRESS_LABELS:
            if message == prefix or message.startswith(f"{prefix}:"):
                return prefix
        return message


class _DevEvalProgressReporter:
    """Translate seeded dev eval progress events to a single-line renderer."""

    def __init__(
        self,
        stream: Any,
        *,
        clock: Any = time.monotonic,
        min_render_interval: float = 0.25,
    ) -> None:
        title_limit = _live_progress_title_limit(stream)
        self._progress = SingleLineProgressReporter(
            stream,
            labels=_DEV_EVAL_PROGRESS_LABELS,
            clock=clock,
            min_render_interval=min_render_interval,
            title_limit=12 if title_limit is None else title_limit,
        )

    def __enter__(self) -> _DevEvalProgressReporter:
        self._progress.__enter__()
        return self

    def __exit__(self, *_: object) -> None:
        self.finish()

    def finish(self) -> None:
        self._progress.finish()

    def phase(self, message: str) -> None:
        self._progress.phase(message)

    def __call__(self, event: dict[str, Any]) -> None:
        label = str(event.get("label") or event.get("phase") or "dev eval")
        self._progress.update(
            label,
            completed=int(event.get("completed") or 0),
            total=int(event.get("total") or 0),
        )

    def _format_line(
        self,
        label: str,
        percent: int,
        completed: int | None,
        total: int | None,
    ) -> str:
        return self._progress._format_line(label, percent, completed, total)

    def _bar_width(self, label: str, completed: int | None, total: int | None) -> int:
        return self._progress._bar_width(label, completed, total)


def _parse_config_value(raw: str) -> Any:
    """Parse a CLI-provided config value as JSON; fall back to string on failure."""
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _resolve_config_path(explicit_path: str | None) -> Path:
    """Resolve the config file path from --config flag or default XDG location."""
    from platformdirs import user_config_dir

    if explicit_path is not None:
        return Path(explicit_path)
    return Path(user_config_dir("recollectium")) / "config.json"


def _core_config_path(explicit_path: str | None) -> Path | None:
    """Return only explicit config paths for core/service initialization."""
    if explicit_path is None:
        return None
    return Path(explicit_path)


def _extract_cli_output_override(
    argv: Sequence[str] | None,
) -> tuple[list[str] | None, str | None, str | None, bool, bool, bool]:
    """Remove unambiguous global output and verbosity flags around subcommands."""
    raw_args = list(sys.argv[1:] if argv is None else argv)
    output_format: str | None = None
    response_verbosity: str | None = None
    cleaned: list[str] = []
    output_conflict = False
    verbosity_conflict = False
    explicit_json = False
    literal_args = False
    command_seen = False
    pending_option_value = False
    config_set_tokens: list[str] = []
    config_set_value_pending = False
    root_commands = {
        "init",
        "config",
        "add",
        "update",
        "archive",
        "search-user",
        "search-workspace",
        "list",
        "get",
        "workspace",
        "db-status",
        "embedding-status",
        "embedding-maintenance",
        "embedding-refresh",
        "embedding-jobs",
        "embedding-jobs-clear",
        "service",
        "mcp-stdio",
        "dev",
        "upgrade",
        "uninstall",
        "completion",
    }
    value_options = {
        "--config",
        "--db",
        "--log-level",
        "--space",
        "--type",
        "--content",
        "--workspace-uid",
        "--metadata",
        "--source",
        "--confidence",
        "--id",
        "--status",
        "--limit",
        "--protected-minimum",
        "--match-threshold",
        "--host",
        "--port",
        "--pid-file",
        "--log-file",
        "--format",
        "--timeout",
        "--timeout-seconds",
        "--complete-line",
        "--shell",
        "--target",
        "--apply",
        "--min",
        "--max",
        "--steps",
        "--output",
    }

    def append_cleaned(item: str) -> None:
        nonlocal command_seen, pending_option_value, config_set_value_pending
        cleaned.append(item)
        if item in value_options:
            pending_option_value = True
        if not command_seen and item in root_commands:
            command_seen = True
        if command_seen and len(config_set_tokens) < 3:
            config_set_tokens.append(item)
            if len(config_set_tokens) == 3 and config_set_tokens[:2] == [
                "config",
                "set",
            ]:
                config_set_value_pending = True

    for item in raw_args:
        if literal_args:
            cleaned.append(item)
            continue
        if pending_option_value:
            cleaned.append(item)
            pending_option_value = False
            continue
        if item == "--":
            literal_args = True
            cleaned.append(item)
            continue
        if config_set_value_pending:
            cleaned.append(item)
            config_set_value_pending = False
            continue
        if item == "--json":
            explicit_json = True
            if output_format == CLI_OUTPUT_HUMAN_READABLE:
                output_conflict = True
            output_format = CLI_OUTPUT_JSON
            continue
        if item == "--human-readable":
            if output_format == CLI_OUTPUT_JSON:
                output_conflict = True
            output_format = CLI_OUTPUT_HUMAN_READABLE
            continue
        if item == "--compact":
            if response_verbosity == RESPONSE_VERBOSITY_VERBOSE:
                verbosity_conflict = True
            response_verbosity = RESPONSE_VERBOSITY_COMPACT
            continue
        if item == "--verbose":
            if response_verbosity == RESPONSE_VERBOSITY_COMPACT:
                verbosity_conflict = True
            response_verbosity = RESPONSE_VERBOSITY_VERBOSE
            continue
        append_cleaned(item)
    if argv is None:
        cleaned_arg: list[str] | None = None if cleaned == raw_args else cleaned
        return (
            cleaned_arg,
            output_format,
            response_verbosity,
            output_conflict,
            verbosity_conflict,
            explicit_json,
        )
    return (
        cleaned,
        output_format,
        response_verbosity,
        output_conflict,
        verbosity_conflict,
        explicit_json,
    )


def _resolve_output_format(
    *,
    config_path: Path,
    explicit: bool,
    override: str | None,
) -> str:
    if override is not None:
        return override
    if not config_path.exists():
        return CLI_OUTPUT_HUMAN_READABLE
    try:
        raw = load_config_file(config_path)
        merged = _deep_merge(deepcopy(DEFAULTS), raw)
        try:
            _validate_config_value(merged)
        except ValidationError:
            configured = raw.get("cli_output") if isinstance(raw, dict) else None
            if configured in {CLI_OUTPUT_JSON, CLI_OUTPUT_HUMAN_READABLE}:
                return str(configured)
            return CLI_OUTPUT_HUMAN_READABLE
    except (FileNotFoundError, ValidationError, OSError):
        return CLI_OUTPUT_HUMAN_READABLE
    return str(merged.get("cli_output", CLI_OUTPUT_HUMAN_READABLE))


def _resolve_response_verbosity(
    *,
    config_path: Path,
    override: str | None,
) -> str:
    if override is not None:
        return str(validate_response_verbosity(override))
    if not config_path.exists():
        return RESPONSE_VERBOSITY_COMPACT
    try:
        raw = load_config_file(config_path)
        merged = _deep_merge(deepcopy(DEFAULTS), raw)
        _validate_config_value(merged)
    except (FileNotFoundError, ValidationError, OSError):
        return RESPONSE_VERBOSITY_COMPACT
    return str(
        validate_response_verbosity(
            str(merged.get("response_verbosity", RESPONSE_VERBOSITY_COMPACT))
        )
    )


def _load_effective_config(config_path: Path, *, explicit: bool) -> RecollectiumConfig:
    """Load effective config with first-run default creation semantics."""
    if explicit:
        return RecollectiumConfig(config_path)
    return RecollectiumConfig()


def _load_effective_config_read_only(
    config_path: Path, *, explicit: bool
) -> dict[str, Any]:
    """Load and validate effective config without creating files or directories."""
    if explicit:
        raw = load_config_file(config_path)
    elif config_path.exists():
        raw = load_config_file(config_path)
    else:
        raw = {}
    merged = _merged_config(raw)
    _validate_config_value(merged)
    return merged


def _merged_config(raw: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(deepcopy(DEFAULTS), raw)
    _apply_explicit_null_overrides(merged, raw)
    return merged


def _raw_config_has_key(config: dict[str, Any], key: str) -> bool:
    try:
        get_config_value(config, key)
    except KeyError:
        return False
    return True


def _remove_empty_config_parents(config: dict[str, Any], key: str) -> None:
    parts = key.split(".")[:-1]
    stack: list[tuple[dict[str, Any], str]] = []
    current: Any = config
    for part in parts:
        if not isinstance(current, dict) or not isinstance(current.get(part), dict):
            return
        stack.append((current, part))
        current = current[part]
    for parent, part in reversed(stack):
        child = parent.get(part)
        if isinstance(child, dict) and not child:
            parent.pop(part)
            continue
        break


def _setup_cli_logging(
    config_path: Path,
    *,
    log_level: str | None,
) -> None:
    """Start file logging before commands that do not build RecollectiumCore."""

    def _fallback_config() -> _CliLoggingConfig:
        effective_config = deepcopy(DEFAULTS)
        if log_level is not None:
            effective_config["logging"]["level"] = log_level
        return _CliLoggingConfig(
            effective_config=effective_config,
            log_dir=Path(user_state_dir("recollectium")) / "logs",
        )

    try:
        if config_path.exists():
            config = RecollectiumConfig(config_path, log_level=log_level)
        else:
            config = _fallback_config()
        setup_logging(config)
    except OSError:
        setup_logging(_fallback_config())
    except ValidationError:
        setup_logging(_fallback_config())


def _directory_writable(path: Path) -> bool:
    """Return True when *path* is writable by current user."""
    try:
        with tempfile.TemporaryFile(dir=path):
            return True
    except OSError:
        return False


def _log_file_warning(message: str, *, event: str) -> None:
    """Write a warning record to managed file logs without emitting to stderr."""

    logger = logging.getLogger("recollectium")
    if not logger.isEnabledFor(logging.WARNING):
        return
    record = _log.makeRecord(
        _log.name,
        logging.WARNING,
        __file__,
        0,
        message,
        (),
        None,
        extra={"event": event},
    )
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and record.levelno >= handler.level:
            handler.handle(record)


def _builtin_fastembed_provider_from_config(
    config: dict[str, Any],
    *,
    model_cache_path: Path | None = None,
) -> BuiltinFastEmbedProvider:
    embedding = config.get("embedding", {})
    model_name = (
        embedding.get("model")
        if isinstance(embedding, dict)
        else DEFAULTS["embedding"]["model"]
    )
    if model_cache_path is None:
        directories = config.get("directories", {})
        xdg_dirs = _resolve_xdg_dirs(
            directories if isinstance(directories, dict) else {}
        )
        model_cache_path = resolve_model_cache_path(xdg_dirs["cache"])
    return BuiltinFastEmbedProvider(str(model_name), cache_dir=model_cache_path)


def _handle_config_command(
    args: argparse.Namespace,
    config_path: Path,
    *,
    explicit: bool,
    output_format: str,
) -> int:
    """Handle the `recollectium config` command and its subcommands."""
    if args.config_action == "get":
        try:
            cfg = _load_effective_config(config_path, explicit=explicit)
            value = get_config_value(cfg.effective_config, args.key)
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="config get")
        except ValidationError as exc:
            return _config_invalid_error(exc, command="config get")
        except KeyError as exc:
            return _not_found_error(exc, command="config get")
        _emit_success(
            value, output_format=output_format, command="config get", label=args.key
        )
        return 0

    if args.config_action == "set":
        value = _parse_config_value(args.value)
        raw = (
            load_config_file(config_path)
            if config_path.exists()
            else deepcopy(DEFAULTS)
        )
        effective = _merged_config(raw)
        try:
            current_value = get_config_value(effective, args.key)
        except KeyError:
            current_value = object()
        candidate = deepcopy(raw)
        set_config_value(candidate, args.key, value)
        # Validate the resulting config before writing or reporting a no-op.
        try:
            merged = _merged_config(candidate)
            _validate_config_value(merged)
        except ValidationError as exc:
            return _config_invalid_error(exc, command="config set")
        if current_value == value:
            _emit_success(
                {
                    "status": "skipped",
                    "reason": "already_set",
                    "key": args.key,
                    "value": value,
                },
                output_format=output_format,
                command="config set",
            )
            return 0
        if not config_path.exists():
            config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8"
            )
            config_path.chmod(0o600)
        config_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        _emit_success(
            {"status": "updated", "key": args.key, "value": value},
            output_format=output_format,
            command="config set",
        )
        return 0

    if args.config_action == "unset":
        if not config_path.exists():
            return _config_missing_error(
                FileNotFoundError(f"config file not found: {config_path}"),
                command="config unset",
            )
        raw = load_config_file(config_path)
        if not _raw_config_has_key(raw, args.key):
            _emit_success(
                {"status": "skipped", "reason": "already_unset", "key": args.key},
                output_format=output_format,
                command="config unset",
            )
            return 0
        unset_config_value(raw, args.key)
        _remove_empty_config_parents(raw, args.key)
        config_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        _emit_success(
            {"status": "removed", "key": args.key},
            output_format=output_format,
            command="config unset",
        )
        return 0

    if args.config_action == "init":
        if config_path.exists() and not args.force:
            return _emit_cli_failure(
                status="operation_failed",
                message="Config file already exists.",
                detail=f"config file already exists: {config_path}",
                hint="Use recollectium config init --force to overwrite it.",
                exit_code=1,
                command="config init",
                event="config.exists",
                compact_human=True,
                compact_message=(
                    "Config file already exists; use recollectium config init --force "
                    "to overwrite it."
                ),
            )
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        config_path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
        config_path.chmod(0o600)
        _emit_success(
            {"status": "initialized", "path": str(config_path)},
            output_format=output_format,
            command="config init",
        )
        return 0

    if args.config_action == "doctor":
        try:
            cfg = _load_effective_config(config_path, explicit=explicit)
        except ValidationError as exc:
            return _config_invalid_error(exc, command="config doctor")
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="config doctor")

        failures: list[str] = []
        checks: dict[str, str] = {"config": str(cfg.config_file_path)}

        for name in ("data", "cache", "logs", "runtime"):
            directory = cfg.xdg_dirs[name]
            if not directory.exists():
                failures.append(f"{name} directory missing: {directory}")
                continue
            if not directory.is_dir():
                failures.append(f"{name} path is not a directory: {directory}")
                continue
            if not _directory_writable(directory):
                failures.append(f"{name} directory is not writable: {directory}")
                continue
            checks[name] = str(directory)

        db_parent = cfg.resolved_database_path.parent
        if not db_parent.exists():
            failures.append(f"database parent directory missing: {db_parent}")
        elif not db_parent.is_dir():
            failures.append(f"database parent path is not a directory: {db_parent}")
        elif not _directory_writable(db_parent):
            failures.append(f"database parent directory is not writable: {db_parent}")
        else:
            checks["database_parent"] = str(db_parent)

        if failures:
            for failure in failures:
                _log_file_warning(failure, event="config.doctor_failed")
            return _emit_cli_failure(
                status="operation_failed",
                message="Config doctor found filesystem problems.",
                detail="; ".join(f"FAIL {failure}" for failure in failures),
                exit_code=1,
                command="config doctor",
                event="config.doctor_failed",
                failures=failures,
                compact_human=True,
                compact_message=(
                    "Config doctor found filesystem problems; rerun with --verbose "
                    "for details."
                ),
            )

        _emit_success(
            {"status": "ok", "checks": checks},
            output_format=output_format,
            command="config doctor",
        )
        return 0

    if args.config_action == "edit":
        if not config_path.exists():
            config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8"
            )
            config_path.chmod(0o600)
        editor = os.environ.get("EDITOR", "vi")
        try:
            return subprocess.call([editor, str(config_path)])
        except FileNotFoundError:
            return _emit_cli_failure(
                status="operation_failed",
                message="Editor was not found.",
                detail=f"editor not found: {editor}",
                hint="Set EDITOR to an installed editor or edit the config file directly.",
                exit_code=1,
                command="config edit",
                event="config.editor_missing",
            )

    if args.config_action == "reset":
        existed = config_path.exists()
        previous_raw: dict[str, Any] | None = None
        if existed:
            previous_raw = load_config_file(config_path)
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        config_path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
        config_path.chmod(0o600)
        payload: dict[str, Any] = {"path": str(config_path)}
        if _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_VERBOSE:
            previous_keys = (
                sorted(previous_raw.keys()) if isinstance(previous_raw, dict) else []
            )
            previous_unknown_keys = sorted(set(previous_keys) - set(DEFAULTS.keys()))
            payload.update(
                {
                    "status": "reset",
                    "existed": existed,
                    "reset_to_defaults": True,
                    "changed": previous_raw != DEFAULTS,
                    "reset_keys": sorted(DEFAULTS.keys()),
                    "previous_keys": previous_keys,
                    "previous_unknown_keys": previous_unknown_keys,
                }
            )
        _emit_success(
            payload,
            output_format=output_format,
            command="config reset",
        )
        return 0

    if args.validate:
        try:
            effective_config = _load_effective_config_read_only(
                config_path, explicit=explicit
            )
        except ValidationError as exc:
            return _config_invalid_error(exc, command="config --validate")
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="config --validate")
        payload: dict[str, Any] = {"status": "valid", "config": effective_config}
        if (
            output_format == CLI_OUTPUT_JSON
            and _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_COMPACT
        ):
            payload = {"status": "valid"}
        _emit_success(payload, output_format=output_format, command="config --validate")
        return 0

    if args.path:
        if output_format == CLI_OUTPUT_HUMAN_READABLE:
            sys.stdout.write(_frame_human_output(str(config_path)))
        else:
            _emit_success(
                {"path": str(config_path)},
                output_format=output_format,
                command="config --path",
            )
        return 0

    if args.defaults:
        _emit_success(
            DEFAULTS,
            output_format=output_format,
            command="config",
            json_indent=2,
        )
        return 0

    # No subcommand or flag: print effective config
    try:
        cfg = _load_effective_config(config_path, explicit=explicit)
    except FileNotFoundError as exc:
        return _config_missing_error(exc, command="config")
    except ValidationError as exc:
        return _config_invalid_error(exc, command="config")
    _emit_success(
        cfg.effective_config,
        output_format=output_format,
        command="config",
        json_indent=2,
    )
    return 0


def _run_embedding_maintenance(
    config_path: Path,
    *,
    explicit: bool,
    db_path: str | None,
    log_level: str | None,
    output_format: str,
) -> dict[str, Any]:
    """Prepare the configured FastEmbed model and refresh stale DB embeddings."""
    config_existed = config_path.exists()
    if explicit and not config_existed:
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        config_path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
        config_path.chmod(0o600)

    cfg = RecollectiumConfig(config_path if explicit else None, log_level=log_level)
    selected_db_path = (
        Path(db_path) if db_path is not None else cfg.resolved_database_path
    )
    database_existed = selected_db_path.exists()
    SQLiteMemoryStore(selected_db_path)
    core = RecollectiumCore(
        db_path=selected_db_path,
        config_path=config_path if explicit else None,
        log_level=log_level,
    )
    _log.info(
        "preparing embedding model and refreshing stale embeddings",
        extra={"event": "embedding_maintenance.start"},
    )
    _ensure_cli_model_ready(core, output_format=output_format)
    refresh = _refresh_stale_embeddings_with_progress(
        core,
        include_archived=True,
        output_format=output_format,
    )
    profile = core.embedding_provider.embedding_profile
    return {
        "status": "embedding_maintenance_completed",
        "config": str(cfg.config_file_path),
        "config_created": not config_existed,
        "data": str(cfg.xdg_dirs["data"]),
        "cache": str(cfg.xdg_dirs["cache"]),
        "logs": str(cfg.xdg_dirs["logs"]),
        "runtime": str(cfg.xdg_dirs["runtime"]),
        "database": str(core.store.db_path),
        "database_created": not database_existed,
        "embedding_model": cfg.effective_config["embedding"]["model"],
        "embedding_profile": profile,
        "model_prepared": True,
        "embedding_refresh": refresh,
    }


def _run_installed_embedding_maintenance(
    *,
    config_path: Path,
    explicit: bool,
    db_path: str | None,
    log_level: str | None,
    timeout_seconds: int,
) -> CommandResult:
    """Run embedding maintenance in a fresh interpreter after package upgrade."""
    command = [sys.executable, "-m", "recollectium", "--json"]
    if explicit:
        command.extend(["--config", str(config_path)])
    if db_path is not None:
        command.extend(["--db", db_path])
    if log_level is not None:
        command.extend(["--log-level", log_level])
    command.append("embedding-maintenance")
    return SubprocessCommandRunner().run(command, timeout_seconds=timeout_seconds)


def _handle_init_command(
    config_path: Path,
    *,
    explicit: bool,
    db_path: str | None,
    log_level: str | None,
    output_format: str,
) -> int:
    """Initialize Recollectium config, directories, database, and model cache."""
    result = _run_embedding_maintenance(
        config_path,
        explicit=explicit,
        db_path=db_path,
        log_level=log_level,
        output_format=output_format,
    )
    refresh = result.get("embedding_refresh")
    refreshed = isinstance(refresh, dict) and refresh.get("refreshed") is True
    result["already_initialized"] = (
        result.get("config_created") is False
        and result.get("database_created") is False
        and not refreshed
    )
    result["status"] = "initialized"
    _emit_success(result, output_format=output_format, command="init")
    return 0


# -- CLI failure contract -------------------------------------------------
#
# Except for argparse-generated help/usage output, command failures follow the
# active CLI output format on stderr and keep stdout reserved for success output.
# Logs are diagnostic telemetry only: they must not be used as CLI control-flow
# payloads, must not write to stdout, and must avoid sensitive content.
def _print_json_stderr(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)


_CURRENT_CLI_OUTPUT_FORMAT = CLI_OUTPUT_JSON


def _set_cli_output_format(output_format: str) -> None:
    global _CURRENT_CLI_OUTPUT_FORMAT
    _CURRENT_CLI_OUTPUT_FORMAT = output_format


def _format_human_error(payload: dict[str, object], *, color: bool = False) -> str:
    if (
        payload.get("compact_human") is True
        and _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_COMPACT
    ):
        compact_message = payload.get("compact_message") or payload.get("message")
        return _style(
            str(compact_message or "Command failed."),
            _RICH_ERROR,
            enabled=color,
        )
    lines = [
        _style(
            str(payload.get("message") or "Command failed."), _RICH_ERROR, enabled=color
        )
    ]
    status = payload.get("status")
    if status is not None:
        lines.append(f"  {_format_label('Status', color=color)} {_json_scalar(status)}")
    detail = payload.get("detail")
    if detail is not None:
        lines.append(f"  {_format_label('Detail', color=color)} {_json_scalar(detail)}")
    hint = payload.get("hint")
    if hint is not None:
        lines.append(
            f"  {_format_label('Hint', color=color)} "
            f"{_style(_json_scalar(hint), _RICH_HINT, enabled=color)}"
        )
    for key, value in payload.items():
        if key in {
            "message",
            "status",
            "detail",
            "hint",
            "compact_human",
            "compact_message",
        }:
            continue
        lines.append(
            f"  {_format_label(_humanize_key(key), color=color)} {_json_scalar(value)}"
        )
    return "\n".join(lines)


def _emit_failure_payload(payload: dict[str, object]) -> None:
    if _CURRENT_CLI_OUTPUT_FORMAT == CLI_OUTPUT_HUMAN_READABLE:
        sys.stderr.write(
            _frame_human_output(
                _format_human_error(payload, color=_supports_color(sys.stderr))
            )
        )
        return
    json_payload = {
        key: value
        for key, value in payload.items()
        if key not in {"compact_human", "compact_message"}
    }
    _print_json_stderr(json_payload)


def _emit_cli_failure(
    *,
    status: str,
    message: str,
    exit_code: int,
    command: str | None = None,
    detail: str | None = None,
    hint: str | None = None,
    event: str = "cli.failure",
    **fields: object,
) -> int:
    payload: dict[str, object] = {"status": status, "message": message}
    if detail is not None:
        payload["detail"] = detail
    if hint is not None:
        payload["hint"] = hint
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    _emit_failure_payload(payload)
    _log.info(
        "CLI command failed",
        extra={
            "event": event,
            "context": {
                "command": command,
                "status": status,
                "exit_code": exit_code,
            },
        },
    )
    return exit_code


def _config_missing_error(exc: FileNotFoundError, *, command: str | None) -> int:
    return _emit_cli_failure(
        status="config_missing",
        message="Config file was not found.",
        detail=str(exc),
        hint="Check the --config path or omit --config to use the default config location.",
        exit_code=1,
        command=command,
        event="config.missing",
    )


def _config_invalid_error(exc: ValidationError, *, command: str | None) -> int:
    return _emit_cli_failure(
        status="config_invalid",
        message="Config is invalid.",
        detail=f"ValidationError: {exc}",
        hint="Fix the config file or run recollectium config reset to restore defaults.",
        exit_code=2,
        command=command,
        event="config.invalid",
    )


def _validation_error(
    exc: ValidationError,
    *,
    command: str | None,
    status: str = "validation_error",
    event: str = "cli.failure",
    exit_code: int = 2,
) -> int:
    message = "Input validation failed."
    return _emit_cli_failure(
        status=status,
        message=message,
        detail=f"ValidationError: {exc}",
        exit_code=exit_code,
        command=command,
        event=event,
    )


def _metadata_invalid_error(exc: _MetadataInvalidError) -> int:
    return _emit_cli_failure(
        status="metadata_invalid",
        message="Metadata must be a JSON object.",
        detail=f"ValidationError: {exc}",
        hint='Pass metadata as a JSON object, for example --metadata \'{"source": "notes"}\'.',
        exit_code=2,
        command="memory metadata",
        event="memory.metadata_invalid",
    )


def _workspace_validation_error(exc: ValidationError, *, command: str) -> int:
    detail = str(exc)
    if (
        "workspace alias already exists" in detail
        or "workspace alias conflicts with existing workspace memories" in detail
    ):
        return _emit_cli_failure(
            status="operation_failed",
            message="Workspace operation could not be completed because of existing resources.",
            detail=f"ValidationError: {exc}",
            hint="Resolve the existing workspace or alias conflict and retry.",
            exit_code=1,
            command=command,
            event="workspace.resource_conflict",
        )
    return _validation_error(exc, command=command, event="workspace.invalid")


def _not_found_error(exc: Exception, *, command: str | None) -> int:
    return _emit_cli_failure(
        status="not_found",
        message="Requested resource was not found.",
        detail=f"{exc.__class__.__name__}: {exc}",
        exit_code=1,
        command=command,
    )


def _service_error(
    exc: Exception,
    *,
    command: str | None,
    status: str = "service_error",
    exit_code: int = 1,
    event: str = "cli.failure",
) -> int:
    return _emit_cli_failure(
        status=status,
        message="Service operation failed.",
        detail=f"{exc.__class__.__name__}: {exc}",
        exit_code=exit_code,
        command=command,
        event=event,
    )


def _embedding_error(exc: Exception, *, command: str | None) -> int:
    if isinstance(exc, EmbeddingReadinessTimeoutError):
        return _emit_cli_failure(
            status="embedding_timeout",
            message="Embedding model readiness timed out.",
            detail=f"{exc.__class__.__name__}: {exc}",
            hint="Check your internet connection and retry recollectium init.",
            exit_code=1,
            command=command,
            event="embedding.readiness_timeout",
        )
    if isinstance(exc, EmbeddingModelUnavailableError):
        return _emit_cli_failure(
            status="embedding_model_unavailable",
            message="Embedding model could not be loaded or downloaded.",
            detail=f"{exc.__class__.__name__}: {exc}",
            hint="Check your internet connection and retry recollectium init.",
            exit_code=1,
            command=command,
            event="embedding.model_unavailable",
        )
    if isinstance(exc, EmbeddingProviderUnavailableError):
        return _emit_cli_failure(
            status="embedding_provider_unavailable",
            message="Embedding provider is unavailable.",
            detail=f"{exc.__class__.__name__}: {exc}",
            hint="Check the local runtime and retry recollectium init.",
            exit_code=1,
            command=command,
            event="embedding.provider_unavailable",
        )
    return _emit_cli_failure(
        status="embedding_error",
        message="Embedding operation failed.",
        detail=f"{exc.__class__.__name__}: {exc}",
        exit_code=1,
        command=command,
    )


def _operation_failed_error(exc: Exception, *, command: str | None) -> int:
    return _emit_cli_failure(
        status="operation_failed",
        message="Operation failed.",
        detail=f"{exc.__class__.__name__}: {exc}",
        exit_code=1,
        command=command,
    )


def _resolve_seeded_dev_database_path(cfg: RecollectiumConfig) -> Path:
    dev_path = Path(cfg.effective_config["development"]["seeded_database_path"])
    if not dev_path.is_absolute():
        dev_path = cfg.xdg_dirs["data"] / dev_path
    return dev_path


def _resolve_regular_database_path(
    cfg: RecollectiumConfig, db_path_override: str | None = None
) -> Path:
    if db_path_override is not None:
        return Path(db_path_override).expanduser()
    db_path = Path(cfg.effective_config["database"]["path"])
    if not db_path.is_absolute():
        db_path = cfg.xdg_dirs["data"] / db_path
    return db_path


def _paths_equal(first: Path, second: Path) -> bool:
    return first.resolve(strict=False) == second.resolve(strict=False)


def _seeded_dev_context(db_path: Path) -> dict[str, object]:
    return {
        "database": str(db_path),
        "initialized": seeded_dev_database_is_initialized(db_path),
        "expected_user_memories": DEV_SEED_USER_MEMORY_COUNT,
        "expected_workspace_memories": DEV_SEED_TOTAL_WORKSPACE_MEMORIES,
        "expected_workspaces": DEV_SEED_WORKSPACE_COUNT,
        "expected_topics": DEV_SEED_TOPIC_COUNT,
    }


def _metric_value(value: float) -> float:
    return round(value, 6)


def _exact_mrr_payload(report: ExactMRRReport) -> dict[str, object]:
    return {
        "value": _metric_value(report.value),
        "cutoff": report.cutoff,
        "targets": report.targets,
        "user_targets": report.user_targets,
        "workspace_targets": report.workspace_targets,
        "user_value": _metric_value(report.user_value),
        "workspace_value": _metric_value(report.workspace_value),
        "hit_at_1": _metric_value(report.hit_at_1),
        "hit_at_3": _metric_value(report.hit_at_3),
    }


def _semantic_mrr_payload(report: SemanticMRRReport) -> dict[str, object]:
    return {
        "value": _metric_value(report.value),
        "cutoff": report.cutoff,
        "targets": report.targets,
        "queries": report.queries,
        "paraphrases_per_target": report.paraphrases_per_target,
        "user_targets": report.user_targets,
        "workspace_targets": report.workspace_targets,
        "user_value": _metric_value(report.user_value),
        "workspace_value": _metric_value(report.workspace_value),
    }


def _thematic_weighted_payload(
    report: ThematicWeightedReport,
    *,
    value: float,
) -> dict[str, object]:
    return {
        "value": _metric_value(value),
        "weighted_precision": _metric_value(report.weighted_precision),
        "weighted_recall": _metric_value(report.weighted_recall),
        "weighted_f1": _metric_value(report.weighted_f1),
        "limit": report.limit,
        "protected_minimum": report.protected_minimum,
        "match_threshold": _metric_value(report.match_threshold),
        "groups": report.groups,
        "queries": report.queries,
        "queries_per_group": report.queries_per_group,
        "user_groups": report.user_groups,
        "workspace_groups": report.workspace_groups,
        "user_weighted_precision": _metric_value(report.user_weighted_precision),
        "user_weighted_recall": _metric_value(report.user_weighted_recall),
        "workspace_weighted_precision": _metric_value(
            report.workspace_weighted_precision
        ),
        "workspace_weighted_recall": _metric_value(report.workspace_weighted_recall),
    }


def _ranked_set_ndcg_payload(report: RankedSetNDCGReport) -> dict[str, object]:
    return {
        "value": _metric_value(report.value),
        "cutoff": report.cutoff,
        "cases": report.cases,
        "user_cases": report.user_cases,
        "workspace_cases": report.workspace_cases,
        "user_value": _metric_value(report.user_value),
        "workspace_value": _metric_value(report.workspace_value),
    }


def _dev_eval_diagnostics_payload(
    exact_report: ExactMRRReport,
    semantic_report: SemanticMRRReport,
    thematic_report: ThematicWeightedReport,
    ranked_set_report: RankedSetNDCGReport,
) -> dict[str, object]:
    return {
        "worst_exact": [
            {
                "target_id": miss.target_id,
                "expected_scope": miss.expected_scope,
                "workspace_uid": miss.workspace_uid,
                "rank": miss.rank,
                "reciprocal_rank": _metric_value(miss.reciprocal_rank),
                "query_snippet": miss.query_snippet,
                "returned_top_ids": list(miss.returned_top_ids),
            }
            for miss in exact_report.worst_misses
        ],
        "worst_semantic": [
            {
                "target_id": target.target_id,
                "expected_scope": target.expected_scope,
                "workspace_uid": target.workspace_uid,
                "average_reciprocal_rank": _metric_value(
                    target.average_reciprocal_rank
                ),
                "queries": [
                    {
                        "query_index": score.query_index,
                        "rank": score.rank,
                        "reciprocal_rank": _metric_value(score.reciprocal_rank),
                        "returned_top_ids": list(score.returned_top_ids),
                    }
                    for score in target.query_scores
                ],
            }
            for target in semantic_report.worst_targets
        ],
        "worst_thematic": [
            {
                "scope": worst.scope,
                "expected_group": worst.expected_group,
                "workspace_uid": worst.workspace_uid,
                "query_index": worst.query_index,
                "query": worst.query,
                "weighted_precision": _metric_value(worst.weighted_precision),
                "weighted_recall": _metric_value(worst.weighted_recall),
                "weighted_f1": _metric_value(worst.weighted_f1),
                "returned_count": worst.returned_count,
                "useful_value_retrieved": _metric_value(worst.useful_value_retrieved),
                "useful_value_total": _metric_value(worst.useful_value_total),
                "retrieved_cost_total": _metric_value(worst.retrieved_cost_total),
                "direct_count": worst.direct_count,
                "adjacent_count": worst.adjacent_count,
                "unrelated_count": worst.unrelated_count,
                "confuser_count": worst.confuser_count,
                "confuser_exposure": _metric_value(worst.confuser_exposure),
                "returned_top_ids": list(worst.returned_top_ids),
                "returned_eval_keys": list(worst.returned_eval_keys),
                "returned_labels": list(worst.returned_labels),
            }
            for worst in thematic_report.worst_queries
        ],
        "worst_ranked_sets": [
            {
                "case_id": case.case_id,
                "expected_scope": case.expected_scope,
                "workspace_uid": case.workspace_uid,
                "ndcg": _metric_value(case.ndcg),
                "expected_memories": [
                    {
                        "memory_id": memory.memory_id,
                        "grade": memory.grade,
                        "rationale": memory.rationale,
                    }
                    for memory in case.expected_memories
                ],
                "returned_top": [
                    {
                        "memory_id": memory.memory_id,
                        "rank": memory.rank,
                        "grade": memory.grade,
                    }
                    for memory in case.returned_top
                ],
            }
            for case in ranked_set_report.lowest_cases
        ],
        "confusers": [],
    }


def _run_seeded_dev_eval(
    cfg: RecollectiumConfig,
    *,
    provider: Any,
    config_path: Path | None,
    regular_db_path: Path,
    eval_progress_reporter: _DevEvalProgressReporter | None = None,
    search_progress_reporter: _ReembeddingProgressReporter | None = None,
    verbose_progress: bool = False,
) -> dict[str, object]:
    dev_db_path = _resolve_seeded_dev_database_path(cfg)
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Preparing seeded development database")
    seed_result = _call_with_optional_progress_callback(
        ensure_seeded_dev_database,
        dev_db_path,
        provider,
        progress_callback=eval_progress_reporter,
    )
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Loading eval fixtures")
    core = RecollectiumCore(
        db_path=dev_db_path,
        config_path=config_path,
        embedding_provider=provider,
        log_level=cfg.effective_config["logging"]["level"],
    )
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Running exact MRR")
    exact_report = evaluate_exact_mrr_for_core(
        cast(Any, core),
        progress_callback=search_progress_reporter,
        eval_progress_callback=eval_progress_reporter,
    )
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Running semantic MRR")
    semantic_report = evaluate_semantic_mrr_for_core(
        cast(Any, core),
        progress_callback=search_progress_reporter,
        eval_progress_callback=eval_progress_reporter,
    )
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Running thematic weighted metrics")
    thematic_report = evaluate_thematic_weighted_metrics_for_core(
        cast(Any, core),
        progress_callback=search_progress_reporter,
        eval_progress_callback=eval_progress_reporter,
    )
    if eval_progress_reporter is not None:
        eval_progress_reporter.phase("Running ranked-set NDCG@5")
    ranked_set_report = evaluate_ranked_set_ndcg_for_core(
        cast(Any, core),
        progress_callback=search_progress_reporter,
        eval_progress_callback=eval_progress_reporter,
    )
    return {
        "status": "ok",
        "database": str(dev_db_path),
        "regular_database": str(regular_db_path),
        "regular_database_not_touched": True,
        "preparation": {
            "seeded_database": "ready"
            if seed_result is None
            else seed_result["status"],
            "fixtures": "loaded",
        },
        "phases": {
            "exact_mrr": {
                "user_memories": exact_report.user_targets,
                "workspace_memories": exact_report.workspace_targets,
                "total": exact_report.targets,
            },
            "semantic_mrr": {
                "paraphrases": semantic_report.queries,
                "targets": semantic_report.targets,
            },
            "thematic_weighted_at_10": {
                "user_topics": thematic_report.user_groups,
                "workspace_themes": thematic_report.workspace_groups,
                "queries": thematic_report.queries,
            },
            "ranked_set_ndcg_at_5": {"cases": ranked_set_report.cases},
        },
        "metrics": {
            "exact_mrr": _exact_mrr_payload(exact_report),
            "semantic_mrr": _semantic_mrr_payload(semantic_report),
            "thematic_weighted_precision_at_10": _thematic_weighted_payload(
                thematic_report, value=thematic_report.weighted_precision
            ),
            "thematic_weighted_recall_at_10": _thematic_weighted_payload(
                thematic_report, value=thematic_report.weighted_recall
            ),
            "ranked_set_ndcg_at_5": _ranked_set_ndcg_payload(ranked_set_report),
        },
        "diagnostics": _dev_eval_diagnostics_payload(
            exact_report,
            semantic_report,
            thematic_report,
            ranked_set_report,
        ),
    }


def _run_seeded_dev_optimize_threshold(
    cfg: RecollectiumConfig,
    *,
    provider: Any,
    config_path: Path,
    regular_db_path: Path,
    args: argparse.Namespace,
    output_format: str,
    response_verbosity: str,
    progress: _ThresholdOptimizationProgressReporter | None = None,
) -> int:
    """Run the seeded threshold optimizer against the PR1 thematic fixtures."""

    dev_db_path = _resolve_seeded_dev_database_path(cfg)
    if progress is not None:
        progress.phase(f"Preparing seeded development database: {dev_db_path}")
    seed_result = _call_with_optional_progress_callback(
        ensure_seeded_dev_database,
        dev_db_path,
        provider,
        progress_callback=progress,
    )
    if progress is not None:
        progress.phase("Loading fixtures")
    cases = threshold_cases_from_fixture()
    core = RecollectiumCore(
        db_path=dev_db_path,
        config_path=config_path,
        embedding_provider=provider,
        log_level=cfg.effective_config["logging"]["level"],
    )
    if progress is not None:
        progress.phase("Loading candidate pools")
    bundles = build_threshold_search_bundles(
        cases,
        search_user=lambda query, limit: core.search_user_memories(
            query=query,
            limit=limit,
            include_archived=False,
            protected_minimum=0,
            match_threshold=None,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            core.search_workspace_memories(
                query=query,
                workspace_uid=workspace_uid,
                limit=limit,
                include_archived=False,
                protected_minimum=0,
                match_threshold=None,
            )
        ),
    )
    output_path = (
        Path(args.output).expanduser()
        if args.output is not None
        else (
            Path.cwd() / "recollectium-threshold-sweep.png"
            if args.format == "png"
            else None
        )
    )
    if progress is not None:
        progress.start_scoring(
            len(generate_threshold_values(args.start, args.end, args.step))
        )
    report = build_threshold_optimization_report(
        model=str(provider.embedding_profile.get("model", "unknown model")),
        provider=str(provider.embedding_profile.get("provider", "unknown provider")),
        start=args.start,
        end=args.end,
        step=args.step,
        beta=args.beta,
        output_format=args.format,
        output_path=str(output_path) if output_path is not None else None,
        wrote_config=args.write_config,
        bundles=bundles,
        scoring_progress=progress.advance_scoring if progress is not None else None,
    )
    policy = resolve_retrieval_policy(
        config_protected_minimum=cfg.effective_config.get("retrieval", {}).get(
            "protected_minimum", 3
        ),
        config_match_threshold=cfg.effective_config.get("retrieval", {}).get(
            "match_threshold", "model_recommended_default"
        ),
        embedding_model=str(provider.embedding_profile.get("model", "")),
    )
    disabled_row = score_runtime_row(
        bundles,
        protected_minimum=0,
        match_threshold=None,
        beta=args.beta,
    )
    current_row = score_runtime_row(
        bundles,
        protected_minimum=policy.protected_minimum,
        match_threshold=policy.match_threshold,
        beta=args.beta,
    )

    if args.write_config:
        if progress is not None:
            progress.phase(f"Writing config: {config_path}")
        raw_config = (
            load_config_file(config_path)
            if config_path.exists()
            else deepcopy(DEFAULTS)
        )
        set_config_value(
            raw_config, "retrieval.match_threshold", report.recommended_threshold
        )
        merged = _deep_merge(deepcopy(DEFAULTS), raw_config)
        _validate_config_value(merged)
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(raw_config, indent=2) + "\n", encoding="utf-8"
        )
        config_path.chmod(0o600)

    if args.format == "png":
        assert output_path is not None
        if progress is not None:
            progress.phase(f"Writing PNG artifact: {output_path}")
        artifact_path = write_threshold_png(report, output_path)
    elif args.output is None:
        artifact_path = output_path
    else:
        csv_output_path = Path(args.output).expanduser()
        if progress is not None:
            progress.phase(f"Writing CSV artifact: {csv_output_path}")
        artifact_path = write_threshold_csv(report.rows, csv_output_path) or output_path

    artifact_display_path = (
        "stdout" if args.format == "csv" and args.output is None else str(artifact_path)
    )

    payload: dict[str, object] = {
        "status": "ok",
        "database": str(dev_db_path),
        "regular_database": str(regular_db_path),
        "regular_database_not_touched": True,
        "preparation": {
            "seeded_database": "ready"
            if seed_result is None
            else seed_result["status"],
            "fixtures": "loaded",
        },
        "optimization": report.to_dict(),
        "baselines": {
            "disabled": {
                **disabled_row.to_dict(),
                "mode": "disabled",
            },
            "current_config": {
                **current_row.to_dict(),
                "mode": policy.match_threshold_source,
                "protected_minimum": policy.protected_minimum,
                "match_threshold": policy.match_threshold,
            },
        },
        "artifact": {
            "format": args.format,
            "path": artifact_display_path,
        },
    }

    if (
        output_format == CLI_OUTPUT_HUMAN_READABLE
        and args.format == "csv"
        and args.output is None
    ):
        if progress is not None:
            progress.phase("Writing CSV sweep to stdout")
            progress.finish()
        sys.stdout.write(threshold_rows_to_csv(report.rows))
        summary_lines = report_summary_lines(
            report,
            output_path=Path("stdout"),
            current_threshold=policy.match_threshold,
            current_source=policy.match_threshold_source,
            verbose=response_verbosity == RESPONSE_VERBOSITY_VERBOSE,
            write_config=args.write_config,
            title_formatter=lambda value: _style(
                value, _RICH_BLUE_HEADING, enabled=_supports_color(sys.stderr)
            ),
            footer_formatter=lambda value: _style(
                value,
                _RICH_SUCCESS if args.write_config else _RICH_HINT,
                enabled=_supports_color(sys.stderr),
            ),
        )
        sys.stderr.write(_frame_human_output("\n".join(summary_lines)))
        sys.stderr.flush()
        return 0

    if output_format == CLI_OUTPUT_HUMAN_READABLE:
        if progress is not None:
            progress.finish()
        assert artifact_path is not None
        summary_lines = report_summary_lines(
            report,
            output_path=artifact_path,
            current_threshold=policy.match_threshold,
            current_source=policy.match_threshold_source,
            verbose=response_verbosity == RESPONSE_VERBOSITY_VERBOSE,
            write_config=args.write_config,
            title_formatter=lambda value: _style(
                value, _RICH_BLUE_HEADING, enabled=_supports_color(sys.stdout)
            ),
            footer_formatter=lambda value: _style(
                value,
                _RICH_SUCCESS if args.write_config else _RICH_HINT,
                enabled=_supports_color(sys.stdout),
            ),
        )
        sys.stdout.write(_frame_human_output("\n".join(summary_lines)))
        return 0

    _emit_success(
        payload,
        output_format=output_format,
        command="dev optimize-threshold",
    )
    return 0


def _handle_upgrade_command(
    args: argparse.Namespace, config_path: Path, *, output_format: str
) -> int:
    """Check for and optionally apply a Recollectium package upgrade."""
    metadata = load_install_metadata()
    install_method = (
        detect_install_method(metadata)
        if args.install_method == "auto"
        else args.install_method
    )
    repo = args.repo or "AlfonsoDehesa/recollectium"
    try:
        target, target_source = select_tracking_target(
            metadata,
            version_selector=args.version,
            main=args.main,
            repo=repo,
        )
    except TargetSelectorError as exc:
        return _emit_cli_failure(
            status="validation_error",
            message="Upgrade target is invalid.",
            detail=str(exc),
            exit_code=2,
            command="upgrade",
            event="upgrade.invalid_target",
        )
    allow_main = args.allow_main or args.repo is not None

    source_root = find_source_checkout_root(Path(__file__).resolve())
    main_ref = None
    latest_release: ReleaseInfo | None
    try:
        latest_release = (
            fetch_latest_release(GitHubReleaseClient(), repo=target.repo)
            if target.kind == "latest_release"
            else None
        )
        if target.kind == "main":
            main_ref = resolve_main_ref(
                repo=target.repo,
                install_method=install_method,
                runner=SubprocessCommandRunner(),
                source_root=source_root,
                timeout_seconds=args.timeout,
                non_mutating=args.check or args.dry_run,
            )
    except ReleaseLookupError as exc:
        if exc.reason == "no_latest_release" and allow_main:
            latest_release = None
            try:
                main_ref = resolve_main_ref(
                    repo=target.repo,
                    install_method=install_method,
                    runner=SubprocessCommandRunner(),
                    source_root=source_root,
                    timeout_seconds=args.timeout,
                    non_mutating=args.check or args.dry_run,
                )
            except ReleaseLookupError as main_exc:
                return _emit_cli_failure(
                    status="network_error",
                    message="Could not resolve Recollectium main from GitHub.",
                    detail=str(main_exc),
                    reason=main_exc.reason,
                    hint="Check your network connection or retry later.",
                    exit_code=1,
                    command="upgrade",
                    event="upgrade.release_lookup_failed",
                )
        else:
            return _emit_cli_failure(
                status="network_error",
                message="Could not resolve Recollectium main from GitHub."
                if target.kind == "main" or exc.reason == "main_lookup_failed"
                else "Could not fetch latest Recollectium release from GitHub.",
                detail=str(exc),
                reason=exc.reason,
                hint="Check your network connection or retry later.",
                exit_code=1,
                command="upgrade",
                event="upgrade.release_lookup_failed",
            )

    plan = build_update_plan(
        current_version=__version__,
        latest_release=latest_release,
        install_method=install_method,
        metadata=metadata,
        force=args.force,
        dry_run=args.dry_run or args.check,
        allow_main=allow_main,
        repo=repo,
        source_root=source_root,
        target=target,
        target_source=target_source,
        main_ref=main_ref,
    )
    payload = plan_to_dict(plan)

    services_to_restart: list[str] = []
    cfg: RecollectiumConfig | None = None
    service_config_path = _core_config_path(
        str(config_path) if args.config_path is not None else None
    )
    should_check_services = not args.check and not (
        args.dry_run
        and (service_config_path is None or not service_config_path.exists())
    )
    if should_check_services:
        try:
            cfg = RecollectiumConfig(
                service_config_path,
                log_level=args.log_level,
            )
            running = check_running_service(cfg)
            if running is not None:
                services_to_restart.append(str(running["type"]))
        except (FileNotFoundError, ValidationError, ServiceError):
            cfg = None
    payload["services_to_restart"] = services_to_restart

    if plan.status in {"up_to_date", "dry_run", "update_available"} and (
        args.check or args.dry_run or plan.command is None
    ):
        _emit_success(payload, output_format=output_format, command="upgrade")
        return 0

    if plan.status == "unsupported_install_method":
        return _emit_cli_failure(
            status=plan.status,
            message="Could not determine how Recollectium was installed.",
            detail=plan.reason,
            hint="Run recollectium upgrade --install-method pip, pipx, uv_tool, or source if you know the install method.",
            exit_code=2,
            command="upgrade",
            event="upgrade.unsupported_install_method",
        )
    if plan.status == "network_error":
        return _emit_cli_failure(
            status=plan.status,
            message="Could not resolve Recollectium main from GitHub."
            if plan.reason == "main_lookup_failed" or plan.target_kind == "main"
            else "Could not fetch latest Recollectium release from GitHub.",
            detail=plan.reason,
            hint="Check your network connection or retry later.",
            exit_code=1,
            command="upgrade",
            event="upgrade.network_error",
        )
    if plan.status == "update_failed" and plan.command is None:
        return _emit_cli_failure(
            status="update_failed",
            message="Could not prepare the Recollectium package upgrade.",
            detail=plan.reason,
            hint="Run from a Recollectium source checkout or choose a different --install-method.",
            returncode=1,
            exit_code=1,
            command="upgrade",
            event="upgrade.prepare_failed",
        )

    service_stop_errors: list[dict[str, str]] = []
    if cfg is not None:
        for service_type in services_to_restart:
            try:
                stop_service(cfg)
            except ServiceError as exc:
                service_stop_errors.append({"type": service_type, "error": str(exc)})
    if service_stop_errors:
        payload["service_stop_errors"] = service_stop_errors
        return _emit_cli_failure(
            status="service_error",
            message="Could not stop running Recollectium services before upgrade.",
            detail="; ".join(error["error"] for error in service_stop_errors),
            service_stop_errors=service_stop_errors,
            exit_code=1,
            command="upgrade",
            event="upgrade.service_stop_failed",
        )

    with _human_upgrade_progress_context(output_format):
        result = apply_update(
            plan, runner=SubprocessCommandRunner(), timeout_seconds=args.timeout
        )
    payload["stdout"] = result.stdout
    payload["stderr"] = result.stderr
    service_restart_errors: list[dict[str, str]] = []
    if result.returncode != 0:
        payload["status"] = "update_failed"
        payload["returncode"] = result.returncode
        payload["message"] = "Recollectium package upgrade failed."
        payload["detail"] = result.stderr or result.stdout or plan.reason
        payload["hint"] = (
            "Review stderr, check that the package manager is installed, and retry after resolving the error."
        )
        if cfg is not None:
            for service_type in services_to_restart:
                try:
                    start_service(
                        cfg,
                        service_type,
                        db_path=args.db_path,
                        log_level=args.log_level,
                    )
                except (ServiceConflictError, ServiceError, ValueError) as exc:
                    service_restart_errors.append(
                        {"type": service_type, "error": str(exc)}
                    )
        if service_restart_errors:
            payload["service_restart_errors"] = service_restart_errors
        return _emit_cli_failure(
            status="update_failed",
            message="Recollectium package upgrade failed.",
            detail=result.stderr or result.stdout or plan.reason,
            hint="Review stderr, check that the package manager is installed, and retry after resolving the error.",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            service_restart_errors=service_restart_errors or None,
            exit_code=result.returncode if 1 <= result.returncode <= 125 else 1,
            command="upgrade",
            event="upgrade.update_failed",
        )

    metadata_warning: str | None = None
    try:
        metadata_path = write_install_metadata_update(plan)
        if metadata_path is not None:
            payload["metadata_path"] = str(metadata_path)
            payload["will_update_metadata"] = False
            payload["metadata_updated"] = True
    except OSError as exc:
        metadata_warning = str(exc)
        payload["metadata_updated"] = False
        payload["metadata_warning"] = metadata_warning

    payload["status"] = "updated"

    maintenance = _run_installed_embedding_maintenance(
        config_path=config_path,
        explicit=args.config_path is not None,
        db_path=args.db_path,
        log_level=args.log_level,
        timeout_seconds=args.timeout,
    )
    payload["embedding_maintenance_stdout"] = maintenance.stdout
    payload["embedding_maintenance_stderr"] = maintenance.stderr
    if maintenance.returncode != 0:
        payload["status"] = "embedding_maintenance_failed"
        payload["returncode"] = maintenance.returncode
        payload["message"] = (
            "Recollectium package upgraded, but embedding maintenance failed."
        )
        payload["detail"] = maintenance.stderr or maintenance.stdout
        if cfg is not None:
            for service_type in services_to_restart:
                try:
                    time.sleep(0.5)
                    start_service(
                        cfg,
                        service_type,
                        db_path=args.db_path,
                        log_level=args.log_level,
                    )
                except (ServiceConflictError, ServiceError, ValueError) as restart_exc:
                    service_restart_errors.append(
                        {"type": service_type, "error": str(restart_exc)}
                    )
        if service_restart_errors:
            payload["service_restart_errors"] = service_restart_errors
        return _emit_cli_failure(
            status="embedding_maintenance_failed",
            message="Recollectium package upgraded, but embedding maintenance failed.",
            detail=maintenance.stderr or maintenance.stdout,
            hint="Fix the embedding or database error, then run recollectium embedding-maintenance.",
            returncode=maintenance.returncode,
            stdout=maintenance.stdout,
            stderr=maintenance.stderr,
            service_restart_errors=service_restart_errors or None,
            exit_code=maintenance.returncode
            if 1 <= maintenance.returncode <= 125
            else 1,
            command="upgrade",
            event="upgrade.embedding_maintenance_failed",
        )
    try:
        payload["embedding_maintenance"] = json.loads(maintenance.stdout)
    except json.JSONDecodeError:
        payload["embedding_maintenance"] = {"raw_stdout": maintenance.stdout}

    if cfg is not None:
        for service_type in services_to_restart:
            try:
                time.sleep(0.5)
                start_service(
                    cfg, service_type, db_path=args.db_path, log_level=args.log_level
                )
            except (ServiceConflictError, ServiceError, ValueError) as exc:
                service_restart_errors.append({"type": service_type, "error": str(exc)})
    if service_restart_errors:
        payload["service_restart_errors"] = service_restart_errors
        return _emit_cli_failure(
            status="service_error",
            message="Recollectium upgraded, but services could not be restarted.",
            detail="; ".join(error["error"] for error in service_restart_errors),
            service_restart_errors=service_restart_errors,
            exit_code=1,
            command="upgrade",
            event="upgrade.service_restart_failed",
        )
    _emit_success(payload, output_format=output_format, command="upgrade")
    return 0


_COMPLETION_RC_FILES: dict[str, str] = {
    "bash": ".bashrc",
    "zsh": ".zshrc",
    "fish": ".config/fish/config.fish",
}
_COMPLETION_SHELLS = ("bash", "zsh", "fish", "powershell")
_COMPLETION_BLOCK_START = "# >>> recollectium completion >>>"
_COMPLETION_BLOCK_END = "# <<< recollectium completion <<<"
_COMPLETION_BLOCK_PATTERN = re.compile(
    rf"\n?{re.escape(_COMPLETION_BLOCK_START)}\n.*?\n"
    rf"{re.escape(_COMPLETION_BLOCK_END)}\n?",
    re.DOTALL,
)


def _detect_shell() -> str | None:
    shell_path = os.environ.get("SHELL", "")
    basename = Path(shell_path).name
    if basename in _COMPLETION_RC_FILES:
        return basename
    if sys.platform.startswith("win") or os.environ.get("PSModulePath"):
        return "powershell"
    return None


def _powershell_profile_path() -> Path:
    override = os.environ.get("RECOLLECTIUM_POWERSHELL_PROFILE")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        documents = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
        return documents / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    return Path.home() / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"


def _completion_target_path(shell: str) -> Path:
    if shell == "powershell":
        return _powershell_profile_path()
    rc_filename = _COMPLETION_RC_FILES.get(shell)
    if rc_filename is None:
        raise KeyError(shell)
    return Path.home() / rc_filename


def _powershell_completion_script() -> str:
    return r"""
Register-ArgumentCompleter -Native -CommandName recollectium -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $line = $commandAst.Extent.Text
    $json = & recollectium completion --complete-line $line --point $cursorPosition 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        return
    }

    try {
        $candidates = $json | ConvertFrom-Json
    }
    catch {
        return
    }

    foreach ($candidate in $candidates) {
        [System.Management.Automation.CompletionResult]::new(
            $candidate,
            $candidate,
            [System.Management.Automation.CompletionResultType]::ParameterValue,
            $candidate
        )
    }
}
""".strip()


def _completion_source(shell: str) -> str:
    if shell == "powershell":
        return _powershell_completion_script()
    return argcomplete.shellcode(["recollectium"], shell=shell)  # pyright: ignore[reportPrivateImportUsage]


def _powershell_completion_profile_block() -> str:
    return r"""
if (Get-Command recollectium -ErrorAction SilentlyContinue) {
    Invoke-Expression ((& recollectium completion --source powershell) -join [Environment]::NewLine)
}
""".strip()


def _completion_block(shell: str) -> str:
    if shell == "powershell":
        body = _powershell_completion_profile_block()
    else:
        body = f'eval "$(recollectium completion --source {shell})"'
    return f"{_COMPLETION_BLOCK_START}\n{body}\n{_COMPLETION_BLOCK_END}\n"


def _completion_marker(shell: str) -> str:
    return f"recollectium completion --source {shell}"


def _completion_candidates(line: str, point: int | None) -> list[str]:
    parser = _build_parser()
    prequote, prefix, _suffix, words, last_wordbreak_pos = argcomplete.split_line(  # pyright: ignore[reportPrivateImportUsage]
        line, point
    )
    finder = argcomplete.CompletionFinder(parser)  # pyright: ignore[reportPrivateImportUsage]
    raw = finder._get_completions(  # pyright: ignore[reportPrivateUsage]
        words,
        prefix,
        prequote,
        last_wordbreak_pos,
    )
    candidates: list[str] = []
    seen: set[str] = set()
    for item in raw:
        candidate = item.rstrip()
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    return candidates


def _handle_completion_command(args: argparse.Namespace, *, output_format: str) -> int:
    explicit_json = bool(getattr(args, "_explicit_json", False))
    if explicit_json and args.complete_line is not None:
        return _emit_cli_failure(
            status="selected_format_error",
            message="Completion raw output is not available with --json.",
            detail="Use completion --install with --json, or omit --json for raw completion source, instructions, or candidates.",
            hint="Run recollectium completion --source <shell> without --json for shell source output.",
            exit_code=2,
            command="completion",
            event="completion.selected_format_error",
        )
    if args.complete_line is not None:
        candidates = _completion_candidates(args.complete_line, args.point)
        print(json.dumps(candidates, sort_keys=True))
        return 0

    shell = args.shell
    if shell is None:
        shell = _detect_shell()
    if shell is None:
        return _emit_cli_failure(
            status="validation_error",
            message="Could not detect a supported shell.",
            hint="Pass the shell name explicitly, such as recollectium completion --install bash.",
            exit_code=2,
            command="completion",
            event="completion.unknown_shell",
        )

    if explicit_json and not args.install:
        return _emit_cli_failure(
            status="selected_format_error",
            message="Completion raw output is not available with --json.",
            detail="Use completion --install with --json, or omit --json for raw completion source, instructions, or candidates.",
            hint="Run recollectium completion --source <shell> without --json for shell source output.",
            exit_code=2,
            command="completion",
            event="completion.selected_format_error",
        )

    if args.source:
        output = _completion_source(shell)
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if args.install:
        try:
            rc_path = _completion_target_path(shell)
        except KeyError:
            return _emit_cli_failure(
                status="operation_failed",
                message="No shell rc file mapping is available.",
                detail=f"No rc file mapping for shell {shell}",
                exit_code=1,
                command="completion --install",
                event="completion.unknown_rc",
            )

        try:
            existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
        except OSError as exc:
            return _emit_cli_failure(
                status="operation_failed",
                message="Could not read rc file.",
                detail=str(exc),
                exit_code=1,
                command="completion --install",
                event="completion.rc_read_error",
                path=str(rc_path),
            )

        marker = _completion_marker(shell)
        if marker in existing and _COMPLETION_BLOCK_START not in existing:
            response_payload: dict[str, Any] = {
                "status": "already_installed",
                "rc_file": str(rc_path),
                "shell": shell,
                "updated": False,
            }
            if shell == "powershell":
                response_payload["profile"] = str(rc_path)
            _emit_success(
                response_payload, output_format=output_format, command="completion"
            )
            return 0

        block = _completion_block(shell)
        status = "installed"
        updated_content = existing
        block_found = _COMPLETION_BLOCK_PATTERN.search(existing) is not None
        if block_found:
            updated_content = _COMPLETION_BLOCK_PATTERN.sub("\n" + block, existing)
            status = "updated"
        else:
            updated_content = existing + (
                "\n" if existing and not existing.endswith("\n") else ""
            )
            updated_content += "\n" + block

        if marker in existing and block_found and block in existing:
            response_payload = {
                "status": "already_installed",
                "rc_file": str(rc_path),
                "shell": shell,
                "updated": False,
            }
            if shell == "powershell":
                response_payload["profile"] = str(rc_path)
            _emit_success(
                response_payload, output_format=output_format, command="completion"
            )
            return 0

        if not args.yes:
            if sys.stdin.isatty():
                _write_tty(
                    f"Will append or refresh the following managed block in {rc_path}:\n\n{block}\n"
                    "Proceed? Type 'yes' to confirm: "
                )
            response = sys.stdin.readline().strip()
            if response.lower() != "yes":
                return _emit_cli_failure(
                    status="operation_failed",
                    message="Completion installation cancelled.",
                    hint="Re-run with --yes to skip the confirmation prompt.",
                    exit_code=1,
                    command="completion --install",
                    event="completion.cancelled",
                )

        try:
            rc_path.parent.mkdir(parents=True, exist_ok=True)
            rc_path.write_text(updated_content, encoding="utf-8")
        except OSError as exc:
            return _emit_cli_failure(
                status="operation_failed",
                message=f"Could not write to {rc_path}.",
                detail=str(exc),
                exit_code=1,
                command="completion --install",
                event="completion.rc_write_error",
                path=str(rc_path),
            )

        response_payload: dict[str, Any] = {
            "status": status,
            "rc_file": str(rc_path),
            "shell": shell,
            "updated": status == "updated",
        }
        if shell == "powershell":
            response_payload["profile"] = str(rc_path)
        _emit_success(
            response_payload, output_format=output_format, command="completion"
        )
        return 0

    if shell == "powershell":
        instructions = [
            "Add this block to $PROFILE.CurrentUserCurrentHost for PowerShell tab completion:",
            "",
            "  Invoke-Expression ((& recollectium completion --source powershell) -join [Environment]::NewLine)",
            "",
            "Or run this to install it automatically:",
            "",
            "  recollectium completion --install powershell",
            "",
            "For all hosts, manually add the same source command to $PROFILE.CurrentUserAllHosts.",
        ]
    else:
        eval_line = f'eval "$(recollectium completion --source {shell})"'
        instructions = [
            f"Add this line to your shell rc file for {shell} tab completion:",
            "",
            f"  {eval_line}",
            "",
            "Or run this to install it automatically:",
            "",
            f"  recollectium completion --install {shell}",
            "",
            "After adding the line, restart your shell or run:",
            f"  source ~/{_COMPLETION_RC_FILES[shell]}",
        ]
    sys.stdout.write(_frame_human_output("\n".join(instructions)))
    return 0


def _load_uninstall_plan(config_path: Path, *, explicit: bool) -> _UninstallPlan:
    """Resolve uninstall targets without creating files or directories."""
    if explicit and not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    if config_path.exists():
        raw = load_config_file(config_path)
    else:
        raw = {}
    effective_config = _deep_merge(deepcopy(DEFAULTS), raw)
    _validate_config_value(effective_config)
    xdg_dirs = _resolve_xdg_dirs(effective_config.get("directories", {}))

    database_path = Path(effective_config["database"]["path"])
    if not database_path.is_absolute():
        database_path = xdg_dirs["data"] / database_path

    model_cache_path = resolve_model_cache_path(xdg_dirs["cache"])
    install_metadata_path = _resolve_install_metadata_path()
    return _UninstallPlan(
        config=_UninstallConfig(
            effective_config=effective_config,
            xdg_dirs=xdg_dirs,
            config_path=config_path,
            database_path=database_path,
        ),
        config_path=config_path,
        database_path=database_path,
        install_metadata_path=install_metadata_path,
        model_cache_path=model_cache_path,
    )


def _resolve_install_metadata_path() -> Path:
    """Return install metadata path, including bootstrap-script legacy paths."""
    default_path = Path(user_state_dir("recollectium")) / _INSTALL_METADATA_FILE
    candidates = [default_path]
    if sys.platform.startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                Path(local_app_data) / "recollectium" / _INSTALL_METADATA_FILE
            )
    else:
        candidates.append(
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
            / "recollectium"
            / _INSTALL_METADATA_FILE
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return default_path


def _load_install_metadata(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        try:
            detected = detect_install_method(load_install_metadata())
        except (AttributeError, OSError):
            detected = "unknown"
        return {"install_method": detected}
    if not isinstance(payload, dict):
        return {"install_method": "unknown"}
    return payload


def _detect_install_method_for_uninstall() -> str:
    try:
        return detect_install_method(load_install_metadata())
    except (AttributeError, OSError):
        return "unknown"


def _metadata_with_detected_install_method(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    raw_method = metadata.get("install_method") if metadata is not None else None
    if isinstance(raw_method, str) and raw_method != "unknown":
        return metadata

    enriched = dict(metadata or {})
    enriched["install_method"] = _detect_install_method_for_uninstall()
    return enriched


def _uninstall_package_instructions(
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    commands = {
        "bootstrap": "uv tool uninstall recollectium",
        "uv_tool": "uv tool uninstall recollectium",
        "pip": f"{sys.executable} -m pip uninstall -y recollectium",
        "pipx": "pipx uninstall recollectium",
        "source": "Remove the source checkout from your shell PATH or deactivate the editable install manually.",
        "unknown": "Install method unknown; inspect how Recollectium was installed and use the matching package manager manually.",
    }
    supported_commands = {"bootstrap", "uv_tool", "pip", "pipx"}
    install_method = None
    source_ref = None
    managed_path_edits: list[str] = []
    if metadata is not None:
        raw_method = metadata.get("install_method")
        raw_ref = metadata.get("source_ref")
        raw_path_edits = metadata.get("managed_path_edits")
        if isinstance(raw_method, str):
            install_method = raw_method if raw_method in commands else "unknown"
        if isinstance(raw_ref, str):
            source_ref = raw_ref
        if isinstance(raw_path_edits, list):
            managed_path_edits = [
                item for item in raw_path_edits if isinstance(item, str)
            ]

    recommended_key = install_method if install_method in commands else "unknown"
    recommended = commands[recommended_key]
    uninstall_payload: dict[str, Any]
    if recommended_key in supported_commands:
        uninstall_payload = {"status": "supported", "command": recommended}
    else:
        uninstall_payload = {
            "status": "unsupported",
            "hint": recommended,
        }
    return {
        "install_method": install_method or "unknown",
        "source_ref": source_ref,
        "recommended": recommended,
        "uninstall": uninstall_payload,
        "commands": commands,
        "managed_path_edits": managed_path_edits,
    }


def _safe_which(name: str) -> str | None:
    try:
        return shutil.which(name)
    except AttributeError:
        return None


def _resolve_executable(name: str) -> str:
    if not sys.platform.startswith("win"):
        return name

    resolved = _safe_which(name)
    if resolved is not None:
        return resolved

    suffix = ".exe" if not name.endswith(".exe") else ""
    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / name / f"{name}{suffix}")
    candidates.append(Path.home() / ".local" / "bin" / f"{name}{suffix}")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return name


def _package_uninstall_command(install_method: str) -> list[str] | None:
    commands = {
        "bootstrap": [_resolve_executable("uv"), "tool", "uninstall", "recollectium"],
        "uv_tool": [_resolve_executable("uv"), "tool", "uninstall", "recollectium"],
        "pip": [sys.executable, "-m", "pip", "uninstall", "-y", "recollectium"],
        "pipx": [_resolve_executable("pipx"), "uninstall", "recollectium"],
    }
    return commands.get(install_method)


def _schedule_windows_package_removal(command: list[str]) -> dict[str, Any]:
    powershell = _safe_which("pwsh") or _safe_which("powershell") or "powershell"
    command_json = json.dumps(command).replace("'", "''")
    script = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        f"$parentPid = {os.getpid()}; "
        f"$cmd = '{command_json}' | ConvertFrom-Json; "
        "if ($parentPid -gt 0) { Wait-Process -Id $parentPid -Timeout 30 }; "
        "& $cmd[0] @($cmd[1..($cmd.Count - 1)]) *> $null"
    )
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    helper = subprocess.Popen(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
    )
    return {
        "status": "scheduled",
        "command": " ".join(command),
        "argv": command,
        "helper_pid": helper.pid,
        "hint": "Package removal was handed off and will finish after this process exits.",
    }


def _remove_installed_package(
    metadata: dict[str, Any] | None,
    *,
    dry_run: bool,
    emit_progress: bool = False,
) -> dict[str, Any]:
    metadata = _metadata_with_detected_install_method(metadata)
    payload = _uninstall_package_instructions(metadata)
    install_method = payload["install_method"]
    command = _package_uninstall_command(install_method)

    if dry_run:
        dry_run_payload: dict[str, Any] = {"status": "dry_run"}
        if command is None:
            dry_run_payload["hint"] = payload["recommended"]
        else:
            dry_run_payload["command"] = payload["recommended"]
            dry_run_payload["argv"] = command
        payload["uninstall"] = dry_run_payload
        return payload

    if command is None:
        payload["uninstall"] = {
            "status": "unsupported",
            "hint": payload["recommended"],
        }
        return payload

    if emit_progress:
        sys.stderr.write("Uninstall in progress...\n")
        sys.stderr.flush()

    if sys.platform.startswith("win"):
        try:
            payload["uninstall"] = _schedule_windows_package_removal(command)
        except FileNotFoundError as exc:
            payload["uninstall"] = {
                "status": "failed",
                "command": payload["recommended"],
                "argv": command,
                "returncode": 127,
                "stderr": str(exc),
                "hint": "Install PowerShell or uninstall Recollectium with the matching package manager manually.",
            }
        return payload

    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        payload["uninstall"] = {
            "status": "failed",
            "command": payload["recommended"],
            "argv": command,
            "returncode": 127,
            "stderr": str(exc),
            "hint": "Install the matching package manager or uninstall Recollectium with it manually.",
        }
        return payload

    already_absent = (
        completed.returncode != 0
        and completed.stderr
        and "is not installed" in completed.stderr
    )
    uninstall_payload: dict[str, Any] = {
        "status": "removed"
        if completed.returncode == 0
        else "not_installed"
        if already_absent
        else "failed",
        "command": payload["recommended"],
        "argv": command,
        "returncode": completed.returncode,
    }
    if completed.stdout:
        uninstall_payload["stdout"] = completed.stdout
    if completed.stderr:
        uninstall_payload["stderr"] = completed.stderr
    if completed.returncode != 0:
        uninstall_payload["hint"] = (
            "Recollectium data and shell cleanup completed, but package removal failed. "
            "Run the listed command manually after fixing the package manager error."
        )
    payload["uninstall"] = uninstall_payload
    return payload


def _completion_rc_paths(metadata: dict[str, Any] | None) -> list[Path]:
    raw_paths: list[Path] = []
    if metadata is not None:
        raw_path_edits = metadata.get("managed_path_edits")
        if isinstance(raw_path_edits, list):
            for item in raw_path_edits:
                if not isinstance(item, str):
                    continue
                if "recollectium completion --source" not in item:
                    continue
                raw_paths.append(Path(item.split(": ", 1)[0]))

        raw_completion_edits = metadata.get("managed_completion_edits")
        if isinstance(raw_completion_edits, list):
            for item in raw_completion_edits:
                if not isinstance(item, dict):
                    continue
                raw_path = item.get("path")
                if isinstance(raw_path, str):
                    raw_paths.append(Path(raw_path))

    home = Path.home()
    raw_paths.extend(home / filename for filename in _COMPLETION_RC_FILES.values())
    raw_paths.append(_powershell_profile_path())

    paths: list[Path] = []
    seen: set[Path] = set()
    for path in raw_paths:
        resolved = path.expanduser().resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append(path)
    return paths


def _remove_completion_blocks(
    metadata: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for path in _completion_rc_paths(metadata):
        payload: dict[str, Any] = {"path": str(path), "removed": False}
        if not path.exists():
            payload["reason"] = "missing"
            results.append(payload)
            continue

        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            payload["reason"] = f"read_error: {exc}"
            results.append(payload)
            continue

        updated, count = _COMPLETION_BLOCK_PATTERN.subn("\n", existing)
        if count == 0:
            payload["reason"] = "not_found"
            results.append(payload)
            continue

        payload["blocks"] = count
        if dry_run:
            payload["reason"] = "dry_run"
            results.append(payload)
            continue

        try:
            path.write_text(updated, encoding="utf-8")
        except OSError as exc:
            payload["reason"] = f"write_error: {exc}"
            results.append(payload)
            continue

        payload["removed"] = True
        results.append(payload)

    return {
        "dry_run": dry_run,
        "targets": results,
        "removed": [item for item in results if item["removed"]],
        "skipped": [item for item in results if not item["removed"]],
    }


def _is_suspicious_purge_path(path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)
    home = Path.home().expanduser().resolve(strict=False)
    cwd = Path.cwd().resolve(strict=False)
    return resolved in {Path(resolved.anchor), home, cwd}


def _is_recollectium_owned_path(path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)
    parts = {part.lower() for part in resolved.parts}
    if "recollectium" in parts:
        return True
    if resolved.name in {"config.json", _INSTALL_METADATA_FILE}:
        return "recollectium" in {part.lower() for part in resolved.parent.parts}
    return False


def _path_payload(
    path: Path, *, deleted: bool, reason: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(path), "deleted": deleted}
    if reason is not None:
        payload["reason"] = reason
    return payload


def _delete_purge_target(
    path: Path,
    *,
    dry_run: bool,
    owned_paths: set[Path] | None = None,
) -> dict[str, Any]:
    if _is_suspicious_purge_path(path):
        return _path_payload(path, deleted=False, reason="suspicious_path")
    resolved = path.expanduser().resolve(strict=False)
    is_owned = (
        resolved in owned_paths
        if owned_paths is not None
        else _is_recollectium_owned_path(path)
    )
    if not is_owned:
        return _path_payload(path, deleted=False, reason="not_recollectium_owned")
    if not path.exists():
        return _path_payload(path, deleted=False, reason="missing")
    if dry_run:
        return _path_payload(path, deleted=False, reason="dry_run")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return _path_payload(path, deleted=True)


def _remove_model_cache(plan: _UninstallPlan, *, dry_run: bool) -> dict[str, Any]:
    owned_paths = {plan.model_cache_path.expanduser().resolve(strict=False)}
    result = _delete_purge_target(
        plan.model_cache_path, dry_run=dry_run, owned_paths=owned_paths
    )
    return {
        "dry_run": dry_run,
        "path": str(plan.model_cache_path),
        "targets": [result],
        "deleted": [result] if result["deleted"] else [],
        "skipped": [] if result["deleted"] else [result],
    }


def _purge_targets(plan: _UninstallPlan, *, dry_run: bool) -> dict[str, Any]:
    directory_overrides = plan.config.effective_config.get("directories", {})
    default_dirs = _resolve_xdg_dirs(DEFAULTS["directories"])
    default_config_dir = default_dirs["config"].expanduser().resolve(strict=False)
    owned_paths = {default_config_dir}
    resolved_config_path = plan.config_path.expanduser().resolve(strict=False)
    if resolved_config_path.parent == default_config_dir:
        owned_paths.add(resolved_config_path)
    for key in ("data", "cache", "logs", "runtime"):
        if directory_overrides.get(key) is None:
            owned_paths.add(default_dirs[key].expanduser().resolve(strict=False))
    if plan.config.xdg_dirs["data"].expanduser().resolve(strict=False) in owned_paths:
        owned_paths.add(plan.database_path.expanduser().resolve(strict=False))
    owned_paths.add(plan.install_metadata_path.expanduser().resolve(strict=False))
    resolved_cache_dir = (
        plan.config.xdg_dirs["cache"].expanduser().resolve(strict=False)
    )
    include_model_cache_target = resolved_cache_dir not in owned_paths
    if include_model_cache_target:
        owned_paths.add(plan.model_cache_path.expanduser().resolve(strict=False))

    raw_targets = [
        plan.config_path,
        plan.config_path.parent,
        plan.config.xdg_dirs["data"],
        plan.config.xdg_dirs["cache"],
        plan.config.xdg_dirs["logs"],
        plan.config.xdg_dirs["runtime"],
        plan.install_metadata_path,
    ]
    if include_model_cache_target:
        raw_targets.append(plan.model_cache_path)
    targets: list[Path] = []
    seen: set[Path] = set()
    for target in raw_targets:
        resolved = target.expanduser().resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        targets.append(target)
    targets.sort(
        key=lambda target: len(target.expanduser().resolve(strict=False).parts),
        reverse=True,
    )

    results = [
        _delete_purge_target(target, dry_run=dry_run, owned_paths=owned_paths)
        for target in targets
    ]
    return {
        "dry_run": dry_run,
        "targets": results,
        "deleted": [item for item in results if item["deleted"]],
        "skipped": [item for item in results if not item["deleted"]],
    }


def _clear_managed_logging_handlers() -> None:
    """Remove Recollectium-managed log handlers before purging log files."""
    for logger_name in ("recollectium", "uvicorn", "sqlite3", "httpx"):
        logger = logging.getLogger(logger_name)
        for handler in list(logger.handlers):
            if getattr(handler, "_recollectium_managed", False):
                logger.removeHandler(handler)
                handler.close()


def _handle_uninstall_command(
    args: argparse.Namespace,
    config_path: Path,
    *,
    explicit: bool,
    output_format: str,
) -> int:
    """Print uninstall instructions and optionally purge Recollectium-owned data."""
    if args.yes_delete_all_recollectium_data and not args.purge:
        return _emit_cli_failure(
            status="uninstall_invalid_flags",
            message="--yes-delete-all-recollectium-data requires --purge.",
            hint="Add --purge or remove --yes-delete-all-recollectium-data.",
            exit_code=2,
            command="uninstall",
            event="uninstall.invalid_flags",
        )

    plan = _load_uninstall_plan(config_path, explicit=explicit)
    metadata = _load_install_metadata(plan.install_metadata_path)
    compact_human_output = (
        output_format == CLI_OUTPUT_HUMAN_READABLE
        and _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_COMPACT
    )
    verbose_human_output = (
        output_format == CLI_OUTPUT_HUMAN_READABLE
        and _CURRENT_RESPONSE_VERBOSITY != RESPONSE_VERBOSITY_COMPACT
    )
    purge_preview: dict[str, Any] | None = None
    if args.purge and not args.dry_run:
        purge_preview = _purge_targets(plan, dry_run=True)
        interactive = sys.stdin.isatty()
        if not args.yes_delete_all_recollectium_data:
            if interactive:
                _write_tty(
                    "Type 'delete all recollectium data' to permanently delete Recollectium data: "
                )
            response = sys.stdin.readline().rstrip("\n")
            if response != _PURGE_CONFIRMATION:
                return _emit_cli_failure(
                    status="purge_cancelled",
                    message="purge cancelled",
                    hint="Type the exact confirmation phrase to permanently delete Recollectium data.",
                    exit_code=1,
                    command="uninstall --purge",
                    event="uninstall.purge_cancelled",
                )

    service_payload: dict[str, Any]
    if args.dry_run:
        service_payload = {"status": "dry_run", "note": "service would be stopped"}
    else:
        stopped_pid = stop_service(plan.config)
        service_payload = {"status": "no_service_running"}
        if stopped_pid is not None:
            service_payload = {"status": "stopped", "pid": stopped_pid}

    data_payload: dict[str, Any] = {
        "preserved": not args.purge,
        "memories_preserved": not args.purge,
        "config_preserved": not args.purge,
        "derived_artifacts_removed": not args.dry_run,
        "paths": {
            "config": str(plan.config_path),
            "data": str(plan.config.xdg_dirs["data"]),
            "cache": str(plan.config.xdg_dirs["cache"]),
            "logs": str(plan.config.xdg_dirs["logs"]),
            "runtime": str(plan.config.xdg_dirs["runtime"]),
            "database": str(plan.database_path),
            "model_cache": str(plan.model_cache_path),
        },
    }
    completion_payload = _remove_completion_blocks(metadata, dry_run=args.dry_run)
    model_cache_cleanup_failed = False
    if args.purge:
        data_payload["model_cache"] = {
            "path": str(plan.model_cache_path),
            "handled_by": "purge",
        }

    if args.purge:
        if args.dry_run:
            data_payload["purge"] = _purge_targets(plan, dry_run=True)
        else:
            if verbose_human_output:
                sys.stderr.write(
                    "The following Recollectium-owned paths will be permanently deleted:\n"
                )
                assert purge_preview is not None
                for target in purge_preview["targets"]:
                    if target.get("reason") != "dry_run":
                        continue
                    sys.stderr.write(f"  {target['path']}\n")
                sys.stderr.write("\n")

            logging.shutdown()
            _clear_managed_logging_handlers()
            data_payload["purge"] = _purge_targets(plan, dry_run=False)

    package_payload = _remove_installed_package(
        metadata,
        dry_run=args.dry_run,
        emit_progress=compact_human_output,
    )
    package_status = package_payload["uninstall"]["status"]
    if not args.purge:
        try:
            data_payload["model_cache"] = _remove_model_cache(
                plan, dry_run=args.dry_run
            )
        except OSError as exc:
            model_cache_cleanup_failed = True
            skipped_target = {
                "path": str(plan.model_cache_path),
                "deleted": False,
                "reason": f"cleanup_error: {exc}",
            }
            data_payload["model_cache"] = {
                "dry_run": args.dry_run,
                "path": str(plan.model_cache_path),
                "status": "failed",
                "targets": [skipped_target],
                "deleted": [],
                "skipped": [skipped_target],
            }
            data_payload["derived_artifacts_removed"] = False
            _log.info(
                "Uninstall model cache cleanup failed",
                extra={
                    "event": "uninstall.model_cache_cleanup_failed",
                    "context": {"path": str(plan.model_cache_path)},
                },
            )
    result = {
        "status": (
            "uninstalled_with_warnings"
            if model_cache_cleanup_failed
            and package_status in {"removed", "scheduled", "not_installed"}
            else "dry_run_with_warnings"
            if model_cache_cleanup_failed and package_status == "dry_run"
            else "model_cache_cleanup_failed"
            if model_cache_cleanup_failed
            else "uninstalled"
            if package_status in {"removed", "scheduled", "not_installed"}
            else "dry_run"
            if package_status == "dry_run"
            else "package_removal_unsupported"
            if package_status == "unsupported"
            else "package_removal_failed"
        ),
        "package": package_payload,
        "service": service_payload,
        "shell_completion": completion_payload,
        "data": data_payload,
    }
    if not args.purge:
        _log.info(
            "Uninstall completed",
            extra={"event": "uninstall.completed"},
        )
    _emit_success(result, output_format=output_format, command="uninstall")
    return 1 if package_status == "failed" or model_cache_cleanup_failed else 0


def _handle_workspace_command(
    args: argparse.Namespace,
    *,
    core: RecollectiumCore,
    output_format: str,
) -> int:
    """Handle the `recollectium workspace` subcommands."""
    if args.workspace_action == "list":
        uids = core.list_workspaces(
            include_archived=getattr(args, "include_archived", False),
            include_aliases=getattr(args, "include_aliases", False),
            include_alias_records=(
                getattr(args, "include_aliases", False)
                and _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_VERBOSE
            ),
        )
        _emit_success(uids, output_format=output_format, command="workspace list")
        return 0

    if args.workspace_action == "resolve":
        try:
            result = core.resolve_workspace(args.uid)
            _emit_success(
                result, output_format=output_format, command="workspace resolve"
            )
            return 0
        except ValidationError as exc:
            return _validation_error(
                exc, command="workspace resolve", event="workspace.invalid"
            )

    if args.workspace_action == "alias":
        try:
            if args.alias_action == "add":
                result = core.add_workspace_alias(
                    canonical_uid=args.canonical_uid,
                    alias_uid=args.alias_uid,
                    migrate_existing=getattr(args, "migrate_existing", False),
                )
                command = "workspace alias add"
            elif args.alias_action == "list":
                result = core.list_workspace_aliases(
                    canonical_uid=getattr(args, "workspace", None)
                )
                command = "workspace alias list"
            elif args.alias_action == "remove":
                result = core.remove_workspace_alias(args.alias_uid)
                command = "workspace alias remove"
            else:  # pragma: no cover — parser enforces valid actions
                return 1
            _emit_success(result, output_format=output_format, command=command)
            return 0
        except ValidationError as exc:
            return _workspace_validation_error(exc, command="workspace alias")
        except NotFoundError as exc:
            return _not_found_error(exc, command="workspace alias")

    if args.workspace_action == "rename":
        try:
            result = core.rename_workspace(
                old_uid=args.old_uid,
                new_uid=args.new_uid,
            )
            _emit_success(
                result, output_format=output_format, command="workspace rename"
            )
            return 0
        except ValidationError as exc:
            return _workspace_validation_error(exc, command="workspace rename")
        except NotFoundError as exc:
            return _not_found_error(exc, command="workspace rename")

    return 1  # pragma: no cover — parser enforces valid actions


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = _HumanFramedArgumentParser(
        prog="recollectium",
        description=(
            "Recollectium Core local memory CLI. Human-readable output is the "
            "default. Use --json for structured JSON. Recollectium-controlled "
            "failures follow the selected output format."
        ),
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        help=(
            "Path to Recollectium JSON config file. Defaults to the XDG config "
            "location and auto-creates there on first use. Explicit missing "
            "paths fail except config creation commands."
        ),
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        help=(
            "SQLite database path. Overrides the database.path config value. "
            "Defaults to ~/.local/share/recollectium/recollectium.db."
        ),
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["debug", "info", "warning", "error"],
        help=(
            "Override the logging.level config value for this invocation. "
            "Does not modify the config file."
        ),
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output for this invocation, overriding cli_output.",
    )
    output_group.add_argument(
        "--human-readable",
        action="store_true",
        help="Print human-readable output for this invocation, overriding cli_output.",
    )
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "--compact",
        action="store_true",
        help="Print compact response payloads for this invocation, overriding response_verbosity.",
    )
    verbosity_group.add_argument(
        "--verbose",
        action="store_true",
        help="Print full response payloads for this invocation, overriding response_verbosity.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print installed Recollectium version and exit.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="COMMAND",
    )

    subparsers.add_parser(
        "init",
        help="initialize Recollectium config, database, and model cache",
        description=(
            "Create the config file and XDG directories, run database migrations, "
            "and download the configured built-in FastEmbed model so Recollectium is ready to use. "
            "The first run may take 30-120 seconds depending on the selected model."
        ),
    )
    init_parser = subparsers.choices["init"]
    init_parser.add_argument(
        "--db",
        dest="db_path",
        help=(
            "SQLite database path for initialization. Also available as the global "
            "--db flag before the command."
        ),
    )

    # -- config ----------------------------------------------------------
    config_parser = subparsers.add_parser(
        "config",
        help="inspect, validate, and edit Recollectium configuration",
        description=(
            "Inspect, validate, and edit the Recollectium JSON config file. "
            "Without arguments, prints the effective configuration (defaults "
            "merged with explicit overrides) as human-readable text by default, "
            "or as JSON when requested."
        ),
    )
    config_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the effective config without creating a file.",
    )
    config_parser.add_argument(
        "--path",
        action="store_true",
        help="Print the resolved config file path without creating a file.",
    )
    config_parser.add_argument(
        "--defaults",
        action="store_true",
        help=(
            "Print built-in default values without creating a file. Uses the selected output format."
        ),
    )

    config_sub = config_parser.add_subparsers(
        dest="config_action",
        title="config actions",
        metavar="ACTION",
    )

    get_parser = config_sub.add_parser(
        "get",
        help="get a single config value by dot-notation key",
        description="Print the effective config value for a dot-notation key.",
    )
    get_parser.add_argument(
        "key",
        help='Dot-notation config key, e.g. "service.port".',
    ).completer = ChoicesCompleter(_COMPLETABLE_CONFIG_KEYS)  # pyright: ignore[reportAttributeAccessIssue]

    set_parser = config_sub.add_parser(
        "set",
        help="set a config value by dot-notation key",
        description=(
            "Write a value to the config file, auto-creating it if needed. "
            "embedding.model supports: "
            f"{_SUPPORTED_EMBEDDING_MODELS_HELP}."
        ),
    )
    set_parser.add_argument(
        "key",
        help='Dot-notation config key, e.g. "service.port".',
    ).completer = ChoicesCompleter(_COMPLETABLE_CONFIG_KEYS)  # pyright: ignore[reportAttributeAccessIssue]
    set_parser.add_argument(
        "value",
        help="Value to write. Parsed as JSON when possible; stored as string otherwise.",
    )

    unset_parser = config_sub.add_parser(
        "unset",
        help="remove a key from the config file",
        description="Remove a key from the config file so the built-in default applies.",
    )
    unset_parser.add_argument(
        "key",
        help='Dot-notation config key, e.g. "service.port".',
    ).completer = ChoicesCompleter(_COMPLETABLE_CONFIG_KEYS)  # pyright: ignore[reportAttributeAccessIssue]

    init_parser = config_sub.add_parser(
        "init",
        help="create or overwrite the starter config file",
        description="Create a starter config file with all built-in default values.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the config file if it already exists.",
    )

    config_sub.add_parser(
        "doctor",
        help="run config and filesystem checks",
        description=(
            "Validate config and check that resolved data, cache, logs, runtime, "
            "and database parent directories exist, are directories, and are writable."
        ),
    )

    config_sub.add_parser(
        "edit",
        help="open the config file in $EDITOR",
        description=(
            "Open the active config file in $EDITOR. Creates the config file with "
            "defaults first if it does not exist."
        ),
    )

    config_sub.add_parser(
        "reset",
        help="reset the config file to defaults",
        description=(
            "Replace the config file with a fresh copy of built-in defaults. "
            "Creates the file if it does not exist."
        ),
    )

    # -- add --------------------------------------------------------------
    add_parser = subparsers.add_parser(
        "add",
        help="add a user or workspace memory",
        description=(
            "Add a memory to the local Recollectium database. User memories must not "
            "include --workspace-uid. Workspace memories require --workspace-uid."
        ),
    )
    add_parser.add_argument(
        "--space",
        required=True,
        help="Memory space: 'user' for global user memory or 'workspace' for workspace memory.",
    )
    add_parser.add_argument(
        "--type",
        required=True,
        help="Canonical memory type bucket, such as fact, preference, note, decision, or task_context.",
    ).completer = _memory_type_completer  # pyright: ignore[reportAttributeAccessIssue]
    add_parser.add_argument(
        "--content",
        required=True,
        help="Memory text to store and embed for search.",
    )
    add_parser.add_argument(
        "--workspace-uid",
        help="Stable workspace UID. Required when --space workspace; forbidden when --space user.",
    )
    add_parser.add_argument(
        "--metadata",
        help="Optional JSON object metadata, either inline JSON or @path/to/file.json.",
    )
    add_parser.add_argument(
        "--source",
        help="Optional source label describing where the memory came from.",
    )
    add_parser.add_argument(
        "--confidence",
        type=float,
        help="Optional confidence score from 0.0 to 1.0.",
    )
    add_parser.add_argument(
        "--sensitivity",
        help="Optional sensitivity label for privacy-aware handling later.",
    )

    # -- search-user ------------------------------------------------------
    search_user_parser = subparsers.add_parser(
        "search-user",
        help="search global user memories",
        description=(
            "Search active user memories semantically and return ranked results in the selected output format. "
            "Searches default to all user buckets unless --type narrows the scope."
        ),
    )
    search_user_parser.add_argument(
        "query", help="Search text to match against user memories."
    )
    search_user_parser.add_argument(
        "--type",
        help="Optional canonical type bucket to narrow user search results.",
    ).completer = ChoicesCompleter(USER_MEMORY_TYPES)  # pyright: ignore[reportAttributeAccessIssue]
    search_user_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of ranked results to return. Must be positive. Defaults to 20.",
    )
    search_user_parser.add_argument(
        "--protected-minimum",
        type=_parse_non_negative_int,
        default=UNSET,
        help=(
            "Keep this many top-ranked results before threshold filtering. "
            "Must be an integer >= 0. Omit to use the configured protected minimum."
        ),
    )
    search_user_parser.add_argument(
        "--match-threshold",
        type=_parse_match_threshold,
        default=UNSET,
        help=(
            "Threshold for retaining results after the protected minimum. "
            "Accepts model_recommended_default, none, or a number from 0.0 to 1.0. "
            "Omit to use the configured threshold."
        ),
    )
    search_user_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived memories in search candidates.",
    )

    # -- search-workspace -------------------------------------------------
    search_workspace_parser = subparsers.add_parser(
        "search-workspace",
        help="search memories for one workspace UID",
        description=(
            "Search active memories for a specific workspace UID and return ranked results in the selected output format. Searches default to all workspace buckets unless --type narrows the scope."
        ),
    )
    search_workspace_parser.add_argument(
        "query", help="Search text to match against workspace memories."
    )
    search_workspace_parser.add_argument(
        "--type",
        help="Optional canonical type bucket to narrow workspace search results.",
    ).completer = ChoicesCompleter(WORKSPACE_MEMORY_TYPES)  # pyright: ignore[reportAttributeAccessIssue]
    search_workspace_parser.add_argument(
        "--workspace-uid",
        required=True,
        help="Stable workspace UID whose memories should be searched.",
    )
    search_workspace_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of ranked results to return. Must be positive. Defaults to 20.",
    )
    search_workspace_parser.add_argument(
        "--protected-minimum",
        type=_parse_non_negative_int,
        default=UNSET,
        help=(
            "Keep this many top-ranked results before threshold filtering. "
            "Must be an integer >= 0. Omit to use the configured protected minimum."
        ),
    )
    search_workspace_parser.add_argument(
        "--match-threshold",
        type=_parse_match_threshold,
        default=UNSET,
        help=(
            "Threshold for retaining results after the protected minimum. "
            "Accepts model_recommended_default, none, or a number from 0.0 to 1.0. "
            "Omit to use the configured threshold."
        ),
    )
    search_workspace_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived memories in search candidates.",
    )

    # -- list --------------------------------------------------------------
    list_parser = subparsers.add_parser(
        "list",
        help="list memories with optional filters across all buckets by default",
        description=(
            "List memories in the selected output format, optionally filtered by space, type, status, "
            "workspace UID, or result limit. Archived memories are hidden unless "
            "requested."
        ),
    )
    list_parser.add_argument(
        "--space",
        choices=(SPACE_USER, SPACE_WORKSPACE),
        help="Filter by memory space: user or workspace.",
    )
    list_parser.add_argument(
        "--type", help="Filter by canonical memory type bucket."
    ).completer = ChoicesCompleter(ALL_MEMORY_TYPES)  # pyright: ignore[reportAttributeAccessIssue]
    list_parser.add_argument(
        "--status",
        choices=(STATUS_ACTIVE, STATUS_ARCHIVED),
        help="Filter by memory status: active or archived.",
    )
    list_parser.add_argument(
        "--workspace-uid", help="Filter to memories for one stable workspace UID."
    )
    list_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived memories in list results.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of memories to return. Must be positive.",
    )

    # -- get ---------------------------------------------------------------
    get_parser = subparsers.add_parser(
        "get",
        help="retrieve one memory by ID",
        description="Retrieve one memory by its ID and print it in the selected output format.",
    )
    get_parser.add_argument("memory_id", help="Memory ID to retrieve.")

    # -- update ------------------------------------------------------------
    update_parser = subparsers.add_parser(
        "update",
        help="update editable memory fields",
        description=(
            "Update one or more editable fields on a memory. "
            "Updating --content also regenerates that memory's embedding."
        ),
    )
    update_parser.add_argument(
        "memory_id",
        nargs="?",
        help="Memory ID to update. Use `recollectium upgrade` for package upgrades.",
    )
    update_parser.add_argument(
        "--type", help="Replacement canonical memory type bucket."
    ).completer = _memory_type_completer  # pyright: ignore[reportAttributeAccessIssue]
    update_parser.add_argument(
        "--content", help="Replacement memory text. Regenerates the stored embedding."
    )
    update_parser.add_argument(
        "--metadata",
        help="Replacement JSON object metadata, either inline JSON or @path/to/file.json.",
    )
    update_parser.add_argument(
        "--source",
        help="Replacement source label describing where the memory came from.",
    )
    update_parser.add_argument(
        "--confidence",
        type=float,
        help="Replacement confidence score from 0.0 to 1.0.",
    )
    update_parser.add_argument(
        "--sensitivity",
        help="Replacement sensitivity label for privacy-aware handling later.",
    )

    # -- upgrade -----------------------------------------------------------
    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="upgrade the installed Recollectium package",
        description=(
            "Upgrade the Recollectium package. Without --version or --main, follows "
            "the install metadata tracking target; if none is recorded, tracks the "
            "latest release. Only this explicit command mutates the installed package."
        ),
    )
    upgrade_parser.add_argument(
        "--check",
        action="store_true",
        help="Check for an available upgrade and print the plan without applying it.",
    )
    upgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the upgrade command that would run without applying it.",
    )
    upgrade_parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall the already-selected target when a metadata-driven upgrade appears current.",
    )
    target_group = upgrade_parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--version",
        metavar="VERSION",
        help=(
            "Target and reinstall from a release without --force. Use 'latest' to track "
            "the latest GitHub release, or a release version/tag such as '1.0.2' or 'v1.0.2'."
        ),
    )
    target_group.add_argument(
        "--target-version",
        dest="version",
        metavar="VERSION",
        help=argparse.SUPPRESS,
    )
    target_group.add_argument(
        "--main",
        action="store_true",
        help="Track and reinstall from the main branch without --force. Mutually exclusive with --version.",
    )
    upgrade_parser.add_argument(
        "--install-method",
        choices=["auto", "bootstrap", "pip", "pipx", "uv_tool", "source"],
        default="auto",
        help="Override install-method detection. Defaults to auto.",
    )
    upgrade_parser.add_argument(
        "--repo",
        help=(
            "Development/test override for GitHub OWNER/REPO release lookup and "
            "bootstrap URLs. Normal users should not need this."
        ),
    )
    upgrade_parser.add_argument(
        "--allow-main",
        action="store_true",
        help="Permit main-branch fallback for bootstrap/source upgrades if no release exists.",
    )
    upgrade_parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Package-manager command timeout in seconds. Defaults to 600.",
    )

    # -- uninstall ---------------------------------------------------------
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="uninstall Recollectium while preserving memories by default",
        description=(
            "Stop managed services, remove managed shell completions, delete the "
            "derived local model cache, and uninstall the installed Recollectium package "
            "while preserving memories by default. Use --purge to also delete "
            "Recollectium-owned config, data, cache, logs, and runtime paths after "
            "explicit confirmation. Source and unknown installs report a manual "
            "package-removal hint because safe self-removal is not supported."
        ),
    )
    uninstall_parser.add_argument(
        "--purge",
        action="store_true",
        help=(
            "Permanently delete your memories and all Recollectium-owned config, data, "
            "cache, logs, and runtime paths. Without this flag, memories and config are "
            "preserved but derived model artifacts are removed."
        ),
    )
    uninstall_parser.add_argument(
        "--yes-delete-all-recollectium-data",
        action="store_true",
        help=(
            "Confirm destructive data deletion for non-interactive purge. Requires --purge."
        ),
    )
    uninstall_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show planned actions without deleting files, stopping services, removing "
            "completion blocks, removing data, or uninstalling the package. Use with "
            "--purge to preview full deletion paths."
        ),
    )

    # -- archive -----------------------------------------------------------
    archive_parser = subparsers.add_parser(
        "archive",
        help="archive one memory by ID",
        description=(
            "Archive a memory by ID. Archived memories are hidden from default list "
            "and search results but are not hard-deleted."
        ),
    )
    archive_parser.add_argument("memory_id", help="Memory ID to archive.")

    # -- service ------------------------------------------------------------
    service_parser = subparsers.add_parser(
        "service",
        help="manage Recollectium service lifecycle",
        description="Start, stop, check status, and restart Recollectium services.",
    )
    service_sub = service_parser.add_subparsers(
        dest="service_action",
        required=True,
        title="service actions",
        metavar="ACTION",
    )

    # service start
    start_parser = service_sub.add_parser(
        "start",
        help="start a Recollectium service",
        description=(
            "Start a managed Recollectium API or MCP HTTP service in the background. "
            "The service writes owned PID and discovery state files, and API services "
            "use the configured host and port unless overridden elsewhere."
        ),
    )
    start_parser.add_argument(
        "type",
        choices=["api", "mcp"],
        help="Service type to start: api (REST API) or mcp (MCP HTTP server)",
    )

    # service stop
    service_sub.add_parser(
        "stop",
        help="stop the running Recollectium service",
        description=(
            "Stop the managed Recollectium service if it is running. The command "
            "cleans up stale Recollectium-owned PID and discovery files when applicable."
        ),
    )

    # service status
    service_sub.add_parser(
        "status",
        help="show running service details",
        description=(
            "Report managed service state as running, stale, or not running. Output uses the selected output format."
        ),
    )

    # service discover
    service_sub.add_parser(
        "discover",
        help="print machine-readable connection details for the running service",
        description=(
            "Print connection details for local adapters in the selected output format. "
            "The command reports the running endpoint, version and capability URLs, "
            "PID path, and discovery file path without creating a config file."
        ),
    )

    # service restart
    restart_parser = service_sub.add_parser(
        "restart",
        help="restart the running service",
        description=(
            "Restart the existing managed Recollectium service, preserving its service type. "
            "If no running service exists, --type selects the API or MCP service to start."
        ),
    )
    restart_parser.add_argument(
        "--type",
        choices=["api", "mcp"],
        help=(
            "Service type to restart (required if no running service is found "
            "or only a stale PID file exists)"
        ),
    )

    # -- db-status ---------------------------------------------------------
    subparsers.add_parser(
        "db-status",
        help="show database schema migration status",
        description=(
            "Show SQLite migration status in the selected output format for the selected database path. "
            "This command initializes the database if needed and reports current "
            "and pending schema versions."
        ),
    )

    # -- dev ---------------------------------------------------------------
    dev_parser = subparsers.add_parser(
        "dev",
        help="run development database, eval, and debug server tools",
        description=(
            "Run Recollectium development tools: switch between the normal user "
            "database and a pre-seeded development database, reset the development "
            "database to its canonical fixture, run retrieval evaluation against the "
            "seeded development database only, optimize retrieval thresholds, or run "
            "the local-first HTTP API server in the foreground for development and "
            "debugging. The regular database is not touched by seeded database actions. "
            "Switch and reset actions refuse to run while a managed service is already "
            "running."
        ),
    )
    dev_subparsers = dev_parser.add_subparsers(
        dest="dev_action",
        required=True,
        title="dev actions",
        metavar="ACTION",
    )
    dev_serve_parser = dev_subparsers.add_parser(
        "serve",
        help="run the foreground HTTP API server for development/debugging",
        description=(
            "Start a blocking local-first development/debug HTTP JSON service for "
            "Recollectium Core. By default it binds to localhost (127.0.0.1), "
            "exposes the /v1 service API, and keeps running in the foreground "
            "until interrupted. Host and port can be set via config file or CLI "
            "flags. CLI flags override config. Non-local binds can expose "
            "unauthenticated memory operations unless protected by private networking "
            "and external access controls. For a managed background service, use "
            "recollectium service start api."
        ),
    )
    dev_serve_parser.add_argument(
        "--host",
        default=None,
        help=(
            "Host interface to bind. Overrides service.host from config. "
            "Defaults to 127.0.0.1. Non-local binds should be protected by "
            "private networking and external access controls."
        ),
    )
    dev_serve_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "TCP port for the local /v1 service API. Overrides service.port from "
            "config. Defaults to 8765."
        ),
    )
    dev_true_parser = dev_subparsers.add_parser(
        "true",
        help="route future activity to the seeded dev database",
        description=(
            "Enable the seeded development database for future Recollectium activity "
            "and initialize or refresh the seeded fixture if needed."
        ),
    )
    dev_true_parser.set_defaults(state="true")
    dev_false_parser = dev_subparsers.add_parser(
        "false",
        help="return future activity to the normal database",
        description="Disable the seeded development database and return to the normal configured database.",
    )
    dev_false_parser.set_defaults(state="false")
    dev_reset_parser = dev_subparsers.add_parser(
        "reset",
        help="recreate the seeded dev database fixture",
        description=(
            "Recreate the seeded development database fixture with 100 user memories "
            "across 10 topics and 90 workspace memories across 3 workspaces."
        ),
    )
    dev_reset_parser.set_defaults(state="reset")
    dev_eval_parser = dev_subparsers.add_parser(
        "eval",
        help="run seeded development retrieval regression metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Initialize or refresh the seeded development database if needed, then run\n"
            "Exact MRR, Semantic MRR, Thematic Weighted Precision@10, Thematic Weighted\n"
            "Recall@10, and Ranked-set NDCG@5 against that database only.\n\n"
            "This seeded development benchmark helps developers judge a model's expected\n"
            "retrieval performance on Recollectium-style memory tasks. No combined score\n"
            "is reported.\n\n"
            "Metrics:\n"
            "  Exact MRR: Checks whether known exact-memory queries rank the intended\n"
            "    seeded memory first or near the top.\n"
            "  Semantic MRR: Checks whether paraphrased queries retrieve the intended\n"
            "    seeded memory near the top.\n"
            "  Thematic Weighted Precision@10: Checks how much of the top 10 is relevant\n"
            "    to the requested theme, weighted by fixture relevance grades.\n"
            "  Thematic Weighted Recall@10: Checks how much of the theme's expected\n"
            "    relevant set appears in the top 10, weighted by fixture relevance grades.\n"
            "  Ranked-set NDCG@5: Checks whether graded expected results appear in the\n"
            "    right order near the top 5."
        ),
    )
    dev_eval_parser.set_defaults(state="eval")
    dev_eval_parser.set_defaults(dev_action="eval")
    dev_optimize_parser = dev_subparsers.add_parser(
        "optimize-threshold",
        help="optimize a retrieval match threshold from seeded thematic labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Load the seeded development database if needed, evaluate the full labeled "
            "candidate pool for each seeded thematic query, and recommend a match threshold.\n\n"
            "This command is advisory by default and only writes config when explicitly "
            "asked to do so with --write-config. In human-readable output, compact mode "
            "shows the recommendation and metrics; --verbose also shows the threshold "
            "sweep range.\n\n"
            "Metrics:\n"
            "  Weighted precision: Checks how much of the returned set is useful, with "
            "direct matches and adjacent matches counted more than confusers or unrelated "
            "results.\n"
            "  Weighted recall: Checks how much of the total useful labeled set the returned "
            "set captures, using the same relevance weights.\n"
            "  Weighted F-beta: Combines weighted precision and weighted recall so the sweep "
            "can rank thresholds by the chosen precision-recall balance.\n"
            "  Exposure: Checks the share of the returned set that is confuser or unrelated, "
            "where lower is better. Confuser exposure and unrelated exposure are reported "
            "separately.\n"
            "  Average returned count: Checks how many memories are returned on average per "
            "seeded query at the threshold."
        ),
    )
    dev_optimize_parser.add_argument(
        "--start",
        type=float,
        default=0.0,
        help="First threshold to test. Default: 0.00.",
    )
    dev_optimize_parser.add_argument(
        "--end",
        type=float,
        default=1.0,
        help="Last threshold to test. Default: 1.00.",
    )
    dev_optimize_parser.add_argument(
        "--step",
        type=float,
        default=0.01,
        help="Threshold step size. Default: 0.01.",
    )
    dev_optimize_parser.add_argument(
        "--format",
        choices=["png", "csv"],
        default="png",
        help="Output artifact format. Default: png.",
    )
    dev_optimize_parser.add_argument(
        "--output",
        help=(
            "Output path for the PNG or CSV artifact. PNG defaults to a safe path in "
            "the current directory when omitted."
        ),
    )
    dev_optimize_parser.add_argument(
        "--beta",
        type=float,
        default=1.0,
        help="F-beta beta value. Must be > 0. Default: 1.0.",
    )
    dev_optimize_parser.add_argument(
        "--write-config",
        action="store_true",
        help="Persist the recommended threshold into retrieval.match_threshold.",
    )
    dev_optimize_parser.set_defaults(state="optimize-threshold")
    dev_optimize_parser.set_defaults(dev_action="optimize-threshold")

    # -- workspace ---------------------------------------------------------
    workspace_parser = subparsers.add_parser(
        "workspace",
        help="list and manage workspace UIDs",
        description="List, resolve, rename, and manage aliases for workspace UIDs.",
    )
    workspace_sub = workspace_parser.add_subparsers(
        dest="workspace_action",
        required=True,
        title="workspace actions",
        metavar="ACTION",
    )

    list_ws_parser = workspace_sub.add_parser(
        "list",
        help="list known workspace UIDs",
        description="List distinct workspace UIDs from the database in the selected output format.",
    )
    list_ws_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include UIDs that only appear on archived memories.",
    )
    list_ws_parser.add_argument(
        "--include-aliases",
        action="store_true",
        help="Return workspace objects with nested alias arrays.",
    )

    resolve_parser = workspace_sub.add_parser(
        "resolve",
        help="resolve a workspace UID to its canonical UID",
        description="Normalize a workspace UID candidate and resolve any alias mapping.",
    )
    resolve_parser.add_argument("uid", help="Workspace UID candidate to resolve.")

    alias_parser = workspace_sub.add_parser(
        "alias",
        help="manage workspace UID aliases",
        description="Add, list, and remove workspace UID aliases.",
    )
    alias_sub = alias_parser.add_subparsers(
        dest="alias_action",
        required=True,
        title="alias actions",
        metavar="ACTION",
    )
    alias_add_parser = alias_sub.add_parser(
        "add",
        help="add a workspace UID alias",
        description="Create an alias mapping to a canonical workspace UID.",
    )
    alias_add_parser.add_argument("canonical_uid", help="Canonical workspace UID.")
    alias_add_parser.add_argument("alias_uid", help="Alias workspace UID.")
    alias_add_parser.add_argument(
        "--migrate-existing",
        action="store_true",
        help="Move existing alias workspace memories to the canonical UID in the same transaction.",
    )
    alias_list_parser = alias_sub.add_parser(
        "list",
        help="list workspace UID aliases",
        description="List alias mappings, optionally filtered by canonical workspace UID.",
    )
    alias_list_parser.add_argument(
        "--workspace",
        help="Optional canonical workspace UID filter.",
    )
    alias_remove_parser = alias_sub.add_parser(
        "remove",
        help="remove a workspace UID alias",
        description="Remove an alias mapping by alias UID.",
    )
    alias_remove_parser.add_argument("alias_uid", help="Alias workspace UID to remove.")

    rename_parser = workspace_sub.add_parser(
        "rename",
        help="rename a workspace and migrate its memories",
        description=(
            "Rename a workspace by migrating all its memories to a new UID. "
            "Both UIDs are normalized according to the workspace.uid_normalization "
            "config setting before the operation. Archived memories are included."
        ),
    )
    rename_parser.add_argument(
        "old_uid",
        help="Current workspace UID to rename.",
    )
    rename_parser.add_argument(
        "new_uid",
        help="New workspace UID to migrate memories to.",
    )

    # -- embedding-status --------------------------------------------------
    subparsers.add_parser(
        "embedding-status",
        help="show active local FastEmbed profile and startup job",
        description=(
            "Show the active built-in local FastEmbed embedding profile plus startup "
            "re-embedding job metadata, including the resolved model cache path. "
            "Recollectium stores model artifacts under the local Recollectium cache for "
            f"the configured embedding.model. Default: {DEFAULTS['embedding']['model']}. "
            f"Supported models: {_SUPPORTED_EMBEDDING_MODELS_HELP}."
        ),
    )

    # -- embedding-maintenance ---------------------------------------------
    subparsers.add_parser(
        "embedding-maintenance",
        help="prepare the configured model and refresh stale embeddings",
        description=(
            "Create the config/database when needed, download or prepare the configured "
            "built-in FastEmbed model, and refresh stale or missing embeddings inline. "
            "Installers and successful upgrades run this command automatically."
        ),
    )

    # -- embedding-jobs ----------------------------------------------------
    embedding_jobs_parser = subparsers.add_parser(
        "embedding-jobs",
        help="list embedding jobs or fetch one job by id",
        description=(
            "List embedding jobs by default or fetch one job with --job-id. "
            "Jobs track local FastEmbed model download and re-embedding progress."
        ),
    )
    embedding_jobs_parser.add_argument(
        "--job-id",
        help="If provided, return exactly one embedding job by ID.",
    )
    embedding_jobs_parser.add_argument(
        "--state",
        choices=("pending", "in_progress", "completed", "failed"),
        help="Optional list filter by job state: pending, in_progress, completed, or failed.",
    )
    embedding_jobs_parser.add_argument(
        "--limit",
        type=int,
        help="Optional positive integer limit for list mode.",
    )

    # -- embedding-refresh -------------------------------------------------
    embedding_refresh_parser = subparsers.add_parser(
        "embedding-refresh",
        help="force inline refresh of stale embeddings",
        description=(
            "Create an embedding job for stale memories matching the filters, "
            "process it inline, and return after it completes or fails."
        ),
    )
    embedding_refresh_parser.add_argument(
        "--space",
        choices=(SPACE_USER, SPACE_WORKSPACE),
        help="Optional space filter for stale memories.",
    )
    embedding_refresh_parser.add_argument(
        "--workspace-uid",
        help="Optional workspace UID filter. Implies --space workspace if omitted.",
    )
    embedding_refresh_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived memories when finding stale embeddings.",
    )

    # -- embedding-jobs-clear ---------------------------------------------
    embedding_jobs_clear_parser = subparsers.add_parser(
        "embedding-jobs-clear",
        help="delete embedding job records without deleting memories",
        description=(
            "Delete embedding job audit records. By default this removes completed, "
            "failed, and pending records only; memory data is not deleted."
        ),
    )
    embedding_jobs_clear_parser.add_argument(
        "--state",
        action="append",
        dest="states",
        help=(
            "Job state to delete. May be repeated. Default: completed, failed, pending."
        ),
    )
    embedding_jobs_clear_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion of job audit records.",
    )

    # -- mcp-stdio ---------------------------------------------------------
    subparsers.add_parser(
        "mcp-stdio",
        help="run MCP server over stdin/stdout",
        description=(
            "Start an MCP (Model Context Protocol) server over stdin/stdout. "
            "This is intended to be spawned by MCP-compatible clients. "
            "No PID file is created — the server runs for the lifetime of the client connection."
        ),
    )

    # -- completion ---------------------------------------------------------
    completion_parser = subparsers.add_parser(
        "completion",
        help="print shell completion setup instructions",
        description=(
            "Print shell completion setup instructions for bash, zsh, fish, or PowerShell. "
            "With --source, prints only the raw completion function definition "
            "for eval consumption. Setup instructions, --source shell code, and "
            "the hidden completion protocol are raw completion output; --json is "
            "supported only with --install."
        ),
    )
    completion_parser.add_argument(
        "shell",
        nargs="?",
        choices=list(_COMPLETION_SHELLS),
        help="Shell to generate completion for (default: auto-detect bash, zsh, fish, or PowerShell).",
    )
    action_group = completion_parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--source",
        action="store_true",
        help=(
            "Print only the raw completion function definition for eval "
            "consumption. This shell code is emitted as-is; omit --json."
        ),
    )
    action_group.add_argument(
        "--install",
        action="store_true",
        help=(
            "Write completion setup to the shell's startup file "
            "inside a managed comment block. Prompts for confirmation before "
            "modifying any file."
        ),
    )
    # Internal dynamic-completion protocol flags used by generated shell hooks;
    # hidden from public help because users should invoke completion via shell setup.
    action_group.add_argument(
        "--complete-line",
        help=argparse.SUPPRESS,
    )
    completion_parser.add_argument(
        "--point",
        type=int,
        help=argparse.SUPPRESS,
    )
    completion_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when used with --install.",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _rewrite_upgrade_version_selector(argv: list[str]) -> list[str]:
    """Let `recollectium upgrade --version` coexist with global `--version`."""
    try:
        upgrade_index = argv.index("upgrade")
    except ValueError:
        return argv
    rewritten = list(argv)
    for index in range(upgrade_index + 1, len(rewritten)):
        token = rewritten[index]
        if token == "--version":
            rewritten[index] = "--target-version"
            break
        if token.startswith("--version="):
            rewritten[index] = "--target-version=" + token.split("=", 1)[1]
            break
    return rewritten


def _handle_dev_command(
    args: argparse.Namespace,
    *,
    config_path: Path,
    core_config_path: Path | None,
    output_format: str,
    response_verbosity: str,
) -> int:
    dev_action = getattr(args, "dev_action", getattr(args, "state", None))
    if dev_action == "serve":
        host = args.host
        port = args.port
        if host is None or port is None:
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command="dev serve")
            except ValidationError as exc:
                return _config_invalid_error(exc, command="dev serve")
            if host is None:
                host = cfg.effective_config["service"]["host"]
            if port is None:
                port = cfg.effective_config["service"]["port"]
        try:
            run_service(
                host=host,
                port=port,
                db_path=args.db_path,
                config_path=core_config_path,
                log_level=args.log_level,
                cli_structured_errors=True,
                foreground_stderr_logs=True,
            )
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="dev serve")
        except ValidationError as exc:
            return _config_invalid_error(exc, command="dev serve")
        except (
            EmbeddingReadinessTimeoutError,
            EmbeddingModelUnavailableError,
            EmbeddingProviderUnavailableError,
            EmbeddingGenerationError,
        ) as exc:
            return _embedding_error(exc, command="dev serve")
        except ServiceError as exc:
            return _service_error(
                exc, command="dev serve", event="dev.serve.service_error"
            )
        except RecollectiumError as exc:
            return _operation_failed_error(exc, command="dev serve")
        return 0

    try:
        cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
        if dev_action == "eval":
            dev_db_path = _resolve_seeded_dev_database_path(cfg)
            regular_db_path = _resolve_regular_database_path(cfg, args.db_path)
            if _paths_equal(dev_db_path, regular_db_path):
                return _emit_cli_failure(
                    status="unsafe_seeded_database_path",
                    message="Seeded dev database path matches the regular database path.",
                    detail=(
                        "dev eval can reset the seeded database, so it will not run "
                        "when both paths resolve to the same file."
                    ),
                    hint=(
                        "Set development.seeded_database_path to a separate development "
                        "database before running recollectium dev eval."
                    ),
                    exit_code=1,
                    command="dev eval",
                    seeded_database=str(dev_db_path),
                    regular_database=str(regular_db_path),
                )
            progress_reporter = (
                _DevEvalProgressReporter(sys.stderr)
                if output_format == CLI_OUTPUT_HUMAN_READABLE
                and _stderr_supports_live_progress()
                else None
            )
            if progress_reporter is not None:
                with progress_reporter:
                    progress_reporter.phase("Checking embedding provider readiness")
                    provider = _builtin_fastembed_provider_from_config(
                        cfg.effective_config, model_cache_path=cfg.model_cache_path
                    )
                    _ensure_cli_provider_ready(
                        provider,
                        config_path=core_config_path,
                        log_level=args.log_level,
                        output_format=output_format,
                    )
                    search_progress_reporter = _human_reembedding_progress_reporter(
                        output_format
                    )
                    if search_progress_reporter is None:
                        result = _run_seeded_dev_eval(
                            cfg,
                            provider=provider,
                            config_path=core_config_path,
                            eval_progress_reporter=progress_reporter,
                            regular_db_path=regular_db_path,
                            verbose_progress=(
                                response_verbosity == RESPONSE_VERBOSITY_VERBOSE
                            ),
                        )
                    else:
                        with search_progress_reporter:
                            result = _run_seeded_dev_eval(
                                cfg,
                                provider=provider,
                                config_path=core_config_path,
                                eval_progress_reporter=progress_reporter,
                                regular_db_path=regular_db_path,
                                search_progress_reporter=search_progress_reporter,
                                verbose_progress=(
                                    response_verbosity == RESPONSE_VERBOSITY_VERBOSE
                                ),
                            )
            else:
                provider = _builtin_fastembed_provider_from_config(
                    cfg.effective_config, model_cache_path=cfg.model_cache_path
                )
                _ensure_cli_provider_ready(
                    provider,
                    config_path=core_config_path,
                    log_level=args.log_level,
                    output_format=output_format,
                )
                search_progress_reporter = _human_reembedding_progress_reporter(
                    output_format
                )
                if search_progress_reporter is None:
                    result = _run_seeded_dev_eval(
                        cfg,
                        provider=provider,
                        config_path=core_config_path,
                        regular_db_path=regular_db_path,
                        verbose_progress=(
                            response_verbosity == RESPONSE_VERBOSITY_VERBOSE
                        ),
                    )
                else:
                    with search_progress_reporter:
                        result = _run_seeded_dev_eval(
                            cfg,
                            provider=provider,
                            config_path=core_config_path,
                            regular_db_path=regular_db_path,
                            search_progress_reporter=search_progress_reporter,
                            verbose_progress=(
                                response_verbosity == RESPONSE_VERBOSITY_VERBOSE
                            ),
                        )
            _emit_success(result, output_format=output_format, command="dev eval")
            return 0

        if dev_action == "optimize-threshold":
            dev_db_path = _resolve_seeded_dev_database_path(cfg)
            regular_db_path = _resolve_regular_database_path(cfg, args.db_path)
            if _paths_equal(dev_db_path, regular_db_path):
                return _emit_cli_failure(
                    status="unsafe_seeded_database_path",
                    message="Seeded dev database path matches the regular database path.",
                    detail=(
                        "dev optimize-threshold can reset the seeded database, so it "
                        "will not run when both paths resolve to the same file."
                    ),
                    hint=(
                        "Set development.seeded_database_path to a separate development "
                        "database before running recollectium dev optimize-threshold."
                    ),
                    exit_code=1,
                    command="dev optimize-threshold",
                    seeded_database=str(dev_db_path),
                    regular_database=str(regular_db_path),
                )
            validate_threshold_sweep_parameters(
                start=args.start, end=args.end, step=args.step, beta=args.beta
            )
            if (
                output_format == CLI_OUTPUT_HUMAN_READABLE
                and _stderr_supports_live_progress()
            ):
                progress_reporter = _ThresholdOptimizationProgressReporter(sys.stderr)
                with progress_reporter:
                    progress_reporter.phase("Checking embedding provider readiness")
                    provider = _builtin_fastembed_provider_from_config(
                        cfg.effective_config, model_cache_path=cfg.model_cache_path
                    )
                    _ensure_cli_provider_ready(
                        provider,
                        config_path=core_config_path,
                        log_level=args.log_level,
                        output_format=output_format,
                    )
                    return _run_seeded_dev_optimize_threshold(
                        cfg,
                        provider=provider,
                        config_path=config_path,
                        regular_db_path=regular_db_path,
                        args=args,
                        output_format=output_format,
                        response_verbosity=response_verbosity,
                        progress=progress_reporter,
                    )
            provider = _builtin_fastembed_provider_from_config(
                cfg.effective_config, model_cache_path=cfg.model_cache_path
            )
            _ensure_cli_provider_ready(
                provider,
                config_path=core_config_path,
                log_level=args.log_level,
                output_format=output_format,
            )
            return _run_seeded_dev_optimize_threshold(
                cfg,
                provider=provider,
                config_path=config_path,
                regular_db_path=regular_db_path,
                args=args,
                output_format=output_format,
                response_verbosity=response_verbosity,
            )

        raw_config = load_config_file(config_path)
        running = check_running_service(cfg)
        if running is not None:
            return _emit_cli_failure(
                status="service_running",
                message="A Recollectium service is running.",
                detail=f"{running['type']} service PID {running['pid']} is using the current configuration.",
                hint="Stop or restart the service, then run recollectium dev again so future API/MCP activity uses the selected database.",
                exit_code=1,
                command="dev",
                event="dev.service_running",
            )
        if dev_action in {"true", "false"}:
            use_seeded_database = dev_action == "true"
            seeded_db_path = _resolve_seeded_dev_database_path(cfg)
            set_config_value(
                raw_config,
                "development.use_seeded_database",
                use_seeded_database,
            )
            merged = _deep_merge(deepcopy(DEFAULTS), raw_config)
            _validate_config_value(merged)
            if use_seeded_database:
                provider = _builtin_fastembed_provider_from_config(
                    merged,
                    model_cache_path=resolve_model_cache_path(cfg.xdg_dirs["cache"]),
                )
                _ensure_cli_provider_ready(
                    provider,
                    config_path=core_config_path,
                    log_level=args.log_level,
                    output_format=output_format,
                )
                with _human_dev_seed_progress_context(
                    output_format
                ) as progress_reporter:
                    seed_result = _call_with_optional_progress_callback(
                        ensure_seeded_dev_database,
                        seeded_db_path,
                        provider,
                        progress_callback=progress_reporter,
                    )
            else:
                seed_result = None
            config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(raw_config, indent=2) + "\n", encoding="utf-8"
            )
            config_path.chmod(0o600)
            updated_cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            result = {
                "status": "enabled" if use_seeded_database else "disabled",
                "action": dev_action,
                "use_seeded_database": use_seeded_database,
                "database": str(updated_cfg.resolved_database_path),
                "config": str(config_path),
                "seeded_database": _seeded_dev_context(seeded_db_path),
            }
            if use_seeded_database:
                result.update(
                    {
                        "seed_status": "ready"
                        if seed_result is None
                        else seed_result["status"],
                        "user_memories": DEV_SEED_USER_MEMORY_COUNT,
                        "workspace_memories": DEV_SEED_TOTAL_WORKSPACE_MEMORIES,
                        "workspaces": DEV_SEED_WORKSPACE_COUNT,
                        "topics": DEV_SEED_TOPIC_COUNT,
                    }
                )
        else:
            dev_reset_config_path = str(config_path)
            provider = _builtin_fastembed_provider_from_config(
                cfg.effective_config, model_cache_path=cfg.model_cache_path
            )
            _ensure_cli_provider_ready(
                provider,
                config_path=core_config_path,
                log_level=args.log_level,
                output_format=output_format,
            )
            with _human_dev_seed_progress_context(output_format) as progress_reporter:
                result = _call_with_optional_progress_callback(
                    reset_seeded_dev_database,
                    _resolve_seeded_dev_database_path(cfg),
                    provider,
                    progress_callback=progress_reporter,
                )
            result["action"] = "reset"
            result["config"] = dev_reset_config_path
            result["seeded_database"] = _seeded_dev_context(
                _resolve_seeded_dev_database_path(cfg)
            )
    except FileNotFoundError as exc:
        return _config_missing_error(exc, command="dev")
    except ValidationError as exc:
        return _validation_error(exc, command="dev")
    except ThresholdOptimizationError as exc:
        return _emit_cli_failure(
            status="validation_error",
            message="Threshold optimization parameters are invalid.",
            detail=f"ThresholdOptimizationError: {exc}",
            exit_code=2,
            command="dev optimize-threshold",
            event="dev.optimize_threshold.invalid",
        )
    except ServiceError as exc:
        return _service_error(exc, command="dev")
    except (
        EmbeddingReadinessTimeoutError,
        EmbeddingModelUnavailableError,
        EmbeddingProviderUnavailableError,
        EmbeddingGenerationError,
    ) as exc:
        return _embedding_error(exc, command="dev")
    command_name = (
        f"dev {dev_action}" if dev_action in {"true", "false", "reset"} else "dev"
    )
    _emit_success(result, output_format=output_format, command=command_name)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Recollectium CLI."""
    _set_cli_output_format(CLI_OUTPUT_JSON)
    _set_response_verbosity(RESPONSE_VERBOSITY_COMPACT)
    (
        argv,
        output_override,
        verbosity_override,
        output_conflict,
        verbosity_conflict,
        explicit_json,
    ) = _extract_cli_output_override(argv)
    parser = _build_parser()
    argcomplete.autocomplete(parser)
    effective_argv = sys.argv[1:] if argv is None else list(argv)
    if not effective_argv:
        parser.print_help()
        return 0
    effective_argv = _rewrite_upgrade_version_selector(effective_argv)
    if output_conflict:
        _set_cli_output_format(output_override or CLI_OUTPUT_JSON)
        return _emit_cli_failure(
            status="validation_error",
            message="Choose either --json or --human-readable, not both.",
            exit_code=2,
            command="output",
        )
    if verbosity_conflict:
        _set_cli_output_format(output_override or CLI_OUTPUT_HUMAN_READABLE)
        return _emit_cli_failure(
            status="validation_error",
            message="Choose either --compact or --verbose, not both.",
            exit_code=2,
            command="verbosity",
        )
    global _ARGPARSE_JSON_ERRORS
    previous_argparse_json_errors = _ARGPARSE_JSON_ERRORS
    _ARGPARSE_JSON_ERRORS = output_override == CLI_OUTPUT_JSON
    try:
        args = parser.parse_args(effective_argv)
    finally:
        _ARGPARSE_JSON_ERRORS = previous_argparse_json_errors
    setattr(args, "_explicit_json", explicit_json)

    if getattr(args, "command", None) is None and getattr(args, "version", False):
        try:
            installed_version = package_version("recollectium")
        except PackageNotFoundError:
            installed_version = __version__
        if output_override == CLI_OUTPUT_JSON:
            print(
                json.dumps(
                    {"name": "recollectium", "version": installed_version},
                    sort_keys=True,
                )
            )
            return 0
        sys.stdout.write(_frame_human_output(f"recollectium {installed_version}"))
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "completion" and (args.source or args.complete_line is not None):
        if output_override == CLI_OUTPUT_JSON:
            _set_cli_output_format(CLI_OUTPUT_JSON)
            return _handle_completion_command(args, output_format=CLI_OUTPUT_JSON)
        return _handle_completion_command(args, output_format=CLI_OUTPUT_HUMAN_READABLE)

    # Resolve config path
    config_path = _resolve_config_path(args.config_path)
    core_config_path = _core_config_path(args.config_path)
    output_format = _resolve_output_format(
        config_path=config_path,
        explicit=args.config_path is not None,
        override=output_override,
    )
    response_verbosity = _resolve_response_verbosity(
        config_path=config_path,
        override=verbosity_override,
    )
    _set_cli_output_format(output_format)
    _set_response_verbosity(response_verbosity)
    read_only_config_validate = args.command == "config" and args.validate
    if not (
        (args.command == "upgrade" and (args.check or args.dry_run))
        or read_only_config_validate
    ):
        _setup_cli_logging(config_path, log_level=args.log_level)
    _log.info(
        "CLI command started",
        extra={"event": "cli.command", "context": {"command": args.command}},
    )

    if args.command == "completion":
        return _handle_completion_command(args, output_format=output_format)

    # -- config command ---------------------------------------------------
    if args.command == "config":
        return _handle_config_command(
            args,
            config_path,
            explicit=args.config_path is not None,
            output_format=output_format,
        )

    if args.command == "init":
        try:
            return _handle_init_command(
                config_path,
                explicit=args.config_path is not None,
                db_path=args.db_path,
                log_level=args.log_level,
                output_format=output_format,
            )
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="init")
        except ValidationError as exc:
            return _config_invalid_error(exc, command="init")
        except (
            EmbeddingReadinessTimeoutError,
            EmbeddingModelUnavailableError,
            EmbeddingProviderUnavailableError,
            EmbeddingGenerationError,
        ) as exc:
            return _embedding_error(exc, command="init")
        except MigrationError as exc:
            return _emit_cli_failure(
                status="migration_error",
                message="Database migration failed.",
                detail=str(exc),
                exit_code=1,
                command="init",
                event="database.migration_failed",
            )
        except RecollectiumError as exc:
            return _operation_failed_error(exc, command="init")

    if args.command == "embedding-maintenance":
        try:
            result = _run_embedding_maintenance(
                config_path,
                explicit=args.config_path is not None,
                db_path=args.db_path,
                log_level=args.log_level,
                output_format=output_format,
            )
            _emit_success(
                result, output_format=output_format, command="embedding-maintenance"
            )
            return 0
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command="embedding-maintenance")
        except ValidationError as exc:
            return _config_invalid_error(exc, command="embedding-maintenance")
        except (
            EmbeddingReadinessTimeoutError,
            EmbeddingModelUnavailableError,
            EmbeddingProviderUnavailableError,
            EmbeddingGenerationError,
        ) as exc:
            return _embedding_error(exc, command="embedding-maintenance")
        except MigrationError as exc:
            return _emit_cli_failure(
                status="migration_error",
                message="Database migration failed.",
                detail=str(exc),
                exit_code=1,
                command="embedding-maintenance",
                event="database.migration_failed",
            )
        except RecollectiumError as exc:
            return _operation_failed_error(exc, command="embedding-maintenance")

    # -- db-status command ------------------------------------------------
    if args.command == "db-status":
        if args.db_path:
            db_path = Path(args.db_path)
        else:
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
                db_path = cfg.resolved_database_path
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)
        try:
            store = SQLiteMemoryStore(db_path)
            status_payload = (
                store.detailed_migration_status()
                if _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_VERBOSE
                else store.migration_status()
            )
            _emit_success(
                status_payload,
                output_format=output_format,
                command="db-status",
            )
        except MigrationError as exc:
            return _emit_cli_failure(
                status="migration_error",
                message="Database migration status failed.",
                detail=str(exc),
                exit_code=1,
                command="db-status",
                event="database.migration_status_failed",
            )
        return 0

    # -- mcp-stdio command ------------------------------------------------
    if args.command == "mcp-stdio":
        try:
            core = RecollectiumCore(
                db_path=args.db_path,
                config_path=core_config_path,
                log_level=args.log_level,
            )
            _ensure_cli_model_ready(core, output_format="json")
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command=args.command)
        except ValidationError as exc:
            return _config_invalid_error(exc, command=args.command)
        except (
            EmbeddingReadinessTimeoutError,
            EmbeddingModelUnavailableError,
            EmbeddingProviderUnavailableError,
            EmbeddingGenerationError,
        ) as exc:
            return _embedding_error(exc, command=args.command)
        try:
            logging.getLogger("mcp").setLevel(logging.WARNING)
            logging.getLogger("mcp.server").setLevel(logging.WARNING)
            logging.getLogger("rich").setLevel(logging.WARNING)
            mcp = create_mcp_server(core)
            import asyncio

            asyncio.run(mcp.run_stdio_async())
        except Exception as exc:
            return _operation_failed_error(exc, command="mcp-stdio")
        return 0

    # -- service commands --------------------------------------------------
    if args.command == "service":
        if args.service_action == "discover":
            try:
                plan = _load_uninstall_plan(
                    config_path,
                    explicit=args.config_path is not None,
                )
                payload = discover_service(plan.config)
                _emit_success(
                    payload, output_format=output_format, command="service discover"
                )
                if payload["status"] == "not_running":
                    return 1
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)
            except ServiceError as exc:
                return _service_error(exc, command="service discover", exit_code=2)
            return 0

        if args.service_action == "start":
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)
            try:
                pid = start_service(
                    cfg, args.type, db_path=args.db_path, log_level=args.log_level
                )
                host = cfg.effective_config["service"]["host"]
                port = cfg.effective_config["service"]["port"]
                endpoint = f"http://{host}:{port}"
                _emit_success(
                    {
                        "status": "started",
                        "type": args.type,
                        "pid": pid,
                        "endpoint": endpoint,
                    },
                    output_format=output_format,
                    command="service start",
                )
            except ServiceConflictError as exc:
                return _service_error(
                    exc,
                    command=f"service {args.service_action}",
                    status="service_conflict",
                    event="service.startup_rejected",
                )
            except ServiceError as exc:
                return _service_error(exc, command=f"service {args.service_action}")
            except ValueError as exc:
                return _emit_cli_failure(
                    status="validation_error",
                    message="Invalid service request.",
                    detail=str(exc),
                    exit_code=2,
                    command=f"service {args.service_action}",
                )
            return 0

        if args.service_action == "stop":
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)
            pid = stop_service(cfg)
            if pid is not None:
                _emit_success(
                    {"status": "stopped", "pid": pid},
                    output_format=output_format,
                    command="service stop",
                )
            else:
                _emit_success(
                    {"status": "no_service_running"},
                    output_format=output_format,
                    command="service stop",
                )
            return 0

        if args.service_action == "status":
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)
            pid_path = get_pid_file_path(cfg)
            try:
                raw_pid_info = read_pid_file(pid_path)
                running = check_running_service(cfg)
            except ServiceError as exc:
                return _service_error(exc, command=f"service {args.service_action}")
            if running is not None:
                host = cfg.effective_config["service"]["host"]
                port = cfg.effective_config["service"]["port"]
                if _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_VERBOSE:
                    _emit_success(
                        service_discovery_payload(cfg, running),
                        output_format=output_format,
                        command="service status",
                    )
                    return 0
                _emit_success(
                    {
                        "running": True,
                        "type": running["type"],
                        "pid": running["pid"],
                        "endpoint": f"http://{host}:{port}",
                    },
                    output_format=output_format,
                    command="service status",
                )
            else:
                if _CURRENT_RESPONSE_VERBOSITY == RESPONSE_VERBOSITY_VERBOSE:
                    status_info = service_discovery_payload(cfg, None)
                    if raw_pid_info is not None:
                        status_info["last_service"] = {
                            "type": raw_pid_info["type"],
                            "pid": raw_pid_info["pid"],
                        }
                    _emit_success(
                        status_info,
                        output_format=output_format,
                        command="service status",
                    )
                    return 0
                status_info: dict[str, object] = {"running": False}
                if raw_pid_info is not None:
                    status_info["last_service"] = {
                        "type": raw_pid_info["type"],
                        "pid": raw_pid_info["pid"],
                    }
                _emit_success(
                    status_info, output_format=output_format, command="service status"
                )
            return 0

        if args.service_action == "restart":
            try:
                cfg = RecollectiumConfig(core_config_path, log_level=args.log_level)
            except FileNotFoundError as exc:
                return _config_missing_error(exc, command=args.command)
            except ValidationError as exc:
                return _config_invalid_error(exc, command=args.command)

            pid_path = get_pid_file_path(cfg)
            try:
                raw_pid_info = read_pid_file(pid_path)
                running = check_running_service(cfg)
            except ServiceError as exc:
                return _service_error(exc, command=f"service {args.service_action}")
            if running is not None:
                # Service is running: stop it first, then restart same type
                service_type = running["type"]
                _log.warning(
                    f"Stopping existing {service_type} service...",
                    extra={"event": "service.stop"},
                )
                stop_service(cfg)
                time.sleep(0.5)  # let port release before binding again
            elif raw_pid_info is not None:
                service_type = raw_pid_info["type"]
            elif args.type is not None:
                service_type = args.type
            else:
                return _emit_cli_failure(
                    status="service_not_running",
                    message="No running service found.",
                    hint="Use --type to specify which service to restart.",
                    exit_code=1,
                    command="service restart",
                    event="service.no_service",
                )

            try:
                pid = start_service(
                    cfg,
                    service_type,
                    db_path=args.db_path,
                    log_level=args.log_level,
                )
                host = cfg.effective_config["service"]["host"]
                port = cfg.effective_config["service"]["port"]
                _emit_success(
                    {
                        "status": "restarted",
                        "type": service_type,
                        "pid": pid,
                        "endpoint": f"http://{host}:{port}",
                    },
                    output_format=output_format,
                    command="service restart",
                )
            except ServiceConflictError as exc:
                return _service_error(
                    exc,
                    command=f"service {args.service_action}",
                    status="service_conflict",
                    event="service.startup_rejected",
                )
            except ServiceError as exc:
                return _service_error(exc, command=f"service {args.service_action}")
            except ValueError as exc:
                return _emit_cli_failure(
                    status="validation_error",
                    message="Invalid service request.",
                    detail=str(exc),
                    exit_code=2,
                    command=f"service {args.service_action}",
                )
            return 0

    if args.command == "update" and args.memory_id is None:
        return _emit_cli_failure(
            status="validation_error",
            message="Memory ID is required for recollectium update.",
            hint="Use recollectium upgrade to upgrade the installed Recollectium package.",
            exit_code=2,
            command="update",
        )

    if args.command == "upgrade":
        return _handle_upgrade_command(args, config_path, output_format=output_format)

    if args.command == "dev":
        return _handle_dev_command(
            args,
            config_path=config_path,
            core_config_path=core_config_path,
            output_format=output_format,
            response_verbosity=response_verbosity,
        )

    if args.command == "uninstall":
        try:
            return _handle_uninstall_command(
                args,
                config_path,
                explicit=args.config_path is not None,
                output_format=output_format,
            )
        except FileNotFoundError as exc:
            return _config_missing_error(exc, command=args.command)
        except ValidationError as exc:
            return _config_invalid_error(exc, command=args.command)
        except ServiceError as exc:
            return _service_error(
                exc, command="uninstall", event="uninstall.service_stop_failed"
            )
        except OSError as exc:
            return _emit_cli_failure(
                status="operation_failed",
                message="Uninstall purge failed.",
                detail=str(exc),
                exit_code=1,
                command="uninstall",
                event="uninstall.purge_failed",
            )

    # -- all other commands use RecollectiumCore ------------------------------
    try:
        core = RecollectiumCore(
            db_path=args.db_path,
            config_path=core_config_path,
            log_level=args.log_level,
        )

        # Ensure embedding model is ready before commands that need it.
        # Non-embedding commands (list, get, archive, workspace, db-status,
        # config, update metadata-only) skip this gate.
        _EMBEDDING_COMMANDS = frozenset(
            {"add", "search-user", "search-workspace", "embedding-refresh"}
        )
        _needs_embedding = args.command in _EMBEDDING_COMMANDS or (
            args.command == "update" and args.content is not None
        )
        if _needs_embedding:
            _ensure_cli_model_ready(core, output_format=output_format)

        if args.command == "add":
            result = core.add_memory(
                space=args.space,
                type=args.type,
                content=args.content,  # type: ignore[reportArgumentType]
                workspace_uid=args.workspace_uid,
                metadata=_parse_metadata(args.metadata),
                source=args.source,
                confidence=args.confidence,
                sensitivity=args.sensitivity,
            )
        elif args.command == "search-user":
            progress_reporter = _human_reembedding_progress_reporter(output_format)
            if progress_reporter is None:
                result = core.search_user_memories(
                    query=args.query,
                    limit=args.limit,
                    include_archived=args.include_archived,
                    type=args.type,
                    protected_minimum=args.protected_minimum,
                    match_threshold=args.match_threshold,
                )
            else:
                with progress_reporter:
                    result = core.search_user_memories(
                        query=args.query,
                        limit=args.limit,
                        include_archived=args.include_archived,
                        type=args.type,
                        protected_minimum=args.protected_minimum,
                        match_threshold=args.match_threshold,
                        progress_callback=progress_reporter,
                    )
        elif args.command == "search-workspace":
            progress_reporter = _human_reembedding_progress_reporter(output_format)
            if progress_reporter is None:
                result = core.search_workspace_memories(
                    query=args.query,
                    workspace_uid=args.workspace_uid,
                    limit=args.limit,
                    include_archived=args.include_archived,
                    type=args.type,
                    protected_minimum=args.protected_minimum,
                    match_threshold=args.match_threshold,
                )
            else:
                with progress_reporter:
                    result = core.search_workspace_memories(
                        query=args.query,
                        workspace_uid=args.workspace_uid,
                        limit=args.limit,
                        include_archived=args.include_archived,
                        type=args.type,
                        protected_minimum=args.protected_minimum,
                        match_threshold=args.match_threshold,
                        progress_callback=progress_reporter,
                    )
        elif args.command == "list":
            result = core.list_memories(
                space=args.space,
                type=args.type,
                status=args.status,
                workspace_uid=args.workspace_uid,
                include_archived=args.include_archived,
                limit=args.limit,
            )
        elif args.command == "get":
            result = core.get_memory(args.memory_id)
        elif args.command == "update":
            result = core.update_memory(
                args.memory_id,
                type=args.type,
                content=args.content,
                metadata=_parse_metadata(args.metadata),
                source=args.source,
                confidence=args.confidence,
                sensitivity=args.sensitivity,
            )
        elif args.command == "archive":
            result = core.archive_memory(args.memory_id)
        elif args.command == "workspace":
            return _handle_workspace_command(
                args, core=core, output_format=output_format
            )
        elif args.command == "embedding-status":
            result = core.active_embedding_status()
        elif args.command == "embedding-jobs":
            if args.job_id:
                result = core.get_embedding_job(args.job_id)
            else:
                result = core.list_embedding_jobs(state=args.state, limit=args.limit)
        elif args.command == "embedding-refresh":
            result = _refresh_stale_embeddings_with_progress(
                core,
                space=args.space,
                workspace_uid=args.workspace_uid,
                include_archived=args.include_archived,
                output_format=output_format,
            )
        elif args.command == "embedding-jobs-clear":
            if not args.yes:
                return _emit_cli_failure(
                    status="confirmation_required",
                    message="Deleting embedding job audit records requires --yes.",
                    hint="Add --yes to delete job records. Memory data is not deleted.",
                    exit_code=1,
                    command=args.command,
                    event="embedding_jobs_clear.confirmation_required",
                )
            result = core.clear_embedding_jobs(states=args.states)
        else:
            parser.error(f"unknown command: {args.command}")
            return 2
    except _MetadataInvalidError as exc:
        return _metadata_invalid_error(exc)
    except ValidationError as exc:
        return _validation_error(exc, command=args.command)
    except NotFoundError as exc:
        return _not_found_error(exc, command=args.command)
    except FileNotFoundError as exc:
        return _config_missing_error(exc, command=args.command)
    except (
        EmbeddingReadinessTimeoutError,
        EmbeddingModelUnavailableError,
        EmbeddingProviderUnavailableError,
        EmbeddingGenerationError,
    ) as exc:
        return _embedding_error(exc, command=args.command)
    except MigrationError as exc:
        return _emit_cli_failure(
            status="migration_error",
            message="Database migration failed.",
            detail=str(exc),
            exit_code=1,
            command=args.command,
            event="database.migration_failed",
        )
    except RecollectiumError as exc:
        return _operation_failed_error(exc, command=args.command)

    _emit_success(result, output_format=output_format, command=args.command)
    return 0
