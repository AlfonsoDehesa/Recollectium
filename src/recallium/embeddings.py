"""Production embedding provider using FastEmbed."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, Protocol, cast

from recallium.errors import (
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
)


class EmbeddingProvider(Protocol):
    @property
    def embedding_profile(self) -> dict[str, object]: ...

    def embed(self, text: str) -> list[float]: ...

    def similarity(self, first: list[float], second: list[float]) -> float: ...


class BuiltinFastEmbedProvider:
    """Built-in production embedding provider backed by FastEmbed."""

    provider_name = "builtin-fastembed"
    model_name = "mixedbread-ai/mxbai-embed-large-v1"
    dimensions = 1024
    version = "1"
    profile_name = "builtin-fastembed-mxbai-large-v1"
    max_tokens = 512
    chunk_tokens = 384
    chunk_overlap_tokens = 64
    query_prompt_policy = "raw"

    def __init__(self) -> None:
        self._embedder: Any | None = None

    @property
    def embedding_profile(self) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "dimensions": self.dimensions,
            "version": self.version,
            "profile": self.profile_name,
            "max_tokens": self.max_tokens,
            "chunk_tokens": self.chunk_tokens,
            "chunk_overlap_tokens": self.chunk_overlap_tokens,
            "query_prompt_policy": self.query_prompt_policy,
        }

    def embed(self, text: str) -> list[float]:
        normalized = text.strip()
        if not normalized:
            return [0.0] * self.dimensions

        embedder = self._get_embedder()
        try:
            result = next(iter(embedder.embed([normalized])))
        except StopIteration as exc:
            raise EmbeddingGenerationError(
                "embedding provider returned no vector"
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive runtime wrapper
            raise EmbeddingGenerationError(
                f"failed to generate embedding with {self.provider_name}"
            ) from exc

        vector = [float(value) for value in cast(Iterable[float], result)]
        if len(vector) != self.dimensions:
            raise EmbeddingGenerationError(
                f"unexpected embedding dimension: expected {self.dimensions}, got {len(vector)}"
            )
        return self._normalize_vector(vector)

    def similarity(self, first: list[float], second: list[float]) -> float:
        if len(first) != len(second):
            raise EmbeddingGenerationError("embedding vectors must have the same size")
        if len(first) != self.dimensions:
            raise EmbeddingGenerationError(
                f"embedding vector size must be {self.dimensions}"
            )

        first_norm = self._vector_norm(first)
        second_norm = self._vector_norm(second)
        if first_norm == 0.0 or second_norm == 0.0:
            return 0.0

        dot_product = sum(a * b for a, b in zip(first, second, strict=True))
        return dot_product / (first_norm * second_norm)

    def _get_embedder(self) -> Any:
        if self._embedder is not None:
            return self._embedder

        try:
            from fastembed import TextEmbedding
        except Exception as exc:  # pragma: no cover - import wrapper
            raise EmbeddingProviderUnavailableError(
                "FastEmbed is unavailable. Install fastembed and its runtime dependencies."
            ) from exc

        try:
            self._embedder = TextEmbedding(model_name=self.model_name)
        except Exception as exc:
            raise EmbeddingModelUnavailableError(
                f"failed to load embedding model '{self.model_name}'"
            ) from exc

        return self._embedder

    @staticmethod
    def _vector_norm(vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector))

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        norm = self._vector_norm(vector)
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]
