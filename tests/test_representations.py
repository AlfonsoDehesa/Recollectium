"""Tests for shared response projection helpers."""

from __future__ import annotations

from recollectium.representations import (
    OPERATION_DEV_EVAL,
    OPERATION_DEV_OPTIMIZE_THRESHOLD,
    OPERATION_EMBEDDING_JOBS_GET,
    OPERATION_EMBEDDING_MAINTENANCE,
    OPERATION_LIFECYCLE_INIT,
    OPERATION_LIFECYCLE_UNINSTALL,
    OPERATION_LIFECYCLE_UPGRADE,
    OPERATION_SERVICE_DISCOVER,
    OPERATION_SERVICE_LIFECYCLE,
    OPERATION_WORKSPACES_ALIASES_ADD,
    OPERATION_WORKSPACES_ALIASES_LIST,
    OPERATION_WORKSPACES_ALIASES_REMOVE,
    OPERATION_WORKSPACES_LIST,
    OPERATION_WORKSPACES_RENAME,
    OPERATION_WORKSPACES_RESOLVE,
    ResponseVerbosity,
    project_embedding_job,
    project_embedding_refresh,
    project_embedding_status,
    project_memories,
    project_memory,
    project_mutation,
    project_payload,
    project_search_result,
    project_search_results,
)


def test_verbose_projection_helpers_return_original_payloads() -> None:
    memory = {
        "id": "mem-1",
        "content": "Remember compact and verbose shapes.",
        "type": "fact",
        "space": "user",
        "metadata": {"source": "test"},
    }
    search_result = {"memory": memory, "score": 0.75, "rank": 1}
    mutation = {**memory, "updated_at": "2026-01-01T00:00:00Z"}
    embedding_status = {
        "provider_status": "ready",
        "model_status": "ready",
        "embedding_profile": {"model": "fake"},
        "extra": "kept when verbose",
    }
    embedding_job = {
        "id": "job-1",
        "state": "completed",
        "total": 3,
        "succeeded": 3,
        "failed": 0,
        "details": {"kept": True},
    }
    embedding_refresh = {
        "refreshed": 2,
        "stale_count": 0,
        "status_path": "/tmp/status.json",
        "job": {"id": "job-1", "state": "completed"},
    }

    assert project_memory(memory, ResponseVerbosity.VERBOSE) is memory
    assert project_search_result(search_result, "verbose") is search_result
    assert project_mutation(mutation, "verbose", status="updated") is mutation
    assert project_embedding_status(embedding_status, "verbose") is embedding_status
    assert project_embedding_job(embedding_job, "verbose") is embedding_job
    assert project_embedding_refresh(embedding_refresh, "verbose") is embedding_refresh


def test_list_projection_helpers_apply_compact_projection() -> None:
    memory = {
        "id": "mem-1",
        "content": "Compact list projection.",
        "type": "fact",
        "space": "user",
        "metadata": {"omitted": True},
    }
    search_result = {"memory": memory, "score": 0.5, "rank": 1}

    assert project_memories([memory], "compact") == [
        {
            "id": "mem-1",
            "content": "Compact list projection.",
            "type": "fact",
            "space": "user",
        }
    ]
    assert project_search_results([search_result], "compact") == [
        {"id": "mem-1", "content": "Compact list projection.", "match": 0.5}
    ]


def test_compact_search_reprojection_preserves_match() -> None:
    compact_search_result = {
        "id": "mem-1",
        "content": "Already compact search projection.",
        "match": 0.75,
    }

    assert (
        project_search_result(compact_search_result, "compact") == compact_search_result
    )


def test_search_projection_preserves_unexpected_non_dict_search_payload() -> None:
    class NonDictSearchPayload:
        pass

    payload = NonDictSearchPayload()

    assert project_search_result(payload, "compact") is payload  # type: ignore[arg-type]


def test_compact_embedding_job_uses_public_count_keys() -> None:
    payload = {
        "id": "job-1",
        "state": "completed",
        "reason": "manual",
        "total_count": 4,
        "succeeded_count": 3,
        "failed_count": 1,
        "started_at": "2026-01-01T00:00:00Z",
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_EMBEDDING_JOBS_GET
    ) == {
        "id": "job-1",
        "state": "completed",
        "reason": "manual",
        "total_count": 4,
        "succeeded_count": 3,
        "failed_count": 1,
    }


def test_compact_embedding_job_normalizes_legacy_count_keys() -> None:
    payload = {
        "id": "job-legacy",
        "state": "completed",
        "total": 2,
        "succeeded": 2,
        "failed": 0,
    }

    assert project_embedding_job(payload, "compact") == {
        "id": "job-legacy",
        "state": "completed",
        "total_count": 2,
        "succeeded_count": 2,
        "failed_count": 0,
    }


def test_compact_workspace_list_keeps_uid_alias_strings_and_count() -> None:
    payload = [
        "plain-workspace",
        {
            "workspace_uid": "core",
            "aliases": [
                "recollectium",
                {
                    "alias_uid": "recollectium-core",
                    "canonical_uid": "core",
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ],
            "created_at": "2026-01-01T00:00:00Z",
        },
    ]

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_WORKSPACES_LIST
    ) == [
        "plain-workspace",
        {
            "workspace_uid": "core",
            "aliases": ["recollectium", "recollectium-core"],
            "alias_count": 2,
        },
    ]


def test_compact_workspace_resolve_keeps_canonical_and_alias_context() -> None:
    payload = {
        "input_uid": "Recollectium",
        "normalized_uid": "recollectium",
        "canonical_uid": "core",
        "resolved_by_alias": True,
        "created_at": "2026-01-01T00:00:00Z",
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_WORKSPACES_RESOLVE
    ) == {
        "canonical_uid": "core",
        "resolved_by_alias": True,
        "input_uid": "Recollectium",
        "normalized_uid": "recollectium",
    }


def test_compact_workspace_aliases_list_omits_timestamps() -> None:
    payload = [
        {
            "alias_uid": "recollectium",
            "canonical_uid": "core",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
    ]

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_WORKSPACES_ALIASES_LIST
    ) == [{"alias_uid": "recollectium", "canonical_uid": "core"}]


def test_compact_workspace_alias_mutations_are_status_bearing() -> None:
    added = {
        "alias": {
            "alias_uid": "recollectium",
            "canonical_uid": "core",
            "created_at": "2026-01-01T00:00:00Z",
        },
        "migrated_memories": 2,
    }
    removed = {
        "alias_uid": "recollectium",
        "canonical_uid": "core",
        "created_at": "2026-01-01T00:00:00Z",
    }

    assert project_payload(
        added, verbosity="compact", operation=OPERATION_WORKSPACES_ALIASES_ADD
    ) == {
        "canonical_uid": "core",
        "alias_uid": "recollectium",
        "status": "added",
        "migrated_memories": 2,
    }
    assert project_payload(
        removed, verbosity="compact", operation=OPERATION_WORKSPACES_ALIASES_REMOVE
    ) == {
        "alias_uid": "recollectium",
        "canonical_uid": "core",
        "status": "removed",
    }


def test_compact_workspace_rename_adds_status() -> None:
    payload = {
        "old_uid": "old",
        "new_uid": "new",
        "memories_updated": 3,
        "aliases_updated": 1,
        "updated_at": "2026-01-01T00:00:00Z",
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_WORKSPACES_RENAME
    ) == {
        "old_uid": "old",
        "new_uid": "new",
        "memories_updated": 3,
        "aliases_updated": 1,
        "status": "renamed",
    }


def test_verbose_workspace_projection_returns_original_payload() -> None:
    payload = {"workspace_uid": "core", "aliases": [], "created_at": "kept"}

    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_WORKSPACES_LIST
        )
        is payload
    )


def test_compact_init_projection_keeps_paths_and_refresh_summary() -> None:
    payload = {
        "status": "initialized",
        "config": "/cfg.json",
        "data": "/data",
        "cache": "/cache",
        "logs": "/logs",
        "runtime": "/runtime",
        "database": "/db.sqlite",
        "embedding_model": "fake-model",
        "embedding_profile": {"provider": "fake", "dimensions": 3},
        "model_prepared": True,
        "embedding_refresh": {
            "refreshed": 2,
            "stale_count": 0,
            "job": {"id": "job-1", "state": "completed"},
            "memory_ids": ["mem-1", "mem-2"],
        },
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_LIFECYCLE_INIT
    ) == {
        "status": "initialized",
        "config_path": "/cfg.json",
        "database_path": "/db.sqlite",
        "embedding_model": "fake-model",
        "model_status": "ready",
        "refreshed": 2,
        "stale_count": 0,
        "job_id": "job-1",
    }
    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_LIFECYCLE_INIT
        )
        is payload
    )


def test_compact_embedding_maintenance_projection_keeps_refresh_summary() -> None:
    payload = {
        "status": "embedding_maintenance_completed",
        "config": "/cfg.json",
        "database": "/db.sqlite",
        "embedding_model": "fake-model",
        "embedding_profile": {"provider": "fake"},
        "model_prepared": True,
        "embedding_refresh": {"refreshed": 1, "stale_count": 0},
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_EMBEDDING_MAINTENANCE
    ) == {
        "status": "embedding_maintenance_completed",
        "embedding_model": "fake-model",
        "model_status": "ready",
        "refreshed": 1,
        "stale_count": 0,
    }
    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_EMBEDDING_MAINTENANCE
        )
        is payload
    )


def test_compact_upgrade_projection_omits_plan_and_command_internals() -> None:
    payload = {
        "status": "updated",
        "current_version": "0.1.0",
        "target_ref": "v0.2.0",
        "install_method": "pip",
        "command": ["python", "-m", "pip", "install", "pkg"],
        "metadata_path": "/install.json",
        "stdout": "lots",
        "stderr": "",
        "embedding_maintenance": {
            "status": "embedding_maintenance_completed",
            "config": "/cfg.json",
            "database": "/db.sqlite",
            "model_prepared": True,
            "embedding_refresh": {"refreshed": 0, "stale_count": 0},
        },
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_LIFECYCLE_UPGRADE
    ) == {
        "status": "updated",
        "current_version": "0.1.0",
        "target_ref": "v0.2.0",
        "install_method": "pip",
        "embedding_maintenance": {
            "status": "embedding_maintenance_completed",
            "model_status": "ready",
            "refreshed": 0,
            "stale_count": 0,
        },
    }
    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_LIFECYCLE_UPGRADE
        )
        is payload
    )


def test_compact_uninstall_projection_summarizes_data_and_package() -> None:
    payload = {
        "status": "package_removal_unsupported",
        "package": {
            "uninstall": {
                "status": "unsupported",
                "install_method": "source",
                "command": None,
            }
        },
        "service": {"status": "no_service_running"},
        "shell_completion": {"targets": [{"path": "/rc", "removed": False}]},
        "data": {
            "preserved": True,
            "paths": {"database": "/db.sqlite", "config": "/cfg.json"},
        },
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_LIFECYCLE_UNINSTALL
    ) == {
        "status": "package_removal_unsupported",
        "data": {
            "status": "preserved",
            "preserved": True,
            "dry_run": False,
            "action": "preserve",
        },
        "package": {"status": "unsupported", "install_method": "source"},
        "manual_hint": "Manual package removal is required.",
        "service": {"status": "no_service_running"},
    }
    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_LIFECYCLE_UNINSTALL
        )
        is payload
    )


def test_compact_uninstall_projection_keeps_dry_run_purge_outcomes() -> None:
    skipped = {"path": "/data", "deleted": False, "reason": "dry_run"}
    payload = {
        "status": "package_removal_unsupported",
        "package": {
            "uninstall": {
                "status": "unsupported",
                "install_method": "source",
                "manual_hint": "Remove the checkout manually.",
            }
        },
        "service": {"status": "no_service_running"},
        "data": {
            "preserved": False,
            "memories_preserved": False,
            "config_preserved": False,
            "derived_artifacts_removed": False,
            "purge": {
                "dry_run": True,
                "targets": [skipped],
                "deleted": [],
                "skipped": [skipped],
            },
            "model_cache": {
                "dry_run": True,
                "path": "/cache/model",
                "targets": [skipped],
                "deleted": [],
                "skipped": [skipped],
            },
        },
    }

    compact = project_payload(
        payload, verbosity="compact", operation=OPERATION_LIFECYCLE_UNINSTALL
    )

    assert compact["status"] == "package_removal_unsupported"
    assert compact["data"]["status"] == "would_delete"
    assert compact["data"]["dry_run"] is True
    assert compact["data"]["action"] == "delete"
    assert compact["data"]["purge"]["would_delete_count"] == 1
    assert compact["data"]["purge"]["would_delete"] == [skipped]
    assert compact["data"]["purge"]["skipped"] == []
    assert compact["data"]["model_cache"]["path"] == "/cache/model"
    assert compact["package"] == {
        "status": "unsupported",
        "install_method": "source",
        "manual_hint": "Remove the checkout manually.",
    }
    assert compact["manual_hint"] == "Remove the checkout manually."
    assert "paths" not in compact["data"]


def test_compact_dev_eval_projection_keeps_metric_values_only() -> None:
    payload = {
        "status": "ok",
        "database": "/dev.db",
        "metrics": {
            "exact_mrr": {"value": 1.0, "targets": 10},
            "semantic_mrr": {"value": 0.9, "queries": 20},
            "thematic_weighted_precision_at_10": {"value": 0.8, "groups": 4},
            "thematic_weighted_recall_at_10": {"value": 0.7, "groups": 4},
            "ranked_set_ndcg_at_5": {"value": 0.6, "cases": 3},
        },
        "diagnostics": {"worst_exact": [{"target_id": "mem-1"}]},
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_DEV_EVAL
    ) == {
        "status": "ok",
        "metrics": {
            "exact_mrr": {"value": 1.0},
            "semantic_mrr": {"value": 0.9},
            "thematic_weighted_precision_at_10": {"value": 0.8},
            "thematic_weighted_recall_at_10": {"value": 0.7},
            "ranked_set_ndcg_at_5": {"value": 0.6},
        },
    }
    assert (
        project_payload(payload, verbosity="verbose", operation=OPERATION_DEV_EVAL)
        is payload
    )


def test_compact_dev_optimize_projection_omits_sweep_rows() -> None:
    payload = {
        "status": "ok",
        "optimization": {
            "recommended_threshold": 0.42,
            "beta": 1.0,
            "objective": "weighted_f_beta",
            "rows": [
                {
                    "threshold": 0.42,
                    "weighted_precision": 0.9,
                    "weighted_recall": 0.8,
                    "weighted_f_score": 0.85,
                    "direct_recall": 0.7,
                    "adjacent_recall": 0.1,
                    "confuser_exposure": 0.1,
                    "average_returned_count": 4.2,
                    "recommended": True,
                },
                {"threshold": 0.2, "recommended": False},
            ],
        },
        "artifact": {"format": "png", "path": "/sweep.png"},
    }

    assert project_payload(
        payload, verbosity="compact", operation=OPERATION_DEV_OPTIMIZE_THRESHOLD
    ) == {
        "status": "ok",
        "optimization": {
            "recommended_threshold": 0.42,
            "beta": 1.0,
            "objective": "weighted_f_beta",
        },
        "recommendation": {
            "threshold": 0.42,
            "weighted_precision": 0.9,
            "weighted_recall": 0.8,
            "weighted_f_score": 0.85,
            "direct_recall": 0.7,
            "adjacent_recall": 0.1,
            "confuser_exposure": 0.1,
            "average_returned_count": 4.2,
        },
        "artifact": {"format": "png", "path": "/sweep.png"},
    }
    assert (
        project_payload(
            payload, verbosity="verbose", operation=OPERATION_DEV_OPTIMIZE_THRESHOLD
        )
        is payload
    )


def test_compact_service_projections_keep_connection_contract() -> None:
    discover_payload = {
        "status": "running",
        "running": True,
        "type": "api",
        "endpoint": "http://127.0.0.1:8765",
        "pid": 123,
        "version_url": "http://127.0.0.1:8765/v1/version",
        "capabilities_url": "http://127.0.0.1:8765/v1/capabilities",
        "discovery_file": "/runtime/service-discovery.json",
        "config": "/cfg.json",
    }
    lifecycle_payload = {
        "status": "started",
        "type": "api",
        "pid": 123,
        "endpoint": "http://127.0.0.1:8765",
        "debug": {"command": ["python", "-m", "recollectium"]},
    }

    assert project_payload(
        discover_payload, verbosity="compact", operation=OPERATION_SERVICE_DISCOVER
    ) == {
        "status": "running",
        "running": True,
        "type": "api",
        "endpoint": "http://127.0.0.1:8765",
        "pid": 123,
        "version_url": "http://127.0.0.1:8765/v1/version",
        "capabilities_url": "http://127.0.0.1:8765/v1/capabilities",
    }
    nested_discover_payload = {
        "status": "running",
        "versions": {"python": "3.12"},
        "paths": {"runtime": "/runtime"},
        "discovery_file": "/runtime/service-discovery.json",
        "service": {
            "type": "api",
            "endpoint": "http://127.0.0.1:8765",
            "pid": 123,
            "version_url": "http://127.0.0.1:8765/v1/version",
            "capabilities_url": "http://127.0.0.1:8765/v1/capabilities",
            "discovery_file": "/runtime/service-discovery.json",
        },
    }
    assert project_payload(
        nested_discover_payload,
        verbosity="compact",
        operation=OPERATION_SERVICE_DISCOVER,
    ) == {
        "status": "running",
        "type": "api",
        "endpoint": "http://127.0.0.1:8765",
        "pid": 123,
        "version_url": "http://127.0.0.1:8765/v1/version",
        "capabilities_url": "http://127.0.0.1:8765/v1/capabilities",
    }
    assert project_payload(
        lifecycle_payload, verbosity="compact", operation=OPERATION_SERVICE_LIFECYCLE
    ) == {
        "status": "started",
        "type": "api",
        "pid": 123,
        "endpoint": "http://127.0.0.1:8765",
    }
    assert (
        project_payload(
            discover_payload, verbosity="verbose", operation=OPERATION_SERVICE_DISCOVER
        )
        is discover_payload
    )
