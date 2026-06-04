"""Tests for retrieval policy helpers."""

from __future__ import annotations

import pytest

from recollectium.errors import ValidationError
from recollectium.models import Memory, SearchResult, SPACE_USER, STATUS_ACTIVE
from recollectium.retrieval import (
    UNSET,
    _validate_non_negative_int,
    _validate_threshold_number,
    apply_match_threshold,
    resolve_match_threshold,
    resolve_retrieval_policy,
)


def _memory(memory_id: str) -> Memory:
    return Memory(
        id=memory_id,
        space=SPACE_USER,
        type="fact",
        content=f"content for {memory_id}",
        status=STATUS_ACTIVE,
        metadata={},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _result(memory_id: str, score: float, rank: int) -> SearchResult:
    return SearchResult(memory=_memory(memory_id), score=score, rank=rank)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (True, "protected_minimum must be an integer"),
        (-1, "protected_minimum must be >= 0"),
    ],
)
def test_validate_non_negative_int_rejects_invalid_values(
    value: object, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _validate_non_negative_int("protected_minimum", value)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (True, "match_threshold must be a number between 0.0 and 1.0"),
        (1.5, "match_threshold must be between 0.0 and 1.0"),
        (-0.1, "match_threshold must be between 0.0 and 1.0"),
    ],
)
def test_validate_threshold_number_rejects_invalid_values(
    value: object, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _validate_threshold_number("match_threshold", value)


def test_resolve_match_threshold_accepts_all_sources() -> None:
    assert resolve_match_threshold(
        request_override=0.25,
        config_value=UNSET,  # type: ignore[arg-type]
        embedding_model="BAAI/bge-base-en-v1.5",
    ) == 0.25

    assert resolve_match_threshold(
        request_override=None,
        config_value=0.6,
        embedding_model="BAAI/bge-base-en-v1.5",
    ) is None

    assert resolve_match_threshold(
        request_override="model_recommended_default",
        config_value=0.6,
        embedding_model="BAAI/bge-base-en-v1.5",
    ) is None

    assert resolve_match_threshold(
        request_override=UNSET,
        config_value=None,
        embedding_model="BAAI/bge-base-en-v1.5",
    ) is None

    assert resolve_match_threshold(
        request_override=UNSET,
        config_value="model_recommended_default",
        embedding_model="BAAI/bge-base-en-v1.5",
    ) is None


def test_resolve_retrieval_policy_reports_source_precedence() -> None:
    request_policy = resolve_retrieval_policy(
        request_protected_minimum=4,
        request_match_threshold=0.4,
        config_protected_minimum=2,
        config_match_threshold=0.9,
        embedding_model="BAAI/bge-base-en-v1.5",
    )
    assert request_policy.protected_minimum == 4
    assert request_policy.match_threshold == 0.4
    assert request_policy.match_threshold_source == "request"
    assert request_policy.threshold_filtering_enabled is True

    disabled_policy = resolve_retrieval_policy(
        request_protected_minimum=UNSET,
        request_match_threshold=UNSET,
        config_protected_minimum=2,
        config_match_threshold=None,
        embedding_model="BAAI/bge-base-en-v1.5",
    )
    assert disabled_policy.protected_minimum == 2
    assert disabled_policy.match_threshold is None
    assert disabled_policy.match_threshold_source == "disabled"
    assert disabled_policy.threshold_filtering_enabled is False

    model_default_policy = resolve_retrieval_policy(
        request_protected_minimum=UNSET,
        request_match_threshold=UNSET,
        config_protected_minimum=2,
        config_match_threshold="model_recommended_default",
        embedding_model="BAAI/bge-base-en-v1.5",
    )
    assert model_default_policy.match_threshold is None
    assert model_default_policy.match_threshold_source == "disabled"

    config_policy = resolve_retrieval_policy(
        request_protected_minimum=UNSET,
        request_match_threshold=UNSET,
        config_protected_minimum=2,
        config_match_threshold=0.6,
        embedding_model="BAAI/bge-base-en-v1.5",
    )
    assert config_policy.match_threshold == 0.6
    assert config_policy.match_threshold_source == "config"
    assert config_policy.threshold_filtering_enabled is True


def test_apply_match_threshold_keeps_protected_prefix_and_filters_rest() -> None:
    results = [
        _result("one", 0.95, 1),
        _result("two", 0.75, 2),
        _result("three", 0.45, 3),
        _result("four", 0.35, 4),
    ]

    filtered = apply_match_threshold(
        results,
        limit=4,
        protected_minimum=2,
        match_threshold=0.5,
    )

    assert [result.memory.id for result in filtered] == ["one", "two"]

    unprotected_results = [
        _result("one", 0.95, 1),
        _result("two", 0.75, 2),
        _result("three", 0.55, 3),
        _result("four", 0.35, 4),
    ]
    unprotected_filtered = apply_match_threshold(
        unprotected_results,
        limit=4,
        protected_minimum=1,
        match_threshold=0.5,
    )
    assert [result.memory.id for result in unprotected_filtered] == ["one", "two", "three"]
