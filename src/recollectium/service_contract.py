"""Local service contract metadata and JSON-ready payload helpers."""

from __future__ import annotations

from typing import Any

from recollectium import __version__
from recollectium.models import (
    ALL_MEMORY_TYPES,
    USER_MEMORY_TYPES,
    WORKSPACE_MEMORY_TYPES,
    Memory,
    SearchResult,
)
from recollectium.representations import (
    OPERATION_CAPABILITIES_READ,
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_HEALTH_READ,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_GET,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_VERSION_READ,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    project_payload,
)

SERVICE_API_VERSION = "1"
SERVICE_API_PREFIX = f"/v{SERVICE_API_VERSION}"
SERVICE_DEFAULT_HOST = "127.0.0.1"
SERVICE_DEFAULT_PORT = 8765

SERVICE_CAPABILITIES = (
    OPERATION_HEALTH_READ,
    OPERATION_VERSION_READ,
    OPERATION_CAPABILITIES_READ,
    OPERATION_MEMORIES_SEARCH_USER,
    OPERATION_MEMORIES_SEARCH_WORKSPACE,
    OPERATION_MEMORIES_ADD,
    OPERATION_MEMORIES_UPDATE,
    OPERATION_MEMORIES_ARCHIVE,
    OPERATION_MEMORIES_LIST,
    OPERATION_MEMORIES_GET,
    OPERATION_EMBEDDING_STATUS,
    OPERATION_EMBEDDING_JOBS_LIST,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_REFRESH,
    OPERATION_EMBEDDING_JOBS_CLEAR,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
)


def serialize_memory(
    memory: Memory, *, verbosity: str | None = None, operation: str | None = None
) -> dict[str, Any]:
    payload = memory.to_dict()
    if verbosity is None and operation is None:
        return payload
    return project_payload(payload, verbosity=verbosity, operation=operation)


def serialize_search_result(
    result: SearchResult, *, verbosity: str | None = None, operation: str | None = None
) -> dict[str, Any]:
    payload = result.to_dict()
    if verbosity is None and operation is None:
        return payload
    if operation is None:
        operation = OPERATION_MEMORIES_SEARCH_USER
    return project_payload(payload, verbosity=verbosity, operation=operation)


def serialize_memories(
    memories: list[Memory],
    *,
    verbosity: str | None = None,
    operation: str | None = None,
) -> list[dict[str, Any]]:
    return [
        serialize_memory(memory, verbosity=verbosity, operation=operation)
        for memory in memories
    ]


def serialize_search_results(
    results: list[SearchResult],
    *,
    verbosity: str | None = None,
    operation: str | None = None,
) -> list[dict[str, Any]]:
    return [
        serialize_search_result(result, verbosity=verbosity, operation=operation)
        for result in results
    ]


def serialize_embedding_status(
    status: dict[str, Any], *, verbosity: str | None = None, operation: str | None = None
) -> dict[str, Any]:
    if verbosity is None and operation is None:
        return status
    return project_payload(status, verbosity=verbosity, operation=operation)


def serialize_embedding_job(
    job: dict[str, Any], *, verbosity: str | None = None, operation: str | None = None
) -> dict[str, Any]:
    if verbosity is None and operation is None:
        return job
    return project_payload(job, verbosity=verbosity, operation=operation)


def serialize_embedding_jobs(
    jobs: list[dict[str, Any]],
    *,
    verbosity: str | None = None,
    operation: str | None = None,
) -> list[dict[str, Any]]:
    return [
        serialize_embedding_job(job, verbosity=verbosity, operation=operation)
        for job in jobs
    ]


def success_payload(data: Any) -> dict[str, Any]:
    return {"data": data}


def health_payload() -> dict[str, Any]:
    return success_payload({"status": "ok"})


def version_payload() -> dict[str, Any]:
    return success_payload(
        {
            "service_api_version": SERVICE_API_VERSION,
            "recollectium_version": __version__,
        }
    )


def capabilities_payload() -> dict[str, Any]:
    return success_payload(
        {
            "service_api_version": SERVICE_API_VERSION,
            "capabilities": list(SERVICE_CAPABILITIES),
            "memory_types": {
                "user": list(USER_MEMORY_TYPES),
                "workspace": list(WORKSPACE_MEMORY_TYPES),
                "all": list(ALL_MEMORY_TYPES),
            },
        }
    )


def error_payload(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }
