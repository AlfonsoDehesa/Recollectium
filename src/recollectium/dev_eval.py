"""Development retrieval evaluators for seeded Recollectium databases."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE, SearchResult

EXACT_MRR_CUTOFF = 10
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
