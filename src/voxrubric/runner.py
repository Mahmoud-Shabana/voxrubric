from __future__ import annotations

from collections.abc import Iterable

from .metrics import (
    BargeInRecoveryMetric,
    CandidateControlRecoveryMetric,
    CodeSwitchMetric,
    DualLaneBalanceMetric,
    EvidenceGroundingMetric,
    EvidenceProvenanceMetric,
    FollowUpIntegrityMetric,
    GovernanceAuditMetric,
    JudgeAgreementMetric,
    LatencyMetric,
    RubricCoverageMetric,
    ToolArtifactIntegrityMetric,
    VoiceEventIntegrityMetric,
    VoiceLatencyBreakdownMetric,
)
from .metrics.base import Metric
from .models import EvaluationReport, InterviewTrace, Rubric


class Evaluator:
    def __init__(self, metrics: Iterable[Metric]) -> None:
        self.metrics = list(metrics)
        if not self.metrics:
            raise ValueError("Evaluator requires at least one metric")

    def run(self, trace: InterviewTrace, rubric: Rubric) -> EvaluationReport:
        return EvaluationReport(
            session_id=trace.session_id,
            role=trace.role,
            locale=trace.locale,
            metrics=[metric.evaluate(trace, rubric) for metric in self.metrics],
            metadata={"rubric_id": rubric.id},
        )


def default_evaluator(*, latency_budget_ms: int = 2000) -> Evaluator:
    return Evaluator(
        [
            EvidenceGroundingMetric(),
            RubricCoverageMetric(),
            FollowUpIntegrityMetric(),
            LatencyMetric(p95_budget_ms=latency_budget_ms),
            CodeSwitchMetric(),
            JudgeAgreementMetric(),
            DualLaneBalanceMetric(),
            EvidenceProvenanceMetric(),
            GovernanceAuditMetric(),
            CandidateControlRecoveryMetric(),
            ToolArtifactIntegrityMetric(),
            VoiceEventIntegrityMetric(),
            VoiceLatencyBreakdownMetric(),
            BargeInRecoveryMetric(),
        ]
    )
