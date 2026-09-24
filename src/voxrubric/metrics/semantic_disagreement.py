from __future__ import annotations

from itertools import combinations
from statistics import fmean

from ..models import DimensionScore, InterviewTrace, MetricResult, Rubric
from .base import Metric


def _normalized_score(item: DimensionScore) -> float:
    return 10 * item.score / item.max_score


def _evidence_keys(item: DimensionScore) -> set[tuple[str, str]]:
    return {
        (evidence.turn_id, evidence.quote)
        for evidence in item.evidence
    }


def _jaccard(
    left: set[tuple[str, str]],
    right: set[tuple[str, str]],
) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 1.0


class SemanticJudgeDisagreementMetric(Metric):
    """Analyze score and evidence disagreement across semantic judges.

    This remains descriptive: it surfaces where judges disagree and why,
    without selecting a preferred judge or collapsing the result into a
    universal quality ranking.
    """

    name = "semantic_judge_disagreement"

    def __init__(
        self,
        *,
        score_tolerance_points: float = 1.0,
        minimum_evidence_jaccard: float = 0.5,
        maximum_material_disagreement_rate: float = 0.2,
    ) -> None:
        if score_tolerance_points < 0:
            raise ValueError("score_tolerance_points must be >= 0")
        if not 0 <= minimum_evidence_jaccard <= 1:
            raise ValueError("minimum_evidence_jaccard must be between 0 and 1")
        if not 0 <= maximum_material_disagreement_rate <= 1:
            raise ValueError(
                "maximum_material_disagreement_rate must be between 0 and 1"
            )
        self.score_tolerance_points = score_tolerance_points
        self.minimum_evidence_jaccard = minimum_evidence_jaccard
        self.maximum_material_disagreement_rate = (
            maximum_material_disagreement_rate
        )

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        if len(trace.scorecards) < 2:
            return MetricResult(
                metric=self.name,
                summary=(
                    "At least two scorecards are required for semantic "
                    "judge-disagreement analysis."
                ),
                details={
                    "judges": len(trace.scorecards),
                    "score_tolerance_points": self.score_tolerance_points,
                    "minimum_evidence_jaccard": self.minimum_evidence_jaccard,
                },
            )

        dimensions = {item.id for item in rubric.dimensions}
        by_judge = {
            scorecard.judge_id: {
                item.dimension: item
                for item in scorecard.dimensions
                if item.dimension in dimensions
            }
            for scorecard in trace.scorecards
        }
        judges = list(by_judge)

        comparisons: list[dict[str, object]] = []
        material = 0
        score_deltas: list[float] = []
        evidence_similarities: list[float] = []

        for left_id, right_id in combinations(judges, 2):
            common = sorted(
                set(by_judge[left_id]) & set(by_judge[right_id])
            )
            for dimension in common:
                left = by_judge[left_id][dimension]
                right = by_judge[right_id][dimension]

                score_delta = abs(
                    _normalized_score(left)
                    - _normalized_score(right)
                )
                left_evidence = _evidence_keys(left)
                right_evidence = _evidence_keys(right)
                evidence_jaccard = _jaccard(
                    left_evidence,
                    right_evidence,
                )

                score_disagreement = (
                    score_delta > self.score_tolerance_points
                )
                evidence_disagreement = (
                    evidence_jaccard < self.minimum_evidence_jaccard
                )
                is_material = (
                    score_disagreement or evidence_disagreement
                )
                material += int(is_material)
                score_deltas.append(score_delta)
                evidence_similarities.append(evidence_jaccard)

                comparisons.append(
                    {
                        "left_judge": left_id,
                        "right_judge": right_id,
                        "dimension": dimension,
                        "score_delta": round(score_delta, 4),
                        "evidence_jaccard": round(
                            evidence_jaccard,
                            4,
                        ),
                        "score_disagreement": score_disagreement,
                        "evidence_disagreement": (
                            evidence_disagreement
                        ),
                        "material_disagreement": is_material,
                        "left_evidence_count": len(left_evidence),
                        "right_evidence_count": len(right_evidence),
                    }
                )

        if not comparisons:
            return MetricResult(
                metric=self.name,
                summary=(
                    "Scorecards share no rubric dimensions for semantic "
                    "disagreement analysis."
                ),
                details={"judges": judges},
            )

        rate = material / len(comparisons)
        return MetricResult(
            metric=self.name,
            value=round(rate, 4),
            unit="material_disagreement_ratio",
            passed=(
                rate <= self.maximum_material_disagreement_rate
            ),
            summary=(
                f"{material}/{len(comparisons)} judge/dimension pairs "
                "show material score or evidence disagreement."
            ),
            details={
                "judges": judges,
                "comparisons": comparisons,
                "mean_score_delta": round(
                    fmean(score_deltas),
                    4,
                ),
                "mean_evidence_jaccard": round(
                    fmean(evidence_similarities),
                    4,
                ),
                "score_tolerance_points": (
                    self.score_tolerance_points
                ),
                "minimum_evidence_jaccard": (
                    self.minimum_evidence_jaccard
                ),
                "maximum_material_disagreement_rate": (
                    self.maximum_material_disagreement_rate
                ),
            },
        )
