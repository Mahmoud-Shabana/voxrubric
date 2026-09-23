from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


class FollowUpIntegrityMetric(Metric):
    """Checks whether declared follow-ups are traceable to candidate answers.

    Semantic quality is intentionally left to a JudgeProvider. This deterministic
    metric catches broken orchestration and bogus parent links first.
    """

    name = "follow_up_integrity"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        by_id = {t.id: t for t in trace.turns}
        interviewers = [t for t in trace.turns if t.speaker is Speaker.INTERVIEWER]
        followups = [t for t in interviewers if t.parent_turn_id]
        valid: list[str] = []
        invalid: list[dict[str, str]] = []
        for turn in followups:
            parent = by_id.get(turn.parent_turn_id or "")
            if parent and parent.speaker is Speaker.CANDIDATE:
                valid.append(turn.id)
            else:
                invalid.append({"turn_id": turn.id, "parent_turn_id": turn.parent_turn_id or ""})
        ratio = len(valid) / len(followups) if followups else 1.0
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="ratio",
            passed=not invalid,
            summary=f"{len(valid)}/{len(followups)} declared follow-ups point to candidate answers.",
            details={"valid_followups": valid, "invalid_followups": invalid},
        )
