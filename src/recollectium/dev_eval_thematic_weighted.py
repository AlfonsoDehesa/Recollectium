"""Weighted judged thematic dev eval metrics for seeded Recollectium databases."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from recollectium.dev_eval_thematic_labels import (
    ADJUDICATED_ALL_POSITIVE_THEMATIC_CASE_IDS,
    ALLOWED_THEMATIC_CONTEXT_LABELS,
    THEMATIC_CONTEXT_LABEL_CASES,
    ThematicContextLabel,
    ThematicContextLabelCase,
    validate_thematic_context_label_cases,
)
from recollectium.models import SPACE_USER, SPACE_WORKSPACE, SearchResult

DEV_EVAL_LIMIT = 10
DEV_EVAL_PROTECTED_MINIMUM = 0
DEV_EVAL_MATCH_THRESHOLD = 0.0
THEMATIC_WEIGHTED_QUERIES_PER_GROUP = 3
DEFAULT_WORST_THEMATIC_LIMIT = 10
DevEvalProgressCallback = Callable[[dict[str, Any]], None]


def _emit_dev_eval_progress(
    progress_callback: DevEvalProgressCallback | None,
    event: dict[str, Any],
) -> None:
    if progress_callback is not None:
        progress_callback(event)

_LABEL_USEFUL_VALUE: Mapping[int, float] = {2: 1.0, 1: 0.5, -1: 0.0, -2: 0.0}
_LABEL_RETRIEVED_COST: Mapping[int, float] = {2: 1.0, 1: 1.0, -1: 1.0, -2: 1.5}


@dataclass(frozen=True, slots=True)
class ThematicWeightedQueryScore:
    """Per-query weighted thematic score details."""

    query_index: int
    query: str
    returned_count: int
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    useful_value_retrieved: float
    useful_value_total: float
    retrieved_cost_total: float
    direct_count: int
    adjacent_count: int
    unrelated_count: int
    confuser_count: int
    returned_top_ids: tuple[str, ...]
    returned_eval_keys: tuple[str, ...]
    returned_labels: tuple[ThematicContextLabel, ...]
    confuser_exposure: float


ThematicWeightedQueryScoreTriple = tuple[
    ThematicWeightedQueryScore,
    ThematicWeightedQueryScore,
    ThematicWeightedQueryScore,
]


@dataclass(frozen=True, slots=True)
class ThematicWeightedGroupScore:
    """Per thematic group weighted averages across its three fixture queries."""

    scope: str
    group: str
    workspace_uid: str | None
    average_weighted_precision: float
    average_weighted_recall: float
    average_weighted_f1: float
    query_scores: ThematicWeightedQueryScoreTriple


@dataclass(frozen=True, slots=True)
class ThematicWeightedWorstQuery:
    """Diagnostic row for a low-scoring weighted thematic query."""

    scope: str
    expected_group: str
    workspace_uid: str | None
    query_index: int
    query: str
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    returned_count: int
    useful_value_retrieved: float
    useful_value_total: float
    retrieved_cost_total: float
    direct_count: int
    adjacent_count: int
    unrelated_count: int
    confuser_count: int
    confuser_exposure: float
    returned_top_ids: tuple[str, ...]
    returned_eval_keys: tuple[str, ...]
    returned_labels: tuple[ThematicContextLabel, ...]


@dataclass(frozen=True, slots=True)
class ThematicWeightedReport:
    """Aggregate weighted thematic metric report."""

    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    user_weighted_precision: float
    user_weighted_recall: float
    user_weighted_f1: float
    workspace_weighted_precision: float
    workspace_weighted_recall: float
    workspace_weighted_f1: float
    limit: int
    protected_minimum: int
    match_threshold: float
    groups: int
    queries: int
    queries_per_group: int
    user_groups: int
    workspace_groups: int
    group_scores: tuple[ThematicWeightedGroupScore, ...]
    worst_queries: tuple[ThematicWeightedWorstQuery, ...]


SearchUser = Callable[[str, int], Sequence[SearchResult]]
SearchWorkspace = Callable[[str, str, int], Sequence[SearchResult]]


def thematic_weighted_cases_from_fixture(
    fixture: Sequence[ThematicContextLabelCase] | None = None,
    *,
    validate: bool | None = None,
) -> tuple[ThematicContextLabelCase, ...]:
    """Return the validated judged thematic label cases."""

    cases = tuple(THEMATIC_CONTEXT_LABEL_CASES if fixture is None else fixture)
    should_validate = validate if validate is not None else fixture is None
    if should_validate:
        validate_thematic_context_label_cases(cases)
    return cases


def _validate_weighted_cases(cases: Sequence[ThematicContextLabelCase]) -> None:
    """Validate caller-supplied weighted thematic cases before scoring."""

    seen_case_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_case_ids:
            raise ValueError(f"duplicate thematic weighted case id: {case.case_id!r}")
        seen_case_ids.add(case.case_id)

        if case.scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValueError(f"unsupported thematic weighted scope: {case.scope!r}")
        if case.scope == SPACE_USER and case.workspace_uid is not None:
            raise ValueError(
                f"user thematic weighted case {case.case_id!r} must not have workspace_uid"
            )
        if case.scope == SPACE_WORKSPACE and case.workspace_uid is None:
            raise ValueError(
                f"workspace thematic weighted case {case.case_id!r} requires workspace_uid"
            )

        labels_tuple = tuple(case.labels.values())
        invalid_labels = sorted(set(labels_tuple) - ALLOWED_THEMATIC_CONTEXT_LABELS)
        if invalid_labels:
            raise ValueError(
                f"thematic weighted case {case.case_id!r} has invalid labels {invalid_labels!r}"
            )
        if not any(label > 0 for label in labels_tuple):
            raise ValueError(
                f"thematic weighted case {case.case_id!r} lacks positive signal"
            )
        if not any(label < 0 for label in labels_tuple):
            if case.case_id not in ADJUDICATED_ALL_POSITIVE_THEMATIC_CASE_IDS:
                raise ValueError(
                    f"thematic weighted case {case.case_id!r} lacks negative signal"
                )


def _search_user_with_progress(
    core: Any,
    query: str,
    *,
    limit: int,
    protected_minimum: int,
    match_threshold: float,
    progress_callback: Any | None,
) -> list[SearchResult]:
    if progress_callback is None:
        return core.search_user_memories(
            query=query,
            limit=limit,
            include_archived=True,
            protected_minimum=protected_minimum,
            match_threshold=match_threshold,
        )
    return core.search_user_memories(
        query=query,
        limit=limit,
        include_archived=True,
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
        progress_callback=progress_callback,
    )


def _search_workspace_with_progress(
    core: Any,
    query: str,
    *,
    workspace_uid: str,
    limit: int,
    protected_minimum: int,
    match_threshold: float,
    progress_callback: Any | None,
) -> list[SearchResult]:
    if progress_callback is None:
        return core.search_workspace_memories(
            query=query,
            workspace_uid=workspace_uid,
            limit=limit,
            include_archived=True,
            protected_minimum=protected_minimum,
            match_threshold=match_threshold,
        )
    return core.search_workspace_memories(
        query=query,
        workspace_uid=workspace_uid,
        limit=limit,
        include_archived=True,
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
        progress_callback=progress_callback,
    )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _weighted_f1(precision: float, recall: float) -> float:
    if precision <= 0.0 or recall <= 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _eval_key_for_result(result: SearchResult) -> str:
    eval_key = result.memory.metadata.get("eval_key")
    if isinstance(eval_key, str) and eval_key.strip():
        return eval_key
    return result.memory.id


def _score_query(
    case: ThematicContextLabelCase,
    query_index: int,
    query: str,
    results: Sequence[SearchResult],
    *,
    limit: int,
) -> ThematicWeightedQueryScore:
    top_results = list(results[:limit])
    returned_top_ids = tuple(result.memory.id for result in top_results)
    returned_eval_keys = tuple(_eval_key_for_result(result) for result in top_results)
    missing_eval_keys = [key for key in returned_eval_keys if key not in case.labels]
    if missing_eval_keys:
        raise ValueError(
            f"thematic weighted fixture drift for {case.case_id!r}: missing labels for "
            f"{', '.join(repr(key) for key in missing_eval_keys)}"
        )
    returned_labels = cast(
        tuple[ThematicContextLabel, ...],
        tuple(case.labels[key] for key in returned_eval_keys),
    )
    label_counts = Counter(returned_labels)
    useful_value_retrieved = sum(
        _LABEL_USEFUL_VALUE[label] for label in returned_labels
    )
    useful_value_total = sum(
        _LABEL_USEFUL_VALUE[label] for label in case.labels.values()
    )
    if useful_value_total <= 0.0:
        raise ValueError(
            f"thematic weighted fixture {case.case_id!r} must have positive useful value"
        )
    retrieved_cost_total = sum(
        _LABEL_RETRIEVED_COST[label] for label in returned_labels
    )
    weighted_precision = (
        useful_value_retrieved / retrieved_cost_total
        if retrieved_cost_total > 0.0
        else 0.0
    )
    weighted_recall = useful_value_retrieved / useful_value_total
    weighted_f1 = _weighted_f1(weighted_precision, weighted_recall)
    returned_count = len(top_results)
    confuser_count = int(label_counts.get(-2, 0))
    return ThematicWeightedQueryScore(
        query_index=query_index,
        query=query,
        returned_count=returned_count,
        weighted_precision=weighted_precision,
        weighted_recall=weighted_recall,
        weighted_f1=weighted_f1,
        useful_value_retrieved=useful_value_retrieved,
        useful_value_total=useful_value_total,
        retrieved_cost_total=retrieved_cost_total,
        direct_count=int(label_counts.get(2, 0)),
        adjacent_count=int(label_counts.get(1, 0)),
        unrelated_count=int(label_counts.get(-1, 0)),
        confuser_count=confuser_count,
        returned_top_ids=returned_top_ids,
        returned_eval_keys=returned_eval_keys,
        returned_labels=returned_labels,
        confuser_exposure=(confuser_count / returned_count) if returned_count else 0.0,
    )


def evaluate_thematic_weighted_metrics(
    cases: Sequence[ThematicContextLabelCase],
    *,
    search_user: SearchUser,
    search_workspace: SearchWorkspace,
    limit: int = DEV_EVAL_LIMIT,
    protected_minimum: int = DEV_EVAL_PROTECTED_MINIMUM,
    match_threshold: float = DEV_EVAL_MATCH_THRESHOLD,
    worst_query_limit: int = DEFAULT_WORST_THEMATIC_LIMIT,
    progress_callback: DevEvalProgressCallback | None = None,
) -> ThematicWeightedReport:
    """Evaluate judged thematic labels under the fixed dev eval retrieval policy."""

    if limit != DEV_EVAL_LIMIT:
        raise ValueError(f"limit must be {DEV_EVAL_LIMIT}")
    if protected_minimum != DEV_EVAL_PROTECTED_MINIMUM:
        raise ValueError(f"protected_minimum must be {DEV_EVAL_PROTECTED_MINIMUM}")
    if match_threshold != DEV_EVAL_MATCH_THRESHOLD:
        raise ValueError(f"match_threshold must be {DEV_EVAL_MATCH_THRESHOLD}")
    if worst_query_limit < 0:
        raise ValueError("worst_query_limit must be non-negative")

    validated_cases = tuple(cases)
    _validate_weighted_cases(validated_cases)
    grouped_cases: dict[
        tuple[str, str, str | None], list[ThematicContextLabelCase]
    ] = {}
    for case in validated_cases:
        key = (case.scope, case.group, case.workspace_uid)
        grouped_cases.setdefault(key, []).append(case)

    group_scores: list[ThematicWeightedGroupScore] = []
    all_query_scores: list[ThematicWeightedQueryScore] = []
    scored_queries: list[tuple[str, str, str | None, ThematicWeightedQueryScore]] = []
    user_completed = 0
    workspace_completed = 0
    user_total = sum(1 for case in validated_cases if case.scope == SPACE_USER)
    workspace_total = sum(
        1 for case in validated_cases if case.scope == SPACE_WORKSPACE
    )
    for scope, group, workspace_uid in sorted(grouped_cases):
        group_cases = sorted(
            grouped_cases[(scope, group, workspace_uid)],
            key=lambda case: case.query_index,
        )
        if len(group_cases) != THEMATIC_WEIGHTED_QUERIES_PER_GROUP:
            raise ValueError(
                f"thematic weighted group {group!r} must have exactly "
                f"{THEMATIC_WEIGHTED_QUERIES_PER_GROUP} queries"
            )
        query_scores: list[ThematicWeightedQueryScore] = []
        for case in group_cases:
            if case.scope == SPACE_USER:
                results = search_user(case.query, limit)
            else:
                assert case.workspace_uid is not None
                results = search_workspace(case.query, case.workspace_uid, limit)
            score = _score_query(
                case, case.query_index, case.query, results, limit=limit
            )
            query_scores.append(score)
            all_query_scores.append(score)
            scored_queries.append((scope, group, workspace_uid, score))

        query_score_triple = (query_scores[0], query_scores[1], query_scores[2])
        group_scores.append(
            ThematicWeightedGroupScore(
                scope=scope,
                group=group,
                workspace_uid=workspace_uid,
                average_weighted_precision=_mean(
                    [score.weighted_precision for score in query_score_triple]
                ),
                average_weighted_recall=_mean(
                    [score.weighted_recall for score in query_score_triple]
                ),
                average_weighted_f1=_mean(
                    [score.weighted_f1 for score in query_score_triple]
                ),
                query_scores=query_score_triple,
            )
        )
        if scope == SPACE_USER:
            user_completed += 1
            _emit_dev_eval_progress(
                progress_callback,
                {
                    "phase": "thematic_weighted",
                    "bucket": "user_topics",
                    "label": "Thematic weighted user topics",
                    "scope": SPACE_USER,
                    "completed": user_completed,
                    "total": user_total,
                },
            )
        else:
            workspace_completed += 1
            _emit_dev_eval_progress(
                progress_callback,
                {
                    "phase": "thematic_weighted",
                    "bucket": "workspace_themes",
                    "label": "Thematic weighted workspace themes",
                    "scope": SPACE_WORKSPACE,
                    "completed": workspace_completed,
                    "total": workspace_total,
                },
            )

    user_group_scores = [score for score in group_scores if score.scope == SPACE_USER]
    workspace_group_scores = [
        score for score in group_scores if score.scope == SPACE_WORKSPACE
    ]
    all_group_precision = [score.average_weighted_precision for score in group_scores]
    all_group_recall = [score.average_weighted_recall for score in group_scores]
    all_group_f1 = [score.average_weighted_f1 for score in group_scores]
    worst_queries = tuple(
        ThematicWeightedWorstQuery(
            scope=scope,
            expected_group=group,
            workspace_uid=workspace_uid,
            query_index=query_score.query_index,
            query=query_score.query,
            weighted_precision=query_score.weighted_precision,
            weighted_recall=query_score.weighted_recall,
            weighted_f1=query_score.weighted_f1,
            returned_count=query_score.returned_count,
            useful_value_retrieved=query_score.useful_value_retrieved,
            useful_value_total=query_score.useful_value_total,
            retrieved_cost_total=query_score.retrieved_cost_total,
            direct_count=query_score.direct_count,
            adjacent_count=query_score.adjacent_count,
            unrelated_count=query_score.unrelated_count,
            confuser_count=query_score.confuser_count,
            confuser_exposure=query_score.confuser_exposure,
            returned_top_ids=query_score.returned_top_ids,
            returned_eval_keys=query_score.returned_eval_keys,
            returned_labels=query_score.returned_labels,
        )
        for scope, group, workspace_uid, query_score in sorted(
            scored_queries,
            key=lambda item: (
                min(item[3].weighted_precision, item[3].weighted_recall),
                item[3].weighted_precision,
                item[3].weighted_recall,
                item[0],
                item[2] or "",
                item[1],
                item[3].query_index,
            ),
        )[:worst_query_limit]
    )
    return ThematicWeightedReport(
        weighted_precision=_mean(all_group_precision),
        weighted_recall=_mean(all_group_recall),
        weighted_f1=_mean(all_group_f1),
        user_weighted_precision=_mean(
            [score.average_weighted_precision for score in user_group_scores]
        ),
        user_weighted_recall=_mean(
            [score.average_weighted_recall for score in user_group_scores]
        ),
        user_weighted_f1=_mean(
            [score.average_weighted_f1 for score in user_group_scores]
        ),
        workspace_weighted_precision=_mean(
            [score.average_weighted_precision for score in workspace_group_scores]
        ),
        workspace_weighted_recall=_mean(
            [score.average_weighted_recall for score in workspace_group_scores]
        ),
        workspace_weighted_f1=_mean(
            [score.average_weighted_f1 for score in workspace_group_scores]
        ),
        limit=limit,
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
        groups=len(group_scores),
        queries=len(all_query_scores),
        queries_per_group=THEMATIC_WEIGHTED_QUERIES_PER_GROUP,
        user_groups=len(user_group_scores),
        workspace_groups=len(workspace_group_scores),
        group_scores=tuple(group_scores),
        worst_queries=worst_queries,
    )


def evaluate_thematic_weighted_metrics_for_core(
    core: Any,
    *,
    limit: int = DEV_EVAL_LIMIT,
    protected_minimum: int = DEV_EVAL_PROTECTED_MINIMUM,
    match_threshold: float = DEV_EVAL_MATCH_THRESHOLD,
    worst_query_limit: int = DEFAULT_WORST_THEMATIC_LIMIT,
    progress_callback: Any | None = None,
    eval_progress_callback: DevEvalProgressCallback | None = None,
) -> ThematicWeightedReport:
    """Evaluate judged thematic labels against a seeded development database."""

    cases = thematic_weighted_cases_from_fixture()
    return evaluate_thematic_weighted_metrics(
        cases,
        search_user=lambda query, limit: _search_user_with_progress(
            core,
            query,
            limit=limit,
            protected_minimum=protected_minimum,
            match_threshold=match_threshold,
            progress_callback=progress_callback,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            _search_workspace_with_progress(
                core,
                query,
                workspace_uid=workspace_uid,
                limit=limit,
                protected_minimum=protected_minimum,
                match_threshold=match_threshold,
                progress_callback=progress_callback,
            )
        ),
        limit=limit,
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
        worst_query_limit=worst_query_limit,
        progress_callback=eval_progress_callback,
    )
