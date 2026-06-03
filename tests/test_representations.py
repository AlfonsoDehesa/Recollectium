"""Tests for shared response projection helpers."""

from __future__ import annotations

from recollectium.representations import (
    ResponseVerbosity,
    project_embedding_job,
    project_embedding_refresh,
    project_embedding_status,
    project_memories,
    project_memory,
    project_mutation,
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


def test_search_projection_preserves_unexpected_non_dict_search_payload() -> None:
    class NonDictSearchPayload:
        pass

    payload = NonDictSearchPayload()

    assert project_search_result(payload, "compact") is payload  # type: ignore[arg-type]
