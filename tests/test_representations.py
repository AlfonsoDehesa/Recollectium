"""Tests for shared response projection helpers."""

from __future__ import annotations

from recollectium.representations import (
    OPERATION_EMBEDDING_JOBS_GET,
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
