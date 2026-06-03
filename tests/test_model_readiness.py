"""Tests for _ensure_model_ready() — central embedding readiness wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from recollectium.core import RecollectiumCore
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
        model_cache_path=str(core.config.model_cache_path),
    )
    core._ensure_model_ready(state_dir=state_dir)
    assert provider.ensure_ready_calls == []


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
    assert state["model_cache_path"] == str(core.config.model_cache_path)


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
    assert state["model_cache_path"] == str(core.config.model_cache_path)


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
    from recollectium.errors import EmbeddingModelUnavailableError

    with pytest.raises(EmbeddingModelUnavailableError, match="model download failed"):
        core._ensure_model_ready(state_dir=state_dir)


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
    assert "healthcheck" in provider.embed_calls
