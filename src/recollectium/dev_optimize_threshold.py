"""Threshold optimization helpers for seeded thematic dev eval labels."""

from __future__ import annotations

import csv
import io
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

from recollectium.dev_eval_thematic_labels import (
    THEMATIC_CONTEXT_LABEL_CASES,
    ThematicContextLabelCase,
    validate_thematic_context_label_cases,
)
from recollectium.models import SearchResult

ThresholdFormat = Literal["png", "csv"]

_LABEL_USEFUL_VALUE: Mapping[int, float] = {2: 1.0, 1: 0.5, -1: 0.0, -2: 0.0}
_LABEL_RETRIEVED_COST: Mapping[int, float] = {2: 1.0, 1: 1.0, -1: 1.0, -2: 1.5}
_LABEL_ORDER: tuple[int, int, int, int] = (2, 1, -1, -2)
_MAX_THRESHOLD_POINTS = 1001
_DEFAULT_CSV_COLUMNS: tuple[str, ...] = (
    "threshold",
    "weighted_precision",
    "weighted_recall",
    "weighted_f_score",
    "direct_recall",
    "adjacent_recall",
    "unrelated_exposure",
    "confuser_exposure",
    "average_returned_count",
    "total_returned_count",
    "recommended",
)


@dataclass(frozen=True, slots=True)
class ThresholdSearchBundle:
    """A seeded thematic query plus the full unfiltered ranked results."""

    case_id: str
    scope: str
    group: str
    query_index: int
    query: str
    workspace_uid: str | None
    labels: Mapping[str, int]
    results: tuple[SearchResult, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.labels)

    def label_counts(self) -> Counter[int]:
        return Counter(self.labels.values())


@dataclass(frozen=True, slots=True)
class ThresholdCaseMetrics:
    """Per-query threshold scoring details."""

    case_id: str
    scope: str
    group: str
    query_index: int
    threshold: float
    returned_count: int
    weighted_precision: float
    weighted_recall: float
    weighted_f_score: float
    direct_recall: float
    adjacent_recall: float
    unrelated_exposure: float
    confuser_exposure: float
    direct_retrieved: int
    adjacent_retrieved: int
    unrelated_retrieved: int
    confuser_retrieved: int
    useful_value_retrieved: float
    useful_value_total: float
    retrieved_cost_total: float


@dataclass(frozen=True, slots=True)
class ThresholdSweepRow:
    """Aggregated threshold sweep metrics across all seeded thematic queries."""

    threshold: float
    weighted_precision: float
    weighted_recall: float
    weighted_f_score: float
    direct_recall: float
    adjacent_recall: float
    unrelated_exposure: float
    confuser_exposure: float
    average_returned_count: float
    total_returned_count: int
    recommended: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["recommended"] = bool(self.recommended)
        return payload


@dataclass(frozen=True, slots=True)
class ThresholdOptimizationReport:
    """Threshold sweep report with recommendation metadata."""

    model: str
    provider: str
    start: float
    end: float
    step: float
    beta: float
    tested_thresholds: int
    recommended_threshold: float
    output_format: ThresholdFormat
    output_path: str | None
    wrote_config: bool
    cases: int
    rows: tuple[ThresholdSweepRow, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["rows"] = [row.to_dict() for row in self.rows]
        return payload


class ThresholdOptimizationError(ValueError):
    """Raised when the optimizer inputs or fixture data are invalid."""


SearchUser = Callable[[str, int], list[SearchResult]]
SearchWorkspace = Callable[[str, str, int], list[SearchResult]]


def threshold_cases_from_fixture() -> tuple[ThematicContextLabelCase, ...]:
    """Return the validated PR1 thematic label cases."""

    validate_thematic_context_label_cases()
    return THEMATIC_CONTEXT_LABEL_CASES


def validate_threshold_sweep_parameters(
    *, start: float, end: float, step: float, beta: float
) -> None:
    """Validate the threshold sweep controls."""

    if start < 0.0:
        raise ThresholdOptimizationError("start must be >= 0.0")
    if end > 1.0:
        raise ThresholdOptimizationError("end must be <= 1.0")
    if start > end:
        raise ThresholdOptimizationError("start must be <= end")
    if step <= 0.0:
        raise ThresholdOptimizationError("step must be > 0.0")
    if beta <= 0.0:
        raise ThresholdOptimizationError("beta must be > 0.0")


def generate_threshold_values(
    start: float, end: float, step: float
) -> tuple[float, ...]:
    """Generate inclusive threshold values using Decimal arithmetic."""

    validate_threshold_sweep_parameters(start=start, end=end, step=step, beta=1.0)
    start_decimal = Decimal(str(start))
    end_decimal = Decimal(str(end))
    step_decimal = Decimal(str(step))
    thresholds: list[float] = []
    current = start_decimal
    tolerance = Decimal("1e-12")
    while current <= end_decimal + tolerance:
        thresholds.append(float(current))
        current += step_decimal
        if len(thresholds) > _MAX_THRESHOLD_POINTS:
            raise ThresholdOptimizationError(
                "threshold sweep would test too many values; narrow the range or increase the step"
            )
    if thresholds and thresholds[-1] > end + 1e-12:
        thresholds[-1] = float(end_decimal)
    elif not thresholds or abs(thresholds[-1] - end) > 1e-12:
        thresholds.append(float(end_decimal))
    if len(thresholds) > _MAX_THRESHOLD_POINTS:
        raise ThresholdOptimizationError(
            "threshold sweep would test too many values; narrow the range or increase the step"
        )
    return tuple(thresholds)


def _weighted_f_score(precision: float, recall: float, beta: float) -> float:
    if precision <= 0.0 or recall <= 0.0:
        return 0.0
    beta_squared = beta * beta
    denominator = beta_squared * precision + recall
    return (1.0 + beta_squared) * precision * recall / denominator


def _direct_count(label_counts: Mapping[int, int]) -> int:
    return int(label_counts.get(2, 0))


def _adjacent_count(label_counts: Mapping[int, int]) -> int:
    return int(label_counts.get(1, 0))


def _unrelated_count(label_counts: Mapping[int, int]) -> int:
    return int(label_counts.get(-1, 0))


def _confuser_count(label_counts: Mapping[int, int]) -> int:
    return int(label_counts.get(-2, 0))


def _score_bundle(
    bundle: ThresholdSearchBundle,
    *,
    threshold: float | None,
    protected_minimum: int = 0,
    match_threshold: float | None = None,
) -> ThresholdCaseMetrics:
    labels = bundle.labels
    label_counts = Counter(labels.values())
    useful_total = sum(
        _LABEL_USEFUL_VALUE[label] * count for label, count in label_counts.items()
    )
    direct_total = _direct_count(label_counts)
    adjacent_total = _adjacent_count(label_counts)

    if threshold is None and match_threshold is None:
        retrieved = list(bundle.results)
    elif match_threshold is None:
        assert threshold is not None
        retrieved = [result for result in bundle.results if result.score >= threshold]
    else:
        retrieved = []
        protected_count = min(protected_minimum, len(bundle.results))
        for index, result in enumerate(bundle.results):
            if index < protected_count or result.score >= match_threshold:
                retrieved.append(result)

    retrieved_label_counts: Counter[int] = Counter()
    useful_retrieved = 0.0
    retrieved_cost_total = 0.0
    for result in retrieved:
        label = labels.get(result.memory.id)
        if label is None:
            raise ThresholdOptimizationError(
                f"search returned unlabeled memory {result.memory.id!r} for {bundle.case_id!r}"
            )
        retrieved_label_counts[label] += 1
        useful_retrieved += _LABEL_USEFUL_VALUE[label]
        retrieved_cost_total += _LABEL_RETRIEVED_COST[label]

    direct_retrieved = _direct_count(retrieved_label_counts)
    adjacent_retrieved = _adjacent_count(retrieved_label_counts)
    unrelated_retrieved = _unrelated_count(retrieved_label_counts)
    confuser_retrieved = _confuser_count(retrieved_label_counts)

    weighted_precision = (
        useful_retrieved / retrieved_cost_total if retrieved_cost_total > 0.0 else 0.0
    )
    weighted_recall = useful_retrieved / useful_total if useful_total > 0.0 else 0.0
    direct_recall = direct_retrieved / direct_total if direct_total > 0 else 0.0
    adjacent_recall = adjacent_retrieved / adjacent_total if adjacent_total > 0 else 0.0
    returned_count = len(retrieved)
    unrelated_exposure = (
        unrelated_retrieved / returned_count if returned_count > 0 else 0.0
    )
    confuser_exposure = (
        confuser_retrieved / returned_count if returned_count > 0 else 0.0
    )
    actual_threshold = 0.0 if threshold is None else threshold
    return ThresholdCaseMetrics(
        case_id=bundle.case_id,
        scope=bundle.scope,
        group=bundle.group,
        query_index=bundle.query_index,
        threshold=actual_threshold,
        returned_count=returned_count,
        weighted_precision=weighted_precision,
        weighted_recall=weighted_recall,
        weighted_f_score=_weighted_f_score(weighted_precision, weighted_recall, 1.0),
        direct_recall=direct_recall,
        adjacent_recall=adjacent_recall,
        unrelated_exposure=unrelated_exposure,
        confuser_exposure=confuser_exposure,
        direct_retrieved=direct_retrieved,
        adjacent_retrieved=adjacent_retrieved,
        unrelated_retrieved=unrelated_retrieved,
        confuser_retrieved=confuser_retrieved,
        useful_value_retrieved=useful_retrieved,
        useful_value_total=useful_total,
        retrieved_cost_total=retrieved_cost_total,
    )


def _aggregate_case_metrics(
    metrics: Sequence[ThresholdCaseMetrics], *, threshold: float, beta: float
) -> ThresholdSweepRow:
    if not metrics:
        raise ThresholdOptimizationError(
            "threshold optimization requires at least one case"
        )
    case_count = len(metrics)
    weighted_precision = (
        sum(metric.weighted_precision for metric in metrics) / case_count
    )
    weighted_recall = sum(metric.weighted_recall for metric in metrics) / case_count
    direct_recall = sum(metric.direct_recall for metric in metrics) / case_count
    adjacent_recall = sum(metric.adjacent_recall for metric in metrics) / case_count
    unrelated_exposure = (
        sum(metric.unrelated_exposure for metric in metrics) / case_count
    )
    confuser_exposure = sum(metric.confuser_exposure for metric in metrics) / case_count
    total_returned_count = sum(metric.returned_count for metric in metrics)
    average_returned_count = total_returned_count / case_count
    return ThresholdSweepRow(
        threshold=threshold,
        weighted_precision=weighted_precision,
        weighted_recall=weighted_recall,
        weighted_f_score=_weighted_f_score(weighted_precision, weighted_recall, beta),
        direct_recall=direct_recall,
        adjacent_recall=adjacent_recall,
        unrelated_exposure=unrelated_exposure,
        confuser_exposure=confuser_exposure,
        average_returned_count=average_returned_count,
        total_returned_count=total_returned_count,
        recommended=False,
    )


def build_threshold_search_bundles(
    cases: Sequence[ThematicContextLabelCase],
    *,
    search_user: SearchUser,
    search_workspace: SearchWorkspace,
) -> tuple[ThresholdSearchBundle, ...]:
    """Load the full candidate pools for every thematic optimization case."""

    validate_thematic_context_label_cases(cases)
    bundles: list[ThresholdSearchBundle] = []
    for case in cases:
        candidate_limit = len(case.labels)
        if candidate_limit <= 0:
            raise ThresholdOptimizationError(
                f"case {case.case_id!r} does not have any labeled candidates"
            )
        if case.scope == "user":
            results = tuple(search_user(case.query, candidate_limit))
        elif case.scope == "workspace":
            if case.workspace_uid is None:
                raise ThresholdOptimizationError(
                    f"workspace case {case.case_id!r} is missing workspace_uid"
                )
            results = tuple(
                search_workspace(case.query, case.workspace_uid, candidate_limit)
            )
        else:
            raise ThresholdOptimizationError(f"unsupported case scope: {case.scope!r}")
        unexpected = [
            result.memory.id
            for result in results
            if result.memory.id not in case.labels
        ]
        if unexpected:
            preview = ", ".join(unexpected[:5])
            raise ThresholdOptimizationError(
                f"search returned unlabeled memories for {case.case_id!r}: {preview}"
            )
        bundles.append(
            ThresholdSearchBundle(
                case_id=case.case_id,
                scope=case.scope,
                group=case.group,
                query_index=case.query_index,
                query=case.query,
                workspace_uid=case.workspace_uid,
                labels=case.labels,
                results=results,
            )
        )
    return tuple(bundles)


def score_threshold_bundle(
    bundle: ThresholdSearchBundle, threshold: float
) -> ThresholdCaseMetrics:
    """Score one bundle at a single threshold."""

    return _score_bundle(bundle, threshold=threshold)


def score_runtime_bundle(
    bundle: ThresholdSearchBundle,
    *,
    protected_minimum: int,
    match_threshold: float | None,
) -> ThresholdCaseMetrics:
    """Score one bundle using the runtime protected-minimum policy."""

    return _score_bundle(
        bundle,
        threshold=None,
        protected_minimum=protected_minimum,
        match_threshold=match_threshold,
    )


def score_threshold_rows(
    bundles: Sequence[ThresholdSearchBundle],
    thresholds: Sequence[float],
    *,
    beta: float,
) -> tuple[ThresholdSweepRow, ...]:
    """Aggregate sweep rows for the provided threshold values."""

    if not bundles:
        raise ThresholdOptimizationError(
            "threshold optimization requires at least one bundle"
        )
    rows: list[ThresholdSweepRow] = []
    for threshold in thresholds:
        metrics = [score_threshold_bundle(bundle, threshold) for bundle in bundles]
        rows.append(_aggregate_case_metrics(metrics, threshold=threshold, beta=beta))
    return tuple(rows)


def score_runtime_row(
    bundles: Sequence[ThresholdSearchBundle],
    *,
    protected_minimum: int,
    match_threshold: float | None,
    beta: float,
) -> ThresholdSweepRow:
    """Aggregate one runtime baseline row from the fixed full candidate pools."""

    metrics = [
        score_runtime_bundle(
            bundle,
            protected_minimum=protected_minimum,
            match_threshold=match_threshold,
        )
        for bundle in bundles
    ]
    actual_threshold = 0.0 if match_threshold is None else match_threshold
    return _aggregate_case_metrics(metrics, threshold=actual_threshold, beta=beta)


def select_recommended_row(rows: Sequence[ThresholdSweepRow]) -> ThresholdSweepRow:
    """Pick the highest-scoring row, preferring lower thresholds on ties."""

    if not rows:
        raise ThresholdOptimizationError("threshold optimization produced no rows")
    best_row = rows[0]
    best_score = best_row.weighted_f_score
    for row in rows[1:]:
        score = row.weighted_f_score
        if score > best_score and not math.isclose(
            score, best_score, rel_tol=1e-9, abs_tol=1e-9
        ):
            best_row = row
            best_score = score
            continue
        if (
            math.isclose(score, best_score, rel_tol=1e-9, abs_tol=1e-9)
            and row.threshold < best_row.threshold
        ):
            best_row = row
            best_score = score
    return best_row


def build_threshold_optimization_report(
    *,
    model: str,
    provider: str,
    start: float,
    end: float,
    step: float,
    beta: float,
    output_format: ThresholdFormat,
    output_path: str | None,
    wrote_config: bool,
    bundles: Sequence[ThresholdSearchBundle],
) -> ThresholdOptimizationReport:
    """Build the sweep report for the provided bundles and sweep parameters."""

    validate_threshold_sweep_parameters(start=start, end=end, step=step, beta=beta)
    thresholds = generate_threshold_values(start, end, step)
    rows = score_threshold_rows(bundles, thresholds, beta=beta)
    recommended_row = select_recommended_row(rows)
    annotated_rows = tuple(
        ThresholdSweepRow(
            **{
                **row.to_dict(),
                "recommended": row.threshold == recommended_row.threshold,
            }
        )
        for row in rows
    )
    return ThresholdOptimizationReport(
        model=model,
        provider=provider,
        start=start,
        end=end,
        step=step,
        beta=beta,
        tested_thresholds=len(thresholds),
        recommended_threshold=recommended_row.threshold,
        output_format=output_format,
        output_path=output_path,
        wrote_config=wrote_config,
        cases=len(bundles),
        rows=annotated_rows,
    )


def threshold_rows_to_csv(rows: Sequence[ThresholdSweepRow]) -> str:
    """Serialize sweep rows to CSV text."""

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(_DEFAULT_CSV_COLUMNS))
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "threshold": f"{row.threshold:.6f}",
                "weighted_precision": f"{row.weighted_precision:.6f}",
                "weighted_recall": f"{row.weighted_recall:.6f}",
                "weighted_f_score": f"{row.weighted_f_score:.6f}",
                "direct_recall": f"{row.direct_recall:.6f}",
                "adjacent_recall": f"{row.adjacent_recall:.6f}",
                "unrelated_exposure": f"{row.unrelated_exposure:.6f}",
                "confuser_exposure": f"{row.confuser_exposure:.6f}",
                "average_returned_count": f"{row.average_returned_count:.6f}",
                "total_returned_count": row.total_returned_count,
                "recommended": str(bool(row.recommended)).lower(),
            }
        )
    return stream.getvalue()


def write_threshold_csv(
    rows: Sequence[ThresholdSweepRow],
    output_path: Path | None,
) -> Path | None:
    """Write sweep rows to a CSV file if an output path is supplied."""

    csv_text = threshold_rows_to_csv(rows)
    if output_path is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(csv_text, encoding="utf-8")
    return output_path


def write_threshold_png(
    report: ThresholdOptimizationReport,
    output_path: Path,
) -> Path:
    """Render the sweep report as a PNG plot using a headless matplotlib backend."""

    try:
        import matplotlib  # type: ignore[reportMissingImports]

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - dependency managed in pyproject
        raise ThresholdOptimizationError(
            "PNG plotting requires matplotlib; use --format csv if plotting support is unavailable"
        ) from exc

    if not report.rows:
        raise ThresholdOptimizationError("cannot render an empty threshold sweep")

    thresholds = [row.threshold for row in report.rows]
    weighted_precision = [row.weighted_precision for row in report.rows]
    weighted_recall = [row.weighted_recall for row in report.rows]
    weighted_f_score = [row.weighted_f_score for row in report.rows]
    confuser_exposure = [row.confuser_exposure for row in report.rows]
    average_returned_count = [row.average_returned_count for row in report.rows]
    max_returned_count = max(average_returned_count) if average_returned_count else 1.0
    normalized_returned_count = [
        count / max_returned_count if max_returned_count > 0.0 else 0.0
        for count in average_returned_count
    ]

    fig, (ax_main, ax_diagnostics) = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
    fig.suptitle(f"Recollectium threshold optimization: {report.model}")

    ax_main.plot(
        thresholds, weighted_precision, label="weighted precision", linewidth=2
    )
    ax_main.plot(thresholds, weighted_recall, label="weighted recall", linewidth=2)
    ax_main.plot(
        thresholds, weighted_f_score, label=f"weighted F{report.beta:g}", linewidth=2
    )
    ax_main.axvline(
        report.recommended_threshold,
        color="black",
        linestyle="--",
        linewidth=1.5,
        label=f"recommended {report.recommended_threshold:.2f}",
    )
    ax_main.set_ylabel("score")
    ax_main.set_ylim(0.0, 1.05)
    ax_main.grid(True, alpha=0.3)
    ax_main.legend(loc="best")

    ax_diagnostics.plot(
        thresholds,
        confuser_exposure,
        label="confuser exposure",
        color="tab:red",
        linewidth=2,
    )
    ax_diagnostics.set_xlabel("threshold")
    ax_diagnostics.set_ylabel("confuser exposure")
    ax_diagnostics.set_ylim(0.0, 1.05)
    ax_diagnostics.grid(True, alpha=0.3)
    ax_returned = ax_diagnostics.twinx()
    ax_returned.plot(
        thresholds,
        normalized_returned_count,
        label="average returned count (normalized)",
        color="tab:green",
        linewidth=2,
        linestyle=":",
    )
    ax_returned.set_ylabel("normalized returned count")
    ax_returned.set_ylim(0.0, 1.05)

    lines, labels = ax_diagnostics.get_legend_handles_labels()
    returned_lines, returned_labels = ax_returned.get_legend_handles_labels()
    ax_diagnostics.legend(lines + returned_lines, labels + returned_labels, loc="best")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path


def report_summary_lines(
    report: ThresholdOptimizationReport,
    *,
    output_path: Path,
    current_threshold: float | None,
    current_source: str,
) -> list[str]:
    """Return human-readable summary lines for stderr or terminal output."""

    lines = [
        "Recollectium dev optimize-threshold",
        f"Model: {report.model}",
        f"Thresholds: {report.start:.2f} to {report.end:.2f} by {report.step:.2f}",
        f"Output: {output_path}",
        f"Recommendation: {report.recommended_threshold:.2f}",
    ]
    if current_threshold is None:
        current_line = f"Current config: disabled ({current_source})"
    else:
        current_line = f"Current config: {current_threshold:.2f} ({current_source})"
    lines.append(current_line)
    lines.append(
        f"Apply: recollectium config set retrieval.match_threshold {report.recommended_threshold:.2f}"
    )
    return lines
