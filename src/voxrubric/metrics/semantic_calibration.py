from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


_ALLOWED_STATES = {
    "claimed",
    "demonstrated",
    "contradicted",
    "insufficient_evidence",
}


class SemanticEvidenceCalibrationMetric(Metric):
    """Compare active semantic-judge evidence against benchmark gold labels.

    Gold labels live in trace.metadata["semantic_calibration_targets"] and are
    intended for benchmark fixtures only. Ordinary production traces therefore
    report this metric as not applicable.
    """

    name = "semantic_evidence_calibration"

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        targets = trace.metadata.get(
            "semantic_calibration_targets"
        )
        if not isinstance(targets, list):
            return MetricResult(
                metric=self.name,
                summary=(
                    "Trace does not expose semantic calibration targets."
                ),
                details={"applicable": False},
            )

        graph = trace.metadata.get("evidence_graph")
        if not isinstance(graph, dict):
            return MetricResult(
                metric=self.name,
                value=0.0,
                unit="exact_state_accuracy",
                passed=False,
                summary=(
                    "Calibration targets are present but evidence graph is missing."
                ),
                details={
                    "targets": len(targets),
                    "correct": 0,
                    "problems": ["evidence_graph is missing"],
                },
            )

        correct = 0
        evaluated = 0
        problems: list[str] = []
        confidence_checks = 0
        confidence_valid = 0
        per_target: list[dict] = []

        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                problems.append(
                    f"target[{index}] is not an object"
                )
                continue

            competency_id = target.get("competency_id")
            turn_id = target.get("turn_id")
            expected_state = target.get("expected_state")
            min_confidence = target.get("min_confidence")
            max_confidence = target.get("max_confidence")

            target_problems: list[str] = []
            if (
                not isinstance(competency_id, str)
                or not competency_id
            ):
                target_problems.append(
                    "missing competency_id"
                )
            if not isinstance(turn_id, str) or not turn_id:
                target_problems.append("missing turn_id")
            if expected_state not in _ALLOWED_STATES:
                target_problems.append(
                    "invalid expected_state"
                )
            for label, value in (
                ("min_confidence", min_confidence),
                ("max_confidence", max_confidence),
            ):
                if (
                    value is not None
                    and (
                        not isinstance(value, (int, float))
                        or not 0 <= float(value) <= 1
                    )
                ):
                    target_problems.append(
                        f"{label} must be in [0, 1]"
                    )
            if (
                isinstance(min_confidence, (int, float))
                and isinstance(max_confidence, (int, float))
                and min_confidence > max_confidence
            ):
                target_problems.append(
                    "min_confidence exceeds max_confidence"
                )

            if target_problems:
                problems.append(
                    f"target[{index}]: "
                    + ", ".join(target_problems)
                )
                continue

            node = graph.get(competency_id)
            evidence = (
                node.get("evidence", [])
                if isinstance(node, dict)
                else []
            )
            active_semantic = [
                item
                for item in evidence
                if isinstance(item, dict)
                and item.get("active", True) is True
                and isinstance(item.get("source"), str)
                and item["source"].startswith(
                    "semantic_judge:"
                )
                and item.get("turn_id") == turn_id
            ]

            evaluated += 1
            observed_state = None
            observed_confidence = None

            if len(active_semantic) == 0:
                target_problems.append(
                    "no active semantic evidence"
                )
            elif len(active_semantic) > 1:
                target_problems.append(
                    "multiple active semantic evidence items"
                )
            else:
                item = active_semantic[0]
                observed_state = item.get("state")
                observed_confidence = item.get(
                    "confidence"
                )
                if observed_state != expected_state:
                    target_problems.append(
                        f"expected state {expected_state}, "
                        f"got {observed_state}"
                    )
                else:
                    correct += 1

                if (
                    min_confidence is not None
                    or max_confidence is not None
                ):
                    confidence_checks += 1
                    if not isinstance(
                        observed_confidence,
                        (int, float),
                    ):
                        target_problems.append(
                            "confidence is missing"
                        )
                    elif (
                        min_confidence is not None
                        and observed_confidence
                        < min_confidence
                    ):
                        target_problems.append(
                            f"confidence {observed_confidence} "
                            f"is below {min_confidence}"
                        )
                    elif (
                        max_confidence is not None
                        and observed_confidence
                        > max_confidence
                    ):
                        target_problems.append(
                            f"confidence {observed_confidence} "
                            f"is above {max_confidence}"
                        )
                    else:
                        confidence_valid += 1

            if target_problems:
                problems.append(
                    f"{competency_id}:{turn_id}: "
                    + ", ".join(target_problems)
                )

            per_target.append(
                {
                    "competency_id": competency_id,
                    "turn_id": turn_id,
                    "expected_state": expected_state,
                    "observed_state": observed_state,
                    "confidence": observed_confidence,
                    "problems": target_problems,
                }
            )

        accuracy = (
            correct / evaluated
            if evaluated
            else 0.0
        )
        return MetricResult(
            metric=self.name,
            value=round(accuracy, 4),
            unit="exact_state_accuracy",
            passed=(
                bool(evaluated)
                and not problems
                and correct == evaluated
            ),
            summary=(
                f"{correct}/{evaluated} semantic evidence states "
                "match benchmark gold labels."
            ),
            details={
                "targets": len(targets),
                "evaluated": evaluated,
                "correct": correct,
                "confidence_checks": confidence_checks,
                "confidence_valid": confidence_valid,
                "problems": problems,
                "per_target": per_target,
            },
        )
