from __future__ import annotations

from typing import Protocol

from .models import InterviewScorecard, InterviewTrace, Rubric


class JudgeProvider(Protocol):
    """Provider-neutral contract for semantic judging.

    Implement this adapter for any hosted or local model. VoxRubric intentionally
    keeps provider SDKs out of the core package.
    """

    @property
    def judge_id(self) -> str: ...

    def score(self, trace: InterviewTrace, rubric: Rubric) -> InterviewScorecard: ...
