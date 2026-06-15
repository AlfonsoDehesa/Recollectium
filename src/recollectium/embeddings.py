"""Production embedding provider using FastEmbed."""

from __future__ import annotations

import contextlib
import math
import multiprocessing
import os
import re
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, ClassVar, Protocol, cast

from recollectium.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationError,
    EmbeddingModelUnavailableError,
    EmbeddingProviderUnavailableError,
    EmbeddingReadinessTimeoutError,
)
from recollectium.managed_dirs import ensure_managed_directory


class EmbeddingProvider(Protocol):
    @property
    def embedding_profile(self) -> dict[str, object]: ...

    def embed(self, text: str) -> list[float]: ...

    def similarity(self, first: list[float], second: list[float]) -> float: ...


@contextlib.contextmanager
def _redirect_file_descriptor_to_devnull(fd: int) -> Iterator[None]:
    """Temporarily redirect an OS file descriptor to ``os.devnull``."""
    saved_fd: int | None = None
    devnull_fd: int | None = None
    redirected = False
    try:
        saved_fd = os.dup(fd)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, fd)
        redirected = True
        yield
    finally:
        try:
            if redirected and saved_fd is not None:
                os.dup2(saved_fd, fd)
        finally:
            if devnull_fd is not None:
                os.close(devnull_fd)
            if saved_fd is not None:
                os.close(saved_fd)


@contextlib.contextmanager
def _suppress_fastembed_readiness_output(
    *, suppress_stdout: bool = False
) -> Iterator[None]:
    """Contain native-library readiness output from the FastEmbed child process."""
    with contextlib.ExitStack() as stack:
        stack.enter_context(_redirect_file_descriptor_to_devnull(2))
        if suppress_stdout:
            stack.enter_context(_redirect_file_descriptor_to_devnull(1))
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            if suppress_stdout:
                stack.enter_context(contextlib.redirect_stdout(devnull))
            stack.enter_context(contextlib.redirect_stderr(devnull))
            yield


def _fastembed_readiness_worker(
    result_connection: Connection,
    model_name: str,
    cache_dir: str | None,
    suppress_output: bool = False,
) -> None:
    try:
        provider = BuiltinFastEmbedProvider(model_name, cache_dir=cache_dir)
        with _suppress_fastembed_readiness_output(suppress_stdout=suppress_output):
            provider._ensure_ready_unbounded()
    except Exception as exc:  # pragma: no cover - exercised through parent process
        result_connection.send(
            {
                "ok": False,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }
        )
        result_connection.close()
        return

    result_connection.send({"ok": True})
    result_connection.close()


@dataclass(slots=True)
class ContentChunk:
    chunk_index: int
    text: str
    token_start: int
    token_end: int


@dataclass(frozen=True, slots=True)
class FastEmbedCacheLayout:
    root: tuple[str, ...]
    payload: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FastEmbedModelSpec:
    model_name: str
    dimensions: int
    profile_name: str
    max_tokens: int
    chunk_tokens: int
    chunk_overlap_tokens: int
    cache_layouts: tuple[FastEmbedCacheLayout, ...]
    query_prompt_policy: str = "raw"
    recommended_match_threshold: float | None = None


BGE_BASE_EN_V15_MODEL = "BAAI/bge-base-en-v1.5"
JINA_SMALL_EN_MODEL = "jinaai/jina-embeddings-v2-small-en"

BUILTIN_FASTEMBED_MODEL_SPECS: dict[str, FastEmbedModelSpec] = {
    BGE_BASE_EN_V15_MODEL: FastEmbedModelSpec(
        model_name=BGE_BASE_EN_V15_MODEL,
        dimensions=768,
        profile_name="builtin-fastembed-bge-base-en-v1-5-v1",
        max_tokens=512,
        chunk_tokens=384,
        chunk_overlap_tokens=64,
        cache_layouts=(
            FastEmbedCacheLayout(
                root=("models--qdrant--bge-base-en-v1.5-onnx-q",),
                payload=("model_optimized.onnx",),
            ),
            FastEmbedCacheLayout(
                root=("fast-bge-base-en-v1.5",),
                payload=("model_optimized.onnx",),
            ),
        ),
    ),
    JINA_SMALL_EN_MODEL: FastEmbedModelSpec(
        model_name=JINA_SMALL_EN_MODEL,
        dimensions=512,
        profile_name="builtin-fastembed-jina-v2-small-en-v1",
        max_tokens=8192,
        chunk_tokens=6144,
        chunk_overlap_tokens=512,
        cache_layouts=(
            FastEmbedCacheLayout(
                root=("models--xenova--jina-embeddings-v2-small-en",),
                payload=("onnx", "model.onnx"),
            ),
        ),
    ),
}
DEFAULT_BUILTIN_FASTEMBED_MODEL = BGE_BASE_EN_V15_MODEL


def chunk_text_for_profile(text: str, profile: dict[str, object]) -> list[ContentChunk]:
    """Split text into overlapping chunks using embedding profile token policy."""
    chunk_tokens = _as_positive_int(profile.get("chunk_tokens"), "chunk_tokens")
    overlap_tokens = _as_non_negative_int(
        profile.get("chunk_overlap_tokens"), "chunk_overlap_tokens"
    )
    if overlap_tokens >= chunk_tokens:
        raise EmbeddingGenerationError(
            "chunk_overlap_tokens must be smaller than chunk_tokens"
        )

    tokens = _tokenize_for_chunking(text)
    if not tokens:
        return [ContentChunk(chunk_index=0, text="", token_start=0, token_end=0)]

    chunks: list[ContentChunk] = []
    step = chunk_tokens - overlap_tokens
    start = 0
    chunk_index = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        chunk_tokens_slice = tokens[start:end]
        chunks.append(
            ContentChunk(
                chunk_index=chunk_index,
                text=" ".join(chunk_tokens_slice),
                token_start=start,
                token_end=end,
            )
        )
        if end >= len(tokens):
            break
        start += step
        chunk_index += 1

    return chunks


def _tokenize_for_chunking(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _as_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise EmbeddingGenerationError(f"{field_name} must be a positive integer")
    return value


def _as_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EmbeddingGenerationError(f"{field_name} must be a non-negative integer")
    return value


class BuiltinFastEmbedProvider:
    """Built-in production embedding provider backed by FastEmbed."""

    provider_name = "builtin-fastembed"
    version = "1"
    runtime_threads = 1
    _shared_embedders: ClassVar[dict[tuple[str, int, str | None], Any]] = {}

    def __init__(
        self,
        model_name: str = DEFAULT_BUILTIN_FASTEMBED_MODEL,
        *,
        cache_dir: str | Path | None = None,
    ) -> None:
        try:
            spec = BUILTIN_FASTEMBED_MODEL_SPECS[model_name]
        except KeyError as exc:
            supported = ", ".join(sorted(BUILTIN_FASTEMBED_MODEL_SPECS))
            raise EmbeddingModelUnavailableError(
                f"unsupported built-in FastEmbed model {model_name!r}; supported models: {supported}"
            ) from exc
        self.model_name = spec.model_name
        self.dimensions = spec.dimensions
        self.profile_name = spec.profile_name
        self.max_tokens = spec.max_tokens
        self.chunk_tokens = spec.chunk_tokens
        self.chunk_overlap_tokens = spec.chunk_overlap_tokens
        self._cache_layouts = spec.cache_layouts
        self.query_prompt_policy = spec.query_prompt_policy
        self.cache_dir = str(cache_dir) if cache_dir is not None else None
        if cache_dir is not None:
            ensure_managed_directory(Path(cache_dir), purpose="model-cache")
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

    def has_cached_model_artifact(self) -> bool:
        """Return whether the configured FastEmbed cache appears populated."""
        if self.cache_dir is None:
            return False
        cache_root = Path(self.cache_dir)
        if not cache_root.is_dir():
            return False

        for layout in self._cache_layouts:
            candidate = cache_root.joinpath(*layout.root)
            if _cache_tree_has_model_artifact(candidate, layout.payload):
                return True
        return False

    def embed(self, text: str) -> list[float]:
        normalized = text.strip()
        if not normalized:
            return [0.0] * self.dimensions

        embedder = self._get_embedder()
        try:
            result = next(iter(embedder.embed([normalized], batch_size=1)))
        except StopIteration as exc:
            raise EmbeddingGenerationError(
                "embedding provider returned no vector"
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive runtime wrapper
            raise EmbeddingGenerationError(
                f"failed to generate embedding with {self.provider_name}"
            ) from exc

        vector = [float(value) for value in cast(Iterable[float], result)]
        self._validate_dimensions(vector)
        return self._normalize_vector(vector)

    def ensure_ready(
        self,
        *,
        timeout_seconds: float = 60.0,
        suppress_output: bool = False,
        max_attempts: int = 3,
    ) -> None:
        if timeout_seconds <= 0:
            raise EmbeddingReadinessTimeoutError(
                "FastEmbed provider startup timed out after 0 seconds"
            )
        if max_attempts <= 0:
            raise ValueError("max_attempts must be at least 1")

        for attempt in range(1, max_attempts + 1):
            try:
                self._ensure_ready_once(
                    timeout_seconds=timeout_seconds,
                    suppress_output=suppress_output,
                )
                return
            except EmbeddingReadinessTimeoutError:
                raise
            except EmbeddingProviderUnavailableError:
                raise
            except EmbeddingDimensionMismatchError:
                raise
            except (
                EmbeddingModelUnavailableError,
                EmbeddingGenerationError,
            ):
                if attempt == max_attempts:
                    raise
                delay = 2.0 * (2 ** (attempt - 1))
                time.sleep(delay)

    def _ensure_ready_once(
        self,
        *,
        timeout_seconds: float,
        suppress_output: bool,
    ) -> None:

        context = multiprocessing.get_context("spawn")
        parent_connection, child_connection = context.Pipe(duplex=False)
        process_args = (child_connection, self.model_name, self.cache_dir)
        if suppress_output:
            process_args = (*process_args, suppress_output)
        process = context.Process(
            target=_fastembed_readiness_worker,
            args=process_args,
        )
        process.start()
        child_connection.close()
        process.join(timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
            parent_connection.close()
            raise EmbeddingReadinessTimeoutError(
                "FastEmbed provider startup timed out after "
                f"{timeout_seconds:g} seconds"
            )

        if not parent_connection.poll():
            parent_connection.close()
            raise EmbeddingGenerationError(
                "FastEmbed provider readiness check exited without reporting status"
            )

        result = cast(dict[str, object], parent_connection.recv())
        parent_connection.close()

        if result.get("ok") is True:
            return

        message = str(result.get("message") or "FastEmbed provider readiness failed")
        error_type = result.get("error_type")
        if error_type == "EmbeddingProviderUnavailableError":
            raise EmbeddingProviderUnavailableError(message)
        if error_type == "EmbeddingModelUnavailableError":
            raise EmbeddingModelUnavailableError(message)
        if error_type == "EmbeddingDimensionMismatchError":
            raise EmbeddingDimensionMismatchError(message)
        if error_type == "EmbeddingReadinessTimeoutError":
            raise EmbeddingReadinessTimeoutError(message)
        raise EmbeddingGenerationError(message)

    def _ensure_ready_unbounded(self) -> None:
        vector = self.embed("healthcheck")
        self._validate_dimensions(vector)
        if not any(value != 0.0 for value in vector):
            raise EmbeddingGenerationError(
                "FastEmbed provider readiness check returned an empty vector"
            )

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

        cache_key = (self.model_name, self.runtime_threads, self.cache_dir)
        cached_embedder = self._shared_embedders.get(cache_key)
        if cached_embedder is not None:
            self._embedder = cached_embedder
            return cached_embedder

        try:
            from fastembed import TextEmbedding
        except Exception as exc:  # pragma: no cover - import wrapper
            raise EmbeddingProviderUnavailableError(
                "FastEmbed is unavailable. Install fastembed and its runtime dependencies."
            ) from exc

        try:
            self._embedder = TextEmbedding(
                model_name=self.model_name,
                threads=self.runtime_threads,
                cache_dir=self.cache_dir,
            )
        except Exception as exc:
            raise EmbeddingModelUnavailableError(
                f"failed to load embedding model '{self.model_name}'"
            ) from exc

        self._shared_embedders[cache_key] = self._embedder
        return self._embedder

    def _validate_dimensions(self, vector: list[float]) -> None:
        if len(vector) != self.dimensions:
            raise EmbeddingDimensionMismatchError(
                f"unexpected embedding dimension: expected {self.dimensions}, got {len(vector)}"
            )

    @staticmethod
    def _vector_norm(vector: list[float]) -> float:
        return math.sqrt(sum(value * value for value in vector))

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        norm = self._vector_norm(vector)
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def _cache_tree_has_model_artifact(
    path: Path, expected_relative_path: tuple[str, ...] = ("model.onnx",)
) -> bool:
    expected_name = expected_relative_path[-1]
    if path.is_file():
        return path.name == expected_name and _is_model_artifact_file(path)
    if not path.is_dir():
        return False
    return any(
        _has_relative_path_suffix(candidate, expected_relative_path)
        and _is_model_artifact_file(candidate)
        for candidate in path.rglob(expected_name)
    )


def _has_relative_path_suffix(
    path: Path, expected_relative_path: tuple[str, ...]
) -> bool:
    return path.parts[-len(expected_relative_path) :] == expected_relative_path


def _is_model_artifact_file(path: Path) -> bool:
    try:
        is_file = path.is_file()
    except OSError:
        return False
    if not is_file:
        return False
    lowered = path.name.lower()
    if lowered.endswith((".lock", ".incomplete")):
        return False
    try:
        return path.stat().st_size > 0
    except OSError:
        return False
