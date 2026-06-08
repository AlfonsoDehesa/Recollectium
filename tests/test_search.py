from pathlib import Path
import sys
from types import ModuleType
from typing import Any, cast

import pytest

from recollectium.embeddings import (
    BuiltinFastEmbedProvider,
    _cache_tree_has_model_artifact,
    _fastembed_readiness_worker,
    _is_model_artifact_file,
    chunk_text_for_profile,
)
from recollectium.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
    EmbeddingReadinessTimeoutError,
    ValidationError,
)
from recollectium.models import SPACE_USER, STATUS_ACTIVE, Memory, SearchResult
from recollectium.search import ChunkCandidate, rank_memory_candidates
from recollectium.storage import SQLiteMemoryStore


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
        "model": "BAAI/bge-base-en-v1.5",
        "dimensions": 768,
        "version": "1",
        "profile": "builtin-fastembed-bge-base-en-v1-5-v1",
        "max_tokens": 512,
        "chunk_tokens": 384,
        "chunk_overlap_tokens": 64,
        "query_prompt_policy": "raw",
    }

    legacy_provider = BuiltinFastEmbedProvider("jinaai/jina-embeddings-v2-small-en")
    assert (
        legacy_provider.embedding_profile["model"]
        == "jinaai/jina-embeddings-v2-small-en"
    )
    assert legacy_provider.embedding_profile["dimensions"] == 512
    assert (
        legacy_provider.embedding_profile["profile"]
        == "builtin-fastembed-jina-v2-small-en-v1"
    )


def test_provider_cache_artifact_detection_handles_expected_cache_shapes(
    tmp_path: Path,
) -> None:
    provider = BuiltinFastEmbedProvider(cache_dir=None)
    assert not provider.has_cached_model_artifact()

    cache_root = tmp_path / "cache"
    provider = BuiltinFastEmbedProvider(cache_dir=cache_root)
    assert not provider.has_cached_model_artifact()

    artifact = (
        cache_root
        / "models--qdrant--bge-base-en-v1.5-onnx-q"
        / "snapshots"
        / "snapshot-id"
        / "model_optimized.onnx"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"artifact")
    assert provider.has_cached_model_artifact()


def test_provider_cache_artifact_detection_handles_bge_gcs_cache_layout(
    tmp_path: Path,
) -> None:
    provider = BuiltinFastEmbedProvider(cache_dir=tmp_path)
    artifact = tmp_path / "fast-bge-base-en-v1.5" / "model_optimized.onnx"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"artifact")

    assert provider.has_cached_model_artifact()


def test_provider_cache_artifact_detection_handles_jina_hf_cache_layout(
    tmp_path: Path,
) -> None:
    provider = BuiltinFastEmbedProvider(
        "jinaai/jina-embeddings-v2-small-en", cache_dir=tmp_path
    )
    artifact = (
        tmp_path
        / "models--xenova--jina-embeddings-v2-small-en"
        / "snapshots"
        / "snapshot-id"
        / "onnx"
        / "model.onnx"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"artifact")

    assert provider.has_cached_model_artifact()


def test_provider_cache_artifact_detection_ignores_metadata_only_cache(
    tmp_path: Path,
) -> None:
    provider = BuiltinFastEmbedProvider(cache_dir=tmp_path)
    cache_root = tmp_path / "models--qdrant--bge-base-en-v1.5-onnx-q"
    refs = cache_root / "refs"
    snapshot = cache_root / "snapshots" / "snapshot-id"
    refs.mkdir(parents=True)
    snapshot.mkdir(parents=True)
    (refs / "main").write_text("snapshot-id", encoding="utf-8")
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    (snapshot / "tokenizer.json").write_text("{}", encoding="utf-8")
    (snapshot / "model.onnx").write_bytes(b"wrong payload name")

    assert not provider.has_cached_model_artifact()


def test_model_artifact_file_detection_ignores_incomplete_and_stat_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    incomplete = tmp_path / "model.onnx.incomplete"
    incomplete.write_bytes(b"partial")
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"artifact")
    missing = tmp_path / "missing"

    assert not _cache_tree_has_model_artifact(incomplete)
    assert not _cache_tree_has_model_artifact(missing)
    assert not _is_model_artifact_file(incomplete)
    assert not _is_model_artifact_file(missing)

    original_stat = Path.stat

    def raising_stat(self: Path, *args: object, **kwargs: object) -> object:
        if self == artifact:
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", raising_stat)

    assert not _is_model_artifact_file(artifact)

    class StatFailingPath:
        name = "model.onnx"

        def is_file(self) -> bool:
            return True

        def stat(self) -> object:
            raise OSError("stat failed")

    assert not _is_model_artifact_file(cast(Path, StatFailingPath()))


def test_provider_rejects_unsupported_model() -> None:
    with pytest.raises(EmbeddingModelUnavailableError) as exc_info:
        BuiltinFastEmbedProvider("unknown-model")

    message = str(exc_info.value)
    assert "unsupported built-in FastEmbed model 'unknown-model'" in message
    assert "BAAI/bge-base-en-v1.5" in message
    assert "jinaai/jina-embeddings-v2-small-en" in message


def test_real_embedding_shape_is_768() -> None:
    pytest.importorskip("fastembed")
    provider = BuiltinFastEmbedProvider()
    vector = provider.embed("Recollectium should return stable embedding dimensions")

    assert len(vector) == 768
    assert any(value != 0.0 for value in vector)


def test_semantic_search_returns_relevant_memory(tmp_path: Path) -> None:
    provider = BuiltinFastEmbedProvider()
    store = SQLiteMemoryStore(tmp_path / "semantic.db")

    memory = build_memory("mem-1", "Need to fix a release-blocking software bug")
    store.insert_memory(
        memory,
        embedding=provider.embed(memory.content),
        embedding_profile=provider.embedding_profile,
    )

    candidates = store.list_candidates(
        space=SPACE_USER, embedding_profile=provider.embedding_profile
    )
    results = rank_memory_candidates(
        query="repair software defect",
        candidates=candidates,
        embedding_provider=provider,
    )

    assert results
    assert results[0].memory.id == "mem-1"
    assert results[0].score > 0
    assert results[0].rank == 1


def test_ranking_includes_score_and_rank_order() -> None:
    provider = BuiltinFastEmbedProvider()

    primary = build_memory("mem-1", "buy apples bananas and fresh fruit")
    secondary = build_memory("mem-2", "plan database migration rollback")
    candidates = [
        (secondary, provider.embed(secondary.content)),
        (primary, provider.embed(primary.content)),
    ]

    results = rank_memory_candidates(
        query="fresh fruit groceries",
        candidates=candidates,
        embedding_provider=provider,
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


def test_chunk_text_for_profile_creates_single_chunk_at_boundary() -> None:
    provider = BuiltinFastEmbedProvider()
    profile = dict(provider.embedding_profile)
    profile["chunk_tokens"] = 4
    profile["chunk_overlap_tokens"] = 1

    text = "one two three four"
    chunks = chunk_text_for_profile(text, profile)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == text
    assert chunks[0].token_start == 0
    assert chunks[0].token_end == 4


def test_chunk_text_for_profile_splits_with_overlap_without_truncation() -> None:
    provider = BuiltinFastEmbedProvider()
    profile = dict(provider.embedding_profile)
    profile["chunk_tokens"] = 4
    profile["chunk_overlap_tokens"] = 1

    text = "zero one two three four five six"
    chunks = chunk_text_for_profile(text, profile)

    assert [chunk.text for chunk in chunks] == [
        "zero one two three",
        "three four five six",
    ]
    assert [(chunk.token_start, chunk.token_end) for chunk in chunks] == [
        (0, 4),
        (3, 7),
    ]
    covered_tokens = []
    for chunk in chunks:
        covered_tokens.extend(chunk.text.split())
    assert "six" in covered_tokens


def test_chunk_text_for_profile_rejects_overlap_greater_than_or_equal_to_chunk_size() -> (
    None
):
    provider = BuiltinFastEmbedProvider()
    profile = dict(provider.embedding_profile)
    profile["chunk_tokens"] = 4
    profile["chunk_overlap_tokens"] = 4

    with pytest.raises(
        EmbeddingGenerationError,
        match="chunk_overlap_tokens must be smaller than chunk_tokens",
    ):
        chunk_text_for_profile("zero one two three", profile)


def test_chunk_text_for_profile_handles_empty_text_and_bad_token_settings() -> None:
    provider = BuiltinFastEmbedProvider()
    profile = dict(provider.embedding_profile)

    chunks = chunk_text_for_profile("   ", profile)
    assert len(chunks) == 1

    empty_chunk = chunks[0]
    assert empty_chunk.text == ""
    assert empty_chunk.token_start == 0
    assert empty_chunk.token_end == 0

    bad_chunk_profile = dict(profile)
    bad_chunk_profile["chunk_tokens"] = True
    with pytest.raises(EmbeddingGenerationError, match="chunk_tokens"):
        chunk_text_for_profile("hello", bad_chunk_profile)

    bad_overlap_profile = dict(profile)
    bad_overlap_profile["chunk_overlap_tokens"] = -1
    with pytest.raises(EmbeddingGenerationError, match="chunk_overlap_tokens"):
        chunk_text_for_profile("hello", bad_overlap_profile)


def test_builtin_fastembed_embed_handles_empty_text_and_empty_provider_result() -> None:
    provider = BuiltinFastEmbedProvider()
    assert provider.embed("   ") == [0.0] * provider.dimensions

    class EmptyEmbedder:
        def embed(self, texts: list[str], batch_size: int) -> list[list[float]]:
            return []

    provider._embedder = EmptyEmbedder()
    with pytest.raises(EmbeddingGenerationError, match="no vector"):
        provider.embed("hello")


def test_builtin_fastembed_similarity_validates_vectors() -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(EmbeddingGenerationError, match="same size"):
        provider.similarity([1.0, 0.0], [1.0])

    with pytest.raises(EmbeddingGenerationError, match="embedding vector size"):
        provider.similarity([1.0, 0.0], [1.0, 0.0])

    assert (
        provider.similarity([0.0] * provider.dimensions, [1.0] * provider.dimensions)
        == 0.0
    )


def test_builtin_fastembed_get_embedder_import_load_and_cache_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    BuiltinFastEmbedProvider._shared_embedders.clear()
    monkeypatch.setitem(sys.modules, "fastembed", None)
    with pytest.raises(EmbeddingProviderUnavailableError):
        BuiltinFastEmbedProvider()._get_embedder()

    fastembed_module = ModuleType("fastembed")

    class BrokenTextEmbedding:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("model unavailable")

    setattr(fastembed_module, "TextEmbedding", BrokenTextEmbedding)
    monkeypatch.setitem(sys.modules, "fastembed", fastembed_module)
    with pytest.raises(EmbeddingModelUnavailableError, match="failed to load"):
        BuiltinFastEmbedProvider()._get_embedder()

    class WorkingTextEmbedding:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def embed(self, texts: list[str], batch_size: int) -> list[list[float]]:
            return [[1.0] + [0.0] * 511 for _text in texts]

    setattr(fastembed_module, "TextEmbedding", WorkingTextEmbedding)
    assert WorkingTextEmbedding().embed(["hello"], batch_size=1)[0][0] == 1.0
    provider = BuiltinFastEmbedProvider(cache_dir="/tmp/recollectium-models")
    embedder = provider._get_embedder()
    assert embedder.kwargs["cache_dir"] == "/tmp/recollectium-models"
    assert provider._get_embedder() is embedder
    other_provider = BuiltinFastEmbedProvider(cache_dir="/tmp/recollectium-models")
    assert other_provider._get_embedder() is embedder
    separate_provider = BuiltinFastEmbedProvider(cache_dir="/tmp/other-models")
    assert separate_provider._get_embedder() is not embedder
    BuiltinFastEmbedProvider._shared_embedders.clear()


def test_builtin_fastembed_dimension_validation_and_zero_ready_check() -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(EmbeddingDimensionMismatchError, match="expected 768"):
        provider._validate_dimensions([1.0])

    class ZeroProvider(BuiltinFastEmbedProvider):
        def embed(self, text: str) -> list[float]:
            return [0.0] * self.dimensions

    with pytest.raises(EmbeddingGenerationError, match="empty vector"):
        ZeroProvider()._ensure_ready_unbounded()

    class ReadyProvider(BuiltinFastEmbedProvider):
        def embed(self, text: str) -> list[float]:
            return [1.0] + [0.0] * (self.dimensions - 1)

    ReadyProvider()._ensure_ready_unbounded()

    zero_vector = [0.0] * provider.dimensions
    assert provider._normalize_vector(zero_vector) == zero_vector


class FakeConnection:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.closed = False

    def send(self, payload: dict[str, object]) -> None:
        self.messages.append(payload)

    def close(self) -> None:
        self.closed = True


def test_fastembed_readiness_worker_reports_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class ReadyProvider:
        configured_models: list[str] = []

        def __init__(self, model_name: str, *, cache_dir: str | None = None) -> None:
            self.configured_models.append(model_name)
            self.cache_dir = cache_dir

        def _ensure_ready_unbounded(self) -> None:
            pass

    monkeypatch.setattr(
        "recollectium.embeddings.BuiltinFastEmbedProvider", ReadyProvider
    )
    success_connection = FakeConnection()
    _fastembed_readiness_worker(
        cast(Any, success_connection), "legacy-model", "/tmp/models"
    )
    assert ReadyProvider.configured_models == ["legacy-model"]
    assert success_connection.messages == [{"ok": True}]
    assert success_connection.closed is True

    class NoisyReadyProvider:
        def __init__(self, model_name: str, *, cache_dir: str | None = None) -> None:
            self.model_name = model_name
            self.cache_dir = cache_dir

        def _ensure_ready_unbounded(self) -> None:
            print("readiness stdout noise")
            print("readiness stderr noise", file=sys.stderr)

    monkeypatch.setattr(
        "recollectium.embeddings.BuiltinFastEmbedProvider", NoisyReadyProvider
    )
    noisy_connection = FakeConnection()
    _fastembed_readiness_worker(cast(Any, noisy_connection), "legacy-model", None, True)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert noisy_connection.messages == [{"ok": True}]
    assert noisy_connection.closed is True

    class FailingProvider:
        def __init__(self, model_name: str, *, cache_dir: str | None = None) -> None:
            self.model_name = model_name
            self.cache_dir = cache_dir

        def _ensure_ready_unbounded(self) -> None:
            raise EmbeddingModelUnavailableError(f"missing model {self.model_name}")

    monkeypatch.setattr(
        "recollectium.embeddings.BuiltinFastEmbedProvider", FailingProvider
    )
    failure_connection = FakeConnection()
    _fastembed_readiness_worker(cast(Any, failure_connection), "legacy-model", None)
    assert failure_connection.messages == [
        {
            "ok": False,
            "error_type": "EmbeddingModelUnavailableError",
            "message": "missing model legacy-model",
        }
    ]
    assert failure_connection.closed is True
    assert FakeProcess([]).is_alive() is False


class FakeProcess:
    def __init__(self, alive_results: list[bool]) -> None:
        self.alive_results = alive_results
        self.started = False
        self.terminated = False
        self.killed = False

    def start(self) -> None:
        self.started = True

    def join(self, timeout: float | None = None) -> None:
        pass

    def is_alive(self) -> bool:
        if self.alive_results:
            return self.alive_results.pop(0)
        return False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


class FakeParentConnection:
    def __init__(self, result: dict[str, object] | None) -> None:
        self.result = result
        self.closed = False

    def poll(self) -> bool:
        return self.result is not None

    def recv(self) -> dict[str, object]:
        assert self.result is not None
        return self.result

    def close(self) -> None:
        self.closed = True


class FakeChildConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSpawnContext:
    def __init__(
        self,
        result: dict[str, object] | None,
        alive_results: list[bool] | None = None,
    ) -> None:
        self.parent = FakeParentConnection(result)
        self.child = FakeChildConnection()
        self.process = FakeProcess(alive_results or [False])

    def Pipe(self, *, duplex: bool) -> tuple[FakeParentConnection, FakeChildConnection]:
        assert duplex is False
        return self.parent, self.child

    def Process(self, *, target: object, args: tuple[object, ...]) -> FakeProcess:
        assert target is _fastembed_readiness_worker
        assert args == (self.child, "BAAI/bge-base-en-v1.5", None)
        return self.process


def test_builtin_fastembed_ensure_ready_timeout_and_result_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BuiltinFastEmbedProvider()

    with pytest.raises(EmbeddingReadinessTimeoutError, match="0 seconds"):
        provider.ensure_ready(timeout_seconds=0)

    timeout_context = FakeSpawnContext(None, alive_results=[True, True, False])
    monkeypatch.setattr(
        "recollectium.embeddings.multiprocessing.get_context",
        lambda method: timeout_context,
    )
    with pytest.raises(EmbeddingReadinessTimeoutError, match="timed out"):
        provider.ensure_ready(timeout_seconds=0.01)
    assert timeout_context.process.terminated is True
    assert timeout_context.process.killed is True

    no_result_context = FakeSpawnContext(None)
    monkeypatch.setattr(
        "recollectium.embeddings.multiprocessing.get_context",
        lambda method: no_result_context,
    )
    with pytest.raises(EmbeddingGenerationError, match="without reporting status"):
        provider.ensure_ready(timeout_seconds=1)

    ok_context = FakeSpawnContext({"ok": True})
    monkeypatch.setattr(
        "recollectium.embeddings.multiprocessing.get_context",
        lambda method: ok_context,
    )
    provider.ensure_ready(timeout_seconds=1)

    error_cases: list[tuple[str, type[Exception]]] = [
        ("EmbeddingProviderUnavailableError", EmbeddingProviderUnavailableError),
        ("EmbeddingModelUnavailableError", EmbeddingModelUnavailableError),
        ("EmbeddingDimensionMismatchError", EmbeddingDimensionMismatchError),
        ("EmbeddingReadinessTimeoutError", EmbeddingReadinessTimeoutError),
        ("OtherError", EmbeddingGenerationError),
    ]
    for error_type, expected_error in error_cases:
        error_context = FakeSpawnContext(
            {"ok": False, "error_type": error_type, "message": "mapped error"}
        )
        monkeypatch.setattr(
            "recollectium.embeddings.multiprocessing.get_context",
            lambda method, context=error_context: context,
        )
        with pytest.raises(expected_error, match="mapped error"):
            provider.ensure_ready(timeout_seconds=1)


def test_rank_memory_candidates_deduplicates_parent_memory_by_best_chunk() -> None:
    provider = BuiltinFastEmbedProvider()
    memory = build_memory("mem-1", "parent memory")

    candidates: list[ChunkCandidate] = [
        ChunkCandidate(
            memory=memory,
            embedding=provider.embed("today I should buy groceries and fruit"),
            chunk_index=0,
            matched_text="today I should buy groceries and fruit",
            snippet="buy groceries and fruit",
        ),
        ChunkCandidate(
            memory=memory,
            embedding=provider.embed("database migrations and SQL rollback planning"),
            chunk_index=1,
            matched_text="database migrations and SQL rollback planning",
            snippet="SQL rollback planning",
        ),
    ]

    results = rank_memory_candidates(
        query="buy fruit",
        candidates=candidates,
        embedding_provider=provider,
    )

    assert len(results) == 1
    assert results[0].memory.id == "mem-1"
    assert results[0].chunk_index == 0
    assert results[0].matched_text == "today I should buy groceries and fruit"
    assert results[0].snippet == "buy groceries and fruit"


def test_search_result_json_round_trip_with_matched_context() -> None:
    result = SearchResult(
        memory=build_memory("mem-1", "hello world"),
        score=0.91,
        rank=1,
        matched_text="hello",
        snippet="hello",
        chunk_index=2,
    )

    restored = SearchResult.from_json(result.to_json())

    assert restored.memory.id == result.memory.id
    assert restored.score == result.score
    assert restored.rank == result.rank
    assert restored.matched_text == "hello"
    assert restored.snippet == "hello"
    assert restored.chunk_index == 2


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
