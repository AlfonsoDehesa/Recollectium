from contextlib import contextmanager
import json
import logging
from pathlib import Path
import sqlite3
import sys
import threading
from typing import Any, Iterator, cast

import pytest
from pytest import CaptureFixture

from recollectium.core import RecollectiumCore
from recollectium.embeddings import BuiltinFastEmbedProvider
from recollectium.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    NotFoundError,
    RecollectiumError,
    ReembeddingFailedError,
    ValidationError,
)
from recollectium.model_state import read_model_state, write_model_state
from recollectium.models import SPACE_USER, SPACE_WORKSPACE, STATUS_ARCHIVED


@contextmanager
def sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    try:
        yield connection
    finally:
        connection.commit()
        connection.close()


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.embedding_profile = {
            "provider": "fake",
            "model": "fake-model",
            "dimensions": 3,
            "version": "1",
            "profile": "fake-profile-v1",
            "max_tokens": 16,
            "chunk_tokens": 4,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }

    def embed(self, text: str) -> list[float]:
        size = float(len(text))
        first = float(ord(text[0])) if text else 0.0
        return [size, first, 1.0]

    def similarity(self, first: list[float], second: list[float]) -> float:
        return sum(a * b for a, b in zip(first, second, strict=True))


class ConfigurableEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, vector: list[float], dimensions: object = 3) -> None:
        super().__init__()
        self.vector = vector
        self.embedding_profile["dimensions"] = dimensions

    def embed(self, text: str) -> list[float]:
        return self.vector


class BlockingFakeEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.block_texts: set[str] = set()
        self.started = threading.Event()
        self.release = threading.Event()
        self.fail_texts: set[str] = set()

    def embed(self, text: str) -> list[float]:
        if text in self.block_texts:
            self.started.set()
            if not self.release.wait(5):
                raise RuntimeError("timed out waiting to unblock fake embedding")
        if text in self.fail_texts:
            raise RuntimeError(f"forced embedding failure for {text}")
        return super().embed(text)


def test_ensure_model_ready_reports_progress_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    provider = FakeEmbeddingProvider()
    events: list[dict[str, Any]] = []
    core = RecollectiumCore(
        db_path=tmp_path / "ready.db",
        embedding_provider=provider,
    )

    core._ensure_model_ready(
        progress_callback=events.append,
        suppress_provider_output=True,
    )

    assert events == [{"phase": "Preparing embedding model"}]


def _isolate_core_xdg_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))


def _write_matching_model_state(core: RecollectiumCore, state_dir: Path) -> None:
    profile = core.embedding_provider.embedding_profile
    dimensions = profile["dimensions"]
    assert isinstance(dimensions, int)
    write_model_state(
        state_dir,
        model=str(profile["model"]),
        dimensions=dimensions,
        profile=str(profile["profile"]),
        model_cache_path=str(core.config.model_cache_path),
    )


def _write_fake_fastembed_cache_artifact(cache_root: Path) -> None:
    artifact = (
        cache_root
        / "models--qdrant--bge-base-en-v1.5-onnx-q"
        / "snapshots"
        / "test-snapshot"
        / "model_optimized.onnx"
    )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"fake model artifact")


def test_ensure_model_ready_reprepares_matching_state_when_cache_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_core_xdg_dirs(tmp_path, monkeypatch)
    state_dir = tmp_path / "state" / "recollectium"
    calls: list[bool] = []

    def fake_ensure_ready(
        self: BuiltinFastEmbedProvider, *, suppress_output: bool = False
    ) -> None:
        calls.append(suppress_output)

    monkeypatch.setattr(BuiltinFastEmbedProvider, "ensure_ready", fake_ensure_ready)
    core = RecollectiumCore(db_path=tmp_path / "missing-cache.db")
    _write_matching_model_state(core, state_dir)

    core._ensure_model_ready(suppress_provider_output=True)

    assert calls == [True]
    state = read_model_state(state_dir)
    assert state is not None
    assert state["model_cache_path"] == str(core.config.model_cache_path)


def test_ensure_model_ready_skips_matching_state_when_cache_artifact_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_core_xdg_dirs(tmp_path, monkeypatch)
    state_dir = tmp_path / "state" / "recollectium"
    calls: list[bool] = []

    def fake_ensure_ready(
        self: BuiltinFastEmbedProvider, *, suppress_output: bool = False
    ) -> None:
        calls.append(suppress_output)

    monkeypatch.setattr(BuiltinFastEmbedProvider, "ensure_ready", fake_ensure_ready)
    core = RecollectiumCore(db_path=tmp_path / "present-cache.db")
    _write_matching_model_state(core, state_dir)
    _write_fake_fastembed_cache_artifact(core.config.model_cache_path)

    core._ensure_model_ready(suppress_provider_output=True)

    assert calls == []


def test_ensure_model_ready_suppresses_matching_state_cache_probe_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    _isolate_core_xdg_dirs(tmp_path, monkeypatch)
    state_dir = tmp_path / "state" / "recollectium"

    def fake_ensure_ready(
        self: BuiltinFastEmbedProvider, *, suppress_output: bool = False
    ) -> None:
        raise AssertionError("matching state should return before provider readiness")

    def noisy_cache_probe(model_cache_path: str | None) -> bool:
        assert model_cache_path == str(core.config.model_cache_path)
        print("cache probe stdout leak")
        print("cache probe stderr leak", file=sys.stderr)
        return True

    monkeypatch.setattr(BuiltinFastEmbedProvider, "ensure_ready", fake_ensure_ready)
    core = RecollectiumCore(db_path=tmp_path / "quiet-cache-probe.db")
    _write_matching_model_state(core, state_dir)
    monkeypatch.setattr(core, "_model_cache_artifact_is_present", noisy_cache_probe)

    core._ensure_model_ready(suppress_provider_output=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def make_memories_stale(
    db_path: Path,
    memory_ids: list[str],
    active_profile: dict[str, object],
) -> None:
    stale_profile = {
        **active_profile,
        "profile": "stale-profile",
    }
    stale_json = json.dumps(stale_profile, sort_keys=True)
    placeholders = ", ".join("?" for _ in memory_ids)
    with sqlite_connection(db_path) as connection:
        connection.execute(
            f"UPDATE memories SET embedding_profile_json = ? WHERE id IN ({placeholders})",
            [stale_json, *memory_ids],
        )


def test_core_user_memory_flow_add_get_search_list_update_archive(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(db_path=tmp_path / "core.db")

    created = core.add_memory(
        space="user",
        type="note",
        content="Need to fix bug before release",
        metadata={"source": "chat"},
    )

    assert created.id
    assert created.created_at
    assert created.updated_at

    fetched = core.get_memory(created.id)
    assert fetched.id == created.id
    assert fetched.last_accessed_at is not None

    search_results = core.search_user_memories("repair defect", type="note")
    assert [result.memory.id for result in search_results] == [created.id]

    assert core.search_user_memories("repair defect", type="decision") == []

    listed = core.list_memories(space="user", type="note")
    assert [memory.id for memory in listed] == [created.id]

    assert core.list_memories(space="user", type="decision") == []

    updated = core.update_memory(created.id, content="Need to write release notes")
    assert updated.content == "Need to write release notes"
    assert updated.updated_at != created.updated_at

    refreshed_results = core.search_user_memories("release notes")
    assert refreshed_results[0].memory.id == created.id

    archived = core.archive_memory(created.id)
    assert archived.status == STATUS_ARCHIVED

    active_results = core.search_user_memories("release notes")
    assert active_results == []

    archived_results = core.search_user_memories("release notes", include_archived=True)
    assert [result.memory.id for result in archived_results] == [created.id]


def test_core_workspace_search_isolation_by_workspace_uid(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(db_path=tmp_path / "workspace.db")

    workspace_a = core.add_memory(
        space=SPACE_WORKSPACE,
        type="task_context",
        content="Need to purchase milk",
        workspace_uid="workspace-alpha",
    )
    workspace_b = core.add_memory(
        space=SPACE_WORKSPACE,
        type="task_context",
        content="Need to purchase bread",
        workspace_uid="workspace-beta",
    )

    assert workspace_a.workspace_uid == "workspace-alpha"

    search_a = core.search_workspace_memories(
        "buy milk", workspace_uid="workspace-alpha", type="task_context"
    )
    assert [result.memory.id for result in search_a] == [workspace_a.id]

    search_b = core.search_workspace_memories(
        "buy milk", workspace_uid="workspace-beta", type="task_context"
    )
    assert [result.memory.id for result in search_b] == [workspace_b.id]

    assert (
        core.search_workspace_memories(
            "buy milk", workspace_uid="workspace-alpha", type="fact"
        )
        == []
    )

    user_results = core.search_user_memories("buy")
    assert user_results == []


def test_core_search_logs_omit_raw_query_text(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    core = RecollectiumCore(db_path=tmp_path / "privacy.db")
    core.add_memory(space="user", type="fact", content="Search privacy test")
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="Workspace search privacy test",
        workspace_uid="privacy-workspace",
    )

    secret_query = "needle-secret-query"
    with caplog.at_level(logging.INFO, logger="recollectium.core"):
        core.search_user_memories(secret_query)
        core.search_workspace_memories(secret_query, workspace_uid="privacy-workspace")

    assert secret_query not in caplog.text
    contexts = [record.__dict__.get("context") for record in caplog.records]
    search_contexts = [context for context in contexts if isinstance(context, dict)]
    assert search_contexts
    assert all("query" not in context for context in search_contexts)
    assert {context.get("query_len") for context in search_contexts} == {
        len(secret_query)
    }
    assert {context.get("space") for context in search_contexts} == {
        SPACE_USER,
        SPACE_WORKSPACE,
    }


def test_core_persistence_across_instances_and_not_found(tmp_path: Path) -> None:
    db_path = tmp_path / "persist.db"
    first_core = RecollectiumCore(db_path=db_path)
    created = first_core.add_memory(
        space="user", type="fact", content="Kaylee likes tea"
    )

    second_core = RecollectiumCore(db_path=db_path)
    loaded = second_core.get_memory(created.id)
    assert loaded.content == "Kaylee likes tea"

    with pytest.raises(NotFoundError):
        second_core.get_memory("missing-id")


def test_workspace_identity_validation(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(db_path=tmp_path / "workspace-uid.db")

    with pytest.raises(ValidationError, match="workspace_uid is required"):
        core.add_memory(
            space=SPACE_WORKSPACE,
            type="task_context",
            content="Need to purchase milk",
        )

    with pytest.raises(ValidationError, match="user memories must not include"):
        core.add_memory(
            space="user",
            type="preference",
            content="I like short answers",
            workspace_uid="workspace-alpha",
        )

    with pytest.raises(ValidationError, match="workspace_uid"):
        core.search_workspace_memories("buy milk", workspace_uid=" ")


def test_core_rejects_invalid_list_limit(tmp_path: Path) -> None:
    core = RecollectiumCore(db_path=tmp_path / "limit.db")

    with pytest.raises(ValidationError, match="positive integer"):
        core.list_memories(limit=0)


def test_default_db_path_uses_xdg_style_data_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    core = RecollectiumCore(embedding_provider=FakeEmbeddingProvider())

    assert core.store.db_path == tmp_path / "data" / "recollectium" / "recollectium.db"


def test_core_default_provider_uses_recollectium_model_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

    class CapturingProvider(FakeEmbeddingProvider):
        def __init__(
            self, model_name: str, *, cache_dir: str | Path | None = None
        ) -> None:
            super().__init__()
            self.model_name = model_name
            self.cache_dir = str(cache_dir) if cache_dir is not None else None

    monkeypatch.setattr("recollectium.core.BuiltinFastEmbedProvider", CapturingProvider)

    core = RecollectiumCore(db_path=tmp_path / "cache.db")

    assert isinstance(core.embedding_provider, CapturingProvider)
    assert core.embedding_provider.cache_dir == str(
        tmp_path / "cache" / "recollectium" / "models"
    )


def test_workspace_search_requires_non_empty_workspace_uid(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "workspace-search.db",
        embedding_provider=FakeEmbeddingProvider(),
    )

    with pytest.raises(ValidationError, match="workspace_uid is required"):
        core.search_workspace_memories("hello", workspace_uid=None)


def test_update_memory_source_and_sensitivity_without_model_updates(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "source-sensitivity.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    memory = core.add_memory(space=SPACE_USER, type="fact", content="plain memory")

    updated = core.update_memory(
        memory.id,
        source="manual import",
        sensitivity="low",
    )

    assert updated.source == "manual import"
    assert updated.sensitivity == "low"

    source_only = core.update_memory(memory.id, source="chat")
    assert source_only.source == "chat"

    sensitivity_only = core.update_memory(memory.id, sensitivity="normal")
    assert sensitivity_only.sensitivity == "normal"

    with pytest.raises(ValidationError, match="at least one update field"):
        core.update_memory(memory.id)


def test_update_memory_rejects_blank_source_and_sensitivity(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "blank-source.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    memory = core.add_memory(space=SPACE_USER, type="fact", content="plain memory")

    with pytest.raises(ValidationError, match="source"):
        core.update_memory(memory.id, source=" ")

    with pytest.raises(ValidationError, match="sensitivity"):
        core.update_memory(memory.id, sensitivity=" ")


def test_ensure_embedding_ready_fallback_validates_profile_dimensions(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "ready.db",
        embedding_provider=ConfigurableEmbeddingProvider([1.0, 2.0, 3.0]),
    )
    core.ensure_embedding_ready()

    bool_dimensions = RecollectiumCore(
        db_path=tmp_path / "bool-dimensions.db",
        embedding_provider=ConfigurableEmbeddingProvider([1.0], True),
    )
    with pytest.raises(EmbeddingGenerationError, match="integer dimensions"):
        bool_dimensions.ensure_embedding_ready()

    missing_dimensions = RecollectiumCore(
        db_path=tmp_path / "missing-dimensions.db",
        embedding_provider=ConfigurableEmbeddingProvider([1.0], "3"),
    )
    with pytest.raises(EmbeddingGenerationError, match="integer dimensions"):
        missing_dimensions.ensure_embedding_ready()

    mismatch = RecollectiumCore(
        db_path=tmp_path / "dimension-mismatch.db",
        embedding_provider=ConfigurableEmbeddingProvider([1.0, 2.0], 3),
    )
    with pytest.raises(EmbeddingDimensionMismatchError, match="expected 3"):
        mismatch.ensure_embedding_ready()


def test_add_memory_persists_chunk_embeddings_and_searches_from_chunks(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "chunks.db"
    core = RecollectiumCore(db_path=db_path)

    created = core.add_memory(
        space=SPACE_USER,
        type="note",
        content="dragon fruit smoothie prep for breakfast",
    )

    results = core.search_user_memories("dragon fruit breakfast")
    assert [result.memory.id for result in results] == [created.id]
    assert results[0].matched_text is not None
    assert results[0].chunk_index == 0

    with sqlite_connection(db_path) as connection:
        chunk_count = connection.execute(
            "SELECT COUNT(*) FROM embedding_chunks WHERE memory_id = ?",
            (created.id,),
        ).fetchone()[0]
        assert chunk_count >= 1


def test_update_memory_content_refreshes_chunks(tmp_path: Path) -> None:
    db_path = tmp_path / "update-chunks.db"
    core = RecollectiumCore(db_path=db_path)

    created = core.add_memory(
        space=SPACE_USER,
        type="note",
        content="old release checklist",
    )
    updated = core.update_memory(created.id, content="new launch checklist")
    assert updated.content == "new launch checklist"

    with sqlite_connection(db_path) as connection:
        chunk_texts = connection.execute(
            "SELECT content FROM embedding_chunks WHERE memory_id = ? ORDER BY chunk_index ASC",
            (created.id,),
        ).fetchall()
    assert chunk_texts
    assert all("new" in row[0] for row in chunk_texts)
    assert all("old" not in row[0] for row in chunk_texts)


def test_startup_reembeds_stale_memories_for_active_profile(tmp_path: Path) -> None:
    db_path = tmp_path / "startup-stale.db"
    core = RecollectiumCore(db_path=db_path)
    memory = core.add_memory(space=SPACE_USER, type="fact", content="kiwi notebook")

    stale_profile = {
        **core.embedding_provider.embedding_profile,
        "profile": "stale-profile",
    }
    core.store.update_memory(memory.id, embedding_profile=stale_profile)

    restarted = RecollectiumCore(db_path=db_path, auto_startup_reembedding=True)
    stale_count = restarted.store.count_memories_needing_profile_reembedding(
        embedding_profile=restarted.embedding_provider.embedding_profile,
        space=SPACE_USER,
    )
    assert stale_count == 0

    jobs = restarted.list_embedding_jobs(limit=1)
    assert jobs
    assert jobs[0]["state"] == "completed"
    assert jobs[0]["total_count"] >= 1

    status = restarted.active_embedding_status()
    assert status["provider_status"] == "configured"
    assert status["model_status"] == "managed_by_recollectium_cache"
    assert status["model_cache_path"].endswith("recollectium/models")
    assert status["runtime"] == {"name": "fastembed", "threads": 1, "parallel": None}
    assert status["startup_reembedding_job_id"] == jobs[0]["id"]
    assert status["startup_reembedding_status_path"].endswith(jobs[0]["id"])
    assert status["embedding_jobs_status_path"] == "/v1/embedding/jobs"
    assert status["recent_embedding_jobs"]


def test_active_embedding_status_for_custom_provider_is_not_recollectium_managed(
    tmp_path: Path,
) -> None:
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(
        db_path=tmp_path / "custom-status.db", embedding_provider=provider
    )

    status = core.active_embedding_status()

    assert status["provider_status"] == "configured"
    assert status["embedding_profile"] == provider.embedding_profile
    assert status["model_status"] == "managed_externally"
    assert status["model_cache_path"] is None
    assert status["runtime"] is None
    assert status["embedding_jobs_status_path"] == "/v1/embedding/jobs"


def test_active_embedding_status_for_injected_builtin_provider_is_not_recollectium_managed(
    tmp_path: Path,
) -> None:
    external_cache = tmp_path / "external-fastembed-cache"
    provider = BuiltinFastEmbedProvider(cache_dir=external_cache)
    core = RecollectiumCore(
        db_path=tmp_path / "injected-builtin-status.db",
        embedding_provider=provider,
    )

    status = core.active_embedding_status()

    assert status["provider_status"] == "configured"
    assert status["embedding_profile"] == provider.embedding_profile
    assert status["model_status"] == "managed_externally"
    assert status["model_cache_path"] is None
    assert status["runtime"] is None


def test_search_reembeds_missing_profile_chunks_below_threshold(tmp_path: Path) -> None:
    db_path = tmp_path / "search-reembed.db"
    core = RecollectiumCore(db_path=db_path)
    created = core.add_memory(
        space=SPACE_WORKSPACE,
        type="task_context",
        content="calibrate laser cutter",
        workspace_uid="shop",
    )

    with sqlite_connection(db_path) as connection:
        connection.execute(
            "DELETE FROM embedding_chunks WHERE memory_id = ?", (created.id,)
        )

    results = core.search_workspace_memories("laser calibration", workspace_uid="shop")
    assert [result.memory.id for result in results] == [created.id]

    with sqlite_connection(db_path) as connection:
        refreshed_chunk_count = connection.execute(
            "SELECT COUNT(*) FROM embedding_chunks WHERE memory_id = ?",
            (created.id,),
        ).fetchone()[0]
    assert refreshed_chunk_count >= 1


def test_search_reembeds_stale_memories_inline_regardless_of_count(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "threshold-inline.db"
    core = RecollectiumCore(db_path=db_path, immediate_reembedding_threshold=1)
    one = core.add_memory(space=SPACE_USER, type="note", content="alpha")
    two = core.add_memory(space=SPACE_USER, type="note", content="beta")

    stale_profile = {
        **core.embedding_provider.embedding_profile,
        "profile": "stale-user-profile",
    }
    core.store.update_memory(one.id, embedding_profile=stale_profile)
    core.store.update_memory(two.id, embedding_profile=stale_profile)

    results = core.search_user_memories("alpha")

    assert [result.memory.id for result in results]
    jobs = core.list_embedding_jobs(limit=1)
    assert jobs[0]["state"] == "completed"
    assert jobs[0]["total_count"] == 2
    assert jobs[0]["processed_count"] == 2
    assert jobs[0]["succeeded_count"] == 2
    assert jobs[0]["failed_count"] == 0
    stale_count = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=core.embedding_provider.embedding_profile,
        space=SPACE_USER,
    )
    assert stale_count == 0


def test_startup_reembedding_runs_inline_when_stale_count_exceeds_threshold(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "startup-inline.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        immediate_reembedding_threshold=10,
    )
    memories = [
        core.add_memory(space=SPACE_USER, type="fact", content=f"startup {index}")
        for index in range(2)
    ]
    make_memories_stale(
        db_path, [memory.id for memory in memories], provider.embedding_profile
    )

    restarted = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        immediate_reembedding_threshold=1,
        auto_startup_reembedding=True,
    )

    job_id = restarted._startup_reembedding_job_id
    assert job_id is not None
    job = restarted.get_embedding_job(job_id)
    assert job["state"] == "completed"
    assert job["processed_count"] == 2
    assert job["succeeded_count"] == 2


def test_reembed_stale_memories_returns_none_when_nothing_is_stale(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "no-stale.db",
        embedding_provider=FakeEmbeddingProvider(),
    )

    assert core._reembed_stale_memories(reason="test") is None


def test_inline_reembedding_completes_and_preserves_memory_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "inline-worker.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        immediate_reembedding_threshold=0,
    )
    first = core.add_memory(
        space=SPACE_USER,
        type="fact",
        content="alpha one",
        metadata={"kept": True},
        source="user",
        confidence=0.8,
        sensitivity="normal",
    )
    second = core.add_memory(space=SPACE_USER, type="fact", content="beta two")
    make_memories_stale(
        db_path,
        [first.id, second.id],
        provider.embedding_profile,
    )

    results = core.search_user_memories("alpha")
    assert [result.memory.id for result in results]

    job = core.list_embedding_jobs(limit=1)[0]
    assert job["state"] == "completed"
    assert job["processed_count"] == 2
    assert job["succeeded_count"] == 2
    assert job["failed_count"] == 0
    assert job["started_at"] is not None
    assert job["completed_at"] is not None

    after = core.get_memory(first.id)
    assert after.content == first.content
    assert after.status == first.status
    assert after.space == first.space
    assert after.workspace_uid == first.workspace_uid
    assert after.type == first.type
    assert after.source == first.source
    assert after.confidence == first.confidence
    assert after.sensitivity == first.sensitivity
    assert after.metadata == first.metadata
    assert after.created_at == first.created_at
    assert after.updated_at == first.updated_at

    stale_count = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_USER,
    )
    assert stale_count == 0
    with sqlite_connection(db_path) as connection:
        chunk_count = connection.execute(
            "SELECT COUNT(*) FROM embedding_chunks WHERE memory_id = ?",
            (first.id,),
        ).fetchone()[0]
    assert chunk_count >= 1


def test_inline_reembedding_reports_failures(tmp_path: Path) -> None:
    db_path = tmp_path / "inline-failure.db"
    provider = BlockingFakeEmbeddingProvider()
    core = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        immediate_reembedding_threshold=1,
    )
    first = core.add_memory(space=SPACE_USER, type="note", content="alpha one")
    second = core.add_memory(space=SPACE_USER, type="note", content="beta two")
    make_memories_stale(
        db_path,
        [first.id, second.id],
        provider.embedding_profile,
    )
    provider.fail_texts.add(first.content)

    with pytest.raises(ReembeddingFailedError) as exc_info:
        core.search_user_memories("alpha")

    job = core.get_embedding_job(exc_info.value.job_id)
    assert job["state"] == "failed"
    assert job["processed_count"] == 2
    assert job["succeeded_count"] == 1
    assert job["failed_count"] == 1
    assert "forced embedding failure" in job["error_message"]

    stale_count = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_USER,
    )
    assert stale_count == 1


def test_inline_reembedding_scope_safety_and_archived_exclusion(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "inline-scope.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        immediate_reembedding_threshold=0,
    )
    user_memory = core.add_memory(space=SPACE_USER, type="fact", content="user alpha")
    workspace_a = core.add_memory(
        space=SPACE_WORKSPACE,
        type="task_context",
        content="workspace alpha",
        workspace_uid="workspace-a",
    )
    workspace_b = core.add_memory(
        space=SPACE_WORKSPACE,
        type="task_context",
        content="workspace beta",
        workspace_uid="workspace-b",
    )
    archived = core.add_memory(space=SPACE_USER, type="fact", content="archived alpha")
    core.archive_memory(archived.id)
    make_memories_stale(
        db_path,
        [user_memory.id, workspace_a.id, workspace_b.id, archived.id],
        provider.embedding_profile,
    )

    results = core.search_workspace_memories("alpha", workspace_uid="workspace-a")
    assert [result.memory.id for result in results]

    job = core.list_embedding_jobs(limit=1)[0]
    assert job["state"] == "completed"
    assert job["total_count"] == 1
    assert job["succeeded_count"] == 1

    workspace_a_stale = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_WORKSPACE,
        workspace_uid="workspace-a",
    )
    workspace_b_stale = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_WORKSPACE,
        workspace_uid="workspace-b",
    )
    user_stale = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_USER,
    )
    assert workspace_a_stale == 0
    assert workspace_b_stale == 1
    assert user_stale == 1

    with sqlite_connection(db_path) as connection:
        archived_profile_json = connection.execute(
            "SELECT embedding_profile_json FROM memories WHERE id = ?",
            (archived.id,),
        ).fetchone()[0]
    assert json.loads(archived_profile_json)["profile"] == "stale-profile"


def test_refresh_stale_embeddings_noops_and_filters(tmp_path: Path) -> None:
    db_path = tmp_path / "force-refresh.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)

    assert core.refresh_stale_embeddings()["refreshed"] is False

    user_memory = core.add_memory(space=SPACE_USER, type="fact", content="user alpha")
    workspace_memory = core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="workspace alpha",
        workspace_uid="team-a",
    )
    make_memories_stale(
        db_path,
        [user_memory.id, workspace_memory.id],
        provider.embedding_profile,
    )

    result = core.refresh_stale_embeddings(
        space=SPACE_WORKSPACE, workspace_uid="team-a"
    )

    assert result["refreshed"] is True
    assert result["stale_count"] == 1
    assert result["job"]["state"] == "completed"  # type: ignore[reportOptionalSubscript]
    workspace_stale = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_WORKSPACE,
        workspace_uid="team-a",
    )
    user_stale = core.store.count_memories_needing_profile_reembedding(
        embedding_profile=provider.embedding_profile,
        space=SPACE_USER,
    )
    assert workspace_stale == 0
    assert user_stale == 1


def test_refresh_stale_embeddings_handles_concurrent_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "force-refresh-race.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)
    memory = core.add_memory(space=SPACE_USER, type="fact", content="race alpha")
    make_memories_stale(db_path, [memory.id], provider.embedding_profile)

    def no_job_created(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(core, "_reembed_stale_memories", no_job_created)

    assert core.refresh_stale_embeddings(space=SPACE_USER) == {
        "refreshed": False,
        "stale_count": 0,
        "job": None,
        "status_path": "/v1/embedding/jobs",
    }


def test_refresh_stale_embeddings_validates_scope_and_reports_failures(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "force-refresh-failure.db"
    provider = BlockingFakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)

    with pytest.raises(ValidationError, match="space must be user or workspace"):
        core.refresh_stale_embeddings(space="bad")
    no_space_result = core.refresh_stale_embeddings(workspace_uid="team-a")
    assert no_space_result["refreshed"] is False
    with pytest.raises(ValidationError, match="workspace_uid requires workspace space"):
        core.refresh_stale_embeddings(space=SPACE_USER, workspace_uid="team-a")

    memory = core.add_memory(space=SPACE_USER, type="fact", content="user alpha")
    make_memories_stale(db_path, [memory.id], provider.embedding_profile)
    provider.fail_texts.add(memory.content)

    with pytest.raises(ReembeddingFailedError) as exc_info:
        core.refresh_stale_embeddings()

    assert exc_info.value.status_path.endswith(exc_info.value.job_id)
    job = core.get_embedding_job(exc_info.value.job_id)
    assert job["state"] == "failed"


def test_clear_embedding_jobs_deletes_selected_audit_records(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "clear-jobs.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    for state in ("pending", "completed", "failed", "in_progress"):
        core.store.create_embedding_job(
            job_id=f"job-{state}",
            state=state,
            total_count=1,
            processed_count=0,
            succeeded_count=0,
            failed_count=0,
            provider="fake",
            model="fake-model",
            embedding_profile=core.embedding_provider.embedding_profile,
        )

    with pytest.raises(ValidationError, match="at least one job state"):
        core.clear_embedding_jobs(states=[])
    with pytest.raises(ValidationError, match="at least one job state"):
        core.store.delete_embedding_jobs(states=[])

    result = core.clear_embedding_jobs()

    assert result == {
        "deleted_count": 3,
        "states": ["completed", "failed", "pending"],
        "deleted_job_ids": ["job-failed", "job-completed", "job-pending"],
    }
    remaining = core.list_embedding_jobs()
    assert [job["state"] for job in remaining] == ["in_progress"]

    with pytest.raises(ValidationError, match="invalid embedding job state"):
        core.clear_embedding_jobs(states=["unknown"])
    with pytest.raises(
        ValidationError, match="in_progress embedding jobs cannot be deleted"
    ):
        core.clear_embedding_jobs(states=("in_progress",))
    assert [job["state"] for job in core.list_embedding_jobs()] == ["in_progress"]


def test_delete_embedding_jobs_detects_rowcount_mismatch(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "clear-jobs-rowcount.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.store.create_embedding_job(
        job_id="job-completed",
        state="completed",
        total_count=1,
        processed_count=1,
        succeeded_count=1,
        failed_count=0,
        provider="fake",
        model="fake-model",
        embedding_profile=core.embedding_provider.embedding_profile,
    )

    original_connect = core.store._connect

    class MismatchedConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def execute(self, sql: str, parameters: Any = ()) -> object:
            result = self.connection.execute(sql, parameters)
            if sql.startswith("DELETE FROM embedding_jobs"):
                return type("MismatchedResult", (), {"rowcount": result.rowcount + 1})()
            return result

    @contextmanager
    def mismatched_connect() -> Iterator[MismatchedConnection]:
        with original_connect() as connection:
            yield MismatchedConnection(connection)

    cast(Any, core.store)._connect = mismatched_connect

    with pytest.raises(
        RecollectiumError, match="embedding job deletion count changed unexpectedly"
    ):
        core.store.delete_embedding_jobs(states=("completed",))


def test_startup_reembedding_noops_when_no_stale_memories(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "startup-noop.db",
        embedding_provider=FakeEmbeddingProvider(),
    )

    assert core._start_startup_reembedding() is None


def test_core_can_skip_startup_reembedding_for_control_commands(tmp_path: Path) -> None:
    db_path = tmp_path / "skip-startup.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)
    memory = core.add_memory(space=SPACE_USER, type="fact", content="stale alpha")
    make_memories_stale(db_path, [memory.id], provider.embedding_profile)

    control_core = RecollectiumCore(
        db_path=db_path,
        embedding_provider=provider,
        auto_startup_reembedding=False,
    )

    assert control_core._startup_reembedding_job_id is None
    assert (
        control_core.store.count_memories_needing_profile_reembedding(
            embedding_profile=provider.embedding_profile
        )
        == 1
    )


def test_startup_reembedding_failure_raises_with_job_status(tmp_path: Path) -> None:
    db_path = tmp_path / "startup-failure.db"
    provider = BlockingFakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)
    memory = core.add_memory(space=SPACE_USER, type="fact", content="startup alpha")
    make_memories_stale(db_path, [memory.id], provider.embedding_profile)
    provider.fail_texts.add(memory.content)

    with pytest.raises(ReembeddingFailedError) as exc_info:
        core._start_startup_reembedding()

    assert exc_info.value.status_path.endswith(exc_info.value.job_id)
    job = core.get_embedding_job(exc_info.value.job_id)
    assert job["state"] == "failed"


def test_process_reembedding_job_can_refresh_existing_job(tmp_path: Path) -> None:
    db_path = tmp_path / "process-existing-job.db"
    provider = FakeEmbeddingProvider()
    core = RecollectiumCore(db_path=db_path, embedding_provider=provider)
    memory = core.add_memory(space=SPACE_USER, type="fact", content="user alpha")
    make_memories_stale(db_path, [memory.id], provider.embedding_profile)
    core.store.create_embedding_job(
        job_id="manual-job",
        state="pending",
        total_count=1,
        processed_count=0,
        succeeded_count=0,
        failed_count=0,
        provider="fake",
        model="fake-model",
        embedding_profile=provider.embedding_profile,
    )

    failed = core._process_reembedding_job(job_id="manual-job", reason="manual")

    assert failed is False
    job = core.get_embedding_job("manual-job")
    assert job["state"] == "completed"
    assert job["processed_count"] == 1


def test_reembedding_preserves_updated_at_for_startup_and_runtime(
    tmp_path: Path,
) -> None:
    startup_db = tmp_path / "startup-preserve-updated-at.db"
    core = RecollectiumCore(db_path=startup_db)
    startup_memory = core.add_memory(space=SPACE_USER, type="fact", content="alpha")

    stale_profile = {
        **core.embedding_provider.embedding_profile,
        "profile": "stale-profile",
    }
    with sqlite_connection(startup_db) as connection:
        connection.execute(
            "UPDATE memories SET embedding_profile_json = ? WHERE id = ?",
            (json.dumps(stale_profile, sort_keys=True), startup_memory.id),
        )

    restarted = RecollectiumCore(db_path=startup_db)
    startup_after = restarted.get_memory(startup_memory.id)
    assert startup_after.updated_at == startup_memory.updated_at

    runtime_db = tmp_path / "runtime-preserve-updated-at.db"
    runtime_core = RecollectiumCore(db_path=runtime_db)
    runtime_memory = runtime_core.add_memory(
        space=SPACE_USER, type="fact", content="beta"
    )

    with sqlite_connection(runtime_db) as connection:
        connection.execute(
            "UPDATE memories SET embedding_profile_json = ? WHERE id = ?",
            (json.dumps(stale_profile, sort_keys=True), runtime_memory.id),
        )

    _ = runtime_core.search_user_memories("beta")
    runtime_after = runtime_core.get_memory(runtime_memory.id)
    assert runtime_after.updated_at == runtime_memory.updated_at


def test_blocking_fake_embedding_provider_times_out_quickly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BlockingFakeEmbeddingProvider()
    provider.block_texts.add("slow")
    monkeypatch.setattr(provider.release, "wait", lambda timeout: False)

    with pytest.raises(
        RuntimeError, match="timed out waiting to unblock fake embedding"
    ):
        provider.embed("slow")


def test_runtime_reembedding_failure_blocks_partial_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "runtime-reembed-failure.db"
    core = RecollectiumCore(db_path=db_path)
    first = core.add_memory(space=SPACE_USER, type="note", content="memory one")
    second = core.add_memory(space=SPACE_USER, type="note", content="memory two")

    stale_profile = {
        **core.embedding_provider.embedding_profile,
        "profile": "stale-profile",
    }
    stale_json = json.dumps(stale_profile, sort_keys=True)
    with sqlite_connection(db_path) as connection:
        connection.execute(
            "UPDATE memories SET embedding_profile_json = ? WHERE id IN (?, ?)",
            (stale_json, first.id, second.id),
        )

    original_chunk_embed_pairs = core._chunk_embed_pairs

    def fail_on_second(text: str):
        if text == second.content:
            raise RuntimeError("forced runtime re-embed failure")
        return original_chunk_embed_pairs(text)

    monkeypatch.setattr(core, "_chunk_embed_pairs", fail_on_second)

    assert fail_on_second(first.content) == original_chunk_embed_pairs(first.content)

    with pytest.raises(ReembeddingFailedError) as exc_info:
        core.search_user_memories("memory")

    error = exc_info.value
    job = core.get_embedding_job(error.job_id)
    assert job["state"] == "failed"
    assert job["failed_count"] == 1
    assert error.status_path.endswith(error.job_id)


def test_database_status_surfaces_store_migration_status(tmp_path: Path) -> None:
    db_path = tmp_path / "db-status-core.db"
    core = RecollectiumCore(db_path=db_path)

    status = core.database_status()

    assert status["db_path"] == str(db_path)
    assert status["current_version"] == 3
    assert status["latest_version"] == 3
    assert status["pending_versions"] == []
    assert status["up_to_date"] is True


def test_recollectium_core_uses_config_db_path(tmp_path: Path) -> None:
    """RecollectiumCore with config_path and no db_path uses resolved_database_path."""
    from recollectium.config import _write_starter_config

    config_path = tmp_path / "config.json"
    _write_starter_config(config_path)

    core = RecollectiumCore(config_path=config_path)

    assert core.config is not None
    assert core.store.db_path == core.config.resolved_database_path


# -- workspace operations -------------------------------------------------


def test_core_list_workspaces_returns_sorted(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="ws-b item",
        workspace_uid="project-b",
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="ws-a item",
        workspace_uid="project-a",
    )

    uids = core.list_workspaces()
    assert uids == ["project-a", "project-b"]


def test_core_list_workspaces_empty(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    assert core.list_workspaces() == []


def test_core_rename_workspace_normalizes_uids(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="item",
        workspace_uid="My Project",
    )

    result = core.rename_workspace("My Project", "My New Project")
    assert result["old_uid"] == "my-project"
    assert result["new_uid"] == "my-new-project"
    assert result["memories_updated"] == 1

    uids = core.list_workspaces()
    assert uids == ["my-new-project"]


def test_core_rename_workspace_raises_on_empty_normalization(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    with pytest.raises(ValidationError, match="empty string"):
        core.rename_workspace("!!!", "valid")


def test_core_rename_workspace_raises_not_found(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    with pytest.raises(NotFoundError, match="no workspace memories"):
        core.rename_workspace("nonexistent", "new-project")


def test_core_add_memory_normalizes_workspace_uid(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    memory = core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="item",
        workspace_uid="  Recollectium Core!!!  ",
    )
    assert memory.workspace_uid == "recollectium-core"


def test_core_search_workspace_normalizes_uid(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="searchable item",
        workspace_uid="My Project",
    )

    results = core.search_workspace_memories(
        query="searchable",
        workspace_uid="MY PROJECT",
    )
    assert len(results) == 1


def test_core_list_memories_normalizes_workspace_uid(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="item",
        workspace_uid="My Project",
    )

    memories = core.list_memories(
        space=SPACE_WORKSPACE,
        workspace_uid="  my-project  ",
    )
    assert len(memories) == 1


def test_core_rename_workspace_exact_mode_passthrough(tmp_path: Path) -> None:
    """Exact normalization preserves UIDs as-is."""
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    # Override config to exact mode
    core.config._effective_config["workspace"]["uid_normalization"] = "exact"

    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="item",
        workspace_uid="My Project",
    )
    result = core.rename_workspace("My Project", "My New Project")
    assert result["old_uid"] == "My Project"
    assert result["new_uid"] == "My New Project"
    assert result["memories_updated"] == 1


def test_core_rename_workspace_same_uid_includes_aliases_updated(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "same-uid-rename.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    result = core.rename_workspace("My Project", "my-project")
    assert result == {
        "old_uid": "my-project",
        "new_uid": "my-project",
        "memories_updated": 0,
        "aliases_updated": 0,
    }


def test_workspace_alias_exact_mode_preserves_alias_case(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "aliases-exact-core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.config._effective_config["workspace"]["uid_normalization"] = "exact"

    core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="canonical exact memory",
        workspace_uid="My Project",
    )
    result = core.add_workspace_alias("My Project", "My Project Legacy")

    assert result["migrated_memories"] == 0
    assert core.resolve_workspace("My Project Legacy") == {
        "input_uid": "My Project Legacy",
        "normalized_uid": "My Project Legacy",
        "canonical_uid": "My Project",
        "resolved_by_alias": True,
    }

    alias_memory = core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="alias exact memory",
        workspace_uid="My Project Legacy",
    )
    assert alias_memory.workspace_uid == "My Project"
    assert core.list_workspaces(include_aliases=True) == [
        {"workspace_uid": "My Project", "aliases": ["My Project Legacy"]}
    ]


def test_core_normalize_uid_rejects_whitespace_only(tmp_path: Path) -> None:
    """_normalize_uid raises ValidationError for whitespace-only UIDs."""
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    with pytest.raises(ValidationError, match="empty string"):
        core.rename_workspace("   ", "valid")


def test_core_uid_normalization_falls_back_to_normalize(tmp_path: Path) -> None:
    """_uid_normalization returns normalize when config is malformed."""
    core = RecollectiumCore(
        db_path=tmp_path / "core.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    # Corrupt the workspace config to trigger fallback
    core.config._effective_config["workspace"] = None
    assert core._uid_normalization() == "normalize"


def test_workspace_alias_resolution_flows_through_core_memory_operations(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "aliases-core.db", embedding_provider=FakeEmbeddingProvider()
    )
    canonical = core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="canonical workspace memory",
        workspace_uid="Recollectium",
    )
    result = core.add_workspace_alias("Recollectium", "Recollectium Core")

    assert result["migrated_memories"] == 0
    alias_payload = result["alias"]
    assert isinstance(alias_payload, dict)
    alias: dict[str, Any] = alias_payload
    assert alias["alias_uid"] == "recollectium-core"
    assert core.resolve_workspace("Recollectium Core") == {
        "input_uid": "Recollectium Core",
        "normalized_uid": "recollectium-core",
        "canonical_uid": "recollectium",
        "resolved_by_alias": True,
    }

    alias_memory = core.add_memory(
        space=SPACE_WORKSPACE,
        type="fact",
        content="alias workspace memory",
        workspace_uid="Recollectium Core",
    )
    assert alias_memory.workspace_uid == "recollectium"

    listed = core.list_memories(
        space=SPACE_WORKSPACE, workspace_uid="Recollectium Core"
    )
    assert {memory.id for memory in listed} == {canonical.id, alias_memory.id}
    searched = core.search_workspace_memories(
        "alias", workspace_uid="Recollectium Core"
    )
    assert searched[0].memory.workspace_uid == "recollectium"


def test_workspace_alias_migrate_existing_and_include_aliases(tmp_path: Path) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "aliases-migrate.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE, type="fact", content="old", workspace_uid="Old Name"
    )

    with pytest.raises(ValidationError, match="Use --migrate-existing"):
        core.add_workspace_alias("New Name", "Old Name")

    migrated = core.add_workspace_alias("New Name", "Old Name", migrate_existing=True)
    assert migrated["migrated_memories"] == 1
    assert [
        memory.workspace_uid for memory in core.list_memories(space=SPACE_WORKSPACE)
    ] == ["new-name"]
    assert core.list_workspaces(include_aliases=True) == [
        {"workspace_uid": "new-name", "aliases": ["old-name"]}
    ]


def test_workspace_alias_crud_validation_and_rename_updates_aliases(
    tmp_path: Path,
) -> None:
    core = RecollectiumCore(
        db_path=tmp_path / "aliases-validation.db",
        embedding_provider=FakeEmbeddingProvider(),
    )
    core.add_memory(
        space=SPACE_WORKSPACE, type="fact", content="a", workspace_uid="alpha"
    )
    core.add_workspace_alias("alpha", "legacy-alpha")

    with pytest.raises(ValidationError, match="must differ"):
        core.add_workspace_alias("alpha", "Alpha")
    with pytest.raises(ValidationError, match="already an alias"):
        core.add_workspace_alias("legacy-alpha", "older-alpha")
    with pytest.raises(ValidationError, match="already exists"):
        core.add_workspace_alias("alpha", "legacy-alpha")

    rename = core.rename_workspace("alpha", "beta")
    assert rename["aliases_updated"] == 1
    assert core.resolve_workspace("legacy-alpha")["canonical_uid"] == "beta"
    assert core.list_workspace_aliases("beta")[0]["alias_uid"] == "legacy-alpha"

    removed = core.remove_workspace_alias("legacy-alpha")
    assert removed["canonical_uid"] == "beta"
    with pytest.raises(NotFoundError, match="workspace alias not found"):
        core.remove_workspace_alias("legacy-alpha")
