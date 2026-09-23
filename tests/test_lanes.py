from voxrubric.metrics import DualLaneBalanceMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def rubric():
    return Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])


def test_dual_lane_balance_accepts_discrete_question_tolerance():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        metadata={"anchor_ratio_target": 0.5},
        turns=[
            Turn(id="q1", speaker=Speaker.INTERVIEWER, text="a", metadata={"question_lane": "anchor"}),
            Turn(id="a1", speaker=Speaker.CANDIDATE, text="a"),
            Turn(id="q2", speaker=Speaker.INTERVIEWER, text="b", metadata={"question_lane": "adaptive"}),
            Turn(id="a2", speaker=Speaker.CANDIDATE, text="b"),
            Turn(id="q3", speaker=Speaker.INTERVIEWER, text="c", metadata={"question_lane": "adaptive"}),
        ],
    )
    result = DualLaneBalanceMetric().evaluate(trace, rubric())
    assert result.value == 0.3333
    assert result.passed is True


def test_declared_dual_lane_without_tags_fails():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        metadata={"anchor_ratio_target": 0.4},
        turns=[Turn(id="q", speaker=Speaker.INTERVIEWER, text="?")],
    )
    result = DualLaneBalanceMetric().evaluate(trace, rubric())
    assert result.passed is False
