from __future__ import annotations

from collections.abc import Sequence
from typing import cast
import re

import pytest

from recollectium.dev_eval import (
    ExactMRRTarget,
    SemanticMRRTarget,
    ThematicPrecisionTarget,
    evaluate_exact_mrr,
    evaluate_exact_mrr_for_core,
    evaluate_semantic_mrr,
    evaluate_semantic_mrr_for_core,
    evaluate_thematic_precision,
    evaluate_thematic_precision_for_core,
    seeded_exact_mrr_targets,
    seeded_semantic_mrr_targets,
    semantic_mrr_targets_from_exact_targets,
    thematic_precision_targets_from_fixture,
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
from recollectium.dev_seed import (
    DEV_SEED_PROJECTS,
    DEV_SEED_PROJECT_THEMES_BY_UID,
    DEV_SEED_TOTAL_WORKSPACE_MEMORIES,
    DEV_SEED_USER_MEMORY_COUNT,
    DEV_SEED_USER_TOPICS,
    PROJECT_MEMORIES_BY_UID,
    USER_FACTS_BY_TOPIC,
)
from recollectium.models import Memory, SPACE_USER, SPACE_WORKSPACE, SearchResult


def _memory(
    memory_id: str,
    *,
    space: str = SPACE_USER,
    content: str | None = None,
    workspace_uid: str | None = None,
    dev_seed: bool = True,
    metadata: dict[str, object] | None = None,
) -> Memory:
    memory_metadata = {"dev_seed": dev_seed, **(metadata or {})}
    return Memory(
        id=memory_id,
        space=space,
        type="fact",
        content=content or f"Content for {memory_id}",
        workspace_uid=workspace_uid,
        metadata=memory_metadata,
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


def _thematic_results(
    groups: Sequence[str],
    *,
    scope: str = SPACE_USER,
    workspace_uid: str | None = None,
) -> list[SearchResult]:
    metadata_key = "dev_topic" if scope == SPACE_USER else "dev_theme"
    return [
        SearchResult(
            memory=_memory(
                f"{group}-{rank}",
                space=scope,
                workspace_uid=workspace_uid,
                metadata={metadata_key: group},
            ),
            score=1.0 / rank,
            rank=rank,
        )
        for rank, group in enumerate(groups, start=1)
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


def test_evaluate_semantic_mrr_scores_paraphrases_targets_and_breakdowns() -> None:
    targets = (
        SemanticMRRTarget("user-target", SPACE_USER, ("u1", "u2", "u3")),
        SemanticMRRTarget(
            "workspace-target",
            SPACE_WORKSPACE,
            ("w1", "w2", "w3"),
            "project-a",
        ),
    )
    user_results = {
        "u1": _search_results(["user-target", "other"]),
        "u2": _search_results(["other", "user-target"]),
        "u3": _search_results(["other-a", "other-b"]),
    }
    workspace_results = {
        ("project-a", "w1"): _search_results(
            ["other", "other-2", "workspace-target"], workspace_uid="project-a"
        ),
        ("project-a", "w2"): _search_results(
            ["workspace-target"], workspace_uid="project-a"
        ),
        ("project-a", "w3"): _search_results(
            ["other", "workspace-target"], workspace_uid="project-a"
        ),
    }

    report = evaluate_semantic_mrr(
        targets,
        search_user=lambda query, limit: user_results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: workspace_results[
            (workspace_uid, query)
        ][:limit],
        cutoff=10,
    )

    user_average = (1.0 + 0.5 + 0.0) / 3.0
    workspace_average = ((1.0 / 3.0) + 1.0 + 0.5) / 3.0
    assert report.targets == 2
    assert report.queries == 6
    assert report.paraphrases_per_target == 3
    assert report.user_targets == 1
    assert report.workspace_targets == 1
    assert report.user_value == pytest.approx(user_average)
    assert report.workspace_value == pytest.approx(workspace_average)
    assert report.value == pytest.approx((user_average + workspace_average) / 2.0)
    assert [
        score.average_reciprocal_rank for score in report.target_scores
    ] == pytest.approx([user_average, workspace_average])
    assert [score.rank for score in report.target_scores[0].query_scores] == [
        1,
        2,
        None,
    ]
    assert [
        score.reciprocal_rank for score in report.target_scores[0].query_scores
    ] == pytest.approx([1.0, 0.5, 0.0])


def test_evaluate_semantic_mrr_reports_worst_targets_with_query_details() -> None:
    targets = (
        SemanticMRRTarget("missing", SPACE_USER, ("m1", "m2", "m3")),
        SemanticMRRTarget("ranked", SPACE_USER, ("r1", "r2", "r3")),
        SemanticMRRTarget("perfect", SPACE_USER, ("p1", "p2", "p3")),
    )
    results = {
        "m1": _search_results(["a", "b"]),
        "m2": _search_results(["a", "b"]),
        "m3": _search_results(["a", "b"]),
        "r1": _search_results(["a", "ranked"]),
        "r2": _search_results(["ranked"]),
        "r3": _search_results(["a", "b", "ranked"]),
        "p1": _search_results(["perfect"]),
        "p2": _search_results(["perfect"]),
        "p3": _search_results(["perfect"]),
    }

    report = evaluate_semantic_mrr(
        targets,
        search_user=lambda query, limit: results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: [],
        worst_target_limit=2,
    )

    assert [target.target_id for target in report.worst_targets] == [
        "missing",
        "ranked",
    ]
    assert report.worst_targets[0].average_reciprocal_rank == 0.0
    assert report.worst_targets[0].query_scores[0].query == "m1"
    assert report.worst_targets[0].query_scores[0].returned_top_ids == ("a", "b")


def test_evaluate_semantic_mrr_treats_not_found_beyond_cutoff_as_zero() -> None:
    targets = (SemanticMRRTarget("target", SPACE_USER, ("q1", "q2", "q3")),)
    results = {
        "q1": _search_results(["a", "target"]),
        "q2": _search_results(["a", "b", "target"]),
        "q3": _search_results(["target"]),
    }

    report = evaluate_semantic_mrr(
        targets,
        search_user=lambda query, limit: results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: [],
        cutoff=2,
    )

    assert report.value == pytest.approx((0.5 + 0.0 + 1.0) / 3.0)
    assert [score.rank for score in report.target_scores[0].query_scores] == [
        2,
        None,
        1,
    ]
    assert report.target_scores[0].query_scores[1].returned_top_ids == ("a", "b")


def test_semantic_mrr_targets_validate_fixture_shape_and_mismatches() -> None:
    user = ExactMRRTarget("dev-user", SPACE_USER, "content")
    workspace = ExactMRRTarget("dev-workspace", SPACE_WORKSPACE, "content", "project-a")
    fixture: dict[str, SemanticMRRFixtureEntry] = {
        "dev-user": {
            "scope": SPACE_USER,
            "workspace_uid": None,
            "queries": ("a", "b", "c"),
        },
        "dev-workspace": {
            "scope": SPACE_WORKSPACE,
            "workspace_uid": "project-a",
            "queries": ("d", "e", "f"),
        },
    }

    targets = semantic_mrr_targets_from_exact_targets(
        (workspace, user), fixture=fixture
    )

    assert targets == (
        SemanticMRRTarget("dev-user", SPACE_USER, ("a", "b", "c")),
        SemanticMRRTarget(
            "dev-workspace", SPACE_WORKSPACE, ("d", "e", "f"), "project-a"
        ),
    )
    with pytest.raises(ValueError, match="target mismatch"):
        semantic_mrr_targets_from_exact_targets((user,), fixture={})
    with pytest.raises(ValueError, match="target mismatch"):
        semantic_mrr_targets_from_exact_targets((user,), fixture={**fixture})
    with pytest.raises(ValueError, match="exactly 3"):
        semantic_mrr_targets_from_exact_targets(
            (user,),
            fixture={
                "dev-user": {
                    "scope": SPACE_USER,
                    "workspace_uid": None,
                    "queries": cast(tuple[str, str, str], ("a", "b")),
                }
            },
        )
    with pytest.raises(ValueError, match="empty paraphrase"):
        semantic_mrr_targets_from_exact_targets(
            (user,),
            fixture={
                "dev-user": {
                    "scope": SPACE_USER,
                    "workspace_uid": None,
                    "queries": ("a", "", "c"),
                }
            },
        )
    with pytest.raises(ValueError, match="scope mismatch"):
        semantic_mrr_targets_from_exact_targets(
            (user,),
            fixture={
                "dev-user": {
                    "scope": SPACE_WORKSPACE,
                    "workspace_uid": None,
                    "queries": ("a", "b", "c"),
                }
            },
        )
    with pytest.raises(ValueError, match="workspace_uid mismatch"):
        semantic_mrr_targets_from_exact_targets(
            (workspace,),
            fixture={
                "dev-workspace": {
                    "scope": SPACE_WORKSPACE,
                    "workspace_uid": "wrong",
                    "queries": ("a", "b", "c"),
                }
            },
        )


def test_seeded_semantic_mrr_targets_uses_fixture_for_seeded_memories() -> None:
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
            del type, status, workspace_uid, limit
            assert include_archived is True
            if space == SPACE_USER:
                return [
                    _memory(memory_id, content=memory_id)
                    for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
                    if entry["scope"] == SPACE_USER
                ]
            if space == SPACE_WORKSPACE:
                return [
                    _memory(
                        memory_id,
                        space=SPACE_WORKSPACE,
                        content=memory_id,
                        workspace_uid=entry["workspace_uid"],
                    )
                    for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
                    if entry["scope"] == SPACE_WORKSPACE
                ]
            return []

    targets = seeded_semantic_mrr_targets(FakeLister())

    assert len(targets) == len(SEMANTIC_MRR_FIXTURE)
    assert targets[0].memory_id == "dev-user-001"
    assert targets[0].queries == SEMANTIC_MRR_FIXTURE["dev-user-001"]["queries"]
    cedar_target = next(
        target for target in targets if target.memory_id == "dev-workspace-01-001"
    )
    assert cedar_target.workspace_uid == "proj-fic-cedarledger-01"
    assert (
        cedar_target.queries == SEMANTIC_MRR_FIXTURE["dev-workspace-01-001"]["queries"]
    )


def test_evaluate_semantic_mrr_for_core_uses_seeded_targets_and_scope_searches() -> (
    None
):
    query_to_memory_id = {
        query: memory_id
        for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
        for query in entry["queries"]
    }

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
                return [
                    _memory(memory_id, content=memory_id)
                    for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
                    if entry["scope"] == SPACE_USER
                ]
            if space == SPACE_WORKSPACE:
                return [
                    _memory(
                        memory_id,
                        space=SPACE_WORKSPACE,
                        content=memory_id,
                        workspace_uid=entry["workspace_uid"],
                    )
                    for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
                    if entry["scope"] == SPACE_WORKSPACE
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
            return _search_results([query_to_memory_id[query]])

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
            return _search_results(
                [query_to_memory_id[query]], workspace_uid=workspace_uid
            )

    core = FakeCore()

    report = evaluate_semantic_mrr_for_core(core, cutoff=5)

    assert report.value == 1.0
    assert report.queries == 570
    assert core.user_queries[:3] == [
        (query, 5, True) for query in SEMANTIC_MRR_FIXTURE["dev-user-001"]["queries"]
    ]
    assert (
        SEMANTIC_MRR_FIXTURE["dev-workspace-01-001"]["queries"][0],
        "proj-fic-cedarledger-01",
        5,
        True,
    ) in core.workspace_queries


def test_evaluate_semantic_mrr_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_semantic_mrr(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            cutoff=0,
        )
    with pytest.raises(ValueError, match="worst_target_limit"):
        evaluate_semantic_mrr(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            worst_target_limit=-1,
        )
    with pytest.raises(ValueError, match="exactly 3"):
        evaluate_semantic_mrr(
            (
                SemanticMRRTarget(
                    "bad", SPACE_USER, cast(tuple[str, str, str], ("a", "b"))
                ),
            ),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="workspace_uid"):
        evaluate_semantic_mrr(
            (SemanticMRRTarget("workspace", SPACE_WORKSPACE, ("a", "b", "c")),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="unsupported target scope"):
        evaluate_semantic_mrr(
            (SemanticMRRTarget("bad", "bad-scope", ("a", "b", "c")),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )


def test_evaluate_thematic_precision_scores_groups_and_breakdowns() -> None:
    targets = (
        ThematicPrecisionTarget("user", SPACE_USER, ("u1", "u2", "u3")),
        ThematicPrecisionTarget(
            "workspace", SPACE_WORKSPACE, ("w1", "w2", "w3"), "project-a"
        ),
    )
    user_results = {
        "u1": _thematic_results(["user"] * 10),
        "u2": _thematic_results(["user"] * 5 + ["other"] * 5),
        "u3": _thematic_results(["other"] * 10),
    }
    workspace_results = {
        ("project-a", "w1"): _thematic_results(
            ["workspace"] * 7 + ["review"] * 3,
            scope=SPACE_WORKSPACE,
            workspace_uid="project-a",
        ),
        ("project-a", "w2"): _thematic_results(
            ["workspace"] * 10,
            scope=SPACE_WORKSPACE,
            workspace_uid="project-a",
        ),
        ("project-a", "w3"): _thematic_results(
            ["review"] * 10,
            scope=SPACE_WORKSPACE,
            workspace_uid="project-a",
        ),
    }

    report = evaluate_thematic_precision(
        targets,
        search_user=lambda query, limit: user_results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: workspace_results[
            (workspace_uid, query)
        ][:limit],
    )

    user_average = (1.0 + 0.5 + 0.0) / 3.0
    workspace_average = (0.7 + 1.0 + 0.0) / 3.0
    assert report.groups == 2
    assert report.queries == 6
    assert report.queries_per_group == 3
    assert report.user_groups == 1
    assert report.workspace_groups == 1
    assert report.user_value == pytest.approx(user_average)
    assert report.workspace_value == pytest.approx(workspace_average)
    assert report.value == pytest.approx((user_average + workspace_average) / 2.0)
    assert report.group_scores[0].average_precision == pytest.approx(user_average)
    assert report.group_scores[0].query_scores[1].matching_results == 5
    assert report.group_scores[0].query_scores[1].group_distribution == (
        ("other", 5),
        ("user", 5),
    )


def test_evaluate_thematic_precision_reports_failures_confusers_and_cutoff() -> None:
    target = ThematicPrecisionTarget("target", SPACE_USER, ("q1", "q2", "q3"))
    results = {
        "q1": _thematic_results(["target", "other", "target"]),
        "q2": _thematic_results(["target", "target", "miss"]),
        "q3": _thematic_results(["miss", "other", "target"]),
    }

    report = evaluate_thematic_precision(
        (target,),
        search_user=lambda query, limit: results[query][:limit],
        search_workspace=lambda query, workspace_uid, limit: [],
        cutoff=2,
        failure_limit=2,
        confuser_limit=2,
    )

    assert [score.precision for score in report.group_scores[0].query_scores] == [
        0.5,
        1.0,
        0.0,
    ]
    assert report.value == pytest.approx(0.5)
    assert len(report.failures) == 2
    assert report.failures[0].query == "q3"
    assert report.failures[0].group_distribution == (("miss", 1), ("other", 1))
    assert report.failures[0].returned_top_ids == ("miss-1", "other-2")
    assert [
        (confuser.confuser_group, confuser.count) for confuser in report.confusers
    ] == [
        ("other", 2),
        ("miss", 1),
    ]


def test_evaluate_thematic_precision_counts_scope_workspace_and_missing_confusers() -> (
    None
):
    workspace_target = ThematicPrecisionTarget(
        "exports", SPACE_WORKSPACE, ("q1", "q2", "q3"), "project-a"
    )
    wrong_scope = _memory(
        "wrong-scope",
        metadata={"dev_topic": "exports", "dev_theme": "exports"},
    )
    wrong_workspace = _memory(
        "wrong-workspace",
        space=SPACE_WORKSPACE,
        workspace_uid="project-b",
        metadata={"dev_theme": "exports"},
    )
    missing_theme = _memory(
        "missing-theme",
        space=SPACE_WORKSPACE,
        workspace_uid="project-a",
        metadata={},
    )
    matching = _memory(
        "matching",
        space=SPACE_WORKSPACE,
        workspace_uid="project-a",
        metadata={"dev_theme": "exports"},
    )
    results = [
        SearchResult(memory=wrong_scope, score=1.0, rank=1),
        SearchResult(memory=wrong_workspace, score=0.9, rank=2),
        SearchResult(memory=missing_theme, score=0.8, rank=3),
        SearchResult(memory=matching, score=0.7, rank=4),
    ]

    report = evaluate_thematic_precision(
        (workspace_target,),
        search_user=lambda query, limit: [],
        search_workspace=lambda query, workspace_uid, limit: results[:limit],
        cutoff=4,
    )

    assert report.value == pytest.approx(0.25)
    assert report.group_scores[0].query_scores[0].group_distribution == (
        ("<missing>", 1),
        ("<wrong-scope:user:exports>", 1),
        ("<wrong-workspace:project-b:exports>", 1),
        ("exports", 1),
    )
    assert report.group_scores[0].query_scores[0].matching_results == 1
    assert [
        (confuser.confuser_group, confuser.count) for confuser in report.confusers
    ] == [
        ("<missing>", 3),
        ("<wrong-scope:user:exports>", 3),
        ("<wrong-workspace:project-b:exports>", 3),
    ]


def test_thematic_precision_targets_validate_fixture_shape_and_mismatches() -> None:
    fixture: tuple[ThematicPrecisionFixtureEntry, ...] = (
        {
            "scope": SPACE_USER,
            "group": "travel",
            "workspace_uid": None,
            "queries": ("a", "b", "c"),
        },
        {
            "scope": SPACE_WORKSPACE,
            "group": "exports",
            "workspace_uid": "project-a",
            "queries": ("d", "e", "f"),
        },
    )

    assert thematic_precision_targets_from_fixture(fixture) == (
        ThematicPrecisionTarget("travel", SPACE_USER, ("a", "b", "c")),
        ThematicPrecisionTarget(
            "exports", SPACE_WORKSPACE, ("d", "e", "f"), "project-a"
        ),
    )
    with pytest.raises(ValueError, match="duplicate"):
        thematic_precision_targets_from_fixture((fixture[0], fixture[0]))
    with pytest.raises(ValueError, match="unsupported"):
        thematic_precision_targets_from_fixture(({**fixture[0], "scope": "bad-scope"},))
    with pytest.raises(ValueError, match="non-empty"):
        thematic_precision_targets_from_fixture(({**fixture[0], "group": ""},))
    with pytest.raises(ValueError, match="workspace_uid"):
        thematic_precision_targets_from_fixture(({**fixture[0], "workspace_uid": "x"},))
    with pytest.raises(ValueError, match="workspace_uid"):
        thematic_precision_targets_from_fixture(
            ({**fixture[1], "workspace_uid": None},)
        )
    with pytest.raises(ValueError, match="exactly 3"):
        thematic_precision_targets_from_fixture(
            ({**fixture[0], "queries": cast(tuple[str, str, str], ("a", "b"))},)
        )
    with pytest.raises(ValueError, match="empty query"):
        thematic_precision_targets_from_fixture(
            ({**fixture[0], "queries": ("a", "", "c")},)
        )


def test_evaluate_thematic_precision_for_core_uses_fixture_and_scope_searches() -> None:
    query_to_entry = {
        query: entry
        for entry in THEMATIC_PRECISION_FIXTURE
        for query in entry["queries"]
    }

    class FakeCore:
        def list_memories(
            self,
            space: str | None = None,
            type: str | None = None,
            status: str | None = None,
            workspace_uid: str | None = None,
            include_archived: bool = False,
            limit: int | None = None,
        ) -> list[Memory]:
            del space, type, status, workspace_uid, include_archived, limit
            return []

        def __init__(self) -> None:
            self.user_queries: list[tuple[str, int, bool]] = []
            self.workspace_queries: list[tuple[str, str | None, int, bool]] = []

        def search_user_memories(
            self,
            query: str,
            limit: int = 10,
            include_archived: bool = False,
            type: str | None = None,
        ) -> list[SearchResult]:
            del type
            self.user_queries.append((query, limit, include_archived))
            entry = query_to_entry[query]
            return _thematic_results([entry["group"]] * limit)

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
            entry = query_to_entry[query]
            return _thematic_results(
                [entry["group"]] * limit,
                scope=SPACE_WORKSPACE,
                workspace_uid=workspace_uid,
            )

    core = FakeCore()

    report = evaluate_thematic_precision_for_core(core, cutoff=5)

    assert report.value == 1.0
    assert report.groups == 19
    assert report.queries == 57
    assert core.user_queries[:3] == [
        (query, 5, True) for query in THEMATIC_PRECISION_FIXTURE[0]["queries"]
    ]
    assert (
        THEMATIC_PRECISION_FIXTURE[10]["queries"][0],
        "proj-fic-cedarledger-01",
        5,
        True,
    ) in core.workspace_queries


def test_evaluate_thematic_precision_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_thematic_precision(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            cutoff=0,
        )
    with pytest.raises(ValueError, match="failure_limit"):
        evaluate_thematic_precision(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            failure_limit=-1,
        )
    with pytest.raises(ValueError, match="confuser_limit"):
        evaluate_thematic_precision(
            (),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
            confuser_limit=-1,
        )
    with pytest.raises(ValueError, match="exactly 3"):
        evaluate_thematic_precision(
            (
                ThematicPrecisionTarget(
                    "bad", SPACE_USER, cast(tuple[str, str, str], ("a", "b"))
                ),
            ),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="workspace_uid"):
        evaluate_thematic_precision(
            (ThematicPrecisionTarget("workspace", SPACE_WORKSPACE, ("a", "b", "c")),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="workspace_uid"):
        evaluate_thematic_precision(
            (
                ThematicPrecisionTarget(
                    "user", SPACE_USER, ("a", "b", "c"), "project-a"
                ),
            ),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )
    with pytest.raises(ValueError, match="unsupported target scope"):
        evaluate_thematic_precision(
            (ThematicPrecisionTarget("bad", "bad-scope", ("a", "b", "c")),),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )


def test_thematic_fixture_covers_seeded_groups_with_three_queries() -> None:
    targets = thematic_precision_targets_from_fixture()
    expected_user_groups = set(DEV_SEED_USER_TOPICS)
    expected_workspace_groups = {
        (workspace_uid, theme)
        for workspace_uid, themes in DEV_SEED_PROJECT_THEMES_BY_UID.items()
        for theme in themes
    }
    all_queries = [query for target in targets for query in target.queries]

    assert len(targets) == len(expected_user_groups) + len(expected_workspace_groups)
    assert {
        target.group for target in targets if target.scope == SPACE_USER
    } == expected_user_groups
    assert {
        (target.workspace_uid, target.group)
        for target in targets
        if target.scope == SPACE_WORKSPACE
    } == expected_workspace_groups
    assert all(
        len(target.queries) == THEMATIC_PRECISION_QUERIES_PER_GROUP
        for target in targets
    )
    assert len(all_queries) == 57
    assert len(all_queries) == len(set(all_queries))
    assert not any(not query.strip() for query in all_queries)
    assert not any(
        target.group == query.casefold().strip()
        for target in targets
        for query in target.queries
    )


def test_semantic_fixture_covers_every_seeded_memory_with_three_queries() -> None:
    expected_user_ids = {f"dev-user-{index:03d}" for index in range(1, 101)}
    expected_workspace_ids = {
        f"dev-workspace-{workspace:02d}-{index:03d}"
        for workspace in range(1, 4)
        for index in range(1, 31)
    }

    assert len(SEMANTIC_MRR_FIXTURE) == (
        DEV_SEED_USER_MEMORY_COUNT + DEV_SEED_TOTAL_WORKSPACE_MEMORIES
    )
    assert set(SEMANTIC_MRR_FIXTURE) == expected_user_ids | expected_workspace_ids
    all_queries = [
        query for entry in SEMANTIC_MRR_FIXTURE.values() for query in entry["queries"]
    ]
    banned_fragments = (
        "seeded item",
        "original wording",
        "find the user memory about",
        "the person ",
    )
    banned_patterns = (
        re.compile(r"\bwhich\b.+\bsays\b", re.IGNORECASE),
        re.compile(r"\bwhich\b.+\bmentions\b", re.IGNORECASE),
    )

    assert all(
        len(entry["queries"]) == 3 and all(query.strip() for query in entry["queries"])
        for entry in SEMANTIC_MRR_FIXTURE.values()
    )
    assert len(all_queries) == len(set(all_queries))
    assert not any(
        fragment in query.casefold()
        for query in all_queries
        for fragment in banned_fragments
    )
    assert not any(
        pattern.search(query) for query in all_queries for pattern in banned_patterns
    )
    assert not any(
        query.endswith((" with.", " for.", " and.", " to.")) for query in all_queries
    )


def test_semantic_fixture_queries_are_not_keyword_bag_artifacts() -> None:
    """Reject review-regressed comma-list prompts masquerading as paraphrases."""
    all_queries = [
        query for entry in SEMANTIC_MRR_FIXTURE.values() for query in entry["queries"]
    ]
    comma_list_pattern = re.compile(
        r"\b[\w'-]+(?:,\s+[\w'-]+){4,},?\s+and\s+[\w'-]+[?.]?$",
        re.IGNORECASE,
    )

    assert not any(comma_list_pattern.search(query) for query in all_queries)
    assert not any(query.count(",") >= 8 for query in all_queries)


def test_semantic_fixture_contains_natural_spot_checked_queries() -> None:
    assert SEMANTIC_MRR_FIXTURE["dev-user-001"]["queries"] == (
        "What travel preference says they like unscheduled time for exploring neighborhoods?",
        "Ask for the user's tendency to avoid overbooking vacations with reservations.",
        "Ask about their preference for city trip days with room to wander locally.",
    )
    assert SEMANTIC_MRR_FIXTURE["dev-user-027"]["queries"] == (
        "What kinds of games help the user relax after work?",
        "Look up their preference for cozy games with gentle objectives, pleasant soundtracks, and forgiving systems.",
        "Show their preference for low-stress games that are forgiving when they pause or leave.",
    )
    user_001_text = " ".join(SEMANTIC_MRR_FIXTURE["dev-user-001"]["queries"]).casefold()
    user_027_text = " ".join(SEMANTIC_MRR_FIXTURE["dev-user-027"]["queries"]).casefold()
    assert "neighborhood" in user_001_text
    assert "reservation" in user_001_text
    assert "seaside" not in user_001_text
    assert "train" not in user_001_text
    assert "cozy" in user_027_text
    assert "low-stress" in user_027_text
    assert "synth" not in user_027_text
    assert "chimes" not in user_027_text
    assert SEMANTIC_MRR_FIXTURE["dev-workspace-01-001"]["queries"][0] == (
        "How should CedarLedger divide access between owners, report reviewers, and sales clerks?"
    )
    assert SEMANTIC_MRR_FIXTURE["dev-workspace-03-030"]["queries"][0] == (
        "What assignment problem happened to jobs cleared before the shift change?"
    )


def _semantic_fixture_source_memories() -> dict[str, str]:
    sources: dict[str, str] = {}
    user_index = 1
    for topic_memories in USER_FACTS_BY_TOPIC:
        for memory in topic_memories:
            sources[f"dev-user-{user_index:03d}"] = memory
            user_index += 1
    for workspace_index, project in enumerate(DEV_SEED_PROJECTS, start=1):
        for memory_index, memory in enumerate(
            PROJECT_MEMORIES_BY_UID[project["uid"]], start=1
        ):
            sources[f"dev-workspace-{workspace_index:02d}-{memory_index:03d}"] = memory
    return sources


def _semantic_fixture_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token.strip("'")
        for token in re.findall(r"[a-z0-9][a-z0-9'-]*", text.casefold())
    )


def _max_contiguous_token_overlap(source: str, query: str) -> int:
    source_tokens = _semantic_fixture_tokens(source)
    query_tokens = _semantic_fixture_tokens(query)
    max_overlap = 0
    for source_index in range(len(source_tokens)):
        for query_index in range(len(query_tokens)):
            overlap = 0
            while (
                source_index + overlap < len(source_tokens)
                and query_index + overlap < len(query_tokens)
                and source_tokens[source_index + overlap]
                == query_tokens[query_index + overlap]
            ):
                overlap += 1
            max_overlap = max(max_overlap, overlap)
    return max_overlap


def test_semantic_fixture_avoids_near_exact_source_copies() -> None:
    """Semantic queries must not copy long spans from the target memory.

    Product review found that the original fixture mostly wrapped exact source
    text in shallow templates. Keep every query below a ten-token contiguous
    overlap with its target memory so Semantic MRR remains distinct from Exact
    MRR and continues to exercise paraphrase retrieval.
    """
    source_memories = _semantic_fixture_source_memories()
    assert set(source_memories) == set(SEMANTIC_MRR_FIXTURE)

    overlaps = [
        _max_contiguous_token_overlap(source_memories[memory_id], query)
        for memory_id, entry in SEMANTIC_MRR_FIXTURE.items()
        for query in entry["queries"]
    ]

    assert max(overlaps) < 10
