from __future__ import annotations

from collections.abc import Iterable

from .models import InterviewTrace, Rubric
from .protocols import JudgeProvider


class JudgeEnsemble:
    """Run multiple semantic judges while preserving each scorecard separately."""

    def __init__(self, judges: Iterable[JudgeProvider]) -> None:
        self.judges = list(judges)
        if not self.judges:
            raise ValueError("JudgeEnsemble requires at least one judge")

    def score(self, trace: InterviewTrace, rubric: Rubric) -> InterviewTrace:
        scorecards = [judge.score(trace, rubric) for judge in self.judges]
        return trace.model_copy(update={"scorecards": scorecards})
