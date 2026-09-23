from __future__ import annotations

from statistics import fmean

from pydantic import Field

from .models import (
    InterviewTrace,
    MetricResult,
    Rubric,
    Speaker,
    StrictModel,
    Turn,
)
from .runner import Evaluator, default_evaluator


class MetricDelta(StrictModel):
    metric: str
    left_value: float | None = None
    right_value: float | None = None
    delta: float | None = None
    left_passed: bool | None = None
    right_passed: bool | None = None


class CompetencyEvidenceDelta(StrictModel):
    competency_id: str
    left_state: str | None = None
    right_state: str | None = None
    left_confidence: float | None = None
    right_confidence: float | None = None
    changed: bool


class QuestionPathStep(StrictModel):
    index: int = Field(ge=0)
    left_turn_id: str | None = None
    right_turn_id: str | None = None
    left_tags: list[str] = Field(default_factory=list)
    right_tags: list[str] = Field(default_factory=list)
    tag_similarity: float = Field(ge=0.0, le=1.0)
    left_followup: bool = False
    right_followup: bool = False
    followup_agreement: bool


class TraceDiffReport(StrictModel):
    left_session_id: str
    right_session_id: str
    question_path_similarity: float = Field(ge=0.0, le=1.0)
    followup_action_agreement: float = Field(ge=0.0, le=1.0)
    interviewer_turn_delta: int
    candidate_turn_delta: int
    path_steps: list[QuestionPathStep] = Field(default_factory=list)
    metric_deltas: list[MetricDelta] = Field(default_factory=list)
    evidence_deltas: list[CompetencyEvidenceDelta] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


def _evaluative_questions(trace: InterviewTrace) -> list[Turn]:
    return [
        turn
        for turn in trace.turns
        if turn.speaker is Speaker.INTERVIEWER
        and turn.metadata.get("question_lane") != "closing"
        and not turn.metadata.get("non_evaluative")
        and not turn.metadata.get("candidate_control")
    ]


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _metric_map(report) -> dict[str, MetricResult]:
    return {
        metric.metric: metric
        for metric in report.metrics
    }


def _evidence_nodes(trace: InterviewTrace) -> dict:
    graph = trace.metadata.get("evidence_graph")
    return graph if isinstance(graph, dict) else {}


def compare_traces(
    left: InterviewTrace,
    right: InterviewTrace,
    rubric: Rubric,
    *,
    evaluator: Evaluator | None = None,
) -> TraceDiffReport:
    evaluator = evaluator or default_evaluator()
    left_report = evaluator.run(left, rubric)
    right_report = evaluator.run(right, rubric)

    left_questions = _evaluative_questions(left)
    right_questions = _evaluative_questions(right)
    path_length = max(
        len(left_questions),
        len(right_questions),
    )

    path_steps: list[QuestionPathStep] = []
    similarities: list[float] = []
    followup_agreements: list[float] = []

    for index in range(path_length):
        left_turn = (
            left_questions[index]
            if index < len(left_questions)
            else None
        )
        right_turn = (
            right_questions[index]
            if index < len(right_questions)
            else None
        )

        if left_turn is None or right_turn is None:
            similarity = 0.0
        else:
            similarity = _jaccard(
                set(left_turn.rubric_tags),
                set(right_turn.rubric_tags),
            )

        left_followup = bool(
            left_turn and left_turn.parent_turn_id
        )
        right_followup = bool(
            right_turn and right_turn.parent_turn_id
        )
        followup_agreement = (
            left_turn is not None
            and right_turn is not None
            and left_followup == right_followup
        )

        similarities.append(similarity)
        followup_agreements.append(
            1.0 if followup_agreement else 0.0
        )
        path_steps.append(
            QuestionPathStep(
                index=index,
                left_turn_id=left_turn.id if left_turn else None,
                right_turn_id=right_turn.id if right_turn else None,
                left_tags=left_turn.rubric_tags if left_turn else [],
                right_tags=right_turn.rubric_tags if right_turn else [],
                tag_similarity=round(similarity, 4),
                left_followup=left_followup,
                right_followup=right_followup,
                followup_agreement=followup_agreement,
            )
        )

    question_path_similarity = (
        fmean(similarities)
        if similarities
        else 1.0
    )
    followup_action_agreement = (
        fmean(followup_agreements)
        if followup_agreements
        else 1.0
    )

    left_metrics = _metric_map(left_report)
    right_metrics = _metric_map(right_report)
    metric_deltas: list[MetricDelta] = []
    for name in sorted(
        set(left_metrics) | set(right_metrics)
    ):
        left_metric = left_metrics.get(name)
        right_metric = right_metrics.get(name)
        left_value = (
            float(left_metric.value)
            if left_metric and left_metric.value is not None
            else None
        )
        right_value = (
            float(right_metric.value)
            if right_metric and right_metric.value is not None
            else None
        )
        delta = (
            round(right_value - left_value, 4)
            if left_value is not None
            and right_value is not None
            else None
        )
        metric_deltas.append(
            MetricDelta(
                metric=name,
                left_value=left_value,
                right_value=right_value,
                delta=delta,
                left_passed=(
                    left_metric.passed
                    if left_metric
                    else None
                ),
                right_passed=(
                    right_metric.passed
                    if right_metric
                    else None
                ),
            )
        )

    left_graph = _evidence_nodes(left)
    right_graph = _evidence_nodes(right)
    evidence_deltas: list[CompetencyEvidenceDelta] = []
    for competency_id in sorted(
        set(left_graph) | set(right_graph)
    ):
        left_node = left_graph.get(competency_id)
        right_node = right_graph.get(competency_id)
        left_node = (
            left_node
            if isinstance(left_node, dict)
            else {}
        )
        right_node = (
            right_node
            if isinstance(right_node, dict)
            else {}
        )
        left_state = left_node.get("state")
        right_state = right_node.get("state")
        left_confidence = left_node.get("confidence")
        right_confidence = right_node.get("confidence")
        evidence_deltas.append(
            CompetencyEvidenceDelta(
                competency_id=competency_id,
                left_state=(
                    str(left_state)
                    if left_state is not None
                    else None
                ),
                right_state=(
                    str(right_state)
                    if right_state is not None
                    else None
                ),
                left_confidence=(
                    float(left_confidence)
                    if isinstance(left_confidence, (int, float))
                    else None
                ),
                right_confidence=(
                    float(right_confidence)
                    if isinstance(right_confidence, (int, float))
                    else None
                ),
                changed=(
                    left_state != right_state
                    or left_confidence != right_confidence
                ),
            )
        )

    left_interviewer = sum(
        turn.speaker is Speaker.INTERVIEWER
        for turn in left.turns
    )
    right_interviewer = sum(
        turn.speaker is Speaker.INTERVIEWER
        for turn in right.turns
    )
    left_candidate = sum(
        turn.speaker is Speaker.CANDIDATE
        for turn in left.turns
    )
    right_candidate = sum(
        turn.speaker is Speaker.CANDIDATE
        for turn in right.turns
    )

    return TraceDiffReport(
        left_session_id=left.session_id,
        right_session_id=right.session_id,
        question_path_similarity=round(
            question_path_similarity,
            4,
        ),
        followup_action_agreement=round(
            followup_action_agreement,
            4,
        ),
        interviewer_turn_delta=(
            right_interviewer - left_interviewer
        ),
        candidate_turn_delta=(
            right_candidate - left_candidate
        ),
        path_steps=path_steps,
        metric_deltas=metric_deltas,
        evidence_deltas=evidence_deltas,
        metadata={
            "rubric_id": rubric.id,
            "comparison_direction": "right_minus_left",
            "left_role": left.role,
            "right_role": right.role,
            "left_locale": left.locale,
            "right_locale": right.locale,
            "note": (
                "Trace diff reports structural and metric changes only. "
                "It does not select a better interview agent."
            ),
        },
    )
