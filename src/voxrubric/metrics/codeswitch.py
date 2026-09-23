from __future__ import annotations

import re

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric

_ARABIC = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")


class CodeSwitchMetric(Metric):
    name = "code_switching"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        candidate_turns = [t for t in trace.turns if t.speaker is Speaker.CANDIDATE and t.text.strip()]
        mixed = [t.id for t in candidate_turns if _ARABIC.search(t.text) and _LATIN.search(t.text)]
        arabic = [t.id for t in candidate_turns if _ARABIC.search(t.text)]
        latin = [t.id for t in candidate_turns if _LATIN.search(t.text)]
        ratio = len(mixed) / len(candidate_turns) if candidate_turns else 0.0
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="candidate_turn_ratio",
            summary=f"{len(mixed)} candidate turns contain Arabic/Latin code-switching.",
            details={
                "candidate_turns": len(candidate_turns),
                "mixed_turn_ids": mixed,
                "arabic_turn_ids": arabic,
                "latin_turn_ids": latin,
            },
        )
