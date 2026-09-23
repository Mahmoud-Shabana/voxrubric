from __future__ import annotations

from itertools import combinations
from statistics import fmean

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


class JudgeAgreementMetric(Metric):
    name = "judge_agreement"

    def __init__(self, tolerance_points: float = 1.0) -> None:
        self.tolerance_points = tolerance_points

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        if len(trace.scorecards) < 2:
            return MetricResult(
                metric=self.name,
                summary="At least two scorecards are required for judge-agreement analysis.",
                details={"judges": len(trace.scorecards), "tolerance_points": self.tolerance_points},
            )

        by_judge = {
            s.judge_id: {d.dimension: 10 * d.score / d.max_score for d in s.dimensions}
            for s in trace.scorecards
        }
        diffs: list[float] = []
        comparisons = 0
        within = 0
        per_dimension: dict[str, list[float]] = {}
        judges = list(by_judge)

        for left, right in combinations(judges, 2):
            common = set(by_judge[left]) & set(by_judge[right])
            for dim in common:
                delta = abs(by_judge[left][dim] - by_judge[right][dim])
                diffs.append(delta)
                per_dimension.setdefault(dim, []).append(delta)
                comparisons += 1
                within += delta <= self.tolerance_points

        if not comparisons:
            return MetricResult(
                metric=self.name,
                summary="Scorecards share no comparable dimensions.",
                details={"judges": judges},
            )

        agreement = within / comparisons
        return MetricResult(
            metric=self.name,
            value=round(agreement, 4),
            unit="ratio_within_tolerance",
            passed=agreement >= 0.8,
            summary=f"{within}/{comparisons} normalized scores agree within ±{self.tolerance_points:g} points.",
            details={
                "judges": judges,
                "mean_absolute_delta": round(fmean(diffs), 4),
                "per_dimension_mean_delta": {
                    dim: round(fmean(ds), 4) for dim, ds in sorted(per_dimension.items())
                },
                "tolerance_points": self.tolerance_points,
            },
        )
