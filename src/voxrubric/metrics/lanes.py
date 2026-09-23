from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


class DualLaneBalanceMetric(Metric):
    """Check the standardized/adaptive question mix exported by dual-lane agents."""

    name = "dual_lane_balance"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        target = trace.metadata.get("anchor_ratio_target")
        if target is None:
            return MetricResult(
                metric=self.name,
                summary="Trace does not declare a dual-lane anchor target.",
                details={"applicable": False},
            )

        try:
            target = float(target)
        except (TypeError, ValueError):
            return MetricResult(
                metric=self.name,
                passed=False,
                summary="anchor_ratio_target is not numeric.",
                details={"anchor_ratio_target": target},
            )

        interviewers = [
            turn for turn in trace.turns
            if turn.speaker is Speaker.INTERVIEWER
            and turn.metadata.get("question_lane") in {"anchor", "adaptive"}
        ]
        if not interviewers:
            return MetricResult(
                metric=self.name,
                value=0.0,
                unit="anchor_turn_ratio",
                passed=False,
                summary="Dual-lane target is declared but no lane-tagged interviewer turns exist.",
                details={"anchor_ratio_target": target, "lane_turns": 0},
            )

        anchors = [
            turn for turn in interviewers
            if turn.metadata.get("question_lane") == "anchor"
        ]
        actual = len(anchors) / len(interviewers)

        # Discrete question counts cannot always represent the target exactly.
        # One-question tolerance prevents a 2/5 interview from failing a 50% target.
        tolerance = 1 / len(interviewers)
        passed = actual + tolerance >= target

        return MetricResult(
            metric=self.name,
            value=round(actual, 4),
            unit="anchor_turn_ratio",
            passed=passed,
            summary=(
                f"{len(anchors)}/{len(interviewers)} evaluative interviewer turns "
                f"are standardized anchors."
            ),
            details={
                "anchor_ratio_target": target,
                "anchor_turns": len(anchors),
                "adaptive_turns": len(interviewers) - len(anchors),
                "discrete_tolerance": round(tolerance, 4),
            },
        )
