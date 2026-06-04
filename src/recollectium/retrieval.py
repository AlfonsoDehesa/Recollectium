"""Retrieval policy helpers for Recollectium search surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from recollectium.embeddings import BUILTIN_FASTEMBED_MODEL_SPECS
from recollectium.errors import ValidationError
from recollectium.models import SearchResult


class _UnsetType(Enum):
    UNSET = "UNSET"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "UNSET"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "UNSET"


UNSET = _UnsetType.UNSET
UnsetType = _UnsetType

MatchThresholdConfigValue = float | None | Literal["model_recommended_default"]
MatchThresholdSource = Literal[
    "request",
    "config",
    "model_recommended_default",
    "disabled",
]


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """Resolved retrieval policy for a single search request."""

    protected_minimum: int
    match_threshold: float | None
    match_threshold_source: MatchThresholdSource
    threshold_filtering_enabled: bool


def _validate_non_negative_int(field_name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer")
    if value < 0:
        raise ValidationError(f"{field_name} must be >= 0")
    return value


def _validate_threshold_number(field_name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a number between 0.0 and 1.0")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise ValidationError(f"{field_name} must be between 0.0 and 1.0")
    return normalized


def _recommended_match_threshold(embedding_model: str) -> float | None:
    spec = BUILTIN_FASTEMBED_MODEL_SPECS.get(embedding_model)
    if spec is None:
        return None
    return spec.recommended_match_threshold


def resolve_protected_minimum(
    *,
    request_override: int | None | _UnsetType = UNSET,
    config_value: int,
) -> int:
    """Resolve the effective protected minimum with request override precedence."""

    if request_override is UNSET:
        value: Any = config_value
    else:
        value = request_override
    return _validate_non_negative_int("protected_minimum", value)


def resolve_match_threshold(
    *,
    request_override: MatchThresholdConfigValue | _UnsetType = UNSET,
    config_value: MatchThresholdConfigValue,
    embedding_model: str,
) -> float | None:
    """Resolve the effective match threshold with request/config/model precedence."""

    if request_override is not UNSET:
        if request_override is None:
            return None
        if request_override == "model_recommended_default":
            return _recommended_match_threshold(embedding_model)
        return _validate_threshold_number("match_threshold", request_override)

    if config_value is None:
        return None
    if config_value == "model_recommended_default":
        return _recommended_match_threshold(embedding_model)
    return _validate_threshold_number("match_threshold", config_value)


def resolve_retrieval_policy(
    *,
    request_protected_minimum: int | None | _UnsetType = UNSET,
    request_match_threshold: MatchThresholdConfigValue | _UnsetType = UNSET,
    config_protected_minimum: int,
    config_match_threshold: MatchThresholdConfigValue,
    embedding_model: str,
) -> RetrievalPolicy:
    """Resolve the effective retrieval policy for a request."""

    protected_minimum = resolve_protected_minimum(
        request_override=request_protected_minimum,
        config_value=config_protected_minimum,
    )
    match_threshold = resolve_match_threshold(
        request_override=request_match_threshold,
        config_value=config_match_threshold,
        embedding_model=embedding_model,
    )
    if request_match_threshold is not UNSET:
        source: MatchThresholdSource = "request"
    elif config_match_threshold == "model_recommended_default":
        source = (
            "model_recommended_default" if match_threshold is not None else "disabled"
        )
    elif config_match_threshold is None:
        source = "disabled"
    else:
        source = "config"

    return RetrievalPolicy(
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
        match_threshold_source=source,
        threshold_filtering_enabled=match_threshold is not None,
    )


def apply_match_threshold(
    results: list[SearchResult],
    *,
    limit: int,
    protected_minimum: int,
    match_threshold: float | None,
) -> list[SearchResult]:
    """Apply protected-minimum and match-threshold filtering to ranked results."""

    capped = list(results[:limit])
    if match_threshold is None:
        return capped

    protected_count = min(protected_minimum, len(capped))
    filtered: list[SearchResult] = []
    for index, result in enumerate(capped):
        if index < protected_count:
            filtered.append(result)
            continue
        if result.score >= match_threshold:
            filtered.append(result)
    return filtered
