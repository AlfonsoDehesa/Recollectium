"""Development retrieval evaluators for seeded Recollectium databases."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from recollectium.dev_eval_semantic_fixtures import (
    SEMANTIC_MRR_FIXTURE,
    SemanticMRRFixtureEntry,
)
from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE, SearchResult

EXACT_MRR_CUTOFF = 10
SEMANTIC_MRR_CUTOFF = 10
SEMANTIC_MRR_PARAPHRASES_PER_TARGET = 3
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
