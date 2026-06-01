from __future__ import annotations

from collections.abc import Sequence
import pytest

from recollectium.dev_eval import (
    ExactMRRTarget,
    evaluate_exact_mrr,
    evaluate_exact_mrr_for_core,
    seeded_exact_mrr_targets,
)
from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE, SearchResult


def _memory(
    memory_id: str,
    *,
    space: str = SPACE_USER,
    content: str | None = None,
    workspace_uid: str | None = None,
    dev_seed: bool = True,
) -> Memory:
    return Memory(
        id=memory_id,
        space=space,
        type="fact",
        content=content or f"Content for {memory_id}",
        workspace_uid=workspace_uid,
        metadata={"dev_seed": dev_seed},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _search_results(
    ids: Sequence[str], *, workspace_uid: str | None = None
) -> list[SearchResult]:
    space = SPACE_WORKSPACE if workspace_uid is not None else SPACE_USER
    return [
        SearchResult(
            memory=_memory(memory_id, space=space, workspace_uid=workspace_uid),
            score=1.0 / rank,
            rank=rank,
        )
        for rank, memory_id in enumerate(ids, start=1)
    ]


def test_evaluate_exact_mrr_calculates_reciprocal_rank_hits_and_breakdowns() -> None:
    targets = (
        ExactMRRTarget("user-rank-1", SPACE_USER, "query user rank one"),
        ExactMRRTarget("user-rank-2", SPACE_USER, "query user rank two"),
        ExactMRRTarget(
            "workspace-rank-3",
            SPACE_WORKSPACE,
            "query workspace rank three",
            "project-a",
        ),
        ExactMRRTarget(
            "workspace-missing",
            SPACE_WORKSPACE,
            "query workspace missing",
            "project-a",
        ),
    )
    user_results = {
        "query user rank one": _search_results(["user-rank-1", "other-user"]),
        "query user rank two": _search_results(["other-user", "user-rank-2"]),
    }
    workspace_results = {
        ("project-a", "query workspace rank three"): _search_results(
            ["other-workspace-a", "other-workspace-b", "workspace-rank-3"],
            workspace_uid="project-a",
        ),
        ("project-a", "query workspace missing"): _search_results(
            ["other-workspace-a", "other-workspace-b", "other-workspace-c"],
            workspace_uid="project-a",
        ),
    }

    report = evaluate_exact_mrr(
        targets,
        search_user=lambda query, limit: user_results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: workspace_results[
            (workspace_uid, query)
        ][:limit],
        cutoff=10,
    )

    assert report.targets == 4
    assert report.user_targets == 2
    assert report.workspace_targets == 2
    assert report.value == pytest.approx((1.0 + 0.5 + (1.0 / 3.0) + 0.0) / 4.0)
    assert report.user_value == pytest.approx(0.75)
    assert report.workspace_value == pytest.approx(1.0 / 6.0)
    assert report.hit_at_1 == pytest.approx(0.25)
    assert report.hit_at_3 == pytest.approx(0.75)
    assert [score.rank for score in report.target_scores] == [1, 2, 3, None]
    assert [score.reciprocal_rank for score in report.target_scores] == pytest.approx(
        [1.0, 0.5, 1.0 / 3.0, 0.0]
    )


def test_evaluate_exact_mrr_reports_worst_miss_diagnostics() -> None:
    long_query = " ".join(["diagnostic"] * 30)
    targets = (
        ExactMRRTarget("missing-target", SPACE_USER, long_query),
        ExactMRRTarget("rank-4-target", SPACE_USER, "rank four query"),
        ExactMRRTarget("rank-1-target", SPACE_USER, "rank one query"),
    )
    results = {
        long_query: _search_results(["a", "b", "c"]),
        "rank four query": _search_results(["a", "b", "c", "rank-4-target"]),
        "rank one query": _search_results(["rank-1-target", "a", "b"]),
    }

    report = evaluate_exact_mrr(
        targets,
        search_user=lambda query, limit: results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: [],
        cutoff=10,
        worst_miss_limit=2,
    )

    assert [miss.target_id for miss in report.worst_misses] == [
        "missing-target",
        "rank-4-target",
    ]
    assert report.worst_misses[0].expected_scope == SPACE_USER
    assert report.worst_misses[0].rank is None
    assert report.worst_misses[0].reciprocal_rank == 0.0
    assert report.worst_misses[0].returned_top_ids == ("a", "b", "c")
    assert len(report.worst_misses[0].query_snippet) == 120
    assert report.worst_misses[0].query_snippet.endswith("…")
    assert report.worst_misses[1].rank == 4
    assert report.worst_misses[1].reciprocal_rank == 0.25


def test_evaluate_exact_mrr_treats_not_found_beyond_cutoff_as_zero() -> None:
    targets = (ExactMRRTarget("target", SPACE_USER, "query"),)

    report = evaluate_exact_mrr(
        targets,
        search_user=lambda query, limit: _search_results(["a", "b", "target"])[:limit],
        search_workspace=lambda query, workspace_uid, limit: [],
        cutoff=2,
    )

    assert report.value == 0.0
    assert report.hit_at_1 == 0.0
    assert report.hit_at_3 == 0.0
    assert report.target_scores[0].rank is None
    assert report.target_scores[0].returned_top_ids == ("a", "b")


def test_seeded_exact_mrr_targets_filters_and_sorts_seeded_memories() -> None:
    class FakeLister:
        def list_memories(
            self,
            space: str | None = None,
            type: str | None = None,
            status: str | None = None,
            workspace_uid: str | None = None,
            include_archived: bool = False,
            limit: int | None = None,
        ) -> list[Memory]:
            assert include_archived is True
            del type, status, workspace_uid, limit
            if space == SPACE_USER:
                return [
                    _memory("dev-user-002", content="second"),
                    _memory("local-user", dev_seed=False),
                    _memory("dev-user-001", content="first"),
                ]
            if space == SPACE_WORKSPACE:
                return [
                    _memory(
                        "dev-workspace-001",
                        space=SPACE_WORKSPACE,
                        content="workspace",
                        workspace_uid="project-a",
                    ),
                    _memory(
                        "local-workspace",
                        space=SPACE_WORKSPACE,
                        workspace_uid="project-a",
                        dev_seed=False,
                    ),
                ]
            return []

    targets = seeded_exact_mrr_targets(FakeLister())

    assert targets == (
        ExactMRRTarget("dev-user-001", SPACE_USER, "first"),
        ExactMRRTarget("dev-user-002", SPACE_USER, "second"),
        ExactMRRTarget(
            "dev-workspace-001",
            SPACE_WORKSPACE,
            "workspace",
            "project-a",
        ),
    )


def test_evaluate_exact_mrr_for_core_uses_seeded_targets_and_scope_searches() -> None:
    class FakeCore:
        def __init__(self) -> None:
            self.user_queries: list[tuple[str, int, bool]] = []
            self.workspace_queries: list[tuple[str, str | None, int, bool]] = []

        def list_memories(
            self,
            space: str | None = None,
            type: str | None = None,
            status: str | None = None,
            workspace_uid: str | None = None,
            include_archived: bool = False,
            limit: int | None = None,
        ) -> list[Memory]:
            del type, status, workspace_uid, limit
            assert include_archived is True
            if space == SPACE_USER:
                return [_memory("dev-user", content="user query")]
            if space == SPACE_WORKSPACE:
                return [
                    _memory(
                        "dev-workspace",
                        space=SPACE_WORKSPACE,
                        content="workspace query",
                        workspace_uid="project-a",
                    )
                ]
            return []

        def search_user_memories(
            self,
            query: str,
            limit: int = 10,
            include_archived: bool = False,
            type: str | None = None,
        ) -> list[SearchResult]:
            del type
            self.user_queries.append((query, limit, include_archived))
            return _search_results(["dev-user"])

        def search_workspace_memories(
            self,
            query: str,
            workspace_uid: str | None,
            limit: int = 10,
            include_archived: bool = False,
            type: str | None = None,
        ) -> list[SearchResult]:
            del type
            self.workspace_queries.append(
                (query, workspace_uid, limit, include_archived)
            )
            return _search_results(["dev-workspace"], workspace_uid="project-a")

    core = FakeCore()

    report = evaluate_exact_mrr_for_core(core, cutoff=5)

    assert report.value == 1.0
    assert report.user_value == 1.0
    assert report.workspace_value == 1.0
    assert core.user_queries == [("user query", 5, True)]
    assert core.workspace_queries == [("workspace query", "project-a", 5, True)]


def test_evaluate_exact_mrr_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_exact_mrr(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            cutoff=0,
        )
    with pytest.raises(ValueError, match="worst_miss_limit"):
        evaluate_exact_mrr(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            worst_miss_limit=-1,
        )
    with pytest.raises(ValueError, match="workspace_uid"):
        evaluate_exact_mrr(
            (ExactMRRTarget("workspace", SPACE_WORKSPACE, "query"),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="unsupported target scope"):
        evaluate_exact_mrr(
            (ExactMRRTarget("bad", "bad-scope", "query"),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
