"""Tests for _ensure_model_ready() — central embedding readiness wrapper."""

from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path

import pytest

from recollectium.core import RecollectiumCore
import recollectium.core as core_module
import recollectium.embeddings as embeddings_module
from recollectium.embeddings import BuiltinFastEmbedProvider
from recollectium.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingReadinessTimeoutError,
)
from recollectium.model_state import read_model_state, write_model_state

# The default model name config validation accepts.
_SUPPORTED_MODEL = "BAAI/bge-base-en-v1.5"


class TrackedEmbeddingProvider:
    """Fake provider that tracks ensure_ready calls."""

    def __init__(self) -> None:
        self.ensure_ready_calls: list[tuple] = []
        self.should_fail: str | None = None
        self.cache_dir: str | None = None
        self.embedding_profile: dict[str, object] = {
            "provider": "fake",
            "model": _SUPPORTED_MODEL,
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

    def ensure_ready(self, *, timeout_seconds: float = 60.0) -> None:
        self.ensure_ready_calls.append((timeout_seconds,))
        if self.should_fail:
            from recollectium.errors import EmbeddingModelUnavailableError

            raise EmbeddingModelUnavailableError(self.should_fail)


def _make_config(tmp_path: Path) -> Path:
    """Write a minimal valid Recollectium config pointing to a temp database."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "database": {"path": str(tmp_path / "recollectium.db")},
                "embedding": {
                    "provider": "builtin-fastembed",
                    "model": _SUPPORTED_MODEL,
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_ensure_model_ready_noop_when_model_matches(tmp_path: Path):
    """If model state matches config, ensure_ready is NOT called."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    write_model_state(
        state_dir,
        model=_SUPPORTED_MODEL,
        dimensions=3,
        profile="fake-profile-v1",
        model_cache_path=None,
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert provider.ensure_ready_calls == []
    assert provider.embed("abc") == [3.0, 97.0, 1.0]
    assert provider.similarity([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 32.0


def test_ensure_model_ready_prepares_when_state_missing(tmp_path: Path):
    """If no state file, ensure_ready is called and state is written."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state is not None
    assert state["prepared_model"] == _SUPPORTED_MODEL  # type: ignore[reportOptionalSubscript]
    assert state["dimensions"] == 3
    assert state["model_cache_path"] is None


def test_ensure_model_ready_prepares_when_legacy_state_lacks_cache_path(
    tmp_path: Path,
):
    """Legacy state without a cache path is stale for the owned cache."""
    state_dir = tmp_path / "state"
    write_model_state(
        state_dir,
        model=_SUPPORTED_MODEL,
        dimensions=3,
        profile="fake-profile-v1",
    )
    state_path = state_dir / "model-state.json"
    legacy_payload = json.loads(state_path.read_text(encoding="utf-8"))
    legacy_payload.pop("model_cache_path")
    state_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )

    core._ensure_model_ready(state_dir=state_dir)

    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state is not None
    assert state["model_cache_path"] is None


def test_ensure_model_ready_prepares_when_cache_path_mismatch(tmp_path: Path):
    """If model cache path changed, the provider is prepared again."""
    state_dir = tmp_path / "state"
    write_model_state(
        state_dir,
        model=_SUPPORTED_MODEL,
        dimensions=3,
        profile="fake-profile-v1",
        model_cache_path=str(tmp_path / "old-cache" / "models"),
    )
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )

    core._ensure_model_ready(state_dir=state_dir)

    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state is not None
    assert state["model_cache_path"] is None


def test_ensure_model_ready_uses_config_cache_for_internally_managed_provider(
    tmp_path: Path,
):
    """Internally managed providers use Recollectium's configured model cache."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(db_path=tmp_path / "test.db", config_path=config)
    core.embedding_provider = provider

    core._ensure_model_ready(state_dir=state_dir)

    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state is not None
    assert state["model_cache_path"] == str(core.config.model_cache_path)


def test_ensure_model_ready_uses_provider_cache_dir_in_state(tmp_path: Path):
    """Provider cache_dir participates in model readiness state comparison."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    provider.cache_dir = str(tmp_path / "provider-cache")
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )

    core._ensure_model_ready(state_dir=state_dir)
    core._ensure_model_ready(state_dir=state_dir)

    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state is not None
    assert state["model_cache_path"] == provider.cache_dir


def test_ensure_model_ready_prepares_when_model_mismatch(tmp_path: Path):
    """If model in state file differs from config, ensure_ready is called."""
    state_dir = tmp_path / "state"
    write_model_state(
        state_dir, model="old-model", dimensions=128, profile="old-profile"
    )
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state["prepared_model"] == _SUPPORTED_MODEL  # type: ignore[reportOptionalSubscript]


def test_ensure_model_ready_prepares_when_profile_mismatch(tmp_path: Path):
    """If profile in state file differs from provider profile, ensure_ready is called."""
    state_dir = tmp_path / "state"
    write_model_state(
        state_dir,
        model=_SUPPORTED_MODEL,
        dimensions=3,
        profile="old-profile",
    )
    provider = TrackedEmbeddingProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert len(provider.ensure_ready_calls) == 1
    state = read_model_state(state_dir)
    assert state["profile"] == "fake-profile-v1"  # type: ignore[reportOptionalSubscript]


def test_ensure_model_ready_raises_on_provider_failure(tmp_path: Path):
    """If ensure_ready fails, the error propagates."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    provider.should_fail = "model download failed"
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    with pytest.raises(EmbeddingModelUnavailableError, match="model download failed"):
        core._ensure_model_ready(state_dir=state_dir)

    assert read_model_state(state_dir) is None


def test_builtin_fastembed_readiness_suppresses_child_fd2_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """FastEmbed readiness child fd-level stderr is contained on success."""
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("fd-level child readiness suppression test requires fork")

    fork_context = multiprocessing.get_context("fork")
    monkeypatch.setattr(
        embeddings_module.multiprocessing,
        "get_context",
        lambda method: fork_context,
    )

    def noisy_success(self: BuiltinFastEmbedProvider) -> None:
        _ = self
        os.write(2, b"native fd2 readiness noise\n")

    monkeypatch.setattr(
        BuiltinFastEmbedProvider, "_ensure_ready_unbounded", noisy_success
    )
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL, cache_dir=tmp_path)

    provider.ensure_ready(timeout_seconds=5.0, suppress_output=True)

    captured = capfd.readouterr()
    assert captured.err == ""


def test_builtin_fastembed_readiness_suppresses_child_fd2_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """FastEmbed readiness child fd-level stderr is contained on strict failure."""
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("fd-level child readiness suppression test requires fork")

    fork_context = multiprocessing.get_context("fork")
    monkeypatch.setattr(
        embeddings_module.multiprocessing,
        "get_context",
        lambda method: fork_context,
    )

    def noisy_failure(self: BuiltinFastEmbedProvider) -> None:
        _ = self
        os.write(2, b"native fd2 readiness failure noise\n")
        raise EmbeddingModelUnavailableError("model download failed")

    monkeypatch.setattr(
        BuiltinFastEmbedProvider, "_ensure_ready_unbounded", noisy_failure
    )
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL, cache_dir=tmp_path)

    with pytest.raises(EmbeddingModelUnavailableError, match="model download failed"):
        provider.ensure_ready(timeout_seconds=5.0, suppress_output=True)

    captured = capfd.readouterr()
    assert captured.err == ""


def test_redirect_file_descriptor_to_devnull_closes_saved_fd_when_open_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saved fd is not leaked if opening os.devnull fails after os.dup()."""
    real_dup = embeddings_module.os.dup
    real_open = embeddings_module.os.open
    real_close = embeddings_module.os.close
    saved_fds: list[int] = []
    closed_fds: list[int] = []
    target_fd = real_open(os.devnull, os.O_WRONLY)

    def track_dup(fd: int) -> int:
        saved_fd = real_dup(fd)
        saved_fds.append(saved_fd)
        return saved_fd

    def fail_open(path: str, flags: int) -> int:
        assert path == os.devnull
        assert flags == os.O_WRONLY
        raise OSError("devnull unavailable")

    def track_close(fd: int) -> None:
        closed_fds.append(fd)
        real_close(fd)

    try:
        with monkeypatch.context() as patch_context:
            patch_context.setattr(embeddings_module.os, "dup", track_dup)
            patch_context.setattr(embeddings_module.os, "open", fail_open)
            patch_context.setattr(embeddings_module.os, "close", track_close)

            with pytest.raises(OSError, match="devnull unavailable"):
                with embeddings_module._redirect_file_descriptor_to_devnull(target_fd):
                    raise AssertionError("context body should not execute")
    finally:
        real_close(target_fd)

    assert len(saved_fds) == 1
    assert saved_fds[0] in closed_fds


def test_ensure_model_ready_writes_state_with_provider_dimensions(tmp_path: Path):
    """State file uses the provider's actual dimensions from embedding_profile."""
    state_dir = tmp_path / "state"
    provider = TrackedEmbeddingProvider()
    provider.embedding_profile["dimensions"] = 768
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    core._ensure_model_ready(state_dir=state_dir)
    state = read_model_state(state_dir)
    assert state["dimensions"] == 768  # type: ignore[reportOptionalSubscript]


def test_ensure_model_ready_falls_back_to_embed_healthcheck(tmp_path: Path):
    """Provider without ensure_ready() uses embed('healthcheck') fallback."""
    state_dir = tmp_path / "state"

    class NoEnsureReadyProvider:
        embedding_profile: dict[str, object] = {
            "provider": "bare",
            "model": _SUPPORTED_MODEL,
            "dimensions": 3,
            "version": "1",
            "profile": "bare-profile",
            "max_tokens": 16,
            "chunk_tokens": 4,
            "chunk_overlap_tokens": 0,
            "query_prompt_policy": "raw",
        }
        embed_calls: list[str] = []

        def embed(self, text: str) -> list[float]:
            self.embed_calls.append(text)
            return [1.0, 2.0, 3.0]

        def similarity(self, first: list[float], second: list[float]) -> float:
            return 1.0

    provider = NoEnsureReadyProvider()
    config = _make_config(tmp_path)
    core = RecollectiumCore(
        db_path=tmp_path / "test.db",
        config_path=config,
        embedding_provider=provider,
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert provider.similarity([1.0], [1.0]) == 1.0
    assert "healthcheck" in provider.embed_calls


def test_model_readiness_keyword_detection_returns_false_for_opaque_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raises_value_error(callback: object) -> object:
        raise ValueError("no signature available")

    monkeypatch.setattr(core_module.inspect, "signature", raises_value_error)

    def callback(**kwargs: object) -> None:
        raise AssertionError("callback should not be invoked")

    assert not core_module._callable_accepts_keyword(callback, "progress_callback")


def test_builtin_fastembed_ensure_ready_retries_transient_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL)

    call_count = [0]

    def fail_twice_then_succeed(
        self: BuiltinFastEmbedProvider,
        *,
        timeout_seconds: float,
        suppress_output: bool,
    ) -> None:
        call_count[0] += 1
        if call_count[0] < 3:
            raise EmbeddingModelUnavailableError("model download failed")

    monkeypatch.setattr(
        BuiltinFastEmbedProvider, "_ensure_ready_once", fail_twice_then_succeed
    )

    provider.ensure_ready(timeout_seconds=5.0, max_attempts=3)

    assert call_count[0] == 3


def test_builtin_fastembed_ensure_ready_raises_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL)

    call_count = [0]

    def always_fail(
        self: BuiltinFastEmbedProvider,
        *,
        timeout_seconds: float,
        suppress_output: bool,
    ) -> None:
        call_count[0] += 1
        raise EmbeddingGenerationError("persistent transient failure")

    monkeypatch.setattr(BuiltinFastEmbedProvider, "_ensure_ready_once", always_fail)

    with pytest.raises(EmbeddingGenerationError, match="persistent transient failure"):
        provider.ensure_ready(timeout_seconds=5.0, max_attempts=3)

    assert call_count[0] == 3


def test_builtin_fastembed_ensure_ready_rejects_non_positive_max_attempts() -> None:
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL)

    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        provider.ensure_ready(timeout_seconds=5.0, max_attempts=0)


def test_builtin_fastembed_ensure_ready_does_not_retry_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL)

    call_count = [0]

    def timeout_once(
        self: BuiltinFastEmbedProvider,
        *,
        timeout_seconds: float,
        suppress_output: bool,
    ) -> None:
        call_count[0] += 1
        raise EmbeddingReadinessTimeoutError("startup timed out after 0 seconds")

    monkeypatch.setattr(BuiltinFastEmbedProvider, "_ensure_ready_once", timeout_once)

    with pytest.raises(EmbeddingReadinessTimeoutError):
        provider.ensure_ready(timeout_seconds=5.0, max_attempts=3)

    assert call_count[0] == 1


def test_builtin_fastembed_ensure_ready_does_not_retry_dimension_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BuiltinFastEmbedProvider(_SUPPORTED_MODEL)

    call_count = [0]

    def mismatch_once(
        self: BuiltinFastEmbedProvider,
        *,
        timeout_seconds: float,
        suppress_output: bool,
    ) -> None:
        call_count[0] += 1
        raise EmbeddingDimensionMismatchError("expected 768 dimensions but got 512")

    monkeypatch.setattr(BuiltinFastEmbedProvider, "_ensure_ready_once", mismatch_once)

    with pytest.raises(EmbeddingDimensionMismatchError):
        provider.ensure_ready(timeout_seconds=5.0, max_attempts=3)

    assert call_count[0] == 1
