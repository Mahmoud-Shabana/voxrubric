from voxrubric.metrics import SemanticJudgeDisagreementMetric
from voxrubric.models import (
    DimensionScore,
    EvidenceRef,
    InterviewScorecard,
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)


def rubric() -> Rubric:
    return Rubric(
        id="backend",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Production debugging",
            ),
        ],
    )


def trace_with(scorecards) -> InterviewTrace:
    return InterviewTrace(
        session_id="session-1",
        role="Backend Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe the incident.",
                rubric_tags=["debugging"],
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text=(
                    "I measured event-loop lag and database latency "
                    "before changing the driver."
                ),
                parent_turn_id="q1",
            ),
            Turn(
                id="a2",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the issue under controlled load.",
                parent_turn_id="q1",
            ),
        ],
        scorecards=scorecards,
    )


def card(judge_id: str, score: float, turn_id: str, quote: str):
    return InterviewScorecard(
        judge_id=judge_id,
        dimensions=[
            DimensionScore(
                dimension="debugging",
                score=score,
                max_score=10,
                evidence=[
                    EvidenceRef(
                        turn_id=turn_id,
                        quote=quote,
                    )
                ],
            )
        ],
    )


def test_semantic_disagreement_reports_consensus():
    trace = trace_with(
        [
            card(
                "judge-a",
                8,
                "a1",
                "event-loop lag and database latency",
            ),
            card(
                "judge-b",
                8.5,
                "a1",
                "event-loop lag and database latency",
            ),
        ]
    )

    result = SemanticJudgeDisagreementMetric().evaluate(
        trace,
        rubric(),
    )

    assert result.value == 0.0
    assert result.passed is True
    comparison = result.details["comparisons"][0]
    assert comparison["score_delta"] == 0.5
    assert comparison["evidence_jaccard"] == 1.0
    assert comparison["material_disagreement"] is False


def test_semantic_disagreement_detects_score_divergence():
    trace = trace_with(
        [
            card(
                "judge-a",
                9,
                "a1",
                "event-loop lag and database latency",
            ),
            card(
                "judge-b",
                6,
                "a1",
                "event-loop lag and database latency",
            ),
        ]
    )

    result = SemanticJudgeDisagreementMetric().evaluate(
        trace,
        rubric(),
    )

    assert result.value == 1.0
    assert result.passed is False
    comparison = result.details["comparisons"][0]
    assert comparison["score_disagreement"] is True
    assert comparison["evidence_disagreement"] is False


def test_semantic_disagreement_detects_evidence_divergence():
    trace = trace_with(
        [
            card(
                "judge-a",
                8,
                "a1",
                "event-loop lag and database latency",
            ),
            card(
                "judge-b",
                8,
                "a2",
                "reproduced the issue under controlled load",
            ),
        ]
    )

    result = SemanticJudgeDisagreementMetric().evaluate(
        trace,
        rubric(),
    )

    assert result.value == 1.0
    assert result.passed is False
    comparison = result.details["comparisons"][0]
    assert comparison["score_disagreement"] is False
    assert comparison["evidence_disagreement"] is True
    assert comparison["evidence_jaccard"] == 0.0


def test_semantic_disagreement_is_not_applicable_with_one_judge():
    trace = trace_with(
        [
            card(
                "judge-a",
                8,
                "a1",
                "event-loop lag and database latency",
            )
        ]
    )

    result = SemanticJudgeDisagreementMetric().evaluate(
        trace,
        rubric(),
    )

    assert result.value is None
    assert result.passed is None
    assert result.details["judges"] == 1
