from voxrubric.metrics import EvidenceProvenanceMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_generic_evidence_quote_must_exist_in_referenced_turn():
    trace = InterviewTrace(
        session_id="s",
        role="System evaluation fixture",
        turns=[
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I compared logs and traces.",
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
                        "quote": "I used a profiler",
                        "note": "Invalid provenance fixture.",
                        "source": "tool:case_study",
                    }],
                }
            }
        },
    )
    rubric = Rubric(
        id="r",
        title="System audit",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Job-related debugging evidence",
            )
        ],
    )

    result = EvidenceProvenanceMetric().evaluate(
        trace,
        rubric,
    )
    assert result.passed is False
    assert "literal substring" in result.details["problems"][0]
