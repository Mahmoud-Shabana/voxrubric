from __future__ import annotations

import math
from statistics import fmean

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


def percentile(values: list[int], p: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    rank = (len(xs) - 1) * p
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return float(xs[lo])
    return xs[lo] + (xs[hi] - xs[lo]) * (rank - lo)


class LatencyMetric(Metric):
    name = "response_latency"

    def __init__(self, p95_budget_ms: int = 2000) -> None:
        self.p95_budget_ms = p95_budget_ms

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        values = [
            t.response_latency_ms
            for t in trace.turns
            if t.speaker is Speaker.INTERVIEWER and t.response_latency_ms is not None
        ]
        if not values:
            return MetricResult(
                metric=self.name,
                summary="No interviewer response-latency samples were recorded.",
                details={"samples": 0, "p95_budget_ms": self.p95_budget_ms},
            )
        p50 = percentile(values, 0.50)
        p95 = percentile(values, 0.95)
        return MetricResult(
            metric=self.name,
            value=round(p95, 2),
            unit="ms_p95",
            passed=p95 <= self.p95_budget_ms,
            summary=f"Interviewer response latency p95 is {p95:.0f} ms.",
            details={
                "samples": len(values),
                "mean_ms": round(fmean(values), 2),
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "max_ms": max(values),
                "p95_budget_ms": self.p95_budget_ms,
            },
        )
