from __future__ import annotations

import re
import unicodedata

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


class EvidenceGroundingMetric(Metric):
    name = "evidence_grounding"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        if not trace.scorecards:
            return MetricResult(
                metric=self.name,
                summary="No scorecards were supplied; evidence grounding is not applicable.",
                details={"scorecards": 0},
            )

        turns = {t.id: t for t in trace.turns}
        total = 0
        grounded = 0
        orphan_turn_refs: list[str] = []
        quote_mismatches: list[dict[str, str]] = []
        empty_dimensions: list[str] = []

        for scorecard in trace.scorecards:
            for dim in scorecard.dimensions:
                if not dim.evidence:
                    empty_dimensions.append(f"{scorecard.judge_id}:{dim.dimension}")
                for ref in dim.evidence:
                    total += 1
                    turn = turns.get(ref.turn_id)
                    if turn is None:
                        orphan_turn_refs.append(ref.turn_id)
                        continue
                    quote = _normalize(ref.quote)
                    source = _normalize(turn.text)
                    if quote and quote in source:
                        grounded += 1
                    else:
                        quote_mismatches.append(
                            {"turn_id": ref.turn_id, "quote": ref.quote, "judge_id": scorecard.judge_id}
                        )

        value = 1.0 if total == 0 and not trace.scorecards else (grounded / total if total else 0.0)
        passed = value >= 0.95 and not orphan_turn_refs and not quote_mismatches
        return MetricResult(
            metric=self.name,
            value=round(value, 4),
            unit="ratio",
            passed=passed,
            summary=f"{grounded}/{total} evidence references are transcript-grounded.",
            details={
                "grounded": grounded,
                "total": total,
                "orphan_turn_refs": orphan_turn_refs,
                "quote_mismatches": quote_mismatches,
                "dimensions_without_evidence": empty_dimensions,
            },
        )
