"""Development retrieval evaluators for seeded Recollectium databases."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import log2
from typing import Protocol

from recollectium.dev_eval_ranked_set_fixtures import (
    RANKED_SET_NDCG_CUTOFF,
    RANKED_SET_NDCG_FIXTURE,
    RankedSetNDCGFixtureEntry,
)
from recollectium.dev_eval_semantic_fixtures import (
    SEMANTIC_MRR_FIXTURE,
    SemanticMRRFixtureEntry,
)
from recollectium.dev_eval_thematic_fixtures import (
    THEMATIC_PRECISION_FIXTURE,
    THEMATIC_PRECISION_QUERIES_PER_GROUP,
    ThematicPrecisionFixtureEntry,
)
from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE, SearchResult

EXACT_MRR_CUTOFF = 10
SEMANTIC_MRR_CUTOFF = 10
SEMANTIC_MRR_PARAPHRASES_PER_TARGET = 3
THEMATIC_PRECISION_CUTOFF = 10
DEFAULT_WORST_MISS_LIMIT = 10
QUERY_SNIPPET_LENGTH = 120


@dataclass(frozen=True, slots=True)
class ExactMRRTarget:
    """A seeded memory target for exact-text MRR evaluation."""

    memory_id: str
    scope: str
    content: str
    workspace_uid: str | None = None


@dataclass(frozen=True, slots=True)
class ExactMRRTargetScore:
    """Per-target exact MRR score details."""

    target_id: str
    scope: str
    workspace_uid: str | None
    rank: int | None
    reciprocal_rank: float
    query_snippet: str
    returned_top_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExactMRRWorstMiss:
    """Diagnostic row for a low-scoring exact MRR target."""

    target_id: str
    expected_scope: str
    workspace_uid: str | None
    rank: int | None
    reciprocal_rank: float
    query_snippet: str
    returned_top_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExactMRRReport:
    """Aggregate exact MRR metric report."""

    value: float
    user_value: float
    workspace_value: float
    hit_at_1: float
    hit_at_3: float
    cutoff: int
    targets: int
    user_targets: int
    workspace_targets: int
    worst_misses: tuple[ExactMRRWorstMiss, ...]
    target_scores: tuple[ExactMRRTargetScore, ...]


@dataclass(frozen=True, slots=True)
class SemanticMRRTarget:
    """A seeded memory target with its semantic paraphrase queries."""

    memory_id: str
    scope: str
    queries: tuple[str, str, str]
    workspace_uid: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticMRRQueryScore:
    """Per-paraphrase semantic MRR score details."""

    query_index: int
    query: str
    rank: int | None
    reciprocal_rank: float
    returned_top_ids: tuple[str, ...]


SemanticMRRQueryScoreTriple = tuple[
    SemanticMRRQueryScore,
    SemanticMRRQueryScore,
    SemanticMRRQueryScore,
]


@dataclass(frozen=True, slots=True)
class SemanticMRRTargetScore:
    """Per-target semantic MRR score averaged across paraphrases."""

    target_id: str
    scope: str
    workspace_uid: str | None
    average_reciprocal_rank: float
    query_scores: SemanticMRRQueryScoreTriple


@dataclass(frozen=True, slots=True)
class SemanticMRRWorstTarget:
    """Diagnostic row for a low-scoring semantic MRR target."""

    target_id: str
    expected_scope: str
    workspace_uid: str | None
    average_reciprocal_rank: float
    query_scores: SemanticMRRQueryScoreTriple


@dataclass(frozen=True, slots=True)
class SemanticMRRReport:
    """Aggregate semantic MRR metric report."""

    value: float
    user_value: float
    workspace_value: float
    cutoff: int
    targets: int
    queries: int
    paraphrases_per_target: int
    user_targets: int
    workspace_targets: int
    worst_targets: tuple[SemanticMRRWorstTarget, ...]
    target_scores: tuple[SemanticMRRTargetScore, ...]


@dataclass(frozen=True, slots=True)
class ThematicPrecisionTarget:
    """A seeded topic or workspace theme group with broad semantic queries."""

    group: str
    scope: str
    queries: tuple[str, str, str]
    workspace_uid: str | None = None


@dataclass(frozen=True, slots=True)
class ThematicPrecisionQueryScore:
    """Per-query thematic Precision@10 score details."""

    query_index: int
    query: str
    matching_results: int
    precision: float
    group_distribution: tuple[tuple[str, int], ...]
    returned_top_ids: tuple[str, ...]


ThematicPrecisionQueryScoreTriple = tuple[
    ThematicPrecisionQueryScore,
    ThematicPrecisionQueryScore,
    ThematicPrecisionQueryScore,
]


@dataclass(frozen=True, slots=True)
class ThematicPrecisionGroupScore:
    """Per-topic or per-theme Precision@10 averaged across fixture queries."""

    scope: str
    group: str
    workspace_uid: str | None
    average_precision: float
    query_scores: ThematicPrecisionQueryScoreTriple


@dataclass(frozen=True, slots=True)
class ThematicPrecisionFailure:
    """Diagnostic row for a thematic query that missed at least one result slot."""

    scope: str
    expected_group: str
    workspace_uid: str | None
    query_index: int
    query: str
    precision: float
    matching_results: int
    group_distribution: tuple[tuple[str, int], ...]
    returned_top_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThematicPrecisionConfuser:
    """Frequently returned non-matching topic or theme group."""

    scope: str
    expected_group: str
    confuser_group: str
    count: int
    workspace_uid: str | None = None


@dataclass(frozen=True, slots=True)
class ThematicPrecisionReport:
    """Aggregate thematic Precision@10 metric report."""

    value: float
    user_value: float
    workspace_value: float
    cutoff: int
    groups: int
    queries: int
    queries_per_group: int
    user_groups: int
    workspace_groups: int
    group_scores: tuple[ThematicPrecisionGroupScore, ...]
    failures: tuple[ThematicPrecisionFailure, ...]
    confusers: tuple[ThematicPrecisionConfuser, ...]


@dataclass(frozen=True, slots=True)
class RankedSetRelevance:
    """A graded relevance judgment for one memory in a ranked-set query."""

    grade: int
    rationale: str


@dataclass(frozen=True, slots=True)
class RankedSetNDCGTarget:
    """A curated query with graded relevance judgments for NDCG@5."""

    case_id: str
    scope: str
    workspace_uid: str | None
    query: str
    relevance: Mapping[str, RankedSetRelevance]


@dataclass(frozen=True, slots=True)
class RankedSetExpectedMemory:
    """Diagnostic view of an expected graded memory."""

    memory_id: str
    grade: int
    rationale: str


@dataclass(frozen=True, slots=True)
class RankedSetReturnedMemory:
    """Diagnostic view of an actual returned memory."""

    memory_id: str
    rank: int
    grade: int


@dataclass(frozen=True, slots=True)
class RankedSetNDCGCaseScore:
    """Per-case ranked-set NDCG@5 score details."""

    case_id: str
    scope: str
    workspace_uid: str | None
    query: str
    dcg: float
    ideal_dcg: float
    ndcg: float
    expected_memories: tuple[RankedSetExpectedMemory, ...]
    returned_top: tuple[RankedSetReturnedMemory, ...]


@dataclass(frozen=True, slots=True)
class RankedSetNDCGWorstCase:
    """Diagnostic row for a low-scoring ranked-set NDCG case."""

    case_id: str
    expected_scope: str
    workspace_uid: str | None
    query: str
    ndcg: float
    expected_memories: tuple[RankedSetExpectedMemory, ...]
    returned_top: tuple[RankedSetReturnedMemory, ...]


@dataclass(frozen=True, slots=True)
class RankedSetNDCGReport:
    """Aggregate ranked-set NDCG@5 metric report."""

    value: float
    user_value: float
    workspace_value: float
    cutoff: int
    cases: int
    user_cases: int
    workspace_cases: int
    lowest_cases: tuple[RankedSetNDCGWorstCase, ...]
    case_scores: tuple[RankedSetNDCGCaseScore, ...]


class SeededMemoryLister(Protocol):
    """Core-like object that can list seeded memories by scope."""

    def list_memories(
        self,
        space: str | None = None,
        type: str | None = None,
        status: str | None = None,
        workspace_uid: str | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[Memory]: ...


class ExactMRRCore(SeededMemoryLister, Protocol):
    """Core-like object that can run exact MRR searches."""

    def search_user_memories(
        self,
        query: str,
        limit: int = 10,
        include_archived: bool = False,
        type: str | None = None,
    ) -> list[SearchResult]: ...

    def search_workspace_memories(
        self,
        query: str,
        workspace_uid: str | None,
        limit: int = 10,
        include_archived: bool = False,
        type: str | None = None,
    ) -> list[SearchResult]: ...


class SemanticMRRCore(ExactMRRCore, Protocol):
    """Core-like object that can run semantic MRR searches."""


class ThematicPrecisionCore(ExactMRRCore, Protocol):
    """Core-like object that can run thematic Precision@10 searches."""


class RankedSetNDCGCore(ExactMRRCore, Protocol):
    """Core-like object that can run ranked-set NDCG@5 searches."""


UserSearch = Callable[[str, int], Sequence[SearchResult]]
WorkspaceSearch = Callable[[str, str, int], Sequence[SearchResult]]


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _query_snippet(query: str, *, length: int = QUERY_SNIPPET_LENGTH) -> str:
    collapsed = " ".join(query.split())
    if len(collapsed) <= length:
        return collapsed
    return f"{collapsed[: length - 1]}…"


def _returned_ids(results: Sequence[SearchResult], cutoff: int) -> tuple[str, ...]:
    return tuple(result.memory.id for result in results[:cutoff])


def _reciprocal_rank(
    target_id: str, returned_ids: Sequence[str]
) -> tuple[int | None, float]:
    for index, memory_id in enumerate(returned_ids, start=1):
        if memory_id == target_id:
            return index, 1.0 / index
    return None, 0.0


def seeded_exact_mrr_targets(core: SeededMemoryLister) -> tuple[ExactMRRTarget, ...]:
    """Return every seeded memory as an exact MRR target.

    User memories are evaluated in user scope. Workspace memories are evaluated
    in their own workspace scope. Only memories marked with ``metadata.dev_seed``
    are included so the evaluator can run safely against a seeded development
    database without scoring unrelated local memories.
    """

    user_memories = core.list_memories(space=SPACE_USER, include_archived=True)
    workspace_memories = core.list_memories(
        space=SPACE_WORKSPACE,
        include_archived=True,
    )
    targets = [
        ExactMRRTarget(
            memory_id=memory.id,
            scope=memory.space,
            content=memory.content,
            workspace_uid=memory.workspace_uid,
        )
        for memory in [*user_memories, *workspace_memories]
        if memory.metadata.get("dev_seed") is True
    ]
    return tuple(sorted(targets, key=lambda target: target.memory_id))


def _validate_semantic_fixture_entry(
    memory_id: str,
    target: ExactMRRTarget,
    entry: SemanticMRRFixtureEntry,
) -> tuple[str, str, str]:
    if entry["scope"] != target.scope:
        raise ValueError(
            f"semantic fixture scope mismatch for {memory_id!r}: "
            f"expected {target.scope!r}, got {entry['scope']!r}"
        )
    if entry["workspace_uid"] != target.workspace_uid:
        raise ValueError(
            f"semantic fixture workspace_uid mismatch for {memory_id!r}: "
            f"expected {target.workspace_uid!r}, got {entry['workspace_uid']!r}"
        )
    queries = entry["queries"]
    if len(queries) != SEMANTIC_MRR_PARAPHRASES_PER_TARGET:
        raise ValueError(
            f"semantic fixture for {memory_id!r} must have exactly "
            f"{SEMANTIC_MRR_PARAPHRASES_PER_TARGET} paraphrases"
        )
    if any(not query.strip() for query in queries):
        raise ValueError(f"semantic fixture for {memory_id!r} has an empty paraphrase")
    return queries


def semantic_mrr_targets_from_exact_targets(
    exact_targets: Sequence[ExactMRRTarget],
    *,
    fixture: Mapping[str, SemanticMRRFixtureEntry] = SEMANTIC_MRR_FIXTURE,
) -> tuple[SemanticMRRTarget, ...]:
    """Attach deterministic semantic paraphrases to every seeded target.

    The checked-in fixture must match the target memory IDs exactly and provide
    exactly three non-empty paraphrase queries per target. This keeps runtime
    evaluation deterministic and prevents silently skipping missing fixture rows.
    """

    target_by_id = {target.memory_id: target for target in exact_targets}
    fixture_ids = set(fixture)
    target_ids = set(target_by_id)
    missing_ids = sorted(target_ids - fixture_ids)
    extra_ids = sorted(fixture_ids - target_ids)
    if missing_ids or extra_ids:
        details: list[str] = []
        if missing_ids:
            details.append(f"missing fixture IDs: {', '.join(missing_ids[:5])}")
        if extra_ids:
            details.append(f"extra fixture IDs: {', '.join(extra_ids[:5])}")
        raise ValueError(
            "semantic fixture target mismatch (" + "; ".join(details) + ")"
        )

    targets: list[SemanticMRRTarget] = []
    for memory_id in sorted(target_by_id):
        exact_target = target_by_id[memory_id]
        queries = _validate_semantic_fixture_entry(
            memory_id,
            exact_target,
            fixture[memory_id],
        )
        targets.append(
            SemanticMRRTarget(
                memory_id=memory_id,
                scope=exact_target.scope,
                workspace_uid=exact_target.workspace_uid,
                queries=queries,
            )
        )
    return tuple(targets)


def seeded_semantic_mrr_targets(
    core: SeededMemoryLister,
) -> tuple[SemanticMRRTarget, ...]:
    """Return every seeded memory target with its semantic paraphrase queries."""

    return semantic_mrr_targets_from_exact_targets(seeded_exact_mrr_targets(core))


def _validate_thematic_fixture_entry(
    entry: ThematicPrecisionFixtureEntry,
) -> tuple[str, str, tuple[str, str, str], str | None]:
    scope = entry["scope"]
    group = entry["group"]
    workspace_uid = entry["workspace_uid"]
    queries = entry["queries"]
    if scope not in {SPACE_USER, SPACE_WORKSPACE}:
        raise ValueError(f"unsupported thematic fixture scope: {scope!r}")
    if not group.strip():
        raise ValueError("thematic fixture group must be non-empty")
    if scope == SPACE_USER and workspace_uid is not None:
        raise ValueError(
            f"user thematic group {group!r} must not include workspace_uid"
        )
    if scope == SPACE_WORKSPACE and workspace_uid is None:
        raise ValueError(f"workspace thematic group {group!r} requires workspace_uid")
    if len(queries) != THEMATIC_PRECISION_QUERIES_PER_GROUP:
        raise ValueError(
            f"thematic fixture group {group!r} must have exactly "
            f"{THEMATIC_PRECISION_QUERIES_PER_GROUP} queries"
        )
    if any(not query.strip() for query in queries):
        raise ValueError(f"thematic fixture group {group!r} has an empty query")
    return scope, group, queries, workspace_uid


def thematic_precision_targets_from_fixture(
    fixture: Sequence[ThematicPrecisionFixtureEntry] = THEMATIC_PRECISION_FIXTURE,
) -> tuple[ThematicPrecisionTarget, ...]:
    """Return deterministic thematic Precision@10 target groups.

    The checked-in fixture is explicit source data: ten user topics and nine
    workspace themes, each with exactly three broad natural-language queries.
    """

    targets: list[ThematicPrecisionTarget] = []
    seen_keys: set[tuple[str, str | None, str]] = set()
    for entry in fixture:
        scope, group, queries, workspace_uid = _validate_thematic_fixture_entry(entry)
        key = (scope, workspace_uid, group)
        if key in seen_keys:
            raise ValueError(f"duplicate thematic fixture group: {key!r}")
        seen_keys.add(key)
        targets.append(
            ThematicPrecisionTarget(
                scope=scope,
                group=group,
                workspace_uid=workspace_uid,
                queries=queries,
            )
        )
    return tuple(targets)


def _validate_ranked_set_fixture_entry(
    entry: RankedSetNDCGFixtureEntry,
) -> tuple[str, str, str | None, Mapping[str, RankedSetRelevance]]:
    case_id = entry["id"]
    scope = entry["scope"]
    workspace_uid = entry["workspace_uid"]
    query = entry["query"]
    relevance = entry["relevance"]
    if not case_id.strip():
        raise ValueError("ranked-set fixture id must be non-empty")
    if scope not in {SPACE_USER, SPACE_WORKSPACE}:
        raise ValueError(f"unsupported ranked-set fixture scope: {scope!r}")
    if scope == SPACE_USER and workspace_uid is not None:
        raise ValueError(
            f"user ranked-set case {case_id!r} must not include workspace_uid"
        )
    if scope == SPACE_WORKSPACE and workspace_uid is None:
        raise ValueError(
            f"workspace ranked-set case {case_id!r} requires workspace_uid"
        )
    if not query.strip():
        raise ValueError(f"ranked-set case {case_id!r} has an empty query")
    if not relevance:
        raise ValueError(f"ranked-set case {case_id!r} requires relevance judgments")

    judgments: dict[str, RankedSetRelevance] = {}
    for memory_id, judgment in relevance.items():
        grade = judgment["grade"]
        rationale = judgment["rationale"]
        if grade not in {1, 2, 3}:
            raise ValueError(
                f"ranked-set case {case_id!r} has invalid grade {grade!r} for {memory_id!r}"
            )
        if not rationale.strip():
            raise ValueError(
                f"ranked-set case {case_id!r} has empty rationale for {memory_id!r}"
            )
        judgments[memory_id] = RankedSetRelevance(grade=grade, rationale=rationale)
    if 3 not in {judgment.grade for judgment in judgments.values()}:
        raise ValueError(f"ranked-set case {case_id!r} requires at least one grade 3")
    return case_id, query, workspace_uid, judgments


def ranked_set_ndcg_targets_from_fixture(
    fixture: Sequence[RankedSetNDCGFixtureEntry] = RANKED_SET_NDCG_FIXTURE,
) -> tuple[RankedSetNDCGTarget, ...]:
    """Return deterministic ranked-set NDCG@5 cases from checked-in fixtures."""

    targets: list[RankedSetNDCGTarget] = []
    seen_ids: set[str] = set()
    seen_queries: set[tuple[str, str | None, str]] = set()
    for entry in fixture:
        case_id, query, workspace_uid, relevance = _validate_ranked_set_fixture_entry(
            entry
        )
        scope = entry["scope"]
        if case_id in seen_ids:
            raise ValueError(f"duplicate ranked-set case id: {case_id!r}")
        seen_ids.add(case_id)
        query_key = (scope, workspace_uid, query.casefold().strip())
        if query_key in seen_queries:
            raise ValueError(f"duplicate ranked-set query: {query!r}")
        seen_queries.add(query_key)
        targets.append(
            RankedSetNDCGTarget(
                case_id=case_id,
                scope=scope,
                workspace_uid=workspace_uid,
                query=query,
                relevance=relevance,
            )
        )
    return tuple(targets)


def _dcg(grades: Sequence[int]) -> float:
    return sum(
        ((2.0**grade) - 1.0) / log2(rank + 1)
        for rank, grade in enumerate(grades, start=1)
    )


def _ranked_set_expected_memories(
    target: RankedSetNDCGTarget,
) -> tuple[RankedSetExpectedMemory, ...]:
    return tuple(
        RankedSetExpectedMemory(
            memory_id=memory_id,
            grade=judgment.grade,
            rationale=judgment.rationale,
        )
        for memory_id, judgment in sorted(
            target.relevance.items(), key=lambda item: (-item[1].grade, item[0])
        )
    )


def _ranked_set_case_score(
    target: RankedSetNDCGTarget,
    results: Sequence[SearchResult],
    cutoff: int,
) -> RankedSetNDCGCaseScore:
    top_results = results[:cutoff]
    returned_top = tuple(
        RankedSetReturnedMemory(
            memory_id=result.memory.id,
            rank=rank,
            grade=target.relevance.get(
                result.memory.id, RankedSetRelevance(0, "")
            ).grade,
        )
        for rank, result in enumerate(top_results, start=1)
    )
    returned_grades = [returned.grade for returned in returned_top]
    dcg = _dcg(returned_grades)
    ideal_grades = sorted(
        (judgment.grade for judgment in target.relevance.values()), reverse=True
    )[:cutoff]
    ideal_dcg = _dcg(ideal_grades)
    return RankedSetNDCGCaseScore(
        case_id=target.case_id,
        scope=target.scope,
        workspace_uid=target.workspace_uid,
        query=target.query,
        dcg=dcg,
        ideal_dcg=ideal_dcg,
        ndcg=dcg / ideal_dcg if ideal_dcg > 0 else 0.0,
        expected_memories=_ranked_set_expected_memories(target),
        returned_top=returned_top,
    )


def evaluate_ranked_set_ndcg(
    targets: Sequence[RankedSetNDCGTarget],
    *,
    search_user: UserSearch,
    search_workspace: WorkspaceSearch,
    cutoff: int = RANKED_SET_NDCG_CUTOFF,
    lowest_case_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> RankedSetNDCGReport:
    """Evaluate curated ranked-set NDCG@5 cases.

    Each case runs one scope-specific search at ``cutoff`` and treats returned
    memories absent from the relevance map as grade zero.
    """

    if cutoff < 1:
        raise ValueError("cutoff must be at least 1")
    if lowest_case_limit < 0:
        raise ValueError("lowest_case_limit must be non-negative")

    case_scores: list[RankedSetNDCGCaseScore] = []
    for target in targets:
        if target.scope == SPACE_WORKSPACE and target.workspace_uid is None:
            raise ValueError(
                f"workspace ranked-set case {target.case_id!r} requires workspace_uid"
            )
        if target.scope == SPACE_USER and target.workspace_uid is not None:
            raise ValueError(
                f"user ranked-set case {target.case_id!r} must not include workspace_uid"
            )
        if target.scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValueError(f"unsupported target scope: {target.scope!r}")
        if target.scope == SPACE_USER:
            results = search_user(target.query, cutoff)
        else:
            assert target.workspace_uid is not None
            results = search_workspace(target.query, target.workspace_uid, cutoff)
        case_scores.append(_ranked_set_case_score(target, results, cutoff))

    user_scores = [score.ndcg for score in case_scores if score.scope == SPACE_USER]
    workspace_scores = [
        score.ndcg for score in case_scores if score.scope == SPACE_WORKSPACE
    ]
    all_scores = [score.ndcg for score in case_scores]
    lowest_cases = tuple(
        RankedSetNDCGWorstCase(
            case_id=score.case_id,
            expected_scope=score.scope,
            workspace_uid=score.workspace_uid,
            query=score.query,
            ndcg=score.ndcg,
            expected_memories=score.expected_memories,
            returned_top=score.returned_top,
        )
        for score in sorted(
            case_scores,
            key=lambda score: (
                score.ndcg,
                score.scope,
                score.workspace_uid or "",
                score.case_id,
            ),
        )[:lowest_case_limit]
        if score.ndcg < 1.0
    )
    return RankedSetNDCGReport(
        value=_mean(all_scores),
        user_value=_mean(user_scores),
        workspace_value=_mean(workspace_scores),
        cutoff=cutoff,
        cases=len(case_scores),
        user_cases=len(user_scores),
        workspace_cases=len(workspace_scores),
        lowest_cases=lowest_cases,
        case_scores=tuple(case_scores),
    )


def evaluate_exact_mrr(
    targets: Sequence[ExactMRRTarget],
    *,
    search_user: UserSearch,
    search_workspace: WorkspaceSearch,
    cutoff: int = EXACT_MRR_CUTOFF,
    worst_miss_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> ExactMRRReport:
    """Evaluate exact-text MRR for seeded memory targets.

    Each target is queried with exactly its stored content. User targets search
    user scope; workspace targets search their own workspace UID. The target ID's
    first rank in the top ``cutoff`` results determines reciprocal rank.
    """

    if cutoff < 1:
        raise ValueError("cutoff must be at least 1")
    if worst_miss_limit < 0:
        raise ValueError("worst_miss_limit must be non-negative")

    target_scores: list[ExactMRRTargetScore] = []
    for target in targets:
        if target.scope == SPACE_USER:
            results = search_user(target.content, cutoff)
        elif target.scope == SPACE_WORKSPACE:
            if target.workspace_uid is None:
                raise ValueError(
                    f"workspace target {target.memory_id!r} requires workspace_uid"
                )
            results = search_workspace(target.content, target.workspace_uid, cutoff)
        else:
            raise ValueError(f"unsupported target scope: {target.scope!r}")

        returned_ids = _returned_ids(results, cutoff)
        rank, reciprocal = _reciprocal_rank(target.memory_id, returned_ids)
        target_scores.append(
            ExactMRRTargetScore(
                target_id=target.memory_id,
                scope=target.scope,
                workspace_uid=target.workspace_uid,
                rank=rank,
                reciprocal_rank=reciprocal,
                query_snippet=_query_snippet(target.content),
                returned_top_ids=returned_ids,
            )
        )

    user_scores = [
        score.reciprocal_rank for score in target_scores if score.scope == SPACE_USER
    ]
    workspace_scores = [
        score.reciprocal_rank
        for score in target_scores
        if score.scope == SPACE_WORKSPACE
    ]
    all_scores = [score.reciprocal_rank for score in target_scores]
    hit_at_1 = _mean([1.0 if score.rank == 1 else 0.0 for score in target_scores])
    hit_at_3 = _mean(
        [
            1.0 if score.rank is not None and score.rank <= 3 else 0.0
            for score in target_scores
        ]
    )
    miss_scores = [score for score in target_scores if score.reciprocal_rank < 1.0]
    worst_source = sorted(
        miss_scores,
        key=lambda score: (
            score.reciprocal_rank,
            score.rank if score.rank is not None else cutoff + 1,
            score.target_id,
        ),
    )[:worst_miss_limit]
    worst_misses = tuple(
        ExactMRRWorstMiss(
            target_id=score.target_id,
            expected_scope=score.scope,
            workspace_uid=score.workspace_uid,
            rank=score.rank,
            reciprocal_rank=score.reciprocal_rank,
            query_snippet=score.query_snippet,
            returned_top_ids=score.returned_top_ids,
        )
        for score in worst_source
    )

    return ExactMRRReport(
        value=_mean(all_scores),
        user_value=_mean(user_scores),
        workspace_value=_mean(workspace_scores),
        hit_at_1=hit_at_1,
        hit_at_3=hit_at_3,
        cutoff=cutoff,
        targets=len(target_scores),
        user_targets=len(user_scores),
        workspace_targets=len(workspace_scores),
        worst_misses=worst_misses,
        target_scores=tuple(target_scores),
    )


def _semantic_query_score(
    target_id: str,
    query_index: int,
    query: str,
    results: Sequence[SearchResult],
    cutoff: int,
) -> SemanticMRRQueryScore:
    returned_ids = _returned_ids(results, cutoff)
    rank, reciprocal = _reciprocal_rank(target_id, returned_ids)
    return SemanticMRRQueryScore(
        query_index=query_index,
        query=query,
        rank=rank,
        reciprocal_rank=reciprocal,
        returned_top_ids=returned_ids,
    )


def evaluate_semantic_mrr(
    targets: Sequence[SemanticMRRTarget],
    *,
    search_user: UserSearch,
    search_workspace: WorkspaceSearch,
    cutoff: int = SEMANTIC_MRR_CUTOFF,
    worst_target_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> SemanticMRRReport:
    """Evaluate semantic MRR for seeded targets using fixture paraphrases.

    Each target must have exactly three paraphrases. Each paraphrase is scored by
    the target memory ID's reciprocal rank in the top ``cutoff`` results, then the
    three scores are averaged for the target and all targets are averaged for the
    aggregate metric.
    """

    if cutoff < 1:
        raise ValueError("cutoff must be at least 1")
    if worst_target_limit < 0:
        raise ValueError("worst_target_limit must be non-negative")

    target_scores: list[SemanticMRRTargetScore] = []
    for target in targets:
        if len(target.queries) != SEMANTIC_MRR_PARAPHRASES_PER_TARGET:
            raise ValueError(
                f"semantic target {target.memory_id!r} must have exactly "
                f"{SEMANTIC_MRR_PARAPHRASES_PER_TARGET} paraphrases"
            )
        if target.scope == SPACE_WORKSPACE and target.workspace_uid is None:
            raise ValueError(
                f"workspace target {target.memory_id!r} requires workspace_uid"
            )
        if target.scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValueError(f"unsupported target scope: {target.scope!r}")

        query_scores: list[SemanticMRRQueryScore] = []
        for index, query in enumerate(target.queries, start=1):
            if target.scope == SPACE_USER:
                results = search_user(query, cutoff)
            else:
                assert target.workspace_uid is not None
                results = search_workspace(query, target.workspace_uid, cutoff)
            query_scores.append(
                _semantic_query_score(target.memory_id, index, query, results, cutoff)
            )

        score_triple = (query_scores[0], query_scores[1], query_scores[2])
        target_scores.append(
            SemanticMRRTargetScore(
                target_id=target.memory_id,
                scope=target.scope,
                workspace_uid=target.workspace_uid,
                average_reciprocal_rank=_mean(
                    [score.reciprocal_rank for score in score_triple]
                ),
                query_scores=score_triple,
            )
        )

    user_scores = [
        score.average_reciprocal_rank
        for score in target_scores
        if score.scope == SPACE_USER
    ]
    workspace_scores = [
        score.average_reciprocal_rank
        for score in target_scores
        if score.scope == SPACE_WORKSPACE
    ]
    all_scores = [score.average_reciprocal_rank for score in target_scores]
    worst_source = sorted(
        target_scores,
        key=lambda score: (score.average_reciprocal_rank, score.target_id),
    )[:worst_target_limit]
    worst_targets = tuple(
        SemanticMRRWorstTarget(
            target_id=score.target_id,
            expected_scope=score.scope,
            workspace_uid=score.workspace_uid,
            average_reciprocal_rank=score.average_reciprocal_rank,
            query_scores=score.query_scores,
        )
        for score in worst_source
        if score.average_reciprocal_rank < 1.0
    )

    return SemanticMRRReport(
        value=_mean(all_scores),
        user_value=_mean(user_scores),
        workspace_value=_mean(workspace_scores),
        cutoff=cutoff,
        targets=len(target_scores),
        queries=len(target_scores) * SEMANTIC_MRR_PARAPHRASES_PER_TARGET,
        paraphrases_per_target=SEMANTIC_MRR_PARAPHRASES_PER_TARGET,
        user_targets=len(user_scores),
        workspace_targets=len(workspace_scores),
        worst_targets=worst_targets,
        target_scores=tuple(target_scores),
    )


def _thematic_metadata_group(scope: str, result: SearchResult) -> str:
    metadata_key = "dev_topic" if scope == SPACE_USER else "dev_theme"
    value = result.memory.metadata.get(metadata_key)
    if isinstance(value, str) and value.strip():
        return value
    return "<missing>"


def _thematic_result_group(
    target: ThematicPrecisionTarget, result: SearchResult
) -> str:
    actual_group = _thematic_metadata_group(result.memory.space, result)
    if result.memory.space != target.scope:
        return f"<wrong-scope:{result.memory.space}:{actual_group}>"
    if (
        target.scope == SPACE_WORKSPACE
        and result.memory.workspace_uid != target.workspace_uid
    ):
        workspace_uid = result.memory.workspace_uid or "<none>"
        return f"<wrong-workspace:{workspace_uid}:{actual_group}>"
    return _thematic_metadata_group(target.scope, result)


def _thematic_result_matches(
    target: ThematicPrecisionTarget, result: SearchResult
) -> bool:
    if result.memory.space != target.scope:
        return False
    if (
        target.scope == SPACE_WORKSPACE
        and result.memory.workspace_uid != target.workspace_uid
    ):
        return False
    return _thematic_result_group(target, result) == target.group


def _thematic_query_score(
    target: ThematicPrecisionTarget,
    query_index: int,
    query: str,
    results: Sequence[SearchResult],
    cutoff: int,
) -> ThematicPrecisionQueryScore:
    top_results = results[:cutoff]
    matching_results = sum(
        1 for result in top_results if _thematic_result_matches(target, result)
    )
    distribution = Counter(
        _thematic_result_group(target, result) for result in top_results
    )
    return ThematicPrecisionQueryScore(
        query_index=query_index,
        query=query,
        matching_results=matching_results,
        precision=matching_results / cutoff,
        group_distribution=tuple(sorted(distribution.items())),
        returned_top_ids=_returned_ids(results, cutoff),
    )


def evaluate_thematic_precision(
    targets: Sequence[ThematicPrecisionTarget],
    *,
    search_user: UserSearch,
    search_workspace: WorkspaceSearch,
    cutoff: int = THEMATIC_PRECISION_CUTOFF,
    failure_limit: int = DEFAULT_WORST_MISS_LIMIT,
    confuser_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> ThematicPrecisionReport:
    """Evaluate thematic Precision@10 for seeded topic and theme groups."""

    if cutoff < 1:
        raise ValueError("cutoff must be at least 1")
    if failure_limit < 0:
        raise ValueError("failure_limit must be non-negative")
    if confuser_limit < 0:
        raise ValueError("confuser_limit must be non-negative")

    group_scores: list[ThematicPrecisionGroupScore] = []
    confuser_counts: Counter[tuple[str, str | None, str, str]] = Counter()
    for target in targets:
        if len(target.queries) != THEMATIC_PRECISION_QUERIES_PER_GROUP:
            raise ValueError(
                f"thematic target {target.group!r} must have exactly "
                f"{THEMATIC_PRECISION_QUERIES_PER_GROUP} queries"
            )
        if target.scope == SPACE_WORKSPACE and target.workspace_uid is None:
            raise ValueError(
                f"workspace thematic group {target.group!r} requires workspace_uid"
            )
        if target.scope == SPACE_USER and target.workspace_uid is not None:
            raise ValueError(
                f"user thematic group {target.group!r} must not include workspace_uid"
            )
        if target.scope not in {SPACE_USER, SPACE_WORKSPACE}:
            raise ValueError(f"unsupported target scope: {target.scope!r}")

        query_scores: list[ThematicPrecisionQueryScore] = []
        for index, query in enumerate(target.queries, start=1):
            if target.scope == SPACE_USER:
                results = search_user(query, cutoff)
            else:
                assert target.workspace_uid is not None
                results = search_workspace(query, target.workspace_uid, cutoff)
            for result in results[:cutoff]:
                if not _thematic_result_matches(target, result):
                    confuser_counts[
                        (
                            target.scope,
                            target.workspace_uid,
                            target.group,
                            _thematic_result_group(target, result),
                        )
                    ] += 1
            query_scores.append(
                _thematic_query_score(target, index, query, results, cutoff)
            )

        score_triple = (query_scores[0], query_scores[1], query_scores[2])
        group_scores.append(
            ThematicPrecisionGroupScore(
                scope=target.scope,
                group=target.group,
                workspace_uid=target.workspace_uid,
                average_precision=_mean([score.precision for score in score_triple]),
                query_scores=score_triple,
            )
        )

    user_scores = [
        score.average_precision for score in group_scores if score.scope == SPACE_USER
    ]
    workspace_scores = [
        score.average_precision
        for score in group_scores
        if score.scope == SPACE_WORKSPACE
    ]
    all_scores = [score.average_precision for score in group_scores]
    failures = sorted(
        (
            ThematicPrecisionFailure(
                scope=group_score.scope,
                expected_group=group_score.group,
                workspace_uid=group_score.workspace_uid,
                query_index=query_score.query_index,
                query=query_score.query,
                precision=query_score.precision,
                matching_results=query_score.matching_results,
                group_distribution=query_score.group_distribution,
                returned_top_ids=query_score.returned_top_ids,
            )
            for group_score in group_scores
            for query_score in group_score.query_scores
            if query_score.precision < 1.0
        ),
        key=lambda failure: (
            failure.precision,
            failure.scope,
            failure.workspace_uid or "",
            failure.expected_group,
            failure.query_index,
        ),
    )[:failure_limit]
    confusers = tuple(
        ThematicPrecisionConfuser(
            scope=scope,
            workspace_uid=workspace_uid,
            expected_group=expected_group,
            confuser_group=confuser_group,
            count=count,
        )
        for (scope, workspace_uid, expected_group, confuser_group), count in sorted(
            confuser_counts.items(),
            key=lambda item: (
                -item[1],
                item[0][0],
                item[0][1] or "",
                item[0][2],
                item[0][3],
            ),
        )[:confuser_limit]
    )

    return ThematicPrecisionReport(
        value=_mean(all_scores),
        user_value=_mean(user_scores),
        workspace_value=_mean(workspace_scores),
        cutoff=cutoff,
        groups=len(group_scores),
        queries=len(group_scores) * THEMATIC_PRECISION_QUERIES_PER_GROUP,
        queries_per_group=THEMATIC_PRECISION_QUERIES_PER_GROUP,
        user_groups=len(user_scores),
        workspace_groups=len(workspace_scores),
        group_scores=tuple(group_scores),
        failures=tuple(failures),
        confusers=confusers,
    )


def evaluate_exact_mrr_for_core(
    core: ExactMRRCore,
    *,
    cutoff: int = EXACT_MRR_CUTOFF,
    worst_miss_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> ExactMRRReport:
    """Evaluate exact MRR against a seeded development database via core methods."""

    targets = seeded_exact_mrr_targets(core)
    return evaluate_exact_mrr(
        targets,
        search_user=lambda query, limit: core.search_user_memories(
            query,
            limit=limit,
            include_archived=True,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            core.search_workspace_memories(
                query,
                workspace_uid=workspace_uid,
                limit=limit,
                include_archived=True,
            )
        ),
        cutoff=cutoff,
        worst_miss_limit=worst_miss_limit,
    )


def evaluate_semantic_mrr_for_core(
    core: SemanticMRRCore,
    *,
    cutoff: int = SEMANTIC_MRR_CUTOFF,
    worst_target_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> SemanticMRRReport:
    """Evaluate semantic MRR against a seeded development database via core methods."""

    targets = seeded_semantic_mrr_targets(core)
    return evaluate_semantic_mrr(
        targets,
        search_user=lambda query, limit: core.search_user_memories(
            query,
            limit=limit,
            include_archived=True,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            core.search_workspace_memories(
                query,
                workspace_uid=workspace_uid,
                limit=limit,
                include_archived=True,
            )
        ),
        cutoff=cutoff,
        worst_target_limit=worst_target_limit,
    )


def evaluate_thematic_precision_for_core(
    core: ThematicPrecisionCore,
    *,
    cutoff: int = THEMATIC_PRECISION_CUTOFF,
    failure_limit: int = DEFAULT_WORST_MISS_LIMIT,
    confuser_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> ThematicPrecisionReport:
    """Evaluate thematic Precision@10 against a seeded development database."""

    targets = thematic_precision_targets_from_fixture()
    return evaluate_thematic_precision(
        targets,
        search_user=lambda query, limit: core.search_user_memories(
            query,
            limit=limit,
            include_archived=True,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            core.search_workspace_memories(
                query,
                workspace_uid=workspace_uid,
                limit=limit,
                include_archived=True,
            )
        ),
        cutoff=cutoff,
        failure_limit=failure_limit,
        confuser_limit=confuser_limit,
    )


def evaluate_ranked_set_ndcg_for_core(
    core: RankedSetNDCGCore,
    *,
    cutoff: int = RANKED_SET_NDCG_CUTOFF,
    lowest_case_limit: int = DEFAULT_WORST_MISS_LIMIT,
) -> RankedSetNDCGReport:
    """Evaluate ranked-set NDCG@5 against a seeded development database."""

    targets = ranked_set_ndcg_targets_from_fixture()
    return evaluate_ranked_set_ndcg(
        targets,
        search_user=lambda query, limit: core.search_user_memories(
            query,
            limit=limit,
            include_archived=True,
        ),
        search_workspace=lambda query, workspace_uid, limit: (
            core.search_workspace_memories(
                query,
                workspace_uid=workspace_uid,
                limit=limit,
                include_archived=True,
            )
        ),
        cutoff=cutoff,
        lowest_case_limit=lowest_case_limit,
    )
