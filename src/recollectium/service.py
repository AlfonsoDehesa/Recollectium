"""FastAPI local HTTP JSON service for Recollectium Core."""

from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias, cast

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    model_validator,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

from recollectium.config import RESPONSE_VERBOSITY_COMPACT, RESPONSE_VERBOSITY_VERBOSE
from recollectium.core import RecollectiumCore
from recollectium.logging import setup_logging
from recollectium.retrieval import UNSET
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

from recollectium.models import (
    SPACE_USER,
    SPACE_WORKSPACE,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
)

import logging

_log = logging.getLogger(__name__)

_VERBOSITY_ENUM = ["compact", "verbose"]
_VERBOSITY_QUERY_DESCRIPTION = (
    "Optional response verbosity override. Use compact for token-sensitive "
    "minimal payloads or verbose for full detail. Query value takes precedence "
    "over X-Recollectium-Verbosity."
)
_VERBOSITY_HEADER_DESCRIPTION = (
    "Optional response verbosity override. Use compact for token-sensitive "
    "minimal payloads or verbose for full detail. Ignored when the verbosity "
    "query parameter is present."
)

ResponseVerbosityQuery = Annotated[
    str | None,
    Query(
        description=_VERBOSITY_QUERY_DESCRIPTION,
        json_schema_extra={"enum": _VERBOSITY_ENUM},
    ),
]
ResponseVerbosityHeader = Annotated[
    str | None,
    Header(
        alias="X-Recollectium-Verbosity",
        description=_VERBOSITY_HEADER_DESCRIPTION,
        json_schema_extra={"enum": _VERBOSITY_ENUM},
    ),
]
StrictBoolQuery: TypeAlias = Annotated[
    str | None,
    Query(
        pattern="^(true|false)$",
        description="Strict boolean query value. Accepted values are exactly true or false.",
    ),
]
PositiveIntQuery: TypeAlias = Annotated[
    str | None,
    Query(
        pattern="^[1-9][0-9]*$",
        description="Positive integer query value encoded as decimal digits.",
    ),
]
SpaceQuery: TypeAlias = Annotated[
    str | None,
    Query(
        description="Optional memory space filter.",
        json_schema_extra={"enum": [SPACE_USER, SPACE_WORKSPACE]},
    ),
]
StatusQuery: TypeAlias = Annotated[
    str | None,
    Query(
        description="Optional memory status filter.",
        json_schema_extra={"enum": [STATUS_ACTIVE, STATUS_ARCHIVED]},
    ),
]


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


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _reject_non_json_number(value: Any) -> Any:
    if isinstance(value, bool | str):
        raise ValueError("match_threshold must be a JSON number")
    return value


SearchProtectedMinimum: TypeAlias = Annotated[int, Field(ge=0, strict=True)]
SearchMatchThresholdNumber: TypeAlias = Annotated[
    float,
    Field(ge=0.0, le=1.0),
    BeforeValidator(_reject_non_json_number),
]
SearchMatchThreshold: TypeAlias = (
    SearchMatchThresholdNumber | Literal["model_recommended_default"] | None
)


class SearchUserRequest(StrictRequestModel):
    query: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=20, ge=1, strict=True)
    protected_minimum: SearchProtectedMinimum = Field(
        default_factory=lambda: cast(int, UNSET)
    )
    match_threshold: SearchMatchThreshold = Field(
        default_factory=lambda: cast(SearchMatchThreshold, UNSET)
    )
    include_archived: StrictBool = False


class SearchWorkspaceRequest(StrictRequestModel):
    query: str = Field(min_length=1)
    type: str | None = Field(default=None, min_length=1)
    workspace_uid: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, strict=True)
    protected_minimum: SearchProtectedMinimum = Field(
        default_factory=lambda: cast(int, UNSET)
    )
    match_threshold: SearchMatchThreshold = Field(
        default_factory=lambda: cast(SearchMatchThreshold, UNSET)
    )
    include_archived: StrictBool = False


class AddMemoryRequest(StrictRequestModel):
    space: Literal["user", "workspace"]
    type: str = Field(min_length=1)
    content: str = Field(min_length=1)
    workspace_uid: str | None = Field(default=None, min_length=1)
    metadata: dict[str, object] | None = None
    source: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, strict=True)
    sensitivity: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_workspace_uid_for_space(self) -> AddMemoryRequest:
        if self.space == SPACE_USER and self.workspace_uid is not None:
            raise ValueError("workspace_uid is only valid for workspace memories")
        if self.space == SPACE_WORKSPACE and self.workspace_uid is None:
            raise ValueError("workspace_uid is required for workspace memories")
        return self


class UpdateMemoryRequest(StrictRequestModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"minProperties": 1})

    type: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)
    metadata: dict[str, object] | None = None
    source: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, strict=True)
    sensitivity: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _require_update_field(self) -> UpdateMemoryRequest:
        if not self.model_fields_set:
            raise ValueError("at least one update field is required")
        return self


class RenameWorkspaceRequest(StrictRequestModel):
    new_uid: str = Field(min_length=1)


class AddWorkspaceAliasRequest(StrictRequestModel):
    alias_uid: str = Field(min_length=1)
    migrate_existing: StrictBool = False


class EmbeddingRefreshRequest(StrictRequestModel):
    space: Literal["user", "workspace"] | None = None
    workspace_uid: str | None = Field(default=None, min_length=1)
    include_archived: StrictBool = False


class ClearEmbeddingJobsRequest(StrictRequestModel):
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
    if raw == "true":
        return True
    if raw == "false":
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


def _parse_optional_choice(
    raw: str | None, *, field_name: str, choices: set[str]
) -> str | None:
    if raw is None:
        return None
    if raw not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValidationError(f"{field_name} must be one of: {allowed}")
    return raw


def _request_override_from_model(model: BaseModel, field_name: str) -> Any:
    if field_name in model.model_fields_set:
        return getattr(model, field_name)
    return UNSET


def _validation_error_response_schema() -> dict[str, Any]:
    return {
        "description": "Request validation failed.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/RecollectiumErrorEnvelope"},
                "example": error_payload(
                    "validation_error", "request validation failed"
                ),
            }
        },
    }


def _error_response_schema(description: str, code: str, message: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/RecollectiumErrorEnvelope"},
                "example": error_payload(code, message),
            }
        },
    }


_OPENAPI_SHARED_ERROR_RESPONSES = {
    "404": ("RecollectiumNotFound", "Requested resource was not found.", "not_found"),
    "409": (
        "RecollectiumConflict",
        "Request conflicts with current state.",
        "conflict",
    ),
    "500": ("RecollectiumInternalError", "Internal server error.", "internal_error"),
    "503": (
        "RecollectiumEmbeddingProviderUnavailable",
        "Embedding provider is temporarily unavailable.",
        "embedding_provider_unavailable",
    ),
}


def _customize_openapi_validation_responses(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas["RecollectiumErrorEnvelope"] = {
        "additionalProperties": False,
        "properties": {
            "error": {
                "additionalProperties": False,
                "properties": {
                    "code": {
                        "description": "Stable Recollectium error code.",
                        "type": "string",
                    },
                    "message": {
                        "description": "Human-readable error summary.",
                        "type": "string",
                    },
                    "details": {
                        "additionalProperties": True,
                        "description": "Optional machine-readable error details.",
                        "type": "object",
                    },
                },
                "required": ["code", "message", "details"],
                "type": "object",
            }
        },
        "required": ["error"],
        "title": "RecollectiumErrorEnvelope",
        "type": "object",
    }
    responses_component = components.setdefault("responses", {})
    for status, (name, description, code) in _OPENAPI_SHARED_ERROR_RESPONSES.items():
        responses_component[name] = _error_response_schema(
            description, code, description.rstrip(".").lower()
        )
    validation_response = _validation_error_response_schema()
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            responses = (
                operation.get("responses", {}) if isinstance(operation, dict) else {}
            )
            if isinstance(responses, dict) and "422" in responses:
                responses.pop("422", None)
                responses.setdefault("400", validation_response)
            if isinstance(responses, dict):
                for status, (
                    name,
                    _description,
                    _code,
                ) in _OPENAPI_SHARED_ERROR_RESPONSES.items():
                    responses.setdefault(
                        status, {"$ref": f"#/components/responses/{name}"}
                    )
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    app.openapi_schema = schema
    return schema


def _resolve_verbosity(
    query_value: str | None,
    header_value: str | None,
    config_default: str | None,
) -> str:
    """Resolve effective verbosity with precedence: query > header > config.

    Returns a resolved verbosity string or the default compact value.
    """
    selected = (
        query_value
        if query_value is not None
        else header_value
        if header_value is not None
        else config_default
        if config_default is not None
        else RESPONSE_VERBOSITY_COMPACT
    )
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
                    "error_code": payload.get("error", {}).get("code", "unknown"),
                },
            },
        )
        return _json_response(status, payload)

    @app.get(f"{SERVICE_API_PREFIX}/health", tags=["service"])
    def health(
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
    ) -> dict[str, Any]:
        _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        return health_payload()

    @app.get(f"{SERVICE_API_PREFIX}/version", tags=["service"])
    def version(
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
    ) -> dict[str, Any]:
        _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        return version_payload()

    @app.get(f"{SERVICE_API_PREFIX}/capabilities", tags=["service"])
    def capabilities(
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            protected_minimum=_request_override_from_model(body, "protected_minimum"),
            match_threshold=_request_override_from_model(body, "match_threshold"),
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            protected_minimum=_request_override_from_model(body, "protected_minimum"),
            match_threshold=_request_override_from_model(body, "match_threshold"),
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        state: Literal["pending", "in_progress", "completed", "failed"] | None = None,
        limit: PositiveIntQuery = None,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        space: SpaceQuery = None,
        type: str | None = None,
        status: StatusQuery = None,
        workspace_uid: str | None = None,
        include_archived: StrictBoolQuery = None,
        limit: PositiveIntQuery = None,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        parsed_space = _parse_optional_choice(
            space,
            field_name="space",
            choices={SPACE_USER, SPACE_WORKSPACE},
        )
        parsed_status = _parse_optional_choice(
            status,
            field_name="status",
            choices={STATUS_ACTIVE, STATUS_ARCHIVED},
        )
        memories = core.list_memories(
            space=parsed_space,
            type=type,
            status=parsed_status,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
        include_archived: StrictBoolQuery = None,
        include_aliases: StrictBoolQuery = None,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            include_alias_records=bool(parsed_include_aliases)
            and resolved == RESPONSE_VERBOSITY_VERBOSE,
        )
        _log.info(
            "list_workspaces completed",
            extra={
                "event": "service.list_workspaces_completed",
                "context": {"result_count": len(uids)},
            },
        )
        return success_payload(
            project_payload(
                uids, verbosity=resolved, operation=OPERATION_WORKSPACES_LIST
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/workspaces/resolve", tags=["workspaces"])
    def resolve_workspace(
        uid: str,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            project_payload(
                result, verbosity=resolved, operation=OPERATION_WORKSPACES_RESOLVE
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/aliases", tags=["workspaces"])
    def list_workspace_aliases(
        uid: str,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            project_payload(
                result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_LIST
            )
        )

    @app.get(f"{SERVICE_API_PREFIX}/workspaces/aliases", tags=["workspaces"])
    def list_all_workspace_aliases(
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
    ) -> dict[str, Any]:
        """List all workspace alias mappings."""

        resolved = _resolve_verbosity(
            verbosity,
            x_recollectium_verbosity,
            core.config.effective_config.get("response_verbosity"),
        )
        result = core.list_workspace_aliases()
        _log.info(
            "list_all_workspace_aliases completed",
            extra={
                "event": "service.list_all_workspace_aliases_completed",
                "context": {"result_count": len(result)},
            },
        )
        return success_payload(
            project_payload(
                result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_LIST
            )
        )

    @app.post(f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/aliases", tags=["workspaces"])
    def add_workspace_alias(
        uid: str,
        body: AddWorkspaceAliasRequest,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            project_payload(
                result, verbosity=resolved, operation=OPERATION_WORKSPACES_ALIASES_ADD
            )
        )

    @app.delete(
        f"{SERVICE_API_PREFIX}/workspaces/aliases/{{alias_uid}}", tags=["workspaces"]
    )
    def remove_workspace_alias(
        alias_uid: str,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            project_payload(
                result,
                verbosity=resolved,
                operation=OPERATION_WORKSPACES_ALIASES_REMOVE,
            )
        )

    @app.post(
        f"{SERVICE_API_PREFIX}/workspaces/{{uid}}/rename",
        tags=["workspaces"],
    )
    def rename_workspace(
        uid: str,
        body: RenameWorkspaceRequest,
        verbosity: ResponseVerbosityQuery = None,
        x_recollectium_verbosity: ResponseVerbosityHeader = None,
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
            project_payload(
                result, verbosity=resolved, operation=OPERATION_WORKSPACES_RENAME
            )
        )

    app.openapi = lambda: _customize_openapi_validation_responses(app)  # type: ignore[method-assign]

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
    foreground_stderr_logs: bool = False,
) -> None:
    import uvicorn

    core = RecollectiumCore(
        db_path=db_path, config_path=config_path, log_level=log_level
    )
    log_level = core.config.effective_config["logging"]["level"]
    if foreground_stderr_logs:
        setup_logging(
            core.config,
            stderr_level=log_level,
            library_log_level=log_level,
        )

    # Block until the embedding model is ready before accepting connections.
    try:
        core._ensure_model_ready()
    except Exception as exc:
        if cli_structured_errors:
            from recollectium.errors import EmbeddingGenerationError

            raise EmbeddingGenerationError(f"model readiness failed: {exc}") from exc
        import sys

        print(f"recollectium service: model readiness failed: {exc}", file=sys.stderr)
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
