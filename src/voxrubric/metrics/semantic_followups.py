from __future__ import annotations

from statistics import fmean

from ..models import (
    InterviewTrace,
    MetricResult,
    Rubric,
    RubricDimension,
    Speaker,
)
from ..protocols import JudgeProvider
from .base import Metric


class SemanticFollowUpQualityMetric(Metric):
    """Use a semantic judge to evaluate whether follow-ups use candidate evidence.

    This metric is intentionally opt-in because it invokes a JudgeProvider.
    Structural follow-up integrity remains deterministic and belongs in the
    default evaluator.
    """

    name = "semantic_follow_up_quality"

    def __init__(
        self,
        judge: JudgeProvider,
        *,
        minimum_score: float = 6.0,
    ) -> None:
        if not 0 <= minimum_score <= 10:
            raise ValueError("minimum_score must be between 0 and 10")
        self.judge = judge
        self.minimum_score = minimum_score

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        by_id = {turn.id: turn for turn in trace.turns}
        followups = [
            turn
            for turn in trace.turns
            if turn.speaker is Speaker.INTERVIEWER
            and turn.parent_turn_id
        ]
        if not followups:
            return MetricResult(
                metric=self.name,
                summary="Trace contains no declared interviewer follow-ups.",
                details={
                    "applicable": False,
                    "judge_id": self.judge.judge_id,
                },
            )

        semantic_rubric = Rubric(
            id=f"{rubric.id}:follow-up-quality",
            title=f"{rubric.title} follow-up quality",
            dimensions=[
                RubricDimension(
                    id="follow_up_quality",
                    description=(
                        "How specifically and meaningfully the interviewer "
                        "follow-up responds to the immediately referenced "
                        "candidate answer. High scores require the follow-up "
                        "to investigate concrete content from that answer; "
                        "generic, repetitive, leading, or unrelated questions "
                        "should score low."
                    ),
                )
            ],
        )

        scores: list[float] = []
        problems: list[str] = []
        per_followup: list[dict[str, object]] = []

        for followup in followups:
            parent_id = followup.parent_turn_id or ""
            parent = by_id.get(parent_id)
            if parent is None or parent.speaker is not Speaker.CANDIDATE:
                problem = (
                    f"{followup.id}: parent {parent_id!r} is not a "
                    "candidate answer"
                )
                problems.append(problem)
                per_followup.append(
                    {
                        "turn_id": followup.id,
                        "parent_turn_id": parent_id,
                        "score": None,
                        "grounded": False,
                        "passed": False,
                        "problem": problem,
                    }
                )
                continue

            pair_trace = InterviewTrace(
                session_id=(
                    f"{trace.session_id}:semantic-follow-up:{followup.id}"
                ),
                role=trace.role,
                locale=trace.locale,
                turns=[
                    parent.model_copy(
                        update={"parent_turn_id": None}
                    ),
                    followup.model_copy(
                        update={"parent_turn_id": parent.id}
                    ),
                ],
                metadata={
                    "source_session_id": trace.session_id,
                    "source_followup_turn_id": followup.id,
                    "source_parent_turn_id": parent.id,
                },
            )

            try:
                scorecard = self.judge.score(
                    pair_trace,
                    semantic_rubric,
                )
            except Exception as exc:
                problem = (
                    f"{followup.id}: semantic judge failed: "
                    f"{type(exc).__name__}: {exc}"
                )
                problems.append(problem)
                per_followup.append(
                    {
                        "turn_id": followup.id,
                        "parent_turn_id": parent.id,
                        "score": None,
                        "grounded": False,
                        "passed": False,
                        "problem": problem,
                    }
                )
                continue

            dimension = next(
                (
                    item
                    for item in scorecard.dimensions
                    if item.dimension == "follow_up_quality"
                ),
                None,
            )
            if dimension is None:
                problem = (
                    f"{followup.id}: judge omitted follow_up_quality"
                )
                problems.append(problem)
                per_followup.append(
                    {
                        "turn_id": followup.id,
                        "parent_turn_id": parent.id,
                        "score": None,
                        "grounded": False,
                        "passed": False,
                        "problem": problem,
                    }
                )
                continue

            score = 10 * dimension.score / dimension.max_score
            grounded_evidence = [
                evidence
                for evidence in dimension.evidence
                if evidence.turn_id == parent.id
                and evidence.quote in parent.text
            ]
            grounded = bool(grounded_evidence)
            passed = (
                score >= self.minimum_score
                and grounded
            )
            if not grounded:
                problems.append(
                    f"{followup.id}: judge supplied no literal evidence "
                    f"from parent answer {parent.id}"
                )

            scores.append(score)
            per_followup.append(
                {
                    "turn_id": followup.id,
                    "parent_turn_id": parent.id,
                    "score": round(score, 4),
                    "grounded": grounded,
                    "passed": passed,
                    "judge_id": scorecard.judge_id,
                    "evidence_quotes": [
                        evidence.quote
                        for evidence in grounded_evidence
                    ],
                    "rationale": dimension.rationale,
                }
            )

        mean_score = fmean(scores) if scores else 0.0
        all_passed = (
            len(scores) == len(followups)
            and all(
                item.get("passed") is True
                for item in per_followup
            )
            and not problems
        )
        return MetricResult(
            metric=self.name,
            value=round(mean_score, 4),
            unit="mean_score_0_10",
            passed=all_passed,
            summary=(
                f"{sum(item.get('passed') is True for item in per_followup)}"
                f"/{len(followups)} follow-ups meet semantic quality and "
                "literal-evidence requirements."
            ),
            details={
                "applicable": True,
                "judge_id": self.judge.judge_id,
                "minimum_score": self.minimum_score,
                "followups": per_followup,
                "problems": problems,
            },
        )
