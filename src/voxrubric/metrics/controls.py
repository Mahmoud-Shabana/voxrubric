from __future__ import annotations

from collections import Counter

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


class CandidateControlRecoveryMetric(Metric):
    name = "candidate_control_recovery"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        controls = trace.metadata.get("candidate_controls")
        if not isinstance(controls, list):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose candidate control events.",
                details={"applicable": False},
            )

        turn_controls = Counter(
            str(turn.metadata.get("candidate_control"))
            for turn in trace.turns
            if turn.metadata.get("candidate_control")
        )
        required_responses = Counter()
        revision_targets = {
            item.get("turn_id")
            for item in trace.metadata.get("transcript_revisions", [])
            if isinstance(item, dict)
        }

        checks = 0
        valid = 0
        problems: list[str] = []
        paused = False

        for index, control in enumerate(controls):
            if not isinstance(control, dict):
                checks += 1
                problems.append(f"control[{index}] is not an object")
                continue

            kind = str(control.get("kind", ""))
            target = control.get("target_turn_id")
            text = control.get("text")

            if kind in {"repeat", "clarify", "candidate_question"}:
                required_responses[kind] += 1

            if kind == "thinking_time":
                checks += 1
                if paused:
                    problems.append(f"control[{index}] requests thinking_time while already paused")
                else:
                    paused = True
                    valid += 1
            elif kind == "resume":
                checks += 1
                if not paused:
                    problems.append(f"control[{index}] resumes while not paused")
                else:
                    paused = False
                    valid += 1
            elif kind == "correct_last_answer" and isinstance(text, str) and text.strip():
                checks += 1
                if target in revision_targets:
                    valid += 1
                else:
                    problems.append(
                        f"control[{index}] supplied corrected text but no transcript revision exists"
                    )

        for kind, expected in required_responses.items():
            checks += expected
            actual = turn_controls.get(kind, 0)
            valid += min(expected, actual)
            if actual < expected:
                problems.append(
                    f"{kind}: expected {expected} interviewer responses, found {actual}"
                )

        if paused and trace.metadata.get("status") == "completed":
            checks += 1
            problems.append("completed trace ends with an unmatched thinking-time pause")

        if checks == 0:
            return MetricResult(
                metric=self.name,
                value=1.0,
                unit="valid_control_ratio",
                passed=True,
                summary="Candidate controls are present but require no recovery checks.",
                details={"controls": len(controls), "problems": []},
            )

        ratio = valid / checks
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_control_ratio",
            passed=not problems,
            summary=f"{valid}/{checks} candidate-control recovery checks hold.",
            details={
                "controls": len(controls),
                "problems": problems,
                "interviewer_control_responses": dict(turn_controls),
            },
        )
