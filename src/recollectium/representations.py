"""Shared JSON-ready response projection helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from recollectium.config import (
    RESPONSE_VERBOSITY_COMPACT,
    RESPONSE_VERBOSITY_VERBOSE,
    SUPPORTED_RESPONSE_VERBOSITIES,
)
from recollectium.errors import ValidationError


class ResponseVerbosity(StrEnum):
    """Supported response detail levels."""

    COMPACT = RESPONSE_VERBOSITY_COMPACT
    VERBOSE = RESPONSE_VERBOSITY_VERBOSE


OPERATION_MEMORIES_SEARCH_USER = "memories.search_user"
OPERATION_MEMORIES_SEARCH_WORKSPACE = "memories.search_workspace"
OPERATION_MEMORIES_ADD = "memories.add"
OPERATION_MEMORIES_UPDATE = "memories.update"
OPERATION_MEMORIES_ARCHIVE = "memories.archive"
OPERATION_MEMORIES_LIST = "memories.list"
OPERATION_MEMORIES_GET = "memories.get"
OPERATION_EMBEDDING_STATUS = "embedding.status"
OPERATION_EMBEDDING_JOBS_LIST = "embedding.jobs.list"
OPERATION_EMBEDDING_JOBS_GET = "embedding.jobs.get"
OPERATION_EMBEDDING_REFRESH = "embedding.refresh"
OPERATION_EMBEDDING_JOBS_CLEAR = "embedding.jobs.clear"
OPERATION_HEALTH_READ = "health.read"
OPERATION_VERSION_READ = "version.read"
OPERATION_CAPABILITIES_READ = "capabilities.read"
OPERATION_WORKSPACES_LIST = "workspaces.list"
OPERATION_WORKSPACES_RENAME = "workspaces.rename"
OPERATION_WORKSPACES_RESOLVE = "workspaces.resolve"
OPERATION_WORKSPACES_ALIASES_LIST = "workspaces.aliases.list"
OPERATION_WORKSPACES_ALIASES_ADD = "workspaces.aliases.add"
OPERATION_WORKSPACES_ALIASES_REMOVE = "workspaces.aliases.remove"


def validate_response_verbosity(
    value: str | ResponseVerbosity | None,
) -> ResponseVerbosity:
    """Normalize and validate a response verbosity value."""
    if isinstance(value, ResponseVerbosity):
        return value
    if value is None:
        return ResponseVerbosity(RESPONSE_VERBOSITY_COMPACT)
    verbosity = value.lower()
    if verbosity not in SUPPORTED_RESPONSE_VERBOSITIES:
        allowed = ", ".join(sorted(SUPPORTED_RESPONSE_VERBOSITIES))
        raise ValidationError(f"verbosity must be one of: {allowed}")
    return ResponseVerbosity(verbosity)


def _compact_dict(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: payload[key] for key in keys if key in payload and payload[key] is not None
    }


def project_memory(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a memory payload for the selected verbosity."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    return _compact_dict(payload, ("id", "content", "type", "space", "workspace_uid"))


def project_search_result(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a search result payload for the selected verbosity."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    if not isinstance(payload, dict):
        return payload
    nested_memory = payload.get("memory")
    memory = nested_memory if isinstance(nested_memory, dict) else payload
    compact = _compact_dict(memory, ("id", "content"))
    compact["match"] = float(payload.get("match", payload.get("score", 0.0)))
    return compact


def project_memories(
    payloads: list[dict[str, Any]], verbosity: str | ResponseVerbosity | None
) -> list[dict[str, Any]]:
    """Project memory payloads for the selected verbosity."""
    return [project_memory(payload, verbosity) for payload in payloads]


def project_search_results(
    payloads: list[dict[str, Any]], verbosity: str | ResponseVerbosity | None
) -> list[dict[str, Any]]:
    """Project search result payloads for the selected verbosity."""
    return [project_search_result(payload, verbosity) for payload in payloads]


def project_mutation(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None, *, status: str
) -> dict[str, Any]:
    """Project an add/update/archive mutation payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact: dict[str, Any] = {"status": status}
    if payload.get("id") is not None:
        compact = {"id": payload["id"], **compact}
    return compact


def project_embedding_status(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project an embedding status payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    return _compact_dict(
        payload,
        (
            "provider_status",
            "embedding_profile",
            "model_status",
            "model_cache_path",
            "embedding_jobs_status_path",
        ),
    )


def project_embedding_job(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project an embedding job payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(
        payload,
        (
            "id",
            "state",
            "reason",
            "total_count",
            "succeeded_count",
            "failed_count",
        ),
    )
    legacy_count_keys = {
        "total_count": "total",
        "succeeded_count": "succeeded",
        "failed_count": "failed",
    }
    for public_key, legacy_key in legacy_count_keys.items():
        if public_key not in compact and payload.get(legacy_key) is not None:
            compact[public_key] = payload[legacy_key]
    return compact


def _compact_workspace_alias(alias: dict[str, Any]) -> dict[str, Any]:
    return _compact_dict(alias, ("alias_uid", "canonical_uid"))


def project_workspace_list_item(
    payload: Any, verbosity: str | ResponseVerbosity | None
) -> Any:
    """Project one workspace list item."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return payload
    compact = _compact_dict(payload, ("workspace_uid",))
    aliases = payload.get("aliases")
    if isinstance(aliases, list):
        alias_uids: list[str] = []
        for alias in aliases:
            if isinstance(alias, str):
                alias_uids.append(alias)
            elif isinstance(alias, dict) and isinstance(alias.get("alias_uid"), str):
                alias_uids.append(alias["alias_uid"])
        compact["aliases"] = alias_uids
        compact["alias_count"] = len(alias_uids)
    elif isinstance(aliases, int) and not isinstance(aliases, bool):
        compact["alias_count"] = aliases
    return compact


def project_workspace_resolve(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a workspace resolution payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(payload, ("canonical_uid", "resolved_by_alias"))
    if payload.get("resolved_by_alias"):
        compact.update(_compact_dict(payload, ("input_uid", "normalized_uid")))
    elif payload.get("input_uid") != payload.get("normalized_uid"):
        compact.update(_compact_dict(payload, ("input_uid", "normalized_uid")))
    return compact


def project_workspace_alias(
    payload: Any, verbosity: str | ResponseVerbosity | None
) -> Any:
    """Project a workspace alias payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return _compact_workspace_alias(payload)
    return payload


def project_workspace_alias_add(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a workspace alias creation payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    alias = payload.get("alias")
    alias_payload = alias if isinstance(alias, dict) else payload
    compact = _compact_dict(alias_payload, ("canonical_uid", "alias_uid"))
    compact["status"] = "added"
    if payload.get("migrated_memories") is not None:
        compact["migrated_memories"] = payload["migrated_memories"]
    return compact


def project_workspace_alias_remove(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a workspace alias removal payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(payload, ("alias_uid", "canonical_uid"))
    compact["status"] = "removed"
    return compact


def project_workspace_rename(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project a workspace rename payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(
        payload, ("old_uid", "new_uid", "memories_updated", "aliases_updated")
    )
    compact["status"] = "renamed"
    return compact


def project_embedding_refresh(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project an embedding refresh payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(payload, ("refreshed", "stale_count", "status_path"))
    job = payload.get("job")
    if isinstance(job, dict) and job.get("id") is not None:
        compact["job_id"] = job["id"]
    return compact


def _is_memory_payload(payload: dict[str, Any]) -> bool:
    """Return whether an untagged payload has the expected memory shape."""
    return (
        isinstance(payload.get("id"), str)
        and isinstance(payload.get("content"), str)
        and any(key in payload for key in ("type", "space", "workspace_uid"))
    )


def project_payload(
    data: Any,
    *,
    verbosity: str | ResponseVerbosity | None = None,
    operation: str | None = None,
) -> Any:
    """Project a JSON-ready payload into compact or verbose response shape."""
    selected = validate_response_verbosity(verbosity)
    if selected == ResponseVerbosity.VERBOSE:
        return data
    if isinstance(data, list):
        return [
            project_payload(item, verbosity=selected, operation=operation)
            for item in data
        ]
    if not isinstance(data, dict):
        return data
    if operation in {
        OPERATION_MEMORIES_ADD,
        OPERATION_MEMORIES_UPDATE,
        OPERATION_MEMORIES_ARCHIVE,
    }:
        status = {
            OPERATION_MEMORIES_ADD: "saved",
            OPERATION_MEMORIES_UPDATE: "updated",
            OPERATION_MEMORIES_ARCHIVE: "archived",
        }[operation]
        return project_mutation(data, selected, status=status)
    if operation in {
        OPERATION_MEMORIES_SEARCH_USER,
        OPERATION_MEMORIES_SEARCH_WORKSPACE,
    }:
        return project_search_result(data, selected)
    if operation in {
        OPERATION_MEMORIES_LIST,
        OPERATION_MEMORIES_GET,
    } or _is_memory_payload(data):
        return project_memory(data, selected)
    if operation == OPERATION_EMBEDDING_STATUS:
        return project_embedding_status(data, selected)
    if operation in {OPERATION_EMBEDDING_JOBS_LIST, OPERATION_EMBEDDING_JOBS_GET}:
        return project_embedding_job(data, selected)
    if operation == OPERATION_EMBEDDING_REFRESH:
        return project_embedding_refresh(data, selected)
    if operation == OPERATION_EMBEDDING_JOBS_CLEAR:
        return _compact_dict(data, ("deleted_count", "states"))
    if operation == OPERATION_WORKSPACES_LIST:
        return project_workspace_list_item(data, selected)
    if operation == OPERATION_WORKSPACES_RESOLVE:
        return project_workspace_resolve(data, selected)
    if operation == OPERATION_WORKSPACES_ALIASES_LIST:
        return project_workspace_alias(data, selected)
    if operation == OPERATION_WORKSPACES_ALIASES_ADD:
        return project_workspace_alias_add(data, selected)
    if operation == OPERATION_WORKSPACES_ALIASES_REMOVE:
        return project_workspace_alias_remove(data, selected)
    if operation == OPERATION_WORKSPACES_RENAME:
        return project_workspace_rename(data, selected)
    return data
