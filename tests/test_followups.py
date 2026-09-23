from voxrubric.metrics import FollowUpIntegrityMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_followup_parent_must_be_candidate():
    trace = InterviewTrace(session_id="s", role="x", turns=[
        Turn(id="q1", speaker=Speaker.INTERVIEWER, text="question"),
        Turn(id="a1", speaker=Speaker.CANDIDATE, text="answer"),
        Turn(id="q2", speaker=Speaker.INTERVIEWER, text="follow up", parent_turn_id="a1"),
    ])
    rubric = Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])
    result = FollowUpIntegrityMetric().evaluate(trace, rubric)
    assert result.passed is True
    assert result.value == 1.0
