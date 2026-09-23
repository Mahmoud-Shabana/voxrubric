from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


class RubricCoverageMetric(Metric):
    name = "rubric_coverage"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        touched: set[str] = set()
        asked_by_dimension: dict[str, list[str]] = {d.id: [] for d in rubric.dimensions}
        known = set(asked_by_dimension)
        unknown_tags: set[str] = set()

        for turn in trace.turns:
            if turn.speaker is not Speaker.INTERVIEWER:
                continue
            for tag in turn.rubric_tags:
                if tag in known:
                    touched.add(tag)
                    asked_by_dimension[tag].append(turn.id)
                else:
                    unknown_tags.add(tag)

        required = {d.id for d in rubric.dimensions if d.required}
        missing_required = sorted(required - touched)
        weighted_total = sum(d.weight for d in rubric.dimensions)
        weighted_touched = sum(d.weight for d in rubric.dimensions if d.id in touched)
        value = weighted_touched / weighted_total if weighted_total else 1.0

        return MetricResult(
            metric=self.name,
            value=round(value, 4),
            unit="ratio",
            passed=not missing_required,
            summary=f"Covered {len(touched)}/{len(rubric.dimensions)} rubric dimensions.",
            details={
                "covered": sorted(touched),
                "missing_required": missing_required,
                "question_turns": asked_by_dimension,
                "unknown_tags": sorted(unknown_tags),
            },
        )
