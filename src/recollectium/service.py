"""FastAPI local HTTP JSON service for Recollectium Core."""

from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from recollectium.config import RESPONSE_VERBOSITY_COMPACT
from recollectium.core import RecollectiumCore
from recollectium.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
    EmbeddingReadinessTimeoutError,
    NotFoundError,
    ReembeddingFailedError,
    ReembeddingInProgressError,
    ValidationError,
)
from recollectium.mcp_server import create_mcp_server
from recollectium.representations import (
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_GET,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    ResponseVerbosity,
    project_payload,
    validate_response_verbosity,
)
from recollectium.service_contract import (
    SERVICE_API_PREFIX,
    SERVICE_DEFAULT_HOST,
    SERVICE_DEFAULT_PORT,
    capabilities_payload,
    error_payload,
    health_payload,
    serialize_embedding_job,
    serialize_embedding_jobs,
    serialize_embedding_operation_result,
    serialize_embedding_status,
    serialize_memories,
    serialize_memory,
    serialize_search_results,
    success_payload,
    version_payload,
)

import logging

_log = logging.getLogger(__name__)


_BOUNDARY_ERROR_MAP: tuple[tuple[type[Exception], HTTPStatus, str], ...] = (
    (ValidationError, HTTPStatus.BAD_REQUEST, "validation_error"),
    (NotFoundError, HTTPStatus.NOT_FOUND, "not_found"),
    (
        EmbeddingReadinessTimeoutError,
        HTTPStatus.SERVICE_UNAVAILABLE,
        "embedding_readiness_timeout",
    ),
    (
        EmbeddingProviderUnavailableError,
        HTTPStatus.SERVICE_UNAVAILABLE,
        "embedding_provider_unavailable",
    ),
    (
        EmbeddingModelUnavailableError,
        HTTPStatus.SERVICE_UNAVAILABLE,
        "embedding_model_unavailable",
    ),
    (
        EmbeddingDimensionMismatchError,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "embedding_profile_mismatch",
    ),
    (
        EmbeddingGenerationError,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "embedding_generation_failed",
    ),
    (
        ReembeddingInProgressError,
        HTTPStatus.CONFLICT,
        "reembedding_in_progress",
    ),
    (
        ReembeddingFailedError,
        HTTPStatus.SERVICE_UNAVAILABLE,
        "reembedding_failed",
    ),
    (json.JSONDecodeError, HTTPStatus.BAD_REQUEST, "invalid_json"),
)


class SearchUserRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=10, ge=1)
    include_archived: bool = False


class SearchWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    workspace_uid: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1)
    include_archived: bool = False


class AddMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    space: str = Field(min_length=1)
    type: str = Field(min_length=1)
    content: str = Field(min_length=1)
    workspace_uid: str | None = None
    metadata: dict[str, object] | None = None
    source: str | None = None
    confidence: float | None = None
    sensitivity: str | None = None


class UpdateMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str | None = None
    content: str | None = None
    metadata: dict[str, object] | None = None
    source: str | None = None
    confidence: float | None = None
    sensitivity: str | None = None


class RenameWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    new_uid: str = Field(min_length=1)


class AddWorkspaceAliasRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alias_uid: str = Field(min_length=1)
    migrate_existing: bool = False


class EmbeddingRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    space: str | None = Field(default=None, min_length=1)
    workspace_uid: str | None = Field(default=None, min_length=1)
    include_archived: bool = False


class ClearEmbeddingJobsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    states: list[str] | None = None


def _map_boundary_error(exc: Exception) -> tuple[HTTPStatus, dict[str, Any]]:
    for error_type, status, code in _BOUNDARY_ERROR_MAP:
        if isinstance(exc, error_type):
            if isinstance(exc, json.JSONDecodeError):
                return status, error_payload(code, f"invalid JSON: {exc.msg}")
            if isinstance(exc, ReembeddingInProgressError | ReembeddingFailedError):
                return (
                    status,
                    error_payload(
                        code,
                        str(exc),
                        details={
                            "job_id": exc.job_id,
                            "status_path": exc.status_path,
                        },
                    ),
                )
            return status, error_payload(code, str(exc))
    return (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        error_payload("internal_error", "internal server error"),
    )


def _json_response(status: HTTPStatus, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=int(status), content=payload)


def _parse_optional_bool(raw: str | None, *, field_name: str) -> bool | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValidationError(f"{field_name} must be true or false")


def _parse_optional_positive_int(raw: str | None, *, field_name: str) -> int | None:
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a positive integer") from exc
    if value < 1:
        raise ValidationError(f"{field_name} must be a positive integer")
    return value


def _resolve_verbosity(
    query_value: str | None,
    header_value: str | None,
    config_default: str | None,
) -> str:
    """Resolve effective verbosity with precedence: query > header > config.

    Returns a resolved verbosity string or the default compact value.
    """
    selected = query_value or header_value or config_default or RESPONSE_VERBOSITY_COMPACT
    return validate_response_verbosity(selected).value


def create_app(core: RecollectiumCore) -> FastAPI:
    app = FastAPI(
        title="Recollectium Core Local Service API",
        version="1",
        description=(
            "Local-first HTTP JSON service contract for Recollectium Core. In v1, "
            "the service is localhost-first, has no authentication, and is not "
            "hardened as a public network service. Do not expose it publicly. "
            "Split-machine deployments should use private networking and external access controls."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        _log.warning(
            "HTTP exception: %s",
            str(exc.detail),
            extra={
                "event": "service.http_exception",
                "context": {"status_code": exc.status_code, "detail": str(exc.detail)},
            },
        )
        if exc.status_code in {HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED}:
            return _json_response(
                HTTPStatus.NOT_FOUND,
                error_payload("unsupported_operation", "unsupported operation"),
            )
        return _json_response(
            HTTPStatus(exc.status_code),
            error_payload("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        _log.warning(
            "Request validation failed",
            extra={
                "event": "service.request_validation_error",
                "context": {"error_count": len(list(exc.errors()))},
            },
        )
        for error in exc.errors():
            if error.get("type") == "json_invalid":
                return _json_response(
                    HTTPStatus.BAD_REQUEST,
                    error_payload("invalid_json", "invalid JSON"),
                )
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            error_payload("validation_error", "request validation failed"),
        )

    @app.exception_handler(Exception)
    async def handle_boundary_exception(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        status, payload = _map_boundary_error(exc)
        _log.error(
            "HTTP request failed: %s",
            str(exc),
            extra={
                "event": "service.request_failed",
                "context": {
                    "error_type": type(exc).__name__,
                    "http_status": int(status),
                    "error_code": payload.get("error", "unknown"),
                },
            },
        )
        return _json_response(status, payload)

    @app.get(f"{SERVICE_API_PREFIX}/health", tags=["service"])
    def health(
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        return health_payload()

    @app.get(f"{SERVICE_API_PREFIX}/version", tags=["service"])
    def version(
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        return version_payload()

    @app.get(f"{SERVICE_API_PREFIX}/capabilities", tags=["service"])
    def capabilities(
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        payload = capabilities_payload()
        if resolved == ResponseVerbosity.VERBOSE.value:
            payload["data"]["response_verbosity"] = resolved
        return payload

    @app.post(f"{SERVICE_API_PREFIX}/memories/search_user", tags=["memories"])
    def search_user(
        body: SearchUserRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        results = core.search_user_memories(
            query=body.query,
            limit=body.limit,
            include_archived=body.include_archived,
            type=body.type,
        )
        _log.info(
            "search_user_memories completed",
            extra={
                "event": "service.search_user_completed",
                "context": {
                    "query_len": len(body.query),
                    "limit": body.limit,
                    "result_count": len(results),
                },
            },
        )
        return success_payload(
            serialize_search_results(
                results,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_SEARCH_USER,
            )
        )

    @app.post(f"{SERVICE_API_PREFIX}/memories/search_workspace", tags=["memories"])
    def search_workspace(
        body: SearchWorkspaceRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        results = core.search_workspace_memories(
            query=body.query,
            workspace_uid=body.workspace_uid,
            limit=body.limit,
            include_archived=body.include_archived,
            type=body.type,
        )
        _log.info(
            "search_workspace_memories completed",
            extra={
                "event": "service.search_workspace_completed",
                "context": {
                    "query_len": len(body.query),
                    "workspace_uid": body.workspace_uid,
                    "limit": body.limit,
                    "result_count": len(results),
                },
            },
        )
        return success_payload(
            serialize_search_results(
                results,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_SEARCH_WORKSPACE,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/embedding/status", tags=["embedding"])
    def embedding_status(
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        status = core.active_embedding_status()
        _log.info(
            "embedding_status completed",
            extra={
                "event": "service.embedding_status_completed",
                "context": {"provider_status": status.get("provider_status")},
            },
        )
        return success_payload(
            serialize_embedding_status(
                status,
                verbosity=resolved,
                operation=OPERATION_EMBEDDING_STATUS,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/embedding/jobs", tags=["embedding"])
    def list_embedding_jobs(
        state: str | None = None,
        limit: str | None = None,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        jobs = core.list_embedding_jobs(
            state=state,
            limit=_parse_optional_positive_int(limit, field_name="limit"),
        )
        _log.info(
            "list_embedding_jobs completed",
            extra={
                "event": "service.list_embedding_jobs_completed",
                "context": {"state": state, "result_count": len(jobs)},
            },
        )
        return success_payload(
            serialize_embedding_jobs(
                jobs,
                verbosity=resolved,
                operation=OPERATION_EMBEDDING_JOBS_LIST,
            )
        )

    @app.post(f"{SERVICE_API_PREFIX}/embedding/refresh", tags=["embedding"])
    def refresh_embeddings(
        body: EmbeddingRefreshRequest | None = None,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        request = body or EmbeddingRefreshRequest()
        result = core.refresh_stale_embeddings(
            space=request.space,
            workspace_uid=request.workspace_uid,
            include_archived=request.include_archived,
        )
        _log.info(
            "refresh_embeddings completed",
            extra={
                "event": "service.refresh_embeddings_completed",
                "context": {
                    "refreshed": result.get("refreshed"),
                    "stale_count": result.get("stale_count"),
                },
            },
        )
        return success_payload(
            serialize_embedding_operation_result(
                result,
                verbosity=resolved,
                operation=OPERATION_EMBEDDING_REFRESH,
            )
        )

    @app.delete(f"{SERVICE_API_PREFIX}/embedding/jobs", tags=["embedding"])
    def clear_embedding_jobs(
        body: ClearEmbeddingJobsRequest | None = None,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.clear_embedding_jobs(
            states=body.states if body is not None else None
        )
        _log.info(
            "clear_embedding_jobs completed",
            extra={
                "event": "service.clear_embedding_jobs_completed",
                "context": {"deleted_count": result.get("deleted_count")},
            },
        )
        return success_payload(
            serialize_embedding_operation_result(
                result,
                verbosity=resolved,
                operation=OPERATION_EMBEDDING_JOBS_CLEAR,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/embedding/jobs/{{job_id}}", tags=["embedding"])
    def get_embedding_job(
        job_id: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        job = core.get_embedding_job(job_id)
        _log.info(
            "get_embedding_job completed",
            extra={
                "event": "service.get_embedding_job_completed",
                "context": {"job_id": job_id, "state": job.get("state")},
            },
        )
        return success_payload(
            serialize_embedding_job(
                job,
                verbosity=resolved,
                operation=OPERATION_EMBEDDING_JOBS_GET,
            )
        )

    @app.post(f"{SERVICE_API_PREFIX}/memories", tags=["memories"])
    def add_memory(
        body: AddMemoryRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        memory = core.add_memory(
            space=body.space,
            type=body.type,
            content=body.content,
            workspace_uid=body.workspace_uid,
            metadata=body.metadata,
            source=body.source,
            confidence=body.confidence,
            sensitivity=body.sensitivity,
        )
        _log.info(
            "add_memory completed",
            extra={
                "event": "service.add_memory_completed",
                "context": {
                    "memory_id": memory.id,
                    "space": body.space,
                    "type": body.type,
                    "workspace_uid": body.workspace_uid,
                },
            },
        )
        return success_payload(
            serialize_memory(
                memory,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_ADD,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/memories", tags=["memories"])
    def list_memories(
        space: str | None = None,
        type: str | None = None,
        status: str | None = None,
        workspace_uid: str | None = None,
        include_archived: str | None = None,
        limit: str | None = None,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        parsed_include_archived = _parse_optional_bool(
            include_archived,
            field_name="include_archived",
        )
        memories = core.list_memories(
            space=space,
            type=type,
            status=status,
            workspace_uid=workspace_uid,
            include_archived=parsed_include_archived
            if parsed_include_archived is not None
            else False,
            limit=_parse_optional_positive_int(limit, field_name="limit"),
        )
        _log.info(
            "list_memories completed",
            extra={
                "event": "service.list_memories_completed",
                "context": {
                    "space": space,
                    "type": type,
                    "status": status,
                    "workspace_uid": workspace_uid,
                    "result_count": len(memories),
                },
            },
        )
        return success_payload(
            serialize_memories(
                memories,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_LIST,
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/memories/{{memory_id}}", tags=["memories"])
    def get_memory(
        memory_id: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        memory = core.get_memory(memory_id)
        _log.info(
            "get_memory completed",
            extra={
                "event": "service.get_memory_completed",
                "context": {
                    "memory_id": memory_id,
                    "space": memory.space,
                    "type": memory.type,
                },
            },
        )
        return success_payload(
            serialize_memory(
                memory,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_GET,
            )
        )

    @app.patch(f"{SERVICE_API_PREFIX}/memories/{{memory_id}}", tags=["memories"])
    def update_memory(
        memory_id: str,
        body: UpdateMemoryRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        memory = core.update_memory(
            memory_id,
            content=body.content,
            type=body.type,
            metadata=body.metadata,
            source=body.source,
            confidence=body.confidence,
            sensitivity=body.sensitivity,
        )
        _log.info(
            "update_memory completed",
            extra={
                "event": "service.update_memory_completed",
                "context": {"memory_id": memory_id, "type": body.type},
            },
        )
        return success_payload(
            serialize_memory(
                memory,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_UPDATE,
            )
        )

    @app.post(
        f"{SERVICE_API_PREFIX}/memories/{{memory_id}}/archive",
        tags=["memories"],
    )
    def archive_memory(
        memory_id: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        memory = core.archive_memory(memory_id)
        _log.info(
            "archive_memory completed",
            extra={
                "event": "service.archive_memory_completed",
                "context": {"memory_id": memory_id},
            },
        )
        return success_payload(
            serialize_memory(
                memory,
                verbosity=resolved,
                operation=OPERATION_MEMORIES_ARCHIVE,
            )
        )

    # -- workspace endpoints -----------------------------------------------

    @app.get(f"{SERVICE_API_PREFIX}/workspaces", tags=["workspaces"])
    def list_workspaces(
        include_archived: str | None = None,
        include_aliases: str | None = None,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        parsed_include_archived = _parse_optional_bool(
            include_archived,
            field_name="include_archived",
        )
        parsed_include_aliases = _parse_optional_bool(
            include_aliases,
            field_name="include_aliases",
        )
        uids = core.list_workspaces(
            include_archived=parsed_include_archived
            if parsed_include_archived is not None
            else False,
            include_aliases=parsed_include_aliases
            if parsed_include_aliases is not None
            else False,
        )
        _log.info(
            "list_workspaces completed",
            extra={
                "event": "service.list_workspaces_completed",
                "context": {"result_count": len(uids)},
            },
        )
        return success_payload(
            project_payload(uids, verbosity=resolved, operation=OPERATION_WORKSPACES_LIST)
        )

    @app.get(f"{SERVICE_API_PREFIX}/workspaces/resolve", tags=["workspaces"])
    def resolve_workspace(
        uid: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.resolve_workspace(uid)
        _log.info(
            "resolve_workspace completed",
            extra={
                "event": "service.resolve_workspace_completed",
                "context": {"input_uid": uid},
            },
        )
        return success_payload(
            project_payload(result, verbosity=resolved, operation=OPERATION_WORKSPACES_RESOLVE)
        )

    @app.get(f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/aliases", tags=["workspaces"])
    def list_workspace_aliases(
        uid: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.list_workspace_aliases(canonical_uid=uid)
        _log.info(
            "list_workspace_aliases completed",
            extra={
                "event": "service.list_workspace_aliases_completed",
                "context": {"canonical_uid": uid},
            },
        )
        return success_payload(
            project_payload(result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_LIST)
        )

    @app.post(f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/aliases", tags=["workspaces"])
    def add_workspace_alias(
        uid: str,
        body: AddWorkspaceAliasRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.add_workspace_alias(
            canonical_uid=uid,
            alias_uid=body.alias_uid,
            migrate_existing=body.migrate_existing,
        )
        _log.info(
            "add_workspace_alias completed",
            extra={
                "event": "service.add_workspace_alias_completed",
                "context": {"canonical_uid": uid, "alias_uid": body.alias_uid},
            },
        )
        return success_payload(
            project_payload(result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_ADD)
        )

    @app.delete(
        f"{SERVICE_API_PREFIX}/workspaces/aliases/{{alias_uid}}", tags=["workspaces"]
    )
    def remove_workspace_alias(
        alias_uid: str,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.remove_workspace_alias(alias_uid)
        _log.info(
            "remove_workspace_alias completed",
            extra={
                "event": "service.remove_workspace_alias_completed",
                "context": {"alias_uid": alias_uid},
            },
        )
        return success_payload(
            project_payload(result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_REMOVE)
        )

    @app.post(
        f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/rename",
        tags=["workspaces"],
    )
    def rename_workspace(
        uid: str,
        body: RenameWorkspaceRequest,
        verbosity: str | None = Query(default=None),
        x_recollectium_verbosity: str | None = Header(default=None, alias="X-Recollectium-Verbosity"),
    ) -> dict[str, Any]:
        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.rename_workspace(old_uid=uid, new_uid=body.new_uid)
        _log.info(
            "rename_workspace completed",
            extra={
                "event": "service.rename_workspace_completed",
                "context": {
                    "old_uid": uid,
                    "new_uid": body.new_uid,
                    "memories_updated": result.get("memories_updated"),
                },
            },
        )
        return success_payload(
            project_payload(result, verbosity=resolved, operation=OPERATION_WORKSPACES_RENAME)
        )

    return app


def create_mcp_app(core: RecollectiumCore) -> FastAPI:
    mcp = create_mcp_server(core)
    app = FastAPI(
        title="Recollectium MCP Server",
        version="1",
        description="Local-first MCP server for Recollectium Core. In v1, this service has no authentication and is not hardened as a public network service.",
    )
    app.mount("/", mcp.sse_app())
    return app


def run_service(
    host: str = SERVICE_DEFAULT_HOST,
    port: int = SERVICE_DEFAULT_PORT,
    db_path: str | None = None,
    config_path: str | Path | None = None,
    service_type: str | None = None,
    log_level: str | None = None,
    cli_structured_errors: bool = False,
) -> None:
    import uvicorn

    core = RecollectiumCore(
        db_path=db_path, config_path=config_path, log_level=log_level
    )
    log_level = core.config.effective_config["logging"]["level"]

    # Block until the embedding model is ready before accepting connections.
    try:
        core._ensure_model_ready()
    except Exception as exc:
        if cli_structured_errors:
            from recollectium.errors import EmbeddingGenerationError

            raise EmbeddingGenerationError(f"model readiness failed: {exc}") from exc
        import sys

        print(f"recollectium serve: model readiness failed: {exc}", file=sys.stderr)
        print(
            "Check your internet connection and try 'recollectium init' again.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    if service_type == "mcp":
        app = create_mcp_app(core)
    else:
        app = create_app(core)

    uvicorn.run(app, host=host, port=port, log_level=log_level, log_config=None)
