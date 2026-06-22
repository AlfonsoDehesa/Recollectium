"""FastAPI local WebUI for Recollectium Core."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict
from http import HTTPStatus
import json
import logging
from pathlib import Path
from typing import Any, cast

from platformdirs import user_state_dir

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from recollectium import __version__
from recollectium.config import (
    DEFAULTS,
    RecollectiumConfig,
    _apply_explicit_null_overrides,
    _deep_merge,
    _validate_config_value,
    get_config_value,
    load_config_file,
    set_config_value,
    unset_config_value,
)
from recollectium.dev_eval import (
    evaluate_exact_mrr_for_core,
    evaluate_ranked_set_ndcg_for_core,
    evaluate_semantic_mrr_for_core,
)
from recollectium.dev_eval_thematic_weighted import (
    evaluate_thematic_weighted_metrics_for_core,
)
from recollectium.dev_optimize_threshold import (
    DEFAULT_THRESHOLD_BETA,
    build_threshold_optimization_report,
    build_threshold_search_bundles,
)
from recollectium.dev_seed import (
    ensure_seeded_dev_database,
    reset_seeded_dev_database,
    seeded_dev_database_is_initialized,
)
from recollectium.dev_eval_thematic_labels import THEMATIC_CONTEXT_LABEL_CASES
from recollectium.core import RecollectiumCore
from recollectium.errors import (
    NotFoundError,
    ServiceConflictError,
    ServiceError,
    ValidationError,
)
from recollectium.logging import setup_logging
from recollectium.model_state import read_model_state
from recollectium.memory_spaces import (
    MemorySpaceInfo,
    MemorySpaceResolver,
    resolve_memory_space_database_path,
    validate_memory_space_key,
)
from recollectium.models import SPACE_USER, SPACE_WORKSPACE
from recollectium.representations import (
    project_workspace_alias,
    project_workspace_alias_add,
    project_workspace_alias_remove,
    project_workspace_list_item,
    project_workspace_resolve,
    project_workspace_rename,
)
from recollectium.service_contract import (
    serialize_memories,
    serialize_memory,
    serialize_search_results,
)
from recollectium import service_manager
from recollectium.service_contract import SERVICE_API_PREFIX, capabilities_payload

WEBUI_SERVICE_TYPE = "webui"
WEBUI_DEFAULT_HOST = "127.0.0.1"
WEBUI_DEFAULT_PORT = 8766
WEBUI_TITLE = "Recollectium WebUI"
WEBUI_VERSION = "1"
WEBUI_LOCAL_FIRST = True
WEBUI_AUTHENTICATION = "none"
WEBUI_TLS = False
WEBUI_STATIC_DIR = Path(__file__).with_name("webui_static")

_log = logging.getLogger(__name__)


class StrictBodyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryAddBody(StrictBodyModel):
    space: str = Field(..., description="Memory scope: user or workspace")
    type: str
    content: str
    workspace_uid: str | None = None
    metadata: dict[str, Any] | None = None
    source: str | None = None
    confidence: float | None = None
    sensitivity: str | None = None
    memory_space_key: str | None = None


class MemoryUpdateBody(StrictBodyModel):
    content: str | None = None
    type: str | None = None
    metadata: dict[str, Any] | None = None
    source: str | None = None
    confidence: float | None = None
    sensitivity: str | None = None
    memory_space_key: str | None = None


class MemorySearchBody(StrictBodyModel):
    query: str
    scope: str = Field("user", description="user or workspace")
    workspace_uid: str | None = None
    limit: int = Field(20, ge=1)
    include_archived: bool = False
    type: str | None = None
    protected_minimum: int | None = None
    match_threshold: float | str | None = None
    memory_space_key: str | None = None


class WorkspaceRenameBody(StrictBodyModel):
    new_uid: str
    memory_space_key: str | None = None


class WorkspaceAliasBody(StrictBodyModel):
    alias_uid: str
    migrate_existing: bool = False
    memory_space_key: str | None = None


class ConfigSetBody(StrictBodyModel):
    value: Any


class ConfigValidateBody(StrictBodyModel):
    config: dict[str, Any] | None = None


class ServiceActionBody(StrictBodyModel):
    db_path: str | None = None
    log_level: str | None = None
    allow_self_stop: bool = False


class EmbeddingRefreshBody(StrictBodyModel):
    space: str | None = None
    workspace_uid: str | None = None
    include_archived: bool = False
    memory_space_key: str | None = None


class EmbeddingJobsClearBody(StrictBodyModel):
    states: list[str] | None = None
    memory_space_key: str | None = None


class DevEvalBody(StrictBodyModel):
    memory_space_key: str | None = None


class ThresholdOptimizeBody(StrictBodyModel):
    start: float = 0.0
    end: float = 1.0
    step: float = 0.05
    beta: float = DEFAULT_THRESHOLD_BETA
    output_format: str = "csv"
    output_path: str | None = None
    write_config: bool = False
    memory_space_key: str | None = None


def _webui_urls(host: str, port: int) -> dict[str, str]:
    base = f"http://{host}:{port}"
    return {
        "base": base,
        "health": f"{base}{SERVICE_API_PREFIX}/health",
        "status": f"{base}{SERVICE_API_PREFIX}/status",
        "version": f"{base}{SERVICE_API_PREFIX}/version",
        "capabilities": f"{base}{SERVICE_API_PREFIX}/capabilities",
        "context": f"{base}{SERVICE_API_PREFIX}/webui/context",
        "memories": f"{base}{SERVICE_API_PREFIX}/webui/memories",
        "memory_spaces": f"{base}{SERVICE_API_PREFIX}/webui/memory-spaces",
        "workspaces": f"{base}{SERVICE_API_PREFIX}/webui/workspaces",
        "config": f"{base}{SERVICE_API_PREFIX}/webui/config",
        "services": f"{base}{SERVICE_API_PREFIX}/webui/services",
        "embedding": f"{base}{SERVICE_API_PREFIX}/webui/embedding/status",
        "dev": f"{base}{SERVICE_API_PREFIX}/webui/dev/status",
        "graph": f"{base}{SERVICE_API_PREFIX}/webui/graph",
        "diagnostics": f"{base}{SERVICE_API_PREFIX}/webui/diagnostics",
        "logs": f"{base}{SERVICE_API_PREFIX}/webui/logs",
    }


def _security_warning() -> str:
    return (
        "Recollectium WebUI is localhost-first and unauthenticated in v1. "
        "Do not bind it to a public interface without private-network controls."
    )


def _service_config_summary(config: RecollectiumConfig) -> dict[str, Any]:
    return {
        "default_memory_space_key": config.default_memory_space_key,
        "database_folder": str(config.resolved_database_folder),
        "database_path": str(config.resolved_database_path),
        "config_file_path": str(config.config_file_path),
        "log_level": str(config.effective_config["logging"]["level"]),
        "service_endpoint": f"http://{config.effective_config['service']['host']}:{config.effective_config['service']['port']}",
        "webui_endpoint": f"http://{config.effective_config['webui']['host']}:{config.effective_config['webui']['port']}",
    }


def _recollectium_state_dir() -> Path:
    return Path(user_state_dir("recollectium"))


def _log_files_for_config(config: RecollectiumConfig) -> list[Path]:
    log_dir = config.xdg_dirs["logs"]
    files: list[Path] = []
    main_log = log_dir / "recollectium.log"
    if main_log.exists():
        files.append(main_log)
    service_logs = sorted(
        log_dir.glob("service-*.log"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    files.extend(service_logs[:3])
    return files


def _tail_text(path: Path, *, lines: int = 80) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "lines": [],
            "line_count": 0,
            "truncated": False,
        }

    buffer: deque[str] = deque(maxlen=lines)
    line_count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line_count += 1
            buffer.append(raw_line.rstrip("\n"))
    return {
        "path": str(path),
        "exists": True,
        "lines": list(buffer),
        "line_count": line_count,
        "truncated": line_count > lines,
        "size_bytes": path.stat().st_size,
    }


def _log_summary_payload(
    core: RecollectiumCore, *, tail_lines: int = 80
) -> dict[str, Any]:
    log_dir = core.config.xdg_dirs["logs"]
    files = [
        _tail_text(path, lines=tail_lines)
        for path in _log_files_for_config(core.config)
    ]
    return {
        "status": "ok",
        "log_dir": str(log_dir),
        "log_files": files,
        "recent": files[0] if files else None,
    }


def _model_state_summary(core: RecollectiumCore) -> dict[str, Any]:
    state = read_model_state(_recollectium_state_dir())
    profile = core.embedding_provider.embedding_profile
    model_name = str(profile.get("model", ""))
    profile_name = str(profile.get("profile", ""))
    dimensions = profile.get("dimensions")
    provider_cache_dir = getattr(core.embedding_provider, "cache_dir", None)
    if provider_cache_dir is not None:
        model_cache_path: str | None = str(provider_cache_dir)
    elif getattr(core, "_embedding_provider_managed_by_recollectium", False):
        model_cache_path = str(core.config.model_cache_path)
    else:
        model_cache_path = None
    matches = (
        state is not None
        and state.get("prepared_model") == model_name
        and state.get("profile") == profile_name
        and state.get("dimensions") == dimensions
        and state.get("model_cache_path") == model_cache_path
    )
    return {
        "status": "ok",
        "state_path": str(_recollectium_state_dir() / "model-state.json"),
        "present": state is not None,
        "ready": matches,
        "expected": {
            "prepared_model": model_name,
            "profile": profile_name,
            "dimensions": dimensions,
            "model_cache_path": model_cache_path,
        },
        "state": state,
    }


def _embedding_status_payload(
    core: RecollectiumCore, memory_space_key: str | None
) -> dict[str, Any]:
    payload = core.active_embedding_status(memory_space_key=memory_space_key)
    payload["model_state"] = _model_state_summary(core)
    return payload


def _dev_seeded_database_path(core: RecollectiumCore) -> Path:
    dev_path = Path(core.config.effective_config["development"]["seeded_database_path"])
    if not dev_path.is_absolute():
        dev_path = core.config.xdg_dirs["data"] / dev_path
    return dev_path


def _dev_command_hints(core: RecollectiumCore) -> dict[str, Any]:
    config_path = str(core.config.config_file_path)
    seeded_path = str(_dev_seeded_database_path(core))
    return {
        "seeding": [
            f"recollectium init --config {config_path}",
            f"recollectium dev seed --config {config_path}  # if the CLI surface is available",
        ],
        "eval": [
            f"recollectium dev eval --config {config_path}",
            f"recollectium dev eval --config {config_path} --db {seeded_path}",
        ],
        "threshold_optimizer": [
            f"recollectium dev optimize-threshold --config {config_path} --format csv",
            f"recollectium dev optimize-threshold --config {config_path} --format png",
        ],
    }


def _dev_seed_status_payload(core: RecollectiumCore) -> dict[str, Any]:
    db_path = _dev_seeded_database_path(core)
    return {
        "status": "ok",
        "database": str(db_path),
        "initialized": seeded_dev_database_is_initialized(db_path),
        "command_hints": _dev_command_hints(core)["seeding"],
    }


def _dev_seed_init_payload(core: RecollectiumCore) -> dict[str, Any]:
    db_path = _dev_seeded_database_path(core)
    result = ensure_seeded_dev_database(db_path, core.embedding_provider)
    return {
        "status": "ok" if result is None else result.get("status", "seeded"),
        "database": str(db_path),
        "initialized": True,
        "changed": result is not None,
        "seed_result": result,
        "command_hints": _dev_command_hints(core)["seeding"],
    }


def _dev_seed_reset_payload(core: RecollectiumCore) -> dict[str, Any]:
    db_path = _dev_seeded_database_path(core)
    result = reset_seeded_dev_database(db_path, core.embedding_provider)
    return {
        "status": result.get("status", "reset"),
        "database": str(db_path),
        "initialized": True,
        "changed": True,
        "seed_result": result,
        "command_hints": _dev_command_hints(core)["seeding"],
    }


def _dev_eval_payload(core: RecollectiumCore) -> dict[str, Any]:
    db_path = _dev_seeded_database_path(core)
    seeded = seeded_dev_database_is_initialized(db_path)
    if not seeded:
        return {
            "status": "not_configured",
            "database": str(db_path),
            "initialized": False,
            "command_hints": _dev_command_hints(core)["eval"],
        }

    ensure_seeded_dev_database(db_path, core.embedding_provider)
    seeded_core = RecollectiumCore(
        db_path=db_path,
        config_path=core.config.config_file_path,
        embedding_provider=core.embedding_provider,
        log_level=str(core.config.effective_config["logging"]["level"]),
    )
    exact_report = evaluate_exact_mrr_for_core(cast(Any, seeded_core))
    semantic_report = evaluate_semantic_mrr_for_core(cast(Any, seeded_core))
    thematic_report = evaluate_thematic_weighted_metrics_for_core(
        cast(Any, seeded_core)
    )
    ranked_set_report = evaluate_ranked_set_ndcg_for_core(cast(Any, seeded_core))
    return {
        "status": "ok",
        "database": str(db_path),
        "initialized": True,
        "command_hints": _dev_command_hints(core)["eval"],
        "reports": {
            "exact_mrr": asdict(exact_report),
            "semantic_mrr": asdict(semantic_report),
            "thematic_weighted": asdict(thematic_report),
            "ranked_set_ndcg": asdict(ranked_set_report),
        },
    }


def _threshold_optimizer_payload(
    core: RecollectiumCore,
    *,
    start: float,
    end: float,
    step: float,
    beta: float,
    output_format: str,
    output_path: str | None,
    write_config: bool,
) -> dict[str, Any]:
    db_path = _dev_seeded_database_path(core)
    seeded = seeded_dev_database_is_initialized(db_path)
    if not seeded:
        return {
            "status": "not_configured",
            "database": str(db_path),
            "initialized": False,
            "command_hints": _dev_command_hints(core)["threshold_optimizer"],
        }

    ensure_seeded_dev_database(db_path, core.embedding_provider)
    seeded_core = RecollectiumCore(
        db_path=db_path,
        config_path=core.config.config_file_path,
        embedding_provider=core.embedding_provider,
        log_level=str(core.config.effective_config["logging"]["level"]),
    )
    report = build_threshold_optimization_report(
        model=str(core.embedding_provider.embedding_profile.get("model", "unknown")),
        provider=str(
            core.embedding_provider.embedding_profile.get("provider", "unknown")
        ),
        start=start,
        end=end,
        step=step,
        beta=beta,
        output_format=output_format,  # type: ignore[arg-type]
        output_path=output_path,
        wrote_config=write_config,
        bundles=build_threshold_search_bundles(
            THEMATIC_CONTEXT_LABEL_CASES,
            search_user=lambda query, limit: seeded_core.search_user_memories(
                query=query,
                limit=limit,
                include_archived=False,
                protected_minimum=0,
                match_threshold=None,
            ),
            search_workspace=lambda query, workspace_uid, limit: (
                seeded_core.search_workspace_memories(
                    query=query,
                    workspace_uid=workspace_uid,
                    limit=limit,
                    include_archived=False,
                    protected_minimum=0,
                    match_threshold=None,
                )
            ),
        ),
    )
    return {
        "status": "ok",
        "database": str(db_path),
        "initialized": True,
        "command_hints": _dev_command_hints(core)["threshold_optimizer"],
        "report": report.to_dict(),
    }


def _graph_payload(
    core: RecollectiumCore,
    *,
    memory_space_key: str | None = None,
    space: str | None = None,
    workspace_uid: str | None = None,
    type: str | None = None,
    status: str | None = None,
    include_archived: bool = False,
    limit: int = 40,
) -> dict[str, Any]:
    resolved_space_key = memory_space_key or core.config.default_memory_space_key
    memories = core.list_memories(
        space=space,
        type=type,
        status=status,
        workspace_uid=workspace_uid,
        include_archived=include_archived,
        limit=limit,
        memory_space_key=memory_space_key,
    )
    nodes: list[dict[str, Any]] = [
        {
            "id": f"space:{resolved_space_key}",
            "kind": "memory_space",
            "label": resolved_space_key,
        }
    ]
    edges: list[dict[str, Any]] = []
    workspace_nodes: dict[str, dict[str, Any]] = {}
    type_nodes: dict[str, dict[str, Any]] = {}
    status_nodes: dict[str, dict[str, Any]] = {}
    for memory in memories:
        memory_id = str(memory.id)
        nodes.append(
            {
                "id": memory_id,
                "kind": "memory",
                "label": memory_id,
                "group": memory.space,
                "space": memory.space,
                "type": memory.type,
                "status": memory.status,
                "workspace_uid": memory.workspace_uid,
                "content_preview": memory.content[:120],
            }
        )
        edges.append(
            {
                "source": f"space:{resolved_space_key}",
                "target": memory_id,
                "kind": "belongs_to_space",
            }
        )
        if memory.workspace_uid:
            workspace_id = f"workspace:{memory.workspace_uid}"
            workspace_nodes.setdefault(
                workspace_id,
                {
                    "id": workspace_id,
                    "kind": "workspace",
                    "label": memory.workspace_uid,
                },
            )
            edges.append(
                {
                    "source": workspace_id,
                    "target": memory_id,
                    "kind": "belongs_to_workspace",
                }
            )
        type_id = f"type:{memory.type}"
        type_nodes.setdefault(
            type_id, {"id": type_id, "kind": "type", "label": memory.type}
        )
        edges.append({"source": type_id, "target": memory_id, "kind": "has_type"})
        status_id = f"status:{memory.status}"
        status_nodes.setdefault(
            status_id, {"id": status_id, "kind": "status", "label": memory.status}
        )
        edges.append({"source": status_id, "target": memory_id, "kind": "has_status"})
    nodes.extend(workspace_nodes.values())
    nodes.extend(type_nodes.values())
    nodes.extend(status_nodes.values())
    return {
        "status": "ok",
        "filters": {
            "memory_space_key": resolved_space_key,
            "space": space,
            "workspace_uid": workspace_uid,
            "type": type,
            "status": status,
            "include_archived": include_archived,
            "limit": limit,
        },
        "summary": {
            "memory_count": len(memories),
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }


def _memory_space_payload(
    core: RecollectiumCore, selected_key: str | None = None
) -> dict[str, Any]:
    config = core.config
    resolver = MemorySpaceResolver(
        config.resolved_database_folder, config.default_memory_space_key
    )
    selected_key = selected_key or config.default_memory_space_key
    try:
        selected_key = validate_memory_space_key(selected_key)
    except ValidationError:
        selected_key = config.default_memory_space_key

    spaces: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_space(info: MemorySpaceInfo, *, source: str) -> None:
        if info.key in seen:
            return
        seen.add(info.key)
        spaces.append(
            {
                "key": info.key,
                "db_path": str(info.db_path),
                "exists": info.exists,
                "is_default": info.is_default,
                "selected": info.key == selected_key,
                "source": source,
                "created_at": info.created_at,
                "updated_at": info.updated_at,
            }
        )

    for info in resolver.list_spaces():
        add_space(info, source="manifest")

    default_resolution = resolver.resolve(config.default_memory_space_key)
    add_space(
        MemorySpaceInfo(
            key=default_resolution.key,
            db_path=default_resolution.db_path,
            is_default=True,
            exists=default_resolution.db_path.exists(),
        ),
        source="configured-default",
    )

    if not spaces:
        add_space(
            MemorySpaceInfo(
                key=config.default_memory_space_key,
                db_path=default_resolution.db_path,
                is_default=True,
                exists=default_resolution.db_path.exists(),
            ),
            source="fallback",
        )

    current_path = resolve_memory_space_database_path(
        config.resolved_database_folder,
        selected_key,
        default_key=config.default_memory_space_key,
    )
    return {
        "status": "ok",
        "default_memory_space_key": config.default_memory_space_key,
        "selected_memory_space_key": selected_key,
        "resolved_database_folder": str(config.resolved_database_folder),
        "selected_database_path": str(current_path),
        "spaces": spaces,
    }


def _current_config_payload(core: RecollectiumCore) -> dict[str, Any]:
    config = core.config
    return {
        "status": "ok",
        "surface": WEBUI_TITLE,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "warning": _security_warning(),
        },
        "config": deepcopy(config.effective_config),
        "safe_paths": _service_config_summary(config),
        "memory_spaces": _memory_space_payload(core),
    }


def _raw_config_file_path(core: RecollectiumCore) -> Path:
    return core.config.config_file_path


def _load_raw_config(core: RecollectiumCore) -> dict[str, Any]:
    path = _raw_config_file_path(core)
    if not path.exists():
        return {}
    return load_config_file(path)


def _write_raw_config(core: RecollectiumCore, raw: dict[str, Any]) -> None:
    path = _raw_config_file_path(core)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _remove_empty_config_parents(raw: dict[str, Any], key: str) -> None:
    parts = key.split(".")
    containers: list[tuple[dict[str, Any], str]] = []
    current: Any = raw
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        containers.append((current, part))
        current = current[part]
    if not isinstance(current, dict):
        return
    for container, part in reversed(containers):
        child = container.get(part)
        if isinstance(child, dict) and not child:
            container.pop(part, None)
        else:
            break


def _merged_config(raw: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(deepcopy(DEFAULTS), raw)
    _apply_explicit_null_overrides(merged, raw)
    _validate_config_value(merged)
    return merged


def _validate_optional_service_type(service_type: str) -> str:
    normalized = service_type.strip().lower()
    if normalized not in {"api", "mcp", "webui"}:
        raise ValidationError("service_type must be one of: api, mcp, webui")
    return normalized


def _service_status_payload(
    core: RecollectiumCore, service_type: str
) -> dict[str, Any]:
    service_type = _validate_optional_service_type(service_type)
    discovery = service_manager.discover_service(core.config, service_type)
    return {
        "status": "ok",
        "service_type": service_type,
        "running": discovery.get("status") == "running",
        "discovery": discovery,
        "can_control_self": service_type == WEBUI_SERVICE_TYPE,
        "security_warning": _security_warning(),
    }


def _service_list_payload(core: RecollectiumCore) -> dict[str, Any]:
    return {
        "status": "ok",
        "security_warning": _security_warning(),
        "services": [
            _service_status_payload(core, "api"),
            _service_status_payload(core, "mcp"),
            _service_status_payload(core, "webui"),
        ],
    }


def _guard_self_service_action(
    service_type: str, action: str, body: ServiceActionBody
) -> None:
    if service_type != WEBUI_SERVICE_TYPE:
        return
    if action in {"stop", "restart"} and not body.allow_self_stop:
        raise ValidationError(
            "Stopping or restarting the currently serving WebUI requires allow_self_stop=true"
        )
    if action == "restart":
        raise ValidationError(
            "Restarting the currently serving WebUI is not supported from within the WebUI process"
        )


def _start_service(
    core: RecollectiumCore, service_type: str, body: ServiceActionBody
) -> dict[str, Any]:
    service_type = _validate_optional_service_type(service_type)
    pid = service_manager.start_service(
        core.config,
        service_type,
        db_path=body.db_path,
        log_level=body.log_level,
    )
    return {
        "status": "started",
        "service_type": service_type,
        "pid": pid,
        "discovery": service_manager.discover_service(core.config, service_type),
    }


def _stop_service(
    core: RecollectiumCore, service_type: str, body: ServiceActionBody
) -> dict[str, Any]:
    service_type = _validate_optional_service_type(service_type)
    _guard_self_service_action(service_type, "stop", body)
    stopped_pid = service_manager.stop_service(core.config, service_type)
    return {
        "status": "stopped" if stopped_pid is not None else "not_running",
        "service_type": service_type,
        "pid": stopped_pid,
        "discovery": service_manager.discover_service(core.config, service_type),
    }


def _restart_service(
    core: RecollectiumCore, service_type: str, body: ServiceActionBody
) -> dict[str, Any]:
    service_type = _validate_optional_service_type(service_type)
    _guard_self_service_action(service_type, "restart", body)
    if service_type == WEBUI_SERVICE_TYPE:
        raise ValidationError(
            "Restarting the currently serving WebUI is not supported from within the WebUI process"
        )
    stopped_pid = service_manager.stop_service(core.config, service_type)
    started_pid = service_manager.start_service(
        core.config,
        service_type,
        db_path=body.db_path,
        log_level=body.log_level,
    )
    return {
        "status": "restarted",
        "service_type": service_type,
        "stopped_pid": stopped_pid,
        "pid": started_pid,
        "discovery": service_manager.discover_service(core.config, service_type),
    }


def _workspace_inventory(
    core: RecollectiumCore,
    *,
    include_archived: bool,
    include_aliases: bool,
    include_alias_records: bool,
    memory_space_key: str | None,
) -> list[dict[str, Any]]:
    workspaces = core.list_workspaces(
        include_archived=include_archived,
        include_aliases=include_aliases,
        include_alias_records=include_alias_records,
        memory_space_key=memory_space_key,
    )
    return [project_workspace_list_item(item, None) for item in workspaces]  # type: ignore[arg-type]


def _workspace_aliases(
    core: RecollectiumCore, canonical_uid: str | None, memory_space_key: str | None
) -> list[dict[str, Any]]:
    return [
        project_workspace_alias(alias, None)
        for alias in core.list_workspace_aliases(
            canonical_uid=canonical_uid, memory_space_key=memory_space_key
        )
    ]


def _webui_urls_from_state(app: FastAPI) -> dict[str, str]:
    return _webui_urls(app.state.webui_host, app.state.webui_port)


def webui_capabilities_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "ok",
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "recommended_bind": WEBUI_DEFAULT_HOST,
            "warning": _security_warning(),
        },
        "capabilities": [
            "health",
            "status",
            "capabilities",
            "static-ui",
            "webui.context",
            "webui.memories",
            "webui.memory-spaces",
            "webui.workspaces",
            "webui.config",
            "webui.services",
            "webui.embedding",
            "webui.dev",
            "webui.graph",
            "webui.diagnostics",
            "webui.logs",
        ],
        "endpoints": urls,
        "ui_assets": ["/", "/assets/app.js", "/assets/styles.css"],
    }


def webui_health_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "ok",
        "ready": True,
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "warning": _security_warning(),
        },
        "endpoints": urls,
    }


def webui_status_payload(host: str, port: int) -> dict[str, Any]:
    urls = _webui_urls(host, port)
    return {
        "status": "running",
        "surface": WEBUI_TITLE,
        "service_type": WEBUI_SERVICE_TYPE,
        "version": __version__,
        "webui_version": WEBUI_VERSION,
        "local_first": WEBUI_LOCAL_FIRST,
        "security": {
            "authentication": WEBUI_AUTHENTICATION,
            "tls": WEBUI_TLS,
            "recommended_bind": WEBUI_DEFAULT_HOST,
            "warning": _security_warning(),
        },
        "endpoints": urls,
        "capabilities": [
            "health",
            "status",
            "capabilities",
            "static-ui",
            "webui.context",
            "webui.memories",
            "webui.memory-spaces",
            "webui.workspaces",
            "webui.config",
            "webui.services",
            "webui.embedding",
            "webui.dev",
            "webui.graph",
            "webui.diagnostics",
            "webui.logs",
        ],
        "ui_assets": ["/", "/assets/app.js", "/assets/styles.css"],
    }


def create_app(
    core: RecollectiumCore | None = None,
    *,
    host: str = WEBUI_DEFAULT_HOST,
    port: int = WEBUI_DEFAULT_PORT,
) -> FastAPI:
    core = core or RecollectiumCore()
    app = FastAPI(
        title=WEBUI_TITLE,
        version=WEBUI_VERSION,
        description=(
            "Local-first Recollectium WebUI with direct memory, workspace, config, "
            "and service-control operations. In v1 it has no authentication and is "
            "intended for localhost use only."
        ),
    )
    app.state.webui_host = host
    app.state.webui_port = port
    app.state.core = core

    if WEBUI_STATIC_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(WEBUI_STATIC_DIR)),
            name="webui-assets",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code in {HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED}:
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content={
                    "error": {
                        "code": "unsupported_operation",
                        "message": "unsupported operation",
                        "details": {},
                    }
                },
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail),
                    "details": {},
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {"fields": []}
        for error in exc.errors():
            location = error.get("loc", ())
            field = ".".join(
                str(part) for part in location if part not in {"body", "query", "path"}
            )
            details["fields"].append(
                {
                    "field": field or "request",
                    "message": error.get("msg", "invalid value"),
                }
            )
        message = (
            details["fields"][0]["message"]
            if details["fields"]
            else "request validation failed"
        )
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={
                "error": {
                    "code": "validation_error",
                    "message": message,
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_boundary_exception(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        if isinstance(exc, ValidationError):
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content={
                    "error": {
                        "code": "validation_error",
                        "message": str(exc),
                        "details": {},
                    }
                },
            )
        if isinstance(exc, NotFoundError):
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content={
                    "error": {"code": "not_found", "message": str(exc), "details": {}}
                },
            )
        if isinstance(exc, ServiceConflictError):
            return JSONResponse(
                status_code=HTTPStatus.CONFLICT,
                content={
                    "error": {
                        "code": "service_conflict",
                        "message": str(exc),
                        "details": {},
                    }
                },
            )
        if isinstance(exc, ServiceError):
            return JSONResponse(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                content={
                    "error": {
                        "code": "service_error",
                        "message": str(exc),
                        "details": {},
                    }
                },
            )
        _log.exception("unhandled webui error")
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "internal error",
                    "details": {},
                }
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse(
            (WEBUI_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        )

    @app.get(f"{SERVICE_API_PREFIX}/health")
    def health() -> JSONResponse:
        return JSONResponse(webui_health_payload(host, port))

    @app.get(f"{SERVICE_API_PREFIX}/status")
    def status() -> JSONResponse:
        return JSONResponse(webui_status_payload(host, port))

    @app.get(f"{SERVICE_API_PREFIX}/version")
    def version() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "surface": WEBUI_TITLE,
                "service_type": WEBUI_SERVICE_TYPE,
                "version": __version__,
                "webui_version": WEBUI_VERSION,
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/capabilities")
    def capabilities() -> JSONResponse:
        payload = webui_capabilities_payload(host, port)
        payload["service_contract"] = capabilities_payload(
            default_memory_space_key=core.config.default_memory_space_key
        )["data"]
        return JSONResponse(payload)

    @app.get(f"{SERVICE_API_PREFIX}/webui/context")
    def context() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "surface": WEBUI_TITLE,
                "security": {
                    "warning": _security_warning(),
                    "authentication": WEBUI_AUTHENTICATION,
                    "tls": WEBUI_TLS,
                },
                "capabilities": webui_capabilities_payload(host, port)["capabilities"],
                "config": _current_config_payload(core),
                "services": _service_list_payload(core),
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/memory-spaces")
    def list_memory_spaces(memory_space_key: str | None = None) -> JSONResponse:
        return JSONResponse(_memory_space_payload(core, memory_space_key))

    @app.get(f"{SERVICE_API_PREFIX}/webui/memory-spaces/{{memory_space_key}}")
    def get_memory_space(memory_space_key: str) -> JSONResponse:
        return JSONResponse(_memory_space_payload(core, memory_space_key))

    @app.get(f"{SERVICE_API_PREFIX}/webui/config")
    def get_config() -> JSONResponse:
        return JSONResponse(_current_config_payload(core))

    @app.get(f"{SERVICE_API_PREFIX}/webui/config/{{key:path}}")
    def get_config_key(key: str) -> JSONResponse:
        raw = _load_raw_config(core)
        merged = _merged_config(raw)
        value = get_config_value(merged, key)
        return JSONResponse({"status": "ok", "key": key, "value": value})

    @app.put(f"{SERVICE_API_PREFIX}/webui/config/{{key:path}}")
    def set_config_key(key: str, body: ConfigSetBody) -> JSONResponse:
        raw = _load_raw_config(core)
        candidate = deepcopy(raw)
        set_config_value(candidate, key, body.value)
        merged = _merged_config(candidate)
        _write_raw_config(core, candidate)
        return JSONResponse(
            {
                "status": "updated",
                "key": key,
                "value": body.value,
                "restart_required": True,
                "config": merged,
            }
        )

    @app.delete(f"{SERVICE_API_PREFIX}/webui/config/{{key:path}}")
    def unset_config_key(key: str) -> JSONResponse:
        raw = _load_raw_config(core)
        try:
            removed = get_config_value(raw, key)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc
        unset_config_value(raw, key)
        _remove_empty_config_parents(raw, key)
        merged = _merged_config(raw)
        _write_raw_config(core, raw)
        return JSONResponse(
            {
                "status": "removed",
                "key": key,
                "value": removed,
                "restart_required": True,
                "config": merged,
            }
        )

    @app.post(f"{SERVICE_API_PREFIX}/webui/config/validate")
    def validate_config(body: ConfigValidateBody) -> JSONResponse:
        raw = body.config if body.config is not None else _load_raw_config(core)
        merged = _merged_config(raw)
        return JSONResponse({"status": "ok", "valid": True, "config": merged})

    @app.get(f"{SERVICE_API_PREFIX}/webui/memories")
    def list_memories(
        space: str | None = None,
        type: str | None = None,
        status: str | None = None,
        workspace_uid: str | None = None,
        include_archived: bool = False,
        limit: int | None = None,
        memory_space_key: str | None = None,
    ) -> JSONResponse:
        memories = core.list_memories(
            space=space,
            type=type,
            status=status,
            workspace_uid=workspace_uid,
            include_archived=include_archived,
            limit=limit,
            memory_space_key=memory_space_key,
        )
        return JSONResponse(
            {
                "status": "ok",
                "count": len(memories),
                "memory_space_key": memory_space_key
                or core.config.default_memory_space_key,
                "memories": serialize_memories(memories),
            }
        )

    @app.post(f"{SERVICE_API_PREFIX}/webui/memories/search")
    def search_memories(body: MemorySearchBody) -> JSONResponse:
        scope = body.scope.strip().lower()
        if scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValidationError("scope must be one of: user, workspace")
        if scope == SPACE_WORKSPACE and not body.workspace_uid:
            raise ValidationError("workspace_uid is required for workspace searches")
        results = (
            core.search_workspace_memories(
                query=body.query,
                workspace_uid=body.workspace_uid,
                limit=body.limit,
                include_archived=body.include_archived,
                type=body.type,
                protected_minimum=body.protected_minimum,  # type: ignore[arg-type]
                match_threshold=body.match_threshold,  # type: ignore[arg-type]
                memory_space_key=body.memory_space_key,
            )
            if scope == SPACE_WORKSPACE
            else core.search_user_memories(
                query=body.query,
                limit=body.limit,
                include_archived=body.include_archived,
                type=body.type,
                protected_minimum=body.protected_minimum,  # type: ignore[arg-type]
                match_threshold=body.match_threshold,  # type: ignore[arg-type]
                memory_space_key=body.memory_space_key,
            )
        )
        return JSONResponse(
            {
                "status": "ok",
                "scope": scope,
                "count": len(results),
                "memory_space_key": body.memory_space_key
                or core.config.default_memory_space_key,
                "results": serialize_search_results(results),
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/memories/{{memory_id}}")
    def get_memory(memory_id: str, memory_space_key: str | None = None) -> JSONResponse:
        memory = core.get_memory(memory_id, memory_space_key=memory_space_key)
        return JSONResponse({"status": "ok", "memory": serialize_memory(memory)})

    @app.post(f"{SERVICE_API_PREFIX}/webui/memories")
    def add_memory(body: MemoryAddBody) -> JSONResponse:
        memory = core.add_memory(
            space=body.space,
            type=body.type,
            content=body.content,
            workspace_uid=body.workspace_uid,
            metadata=body.metadata,
            source=body.source,
            confidence=body.confidence,
            sensitivity=body.sensitivity,
            memory_space_key=body.memory_space_key,
        )
        return JSONResponse({"status": "created", "memory": serialize_memory(memory)})

    @app.patch(f"{SERVICE_API_PREFIX}/webui/memories/{{memory_id}}")
    def update_memory(memory_id: str, body: MemoryUpdateBody) -> JSONResponse:
        memory = core.update_memory(
            memory_id,
            content=body.content,
            type=body.type,
            metadata=body.metadata,
            source=body.source,
            confidence=body.confidence,
            sensitivity=body.sensitivity,
            memory_space_key=body.memory_space_key,
        )
        return JSONResponse({"status": "updated", "memory": serialize_memory(memory)})

    @app.post(f"{SERVICE_API_PREFIX}/webui/memories/{{memory_id}}/archive")
    def archive_memory(
        memory_id: str, memory_space_key: str | None = None
    ) -> JSONResponse:
        memory = core.archive_memory(memory_id, memory_space_key=memory_space_key)
        return JSONResponse({"status": "archived", "memory": serialize_memory(memory)})

    @app.get(f"{SERVICE_API_PREFIX}/webui/workspaces")
    def list_workspaces(
        include_archived: bool = False,
        include_aliases: bool = True,
        include_alias_records: bool = False,
        memory_space_key: str | None = None,
    ) -> JSONResponse:
        inventory = _workspace_inventory(
            core,
            include_archived=include_archived,
            include_aliases=include_aliases,
            include_alias_records=include_alias_records,
            memory_space_key=memory_space_key,
        )
        return JSONResponse(
            {
                "status": "ok",
                "count": len(inventory),
                "memory_space_key": memory_space_key
                or core.config.default_memory_space_key,
                "workspaces": inventory,
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/workspaces/{{workspace_uid}}/resolve")
    def resolve_workspace(
        workspace_uid: str, memory_space_key: str | None = None
    ) -> JSONResponse:
        payload = core.resolve_workspace(
            workspace_uid, memory_space_key=memory_space_key
        )
        return JSONResponse(project_workspace_resolve(payload, None))

    @app.post(f"{SERVICE_API_PREFIX}/webui/workspaces/{{workspace_uid}}/rename")
    def rename_workspace(workspace_uid: str, body: WorkspaceRenameBody) -> JSONResponse:
        payload = core.rename_workspace(
            workspace_uid,
            body.new_uid,
            memory_space_key=body.memory_space_key,
        )
        return JSONResponse(project_workspace_rename(payload, None))

    @app.get(f"{SERVICE_API_PREFIX}/webui/workspaces/{{workspace_uid}}/aliases")
    def list_workspace_aliases(
        workspace_uid: str, memory_space_key: str | None = None
    ) -> JSONResponse:
        payload = _workspace_aliases(core, workspace_uid, memory_space_key)
        return JSONResponse({"status": "ok", "aliases": payload, "count": len(payload)})

    @app.post(f"{SERVICE_API_PREFIX}/webui/workspaces/{{workspace_uid}}/aliases")
    def add_workspace_alias(
        workspace_uid: str, body: WorkspaceAliasBody
    ) -> JSONResponse:
        payload = core.add_workspace_alias(
            workspace_uid,
            body.alias_uid,
            migrate_existing=body.migrate_existing,
            memory_space_key=body.memory_space_key,
        )
        return JSONResponse(project_workspace_alias_add(payload, None))

    @app.delete(f"{SERVICE_API_PREFIX}/webui/workspaces/aliases/{{alias_uid}}")
    def remove_workspace_alias(
        alias_uid: str, memory_space_key: str | None = None
    ) -> JSONResponse:
        payload = core.remove_workspace_alias(
            alias_uid, memory_space_key=memory_space_key
        )
        return JSONResponse(project_workspace_alias_remove(payload, None))

    @app.get(f"{SERVICE_API_PREFIX}/webui/services")
    def list_services() -> JSONResponse:
        return JSONResponse(_service_list_payload(core))

    @app.get(f"{SERVICE_API_PREFIX}/webui/services/{{service_type}}")
    def get_service(service_type: str) -> JSONResponse:
        return JSONResponse(_service_status_payload(core, service_type))

    @app.get(f"{SERVICE_API_PREFIX}/webui/services/{{service_type}}/discover")
    def discover_service(service_type: str) -> JSONResponse:
        service_type = _validate_optional_service_type(service_type)
        return JSONResponse(
            {
                "status": "ok",
                "service_type": service_type,
                "discovery": service_manager.discover_service(
                    core.config, service_type
                ),
                "security_warning": _security_warning(),
            }
        )

    @app.post(f"{SERVICE_API_PREFIX}/webui/services/{{service_type}}/start")
    def start_service(service_type: str, body: ServiceActionBody) -> JSONResponse:
        return JSONResponse(_start_service(core, service_type, body))

    @app.post(f"{SERVICE_API_PREFIX}/webui/services/{{service_type}}/stop")
    def stop_service(
        service_type: str, body: ServiceActionBody, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        service_type = _validate_optional_service_type(service_type)
        if service_type == WEBUI_SERVICE_TYPE and not body.allow_self_stop:
            raise ValidationError(
                "Stopping the currently serving WebUI requires allow_self_stop=true"
            )
        if service_type == WEBUI_SERVICE_TYPE and body.allow_self_stop:
            background_tasks.add_task(
                service_manager.stop_service, core.config, service_type
            )
            return JSONResponse(
                {
                    "status": "accepted",
                    "service_type": service_type,
                    "message": "WebUI shutdown scheduled after this response.",
                    "security_warning": _security_warning(),
                }
            )
        return JSONResponse(_stop_service(core, service_type, body))

    @app.post(f"{SERVICE_API_PREFIX}/webui/services/{{service_type}}/restart")
    def restart_service(service_type: str, body: ServiceActionBody) -> JSONResponse:
        return JSONResponse(_restart_service(core, service_type, body))

    @app.get(f"{SERVICE_API_PREFIX}/webui/embedding/status")
    def embedding_status(memory_space_key: str | None = None) -> JSONResponse:
        return JSONResponse(_embedding_status_payload(core, memory_space_key))

    @app.post(f"{SERVICE_API_PREFIX}/webui/embedding/refresh")
    def refresh_embeddings(body: EmbeddingRefreshBody) -> JSONResponse:
        payload = core.refresh_stale_embeddings(
            space=body.space,
            workspace_uid=body.workspace_uid,
            include_archived=body.include_archived,
            memory_space_key=body.memory_space_key,
        )
        return JSONResponse(
            {
                "status": "ok",
                "operation": "refresh_stale_embeddings",
                "memory_space_key": body.memory_space_key
                or core.config.default_memory_space_key,
                "result": payload,
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/embedding/jobs")
    def list_embedding_jobs(
        state: str | None = None,
        limit: int | None = None,
        memory_space_key: str | None = None,
    ) -> JSONResponse:
        jobs = core.list_embedding_jobs(
            state=state, limit=limit, memory_space_key=memory_space_key
        )
        return JSONResponse(
            {
                "status": "ok",
                "count": len(jobs),
                "memory_space_key": memory_space_key
                or core.config.default_memory_space_key,
                "jobs": jobs,
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/embedding/jobs/{{job_id}}")
    def get_embedding_job(
        job_id: str, memory_space_key: str | None = None
    ) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "job": core.get_embedding_job(
                    job_id, memory_space_key=memory_space_key
                ),
            }
        )

    @app.delete(f"{SERVICE_API_PREFIX}/webui/embedding/jobs")
    def clear_embedding_jobs(body: EmbeddingJobsClearBody) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "result": core.clear_embedding_jobs(
                    states=body.states, memory_space_key=body.memory_space_key
                ),
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/dev/status")
    def dev_status() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "seeded_database": _dev_seed_status_payload(core),
                "embedding": _embedding_status_payload(core, None),
                "command_hints": _dev_command_hints(core),
            }
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/dev/seeding/status")
    def dev_seed_status() -> JSONResponse:
        return JSONResponse(_dev_seed_status_payload(core))

    @app.post(f"{SERVICE_API_PREFIX}/webui/dev/seeding/init")
    def dev_seed_init() -> JSONResponse:
        return JSONResponse(_dev_seed_init_payload(core))

    @app.post(f"{SERVICE_API_PREFIX}/webui/dev/seeding/reset")
    def dev_seed_reset() -> JSONResponse:
        return JSONResponse(_dev_seed_reset_payload(core))

    @app.post(f"{SERVICE_API_PREFIX}/webui/dev/eval")
    def dev_eval(_body: DevEvalBody) -> JSONResponse:
        return JSONResponse(_dev_eval_payload(core))

    @app.post(f"{SERVICE_API_PREFIX}/webui/dev/optimize-threshold")
    def dev_optimize_threshold(body: ThresholdOptimizeBody) -> JSONResponse:
        return JSONResponse(
            _threshold_optimizer_payload(
                core,
                start=body.start,
                end=body.end,
                step=body.step,
                beta=body.beta,
                output_format=body.output_format,
                output_path=body.output_path,
                write_config=body.write_config,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/graph")
    def graph(
        memory_space_key: str | None = None,
        space: str | None = None,
        workspace_uid: str | None = None,
        type: str | None = None,
        status: str | None = None,
        include_archived: bool = False,
        limit: int = 40,
    ) -> JSONResponse:
        return JSONResponse(
            _graph_payload(
                core,
                memory_space_key=memory_space_key,
                space=space,
                workspace_uid=workspace_uid,
                type=type,
                status=status,
                include_archived=include_archived,
                limit=limit,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/webui/logs")
    def logs(tail_lines: int = 80) -> JSONResponse:
        return JSONResponse(_log_summary_payload(core, tail_lines=tail_lines))

    @app.get(f"{SERVICE_API_PREFIX}/webui/diagnostics")
    def diagnostics(
        memory_space_key: str | None = None, tail_lines: int = 80
    ) -> JSONResponse:
        config = _merged_config(_load_raw_config(core))
        memory_spaces = _memory_space_payload(core, memory_space_key)
        embedding = _embedding_status_payload(core, memory_space_key)
        log_summary = _log_summary_payload(core, tail_lines=tail_lines)
        db_status = core.database_status(memory_space_key=memory_space_key)
        return JSONResponse(
            {
                "status": "ok",
                "surface": WEBUI_TITLE,
                "version": __version__,
                "webui_version": WEBUI_VERSION,
                "security": {
                    "warning": _security_warning(),
                    "authentication": WEBUI_AUTHENTICATION,
                    "tls": WEBUI_TLS,
                },
                "config_validation": {
                    "status": "ok",
                    "valid": True,
                    "config": config,
                },
                "safe_paths": _service_config_summary(core.config),
                "services": _service_list_payload(core),
                "memory_spaces": memory_spaces,
                "database_status": db_status,
                "embedding_status": embedding,
                "model_state": _model_state_summary(core),
                "logs": log_summary,
                "command_hints": _dev_command_hints(core),
            }
        )

    return app


def run_webui(
    *,
    host: str | None = None,
    port: int | None = None,
    config_path: str | Path | None = None,
    log_level: str | None = None,
    foreground_stderr_logs: bool = False,
) -> None:
    import uvicorn

    cfg = RecollectiumConfig(config_path, log_level=log_level)
    effective_webui = cfg.effective_config.get("webui", {})
    resolved_host = str(host or effective_webui.get("host", WEBUI_DEFAULT_HOST))
    resolved_port = int(port or effective_webui.get("port", WEBUI_DEFAULT_PORT))
    if foreground_stderr_logs:
        effective_level = str(cfg.effective_config["logging"]["level"])
        setup_logging(
            cfg,
            stderr_level=effective_level,
            library_log_level=effective_level,
        )

    from recollectium.core import RecollectiumCore

    core = RecollectiumCore(config_path=config_path, log_level=log_level)
    app = create_app(core=core, host=resolved_host, port=resolved_port)
    uvicorn.run(
        app,
        host=resolved_host,
        port=resolved_port,
        log_level=str(cfg.effective_config["logging"]["level"]),
        log_config=None,
    )
