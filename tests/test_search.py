from pathlib import Path

import pytest

from recallium.embeddings import BuiltinFastEmbedProvider
from recallium.errors import EmbeddingGenerationError, ValidationError
from recallium.models import SPACE_USER, STATUS_ACTIVE, Memory
from recallium.search import rank_memory_candidates
from recallium.storage import SQLiteMemoryStore


def build_memory(memory_id: str, content: str, **overrides: object) -> Memory:
    payload = {
        "id": memory_id,
        "space": SPACE_USER,
        "type": "note",
        "content": content,
        "status": STATUS_ACTIVE,
        "metadata": {},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return Memory(**payload)


def test_provider_profile_matches_fastembed_spec() -> None:
    provider = BuiltinFastEmbedProvider()

    assert provider.embedding_profile == {
        "provider": "builtin-fastembed",
        "model": "mixedbread-ai/mxbai-embed-large-v1",
        "dimensions": 1024,
        "version": "1",
        "profile": "builtin-fastembed-mxbai-large-v1",
        "max_tokens": 512,
        "chunk_tokens": 384,
        "chunk_overlap_tokens": 64,
        "query_prompt_policy": "raw",
    }


def test_real_embedding_shape_is_1024() -> None:
    provider = BuiltinFastEmbedProvider()
    vector = provider.embed("Recallium should return stable embedding dimensions")

    assert len(vector) == 1024
    assert any(value != 0.0 for value in vector)


def test_semantic_search_returns_relevant_memory(tmp_path: Path) -> None:
    provider = BuiltinFastEmbedProvider()
    store = SQLiteMemoryStore(tmp_path / "semantic.db")

    memory = build_memory("mem-1", "Need to fix bug before release")
    store.insert_memory(
        memory,
        embedding=provider.embed(memory.content),
        embedding_profile=provider.embedding_profile,
    )

    candidates = store.list_candidates(
        space=SPACE_USER, embedding_profile=provider.embedding_profile
    )
    results = rank_memory_candidates(
        query="fix software defect", candidates=candidates, embedding_provider=provider
    )

    assert results
    assert results[0].memory.id == "mem-1"
    assert results[0].score > 0
    assert results[0].rank == 1


def test_ranking_includes_score_and_rank_order() -> None:
    provider = BuiltinFastEmbedProvider()

    primary = build_memory("mem-1", "buy groceries and fruit")
    secondary = build_memory("mem-2", "purchase household supplies")
    candidates = [
        (secondary, provider.embed(secondary.content)),
        (primary, provider.embed(primary.content)),
    ]

    results = rank_memory_candidates(
        query="buy fruit", candidates=candidates, embedding_provider=provider
    )

    assert [result.memory.id for result in results] == ["mem-1", "mem-2"]
    assert results[0].rank == 1
    assert results[1].rank == 2
    assert results[0].score >= results[1].score


def test_rank_memory_candidates_rejects_empty_query() -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(ValidationError, match="query"):
        rank_memory_candidates(query="   ", candidates=[], embedding_provider=provider)


def test_similarity_rejects_dimension_mismatch() -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(EmbeddingGenerationError, match="same size"):
        provider.similarity([1.0, 0.0], [1.0])


def test_rank_memory_candidates_rejects_invalid_limit() -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(ValidationError, match="positive integer"):
        rank_memory_candidates(
            query="fix software defect",
            candidates=[],
            embedding_provider=provider,
            limit=0,
        )


def test_archived_filter_is_respected_by_candidate_selection(tmp_path: Path) -> None:
    provider = BuiltinFastEmbedProvider()
    store = SQLiteMemoryStore(tmp_path / "archive-filter.db")

    active = build_memory("active", "buy coffee beans")
    archived = build_memory("archived", "purchase coffee beans")
    store.insert_memory(
        active,
        embedding=provider.embed(active.content),
        embedding_profile=provider.embedding_profile,
    )
    store.insert_memory(
        archived,
        embedding=provider.embed(archived.content),
        embedding_profile=provider.embedding_profile,
    )
    store.archive_memory("archived")

    active_candidates = store.list_candidates(
        space=SPACE_USER, embedding_profile=provider.embedding_profile
    )
    active_results = rank_memory_candidates(
        query="buy coffee",
        candidates=active_candidates,
        embedding_provider=provider,
    )
    assert [result.memory.id for result in active_results] == ["active"]

    all_candidates = store.list_candidates(
        space=SPACE_USER,
        embedding_profile=provider.embedding_profile,
        include_archived=True,
    )
    all_results = rank_memory_candidates(
        query="buy coffee",
        candidates=all_candidates,
        embedding_provider=provider,
    )
    assert [result.memory.id for result in all_results] == ["active", "archived"]
