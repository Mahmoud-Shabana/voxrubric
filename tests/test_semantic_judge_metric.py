from voxrubric.metrics import SemanticJudgeIntegrityMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def rubric():
    return Rubric(
        id="r",
        title="r",
        dimensions=[RubricDimension(id="debugging", description="debugging")],
    )


def test_grounded_semantic_evidence_passes():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the incident and compared traces before changing anything.",
            )
        ],
        metadata={
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "demonstrated",
                    "confidence": 0.9,
                    "evidence": [{
                        "id": "e1",
                        "turn_id": "a1",
                        "state": "demonstrated",
                        "confidence": 0.9,
                        "quote": "compared traces",
                        "note": "Grounded debugging evidence.",
                        "source": "semantic_judge:judge-a",
                    }],
                }
            },
            "evidence_judge_failures": [],
        },
    )
    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is True
    assert result.value == 1.0


def test_fabricated_semantic_quote_fails():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the incident and compared traces.",
            )
        ],
        metadata={
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "demonstrated",
                    "confidence": 0.8,
                    "evidence": [{
                        "id": "e1",
                        "turn_id": "a1",
                        "state": "demonstrated",
                        "confidence": 0.8,
                        "quote": "I used a flame graph",
                        "note": "Fabricated fixture.",
                        "source": "semantic_judge:judge-a",
                    }],
                }
            },
            "evidence_judge_failures": [],
        },
    )
    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "literal substring" in result.details["problems"][0]


def test_transcript_semantic_judge_cannot_emit_verified():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the issue.",
            )
        ],
        metadata={
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "verified",
                    "confidence": 0.99,
                    "evidence": [{
                        "id": "e1",
                        "turn_id": "a1",
                        "state": "verified",
                        "confidence": 0.99,
                        "quote": "reproduced the issue",
                        "note": "Overclaim fixture.",
                        "source": "semantic_judge:judge-a",
                    }],
                }
            },
            "evidence_judge_failures": [],
        },
    )
    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "verified evidence" in result.details["problems"][0]


def test_recorded_judge_failure_fails_integrity_metric():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={
            "evidence_graph": {},
            "evidence_judge_failures": [{
                "seq": 9,
                "turn_id": "a1",
                "payload": {
                    "judge_id": "judge-a",
                    "error": "quote is not grounded",
                },
            }],
        },
    )
    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert result.details["judge_failures"] == 1
