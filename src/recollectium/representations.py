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
OPERATION_LIFECYCLE_INIT = "lifecycle.init"
OPERATION_EMBEDDING_MAINTENANCE = "embedding.maintenance"
OPERATION_LIFECYCLE_UPGRADE = "lifecycle.upgrade"
OPERATION_LIFECYCLE_UNINSTALL = "lifecycle.uninstall"
OPERATION_DEV_MODE = "dev.mode"
OPERATION_DEV_RESET = "dev.reset"
OPERATION_DEV_EVAL = "dev.eval"
OPERATION_DEV_OPTIMIZE_THRESHOLD = "dev.optimize_threshold"
OPERATION_SERVICE_DISCOVER = "service.discover"
OPERATION_SERVICE_LIFECYCLE = "service.lifecycle"


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
    if "reason" not in compact and payload.get("error_message"):
        compact["reason"] = payload["error_message"]
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
    elif isinstance(payload.get("alias_records"), list):
        alias_uids = [
            alias["alias_uid"]
            for alias in payload["alias_records"]
            if isinstance(alias, dict) and isinstance(alias.get("alias_uid"), str)
        ]
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
    return _compact_dict(payload, ("canonical_uid", "resolved_by_alias"))


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


def _refresh_summary(payload: dict[str, Any]) -> dict[str, Any]:
    refresh = payload.get("embedding_refresh")
    if not isinstance(refresh, dict):
        refresh = payload
    compact = _compact_dict(refresh, ("refreshed", "stale_count", "status_path"))
    job = refresh.get("job")
    if isinstance(job, dict) and job.get("id") is not None:
        compact["job_id"] = job["id"]
    return compact


def project_init(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI init payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = {
        "status": payload.get("status", "initialized"),
        **_compact_dict(
            payload,
            (
                "config_path",
                "database_path",
                "model_status",
                "embedding_model",
                "already_initialized",
            ),
        ),
    }
    if "config_path" not in compact and payload.get("config") is not None:
        compact["config_path"] = payload["config"]
    if "database_path" not in compact and payload.get("database") is not None:
        compact["database_path"] = payload["database"]
    if "model_status" not in compact and payload.get("model_prepared") is not None:
        compact["model_status"] = (
            "ready" if payload.get("model_prepared") else "not_ready"
        )
    compact.update(_refresh_summary(payload))
    return {key: value for key, value in compact.items() if value is not None}


def project_embedding_maintenance(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI embedding-maintenance payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = {
        "status": payload.get("status", "embedding_maintenance_completed"),
        **_compact_dict(payload, ("model_status", "embedding_model")),
    }
    if "model_status" not in compact and payload.get("model_prepared") is not None:
        compact["model_status"] = (
            "ready" if payload.get("model_prepared") else "not_ready"
        )
    compact.update(_refresh_summary(payload))
    return {key: value for key, value in compact.items() if value is not None}


def project_upgrade(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI upgrade payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(
        payload,
        (
            "status",
            "current_version",
            "target_version",
            "target_ref",
            "latest_tag",
            "current_commit",
            "target_commit",
            "install_method",
        ),
    )
    if payload.get("reason") is not None and payload.get("status") not in {
        "updated",
        "up_to_date",
        "dry_run",
        "update_available",
    }:
        compact["reason"] = payload["reason"]
    for key in ("returncode", "message", "detail"):
        if payload.get(key) is not None:
            compact[key] = payload[key]
    maintenance = payload.get("embedding_maintenance")
    if isinstance(maintenance, dict):
        compact["embedding_maintenance"] = project_embedding_maintenance(
            maintenance, ResponseVerbosity.COMPACT
        )
    if payload.get("services_to_restart"):
        compact["services_to_restart"] = payload["services_to_restart"]
    if payload.get("service_restart_errors"):
        compact["service_restart_errors"] = payload["service_restart_errors"]
    return compact


def _uninstall_is_dry_run(payload: dict[str, Any], data: dict[str, Any] | None) -> bool:
    if isinstance(payload.get("dry_run"), bool):
        return bool(payload["dry_run"])
    if isinstance(data, dict):
        for nested in (data.get("purge"), data.get("model_cache")):
            if isinstance(nested, dict) and isinstance(nested.get("dry_run"), bool):
                return bool(nested["dry_run"])
    return payload.get("status") in {"dry_run", "dry_run_with_warnings"}


def _path_summary(payload: Any, *, dry_run: bool) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    compact = _compact_dict(payload, ("dry_run",))
    targets = payload.get("targets")
    if isinstance(targets, list):
        compact["target_count"] = len(targets)
    deleted = payload.get("deleted")
    skipped = payload.get("skipped")
    if dry_run:
        would_delete: list[Any] = []
        remaining_skipped: list[Any] | None = None
        if isinstance(deleted, list):
            would_delete.extend(deleted)
        if isinstance(skipped, list):
            would_delete.extend(
                item
                for item in skipped
                if isinstance(item, dict) and item.get("reason") == "dry_run"
            )
            remaining_skipped = [
                item
                for item in skipped
                if not (isinstance(item, dict) and item.get("reason") == "dry_run")
            ]
        if isinstance(deleted, list) or isinstance(skipped, list):
            compact["would_delete"] = would_delete
            compact["would_delete_count"] = len(would_delete)
        if remaining_skipped is not None:
            compact["skipped"] = remaining_skipped
            compact["skipped_count"] = len(remaining_skipped)
    else:
        if isinstance(deleted, list):
            compact["deleted"] = deleted
            compact["deleted_count"] = len(deleted)
        if isinstance(skipped, list):
            compact["skipped"] = skipped
            compact["skipped_count"] = len(skipped)
    if payload.get("status") is not None:
        compact["status"] = payload["status"]
    if payload.get("path") is not None:
        compact["path"] = payload["path"]
    return compact or None


def _project_uninstall_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return {"status": "unknown"}
    dry_run = _uninstall_is_dry_run(payload, data)
    preserved = data.get("preserved") is True
    status = (
        "would_preserve"
        if dry_run and preserved
        else "preserved"
        if preserved
        else "would_delete"
        if dry_run
        else "deleted"
    )
    compact: dict[str, Any] = {
        "status": status,
        "preserved": preserved,
        "dry_run": dry_run,
        "action": "preserve" if preserved else "delete",
    }
    for key in ("memories_preserved", "config_preserved", "derived_artifacts_removed"):
        if data.get(key) is not None:
            compact[key] = data[key]
    purge = _path_summary(data.get("purge"), dry_run=dry_run)
    if purge is not None:
        compact["purge"] = purge
    model_cache = _path_summary(data.get("model_cache"), dry_run=dry_run)
    if model_cache is not None:
        compact["model_cache"] = model_cache
    return compact


def project_uninstall(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI uninstall payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact: dict[str, Any] = {
        "status": payload.get("status"),
        "data": _project_uninstall_data(payload),
    }
    package = payload.get("package")
    if isinstance(package, dict):
        uninstall = package.get("uninstall")
        if isinstance(uninstall, dict):
            compact_package = _compact_dict(
                uninstall,
                ("status", "install_method", "returncode", "manual_hint", "hint"),
            )
            if (
                compact_package.get("install_method") is None
                and package.get("install_method") is not None
            ):
                compact_package["install_method"] = package["install_method"]
            compact["package"] = compact_package
            if uninstall.get("status") == "unsupported" or uninstall.get("manual_hint"):
                compact["manual_hint"] = (
                    uninstall.get("manual_hint")
                    or uninstall.get("hint")
                    or "Manual package removal is required."
                )
        else:
            compact["package"] = _compact_dict(
                package, ("status", "install_method", "returncode")
            )
    service = payload.get("service")
    if isinstance(service, dict):
        compact["service"] = _compact_dict(service, ("status", "pid", "running"))
    elif service is not None:
        compact["service"] = service
    return {key: value for key, value in compact.items() if value is not None}


def project_dev_eval(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI dev eval payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return _compact_dict(payload, ("status",))
    metric_keys = {
        "exact_mrr",
        "semantic_mrr",
        "thematic_weighted_precision_at_10",
        "thematic_weighted_recall_at_10",
        "ranked_set_ndcg_at_5",
    }
    return {
        "status": payload.get("status"),
        "metrics": {
            key: _compact_dict(value, ("value",)) if isinstance(value, dict) else value
            for key, value in metrics.items()
            if key in metric_keys
        },
    }


def project_dev_optimize_threshold(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project the CLI dev optimize-threshold payload."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(payload, ("status",))
    optimization = payload.get("optimization")
    if isinstance(optimization, dict):
        compact["optimization"] = _compact_dict(
            optimization,
            (
                "recommended_threshold",
                "beta",
                "objective",
                "weighted_precision",
                "weighted_recall",
                "weighted_f_beta",
                "weighted_f_score",
                "confuser_exposure",
                "unrelated_exposure",
                "average_returned_count",
            ),
        )
        recommendation = optimization.get("recommendation")
        if not isinstance(recommendation, dict):
            rows = optimization.get("rows")
            if isinstance(rows, list):
                recommended_threshold = optimization.get("recommended_threshold")
                recommendation = next(
                    (
                        row
                        for row in rows
                        if isinstance(row, dict) and row.get("recommended") is True
                    ),
                    None,
                )
                if not isinstance(recommendation, dict):
                    recommendation = next(
                        (
                            row
                            for row in rows
                            if isinstance(row, dict)
                            and row.get("threshold") == recommended_threshold
                        ),
                        None,
                    )
        if isinstance(recommendation, dict):
            compact["recommendation"] = _compact_dict(
                recommendation,
                (
                    "threshold",
                    "weighted_precision",
                    "weighted_recall",
                    "weighted_f_beta",
                    "weighted_f_score",
                    "direct_recall",
                    "adjacent_recall",
                    "confuser_exposure",
                    "unrelated_exposure",
                    "average_returned_count",
                ),
            )
    artifact = payload.get("artifact")
    if isinstance(artifact, dict) and artifact.get("path") is not None:
        compact["artifact"] = _compact_dict(artifact, ("format", "path"))
    return compact


def project_dev_mode(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project seeded development database toggle payloads."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    return _compact_dict(
        payload,
        ("status", "use_seeded_database", "database", "seed_status"),
    )


def project_dev_reset(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project seeded development database reset payloads."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    return _compact_dict(payload, ("status", "database"))


def project_service_discover(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project service discovery payloads while retaining adapter essentials."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    compact = _compact_dict(payload, ("status", "running"))
    service = payload.get("service")
    service_payload = service if isinstance(service, dict) else payload
    compact.update(
        _compact_dict(
            service_payload,
            (
                "type",
                "endpoint",
                "pid",
                "health_url",
                "version_url",
                "capabilities_url",
            ),
        )
    )
    return compact


def project_service_lifecycle(
    payload: dict[str, Any], verbosity: str | ResponseVerbosity | None
) -> dict[str, Any]:
    """Project service lifecycle payloads."""
    if validate_response_verbosity(verbosity) == ResponseVerbosity.VERBOSE:
        return payload
    return _compact_dict(
        payload, ("status", "running", "type", "endpoint", "pid", "last_service")
    )


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
    if operation == OPERATION_LIFECYCLE_INIT:
        return project_init(data, selected)
    if operation == OPERATION_EMBEDDING_MAINTENANCE:
        return project_embedding_maintenance(data, selected)
    if operation == OPERATION_LIFECYCLE_UPGRADE:
        return project_upgrade(data, selected)
    if operation == OPERATION_LIFECYCLE_UNINSTALL:
        return project_uninstall(data, selected)
    if operation == OPERATION_DEV_MODE:
        return project_dev_mode(data, selected)
    if operation == OPERATION_DEV_RESET:
        return project_dev_reset(data, selected)
    if operation == OPERATION_DEV_EVAL:
        return project_dev_eval(data, selected)
    if operation == OPERATION_DEV_OPTIMIZE_THRESHOLD:
        return project_dev_optimize_threshold(data, selected)
    if operation == OPERATION_SERVICE_DISCOVER:
        return project_service_discover(data, selected)
    if operation == OPERATION_SERVICE_LIFECYCLE:
        return project_service_lifecycle(data, selected)
    return data
