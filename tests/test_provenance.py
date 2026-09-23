from voxrubric.metrics import EvidenceProvenanceMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_evidence_graph_rejects_unknown_turn_reference():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[Turn(id="a1", speaker=Speaker.CANDIDATE, text="answer")],
        metadata={
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "verified",
                    "confidence": 0.9,
                    "evidence": [{
                        "id": "e1",
                        "turn_id": "missing",
                        "state": "verified",
                        "confidence": 0.9,
                        "note": "Concrete verification step.",
                        "source": "evaluator",
                    }],
                }
            }
        },
    )
    rubric = Rubric(id="r", title="r", dimensions=[RubricDimension(id="debugging", description="debugging")])
    result = EvidenceProvenanceMetric().evaluate(trace, rubric)
    assert result.passed is False
    assert result.value == 0.0
    assert "unknown turn" in result.details["problems"][0]
