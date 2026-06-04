from __future__ import annotations

from pathlib import Path

import pytest

import recollectium.dev_optimize_threshold as opt
from recollectium.dev_eval_thematic_labels import ThematicContextLabelCase
from recollectium.dev_optimize_threshold import (
    ThresholdOptimizationError,
    ThresholdOptimizationReport,
    ThresholdSearchBundle,
    ThresholdSweepRow,
    build_threshold_optimization_report,
    build_threshold_search_bundles,
    generate_threshold_values,
    report_summary_lines,
    score_runtime_bundle,
    score_runtime_row,
    score_threshold_bundle,
    score_threshold_rows,
    select_recommended_row,
    threshold_rows_to_csv,
    write_threshold_csv,
    write_threshold_png,
)
from recollectium.models import Memory, SearchResult


def _memory(memory_id: str) -> Memory:
    return Memory(
        id=memory_id,
        space="user",
        type="fact",
        content=f"Content for {memory_id}",
        workspace_uid=None,
        metadata={"dev_seed": True},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _bundle(
    scores: list[tuple[str, float]], labels: dict[str, int]
) -> ThresholdSearchBundle:
    return ThresholdSearchBundle(
        case_id="case-1",
        scope="user",
        group="travel",
        query_index=1,
        query="query text",
        workspace_uid=None,
        labels=labels,
        results=tuple(
            SearchResult(memory=_memory(memory_id), score=score, rank=rank)
            for rank, (memory_id, score) in enumerate(scores, start=1)
        ),
    )


def test_generate_threshold_values_includes_bounds_and_rejects_bad_ranges() -> None:
    assert generate_threshold_values(0.0, 1.0, 0.25) == (
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    )
    assert generate_threshold_values(0.0, 0.3, 0.2) == (0.0, 0.2, 0.3)

    with pytest.raises(ThresholdOptimizationError):
        generate_threshold_values(-0.1, 1.0, 0.01)
    with pytest.raises(ThresholdOptimizationError):
        generate_threshold_values(0.0, 1.1, 0.01)
    with pytest.raises(ThresholdOptimizationError):
        generate_threshold_values(0.5, 0.4, 0.01)
    with pytest.raises(ThresholdOptimizationError):
        generate_threshold_values(0.0, 1.0, 0.0)
    with pytest.raises(ThresholdOptimizationError):
        generate_threshold_values(0.0, 1.0, 0.0005)


def test_validate_threshold_sweep_rejects_bad_beta_via_report_builder() -> None:
    bundle = _bundle([("memory-direct", 0.9)], {"memory-direct": 2})

    with pytest.raises(ThresholdOptimizationError, match="beta must be > 0.0"):
        build_threshold_optimization_report(
            model="model",
            provider="provider",
            start=0.0,
            end=1.0,
            step=0.1,
            beta=0.0,
            output_format="csv",
            output_path=None,
            wrote_config=False,
            bundles=(bundle,),
        )


def test_score_threshold_bundle_weights_direct_and_adjacent_more_than_noise() -> None:
    bundle = _bundle(
        [
            ("memory-confuser", 0.95),
            ("memory-direct", 0.90),
            ("memory-adjacent", 0.85),
            ("memory-unrelated", 0.10),
        ],
        {
            "memory-direct": 2,
            "memory-adjacent": 1,
            "memory-unrelated": -1,
            "memory-confuser": -2,
        },
    )

    metrics = score_threshold_bundle(bundle, 0.80)

    assert metrics.returned_count == 3
    assert metrics.direct_retrieved == 1
    assert metrics.adjacent_retrieved == 1
    assert metrics.unrelated_retrieved == 0
    assert metrics.confuser_retrieved == 1
    assert metrics.useful_value_total == pytest.approx(1.5)
    assert metrics.useful_value_retrieved == pytest.approx(1.5)
    assert metrics.weighted_precision == pytest.approx(1.5 / 3.5)
    assert metrics.weighted_recall == pytest.approx(1.0)
    assert metrics.direct_recall == pytest.approx(1.0)
    assert metrics.adjacent_recall == pytest.approx(1.0)
    assert metrics.unrelated_exposure == pytest.approx(0.0)
    assert metrics.confuser_exposure == pytest.approx(1 / 3)


def test_bundle_properties_and_empty_threshold_result_are_safe() -> None:
    bundle = _bundle(
        [("memory-direct", 0.50), ("memory-unrelated", 0.40)],
        {"memory-direct": 2, "memory-unrelated": -1},
    )

    metrics = score_threshold_bundle(bundle, 0.99)

    assert bundle.candidate_count == 2
    assert bundle.label_counts()[2] == 1
    assert metrics.returned_count == 0
    assert metrics.weighted_precision == 0.0
    assert metrics.weighted_recall == 0.0
    assert metrics.weighted_f_score == 0.0


def test_score_threshold_bundle_rejects_unlabeled_search_results() -> None:
    bundle = _bundle(
        [("memory-direct", 0.90), ("memory-unlabeled", 0.80)],
        {"memory-direct": 2},
    )

    with pytest.raises(ThresholdOptimizationError, match="unlabeled memory"):
        score_threshold_bundle(bundle, 0.0)


def test_score_runtime_bundle_keeps_protected_minimum_before_threshold() -> None:
    bundle = _bundle(
        [
            ("memory-top", 0.20),
            ("memory-direct", 0.95),
            ("memory-adjacent", 0.85),
        ],
        {
            "memory-top": -2,
            "memory-direct": 2,
            "memory-adjacent": 1,
        },
    )

    threshold_only = score_threshold_bundle(bundle, 0.90)
    runtime = score_runtime_bundle(
        bundle,
        protected_minimum=1,
        match_threshold=0.90,
    )

    assert threshold_only.returned_count == 1
    assert threshold_only.confuser_retrieved == 0
    assert runtime.returned_count == 2
    assert runtime.confuser_retrieved == 1
    assert runtime.direct_retrieved == 1


def test_score_threshold_rows_and_tie_break_choose_lower_threshold() -> None:
    bundle = _bundle(
        [("memory-direct", 0.95), ("memory-adjacent", 0.94), ("memory-noise", 0.93)],
        {"memory-direct": 2, "memory-adjacent": 1, "memory-noise": -1},
    )

    rows = score_threshold_rows((bundle,), (0.0, 0.9), beta=1.0)
    progress_events: list[tuple[int, float]] = []
    rows_with_progress = score_threshold_rows(
        (bundle,),
        (0.0, 0.9),
        beta=1.0,
        progress_callback=lambda completed, threshold: progress_events.append(
            (completed, threshold)
        ),
    )
    recommended = select_recommended_row(rows)

    assert progress_events == [(1, 0.0), (2, 0.9)]
    assert rows_with_progress == rows
    assert len(rows) == 2
    assert rows[0].weighted_f_score == pytest.approx(rows[1].weighted_f_score)
    assert recommended.threshold == 0.0
    assert rows[0].recommended is False
    assert rows[1].recommended is False


def test_score_rows_reject_empty_inputs_and_runtime_row_handles_disabled() -> None:
    bundle = _bundle(
        [("memory-direct", 0.95)],
        {"memory-direct": 2},
    )

    with pytest.raises(ThresholdOptimizationError):
        score_threshold_rows((), (0.0,), beta=1.0)
    with pytest.raises(ThresholdOptimizationError):
        score_runtime_row((), protected_minimum=0, match_threshold=None, beta=1.0)
    with pytest.raises(ThresholdOptimizationError):
        select_recommended_row(())

    row = score_runtime_row(
        (bundle,), protected_minimum=0, match_threshold=None, beta=1.0
    )
    assert row.threshold == 0.0
    assert row.weighted_precision == pytest.approx(1.0)


def test_select_recommended_row_handles_improvements_and_tie_backtracking() -> None:
    worse = ThresholdSweepRow(
        threshold=0.7,
        weighted_precision=0.5,
        weighted_recall=0.5,
        weighted_f_score=0.5,
        direct_recall=0.5,
        adjacent_recall=0.5,
        unrelated_exposure=0.0,
        confuser_exposure=0.0,
        average_returned_count=1.0,
        total_returned_count=1,
        recommended=False,
    )
    best_high_threshold = ThresholdSweepRow(
        **{**worse.to_dict(), "threshold": 0.8, "weighted_f_score": 0.9}
    )
    best_low_threshold = ThresholdSweepRow(
        **{**worse.to_dict(), "threshold": 0.4, "weighted_f_score": 0.9}
    )

    assert (
        select_recommended_row(
            (worse, best_high_threshold, best_low_threshold)
        ).threshold
        == 0.4
    )


def test_build_threshold_search_bundles_supports_user_and_workspace_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        opt, "validate_thematic_context_label_cases", lambda cases: None
    )
    user_case = ThematicContextLabelCase(
        case_id="user-case",
        scope="user",
        group="travel",
        query_index=1,
        query="user query",
        workspace_uid=None,
        labels={"user-direct": 2},
    )
    workspace_case = ThematicContextLabelCase(
        case_id="workspace-case",
        scope="workspace",
        group="launch",
        query_index=1,
        query="workspace query",
        workspace_uid="workspace-1",
        labels={"workspace-direct": 2},
    )

    bundles = build_threshold_search_bundles(
        (user_case, workspace_case),
        search_user=lambda query, limit: [SearchResult(_memory("user-direct"), 0.9, 1)],
        search_workspace=lambda query, workspace_uid, limit: [
            SearchResult(_memory("workspace-direct"), 0.8, 1)
        ],
    )

    assert [bundle.case_id for bundle in bundles] == ["user-case", "workspace-case"]
    assert bundles[1].workspace_uid == "workspace-1"


def test_build_threshold_search_bundles_rejects_invalid_search_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        opt, "validate_thematic_context_label_cases", lambda cases: None
    )
    case = ThematicContextLabelCase(
        case_id="case",
        scope="user",
        group="travel",
        query_index=1,
        query="query",
        workspace_uid=None,
        labels={"expected": 2},
    )

    with pytest.raises(ThresholdOptimizationError, match="unlabeled memories"):
        build_threshold_search_bundles(
            (case,),
            search_user=lambda query, limit: [
                SearchResult(_memory("unexpected"), 0.9, 1)
            ],
            search_workspace=lambda query, workspace_uid, limit: [],
        )


@pytest.mark.parametrize(
    ("case", "message"),
    [
        (
            ThematicContextLabelCase(
                case_id="empty",
                scope="user",
                group="travel",
                query_index=1,
                query="query",
                workspace_uid=None,
                labels={},
            ),
            "does not have any labeled candidates",
        ),
        (
            ThematicContextLabelCase(
                case_id="workspace-missing-uid",
                scope="workspace",
                group="travel",
                query_index=1,
                query="query",
                workspace_uid=None,
                labels={"expected": 2},
            ),
            "missing workspace_uid",
        ),
        (
            ThematicContextLabelCase(
                case_id="bad-scope",
                scope="project",
                group="travel",
                query_index=1,
                query="query",
                workspace_uid=None,
                labels={"expected": 2},
            ),
            "unsupported case scope",
        ),
    ],
)
def test_build_threshold_search_bundles_rejects_invalid_case_shapes(
    monkeypatch: pytest.MonkeyPatch,
    case: ThematicContextLabelCase,
    message: str,
) -> None:
    monkeypatch.setattr(
        opt, "validate_thematic_context_label_cases", lambda cases: None
    )

    with pytest.raises(ThresholdOptimizationError, match=message):
        build_threshold_search_bundles(
            (case,),
            search_user=lambda query, limit: [],
            search_workspace=lambda query, workspace_uid, limit: [],
        )


def test_threshold_rows_to_csv_includes_recommended_column() -> None:
    row = ThresholdSweepRow(
        threshold=0.5,
        weighted_precision=0.75,
        weighted_recall=0.80,
        weighted_f_score=0.775,
        direct_recall=1.0,
        adjacent_recall=0.5,
        unrelated_exposure=0.25,
        confuser_exposure=0.0,
        average_returned_count=2.0,
        total_returned_count=4,
        recommended=True,
    )

    csv_text = threshold_rows_to_csv((row,))

    assert csv_text.startswith(
        "threshold,weighted_precision,weighted_recall,weighted_f_score,direct_recall"
    )
    assert "0.500000" in csv_text
    assert "true" in csv_text


def test_report_csv_png_and_summary_helpers_write_artifacts(tmp_path: Path) -> None:
    bundle = _bundle(
        [("memory-direct", 0.95), ("memory-adjacent", 0.75)],
        {"memory-direct": 2, "memory-adjacent": 1},
    )
    report = build_threshold_optimization_report(
        model="fake-model",
        provider="fake-provider",
        start=0.0,
        end=1.0,
        step=1.0,
        beta=1.0,
        output_format="png",
        output_path=str(tmp_path / "sweep.png"),
        wrote_config=False,
        bundles=(bundle,),
    )

    csv_path = write_threshold_csv(report.rows, tmp_path / "nested" / "sweep.csv")
    png_path = write_threshold_png(report, tmp_path / "sweep.png")
    stdout_path = write_threshold_csv(report.rows, None)
    disabled_summary = report_summary_lines(
        report,
        output_path=png_path,
        current_threshold=None,
        current_source="disabled",
    )
    enabled_summary = report_summary_lines(
        report,
        output_path=png_path,
        current_threshold=0.42,
        current_source="explicit",
    )

    assert csv_path is not None
    assert csv_path.read_text(encoding="utf-8").startswith("threshold,")
    assert stdout_path is None
    assert png_path.exists()
    assert png_path.stat().st_size > 0
    assert report.to_dict()["recommended_threshold"] == report.recommended_threshold
    assert any(row.recommended for row in report.rows)
    assert (
        "Objective: maximize weighted F1, balancing precision and recall"
        in disabled_summary
    )
    assert any(
        line.startswith("Recommended metrics: precision=") for line in disabled_summary
    )
    assert any(
        line.startswith("Exposure at recommendation: confusers=")
        for line in disabled_summary
    )
    assert "Current config: disabled (disabled)" in disabled_summary
    assert "Current config: 0.42 (explicit)" in enabled_summary


def test_write_threshold_png_rejects_empty_reports(tmp_path: Path) -> None:
    report = ThresholdOptimizationReport(
        model="fake-model",
        provider="fake-provider",
        start=0.0,
        end=1.0,
        step=1.0,
        beta=1.0,
        tested_thresholds=0,
        recommended_threshold=0.0,
        output_format="png",
        output_path=None,
        wrote_config=False,
        cases=0,
        rows=(),
    )

    with pytest.raises(ThresholdOptimizationError, match="empty threshold sweep"):
        write_threshold_png(report, tmp_path / "empty.png")
