"""FastAPI local WebUI for Recollectium Core."""

from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
import json
import logging
from pathlib import Path
from typing import Any

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
from recollectium.core import RecollectiumCore
from recollectium.errors import (
    NotFoundError,
    ServiceConflictError,
    ServiceError,
    ValidationError,
)
from recollectium.logging import setup_logging
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
