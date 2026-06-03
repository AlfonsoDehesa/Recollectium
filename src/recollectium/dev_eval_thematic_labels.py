"""Checked thematic query-memory labels for seeded dev eval PR1.

This module is intentionally a label-dataset foundation only. Recollectium's
runtime dev evaluator does not consume these labels yet; they are checked in so
future scoring work can classify every existing thematic query/candidate pair
with deterministic four-point judgments.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from recollectium.dev_eval_thematic_fixtures import THEMATIC_PRECISION_FIXTURE
from recollectium.dev_seed import (
    DEV_SEED_PROJECTS,
    DEV_SEED_PROJECT_THEMES_BY_UID,
    DEV_SEED_USER_MEMORY_COUNT,
    DEV_SEED_USER_TOPICS,
    DEV_SEED_WORKSPACE_MEMORY_COUNT,
)
from recollectium.models import SPACE_USER, SPACE_WORKSPACE

ThematicContextLabel: TypeAlias = Literal[2, 1, -1, -2]
ALLOWED_THEMATIC_CONTEXT_LABELS: frozenset[ThematicContextLabel] = frozenset(
    {2, 1, -1, -2}
)


@dataclass(frozen=True, slots=True)
class ThematicContextLabelCase:
    """Labels for one checked thematic query across its actual search scope."""

    case_id: str
    scope: str
    group: str
    query_index: int
    query: str
    workspace_uid: str | None
    labels: Mapping[str, ThematicContextLabel]


@dataclass(frozen=True, slots=True)
class SeededEvalKeyIndex:
    """Expected seeded ``metadata.eval_key`` values by retrievable scope."""

    user_eval_keys: tuple[str, ...]
    workspace_eval_keys_by_uid: Mapping[str, tuple[str, ...]]
    group_by_eval_key: Mapping[str, str]


USER_ADJACENT_TOPIC_BY_TOPIC: Mapping[str, str] = {
    topic: DEV_SEED_USER_TOPICS[(index + 1) % len(DEV_SEED_USER_TOPICS)]
    for index, topic in enumerate(DEV_SEED_USER_TOPICS)
}
USER_CONFUSER_TOPIC_BY_TOPIC: Mapping[str, str] = {
    topic: DEV_SEED_USER_TOPICS[(index + 2) % len(DEV_SEED_USER_TOPICS)]
    for index, topic in enumerate(DEV_SEED_USER_TOPICS)
}
WORKSPACE_ADJACENT_THEME_BY_UID_THEME: Mapping[tuple[str, str], str] = {
    (workspace_uid, theme): themes[(index + 1) % len(themes)]
    for workspace_uid, themes in DEV_SEED_PROJECT_THEMES_BY_UID.items()
    for index, theme in enumerate(themes)
}
WORKSPACE_CONFUSER_THEME_BY_UID_THEME: Mapping[tuple[str, str], str] = {
    (workspace_uid, theme): themes[(index + 2) % len(themes)]
    for workspace_uid, themes in DEV_SEED_PROJECT_THEMES_BY_UID.items()
    for index, theme in enumerate(themes)
}


def seeded_eval_key_index() -> SeededEvalKeyIndex:
    """Return expected eval keys and thematic groups for the seeded memories."""

    user_eval_keys = tuple(
        f"dev-user-{index:03d}" for index in range(1, DEV_SEED_USER_MEMORY_COUNT + 1)
    )
    workspace_eval_keys_by_uid = {
        project["uid"]: tuple(
            f"dev-workspace-{workspace_index:02d}-{index:03d}"
            for index in range(1, DEV_SEED_WORKSPACE_MEMORY_COUNT + 1)
        )
        for workspace_index, project in enumerate(DEV_SEED_PROJECTS, start=1)
    }
    group_by_eval_key: dict[str, str] = {}
    for index, eval_key in enumerate(user_eval_keys):
        group_by_eval_key[eval_key] = DEV_SEED_USER_TOPICS[index // 10]
    for workspace_uid, eval_keys in workspace_eval_keys_by_uid.items():
        themes = DEV_SEED_PROJECT_THEMES_BY_UID[workspace_uid]
        for index, eval_key in enumerate(eval_keys):
            group_by_eval_key[eval_key] = themes[index // 10]
    return SeededEvalKeyIndex(
        user_eval_keys=user_eval_keys,
        workspace_eval_keys_by_uid=workspace_eval_keys_by_uid,
        group_by_eval_key=group_by_eval_key,
    )


def _slug(value: str) -> str:
    return value.replace(" ", "-").replace("/", "-")


def _label_for_group(
    *,
    candidate_group: str,
    target_group: str,
    adjacent_group: str,
    confuser_group: str,
) -> ThematicContextLabel:
    if candidate_group == target_group:
        return 2
    if candidate_group == adjacent_group:
        return 1
    if candidate_group == confuser_group:
        return -2
    return -1


def _labels_for_user_group(
    group: str,
    eval_key_index: SeededEvalKeyIndex,
) -> Mapping[str, ThematicContextLabel]:
    adjacent_group = USER_ADJACENT_TOPIC_BY_TOPIC[group]
    confuser_group = USER_CONFUSER_TOPIC_BY_TOPIC[group]
    return {
        eval_key: _label_for_group(
            candidate_group=eval_key_index.group_by_eval_key[eval_key],
            target_group=group,
            adjacent_group=adjacent_group,
            confuser_group=confuser_group,
        )
        for eval_key in eval_key_index.user_eval_keys
    }


def _labels_for_workspace_group(
    *,
    workspace_uid: str,
    group: str,
    eval_key_index: SeededEvalKeyIndex,
) -> Mapping[str, ThematicContextLabel]:
    adjacent_group = WORKSPACE_ADJACENT_THEME_BY_UID_THEME[(workspace_uid, group)]
    confuser_group = WORKSPACE_CONFUSER_THEME_BY_UID_THEME[(workspace_uid, group)]
    return {
        eval_key: _label_for_group(
            candidate_group=eval_key_index.group_by_eval_key[eval_key],
            target_group=group,
            adjacent_group=adjacent_group,
            confuser_group=confuser_group,
        )
        for eval_key in eval_key_index.workspace_eval_keys_by_uid[workspace_uid]
    }


def thematic_context_label_cases() -> tuple[ThematicContextLabelCase, ...]:
    """Return all checked PR1 labels for existing thematic query surfaces."""

    eval_key_index = seeded_eval_key_index()
    cases: list[ThematicContextLabelCase] = []
    for fixture_entry in THEMATIC_PRECISION_FIXTURE:
        scope = fixture_entry["scope"]
        group = fixture_entry["group"]
        workspace_uid = fixture_entry["workspace_uid"]
        for query_index, query in enumerate(fixture_entry["queries"], start=1):
            if scope == SPACE_USER:
                labels = _labels_for_user_group(group, eval_key_index)
                case_workspace_uid = None
            elif scope == SPACE_WORKSPACE:
                if workspace_uid is None:
                    raise ValueError(
                        f"workspace thematic label case {group!r} requires workspace_uid"
                    )
                labels = _labels_for_workspace_group(
                    workspace_uid=workspace_uid,
                    group=group,
                    eval_key_index=eval_key_index,
                )
                case_workspace_uid = workspace_uid
            else:
                raise ValueError(f"unsupported thematic label scope: {scope!r}")
            case_id = f"{scope}-{_slug(case_workspace_uid or 'global')}-{_slug(group)}-q{query_index}"
            cases.append(
                ThematicContextLabelCase(
                    case_id=case_id,
                    scope=scope,
                    group=group,
                    query_index=query_index,
                    query=query,
                    workspace_uid=case_workspace_uid,
                    labels=labels,
                )
            )
    return tuple(cases)


THEMATIC_CONTEXT_LABEL_CASES: tuple[ThematicContextLabelCase, ...] = (
    thematic_context_label_cases()
)


def validate_thematic_context_label_cases(
    cases: Sequence[ThematicContextLabelCase] = THEMATIC_CONTEXT_LABEL_CASES,
    *,
    eval_key_index: SeededEvalKeyIndex | None = None,
) -> None:
    """Validate the checked PR1 label dataset and fail loudly on gaps."""

    expected_index = eval_key_index or seeded_eval_key_index()
    seen_case_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_case_ids:
            raise ValueError(f"duplicate thematic label case id: {case.case_id!r}")
        seen_case_ids.add(case.case_id)
        if case.scope == SPACE_USER and case.workspace_uid is not None:
            raise ValueError(
                f"user label case {case.case_id!r} must not have workspace_uid"
            )
        if case.scope == SPACE_WORKSPACE and case.workspace_uid is None:
            raise ValueError(
                f"workspace label case {case.case_id!r} requires workspace_uid"
            )
        if case.scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValueError(f"unsupported thematic label case scope: {case.scope!r}")

    expected_case_keys = {
        (
            entry["scope"],
            entry["workspace_uid"],
            entry["group"],
            query_index,
            query,
        )
        for entry in THEMATIC_PRECISION_FIXTURE
        for query_index, query in enumerate(entry["queries"], start=1)
    }
    actual_case_keys = {
        (
            case.scope,
            case.workspace_uid,
            case.group,
            case.query_index,
            case.query,
        )
        for case in cases
    }
    missing_cases = expected_case_keys - actual_case_keys
    extra_cases = actual_case_keys - expected_case_keys
    if missing_cases or extra_cases:
        details: list[str] = []
        if missing_cases:
            details.append(f"missing cases: {sorted(missing_cases)[:3]!r}")
        if extra_cases:
            details.append(f"extra cases: {sorted(extra_cases)[:3]!r}")
        raise ValueError("thematic label case mismatch (" + "; ".join(details) + ")")

    for case in cases:
        if case.scope == SPACE_USER:
            expected_eval_keys = set(expected_index.user_eval_keys)
        else:
            assert case.workspace_uid is not None
            expected_eval_keys = set(
                expected_index.workspace_eval_keys_by_uid[case.workspace_uid]
            )

        actual_eval_keys = set(case.labels)
        missing_labels = expected_eval_keys - actual_eval_keys
        extra_labels = actual_eval_keys - expected_eval_keys
        if missing_labels or extra_labels:
            details = []
            if missing_labels:
                details.append(f"missing labels: {sorted(missing_labels)[:5]}")
            if extra_labels:
                details.append(f"extra labels: {sorted(extra_labels)[:5]}")
            raise ValueError(
                f"thematic label coverage mismatch for {case.case_id!r} ("
                + "; ".join(details)
                + ")"
            )

        labels = tuple(case.labels.values())
        invalid_labels = sorted(set(labels) - ALLOWED_THEMATIC_CONTEXT_LABELS)
        if invalid_labels:
            raise ValueError(
                f"thematic label case {case.case_id!r} has invalid labels {invalid_labels!r}"
            )
        if not any(label > 0 for label in labels):
            raise ValueError(
                f"thematic label case {case.case_id!r} lacks positive signal"
            )
        if not any(label < 0 for label in labels):
            raise ValueError(
                f"thematic label case {case.case_id!r} lacks negative signal"
            )
        if -2 not in labels:
            raise ValueError(f"thematic label case {case.case_id!r} lacks -2 confuser")
