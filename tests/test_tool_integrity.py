from voxrubric.metrics import ToolArtifactIntegrityMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension


def rubric():
    return Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])


def test_valid_tool_lifecycle_passes():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={
            "tools": [{
                "id": "tool-1",
                "kind": "coding",
                "title": "Challenge",
                "instructions": "Implement add.",
                "competency_tags": ["x"],
                "status": "evaluated",
                "payload": {
                    "language": "python",
                    "public_tests": ["assert add(1, 2) == 3"],
                    "hidden_test_count": 2,
                },
                "opened_from_turn_id": None,
            }],
            "tool_submissions": [{
                "id": "sub-1",
                "tool_id": "tool-1",
                "content": {"code": "def add(a,b): return a+b"},
            }],
            "tool_evaluations": [{
                "tool_id": "tool-1",
                "submission_id": "sub-1",
                "passed": True,
                "score": 1.0,
                "summary": "Passed tests.",
                "evidence": {"passed_tests": 3, "total_tests": 3},
            }],
        },
    )
    result = ToolArtifactIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is True
    assert result.value == 1.0


def test_public_hidden_test_leak_fails():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={
            "tools": [{
                "id": "tool-1",
                "kind": "coding",
                "status": "open",
                "payload": {"hidden_tests": ["assert secret()"]},
            }],
            "tool_submissions": [],
            "tool_evaluations": [],
        },
    )
    result = ToolArtifactIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "private keys" in result.details["problems"][0]


def test_manual_review_evaluation_cannot_also_assign_score():
    trace = InterviewTrace(
        session_id="s",
        role="Analyst",
        turns=[],
        metadata={
            "tools": [{"id": "t", "kind": "case_study", "status": "evaluated", "payload": {}}],
            "tool_submissions": [{"id": "sub", "tool_id": "t", "content": {"answer": "x"}}],
            "tool_evaluations": [{
                "tool_id": "t",
                "submission_id": "sub",
                "score": 0.8,
                "passed": None,
                "summary": "manual",
                "evidence": {"review_required": True},
            }],
        },
    )
    result = ToolArtifactIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "manual review required" in result.details["problems"][0]
