from voxrubric.models import (
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)
from voxrubric.trace_diff import compare_traces


def rubric():
    return Rubric(
        id="backend",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(id="python", description="Python"),
            RubricDimension(id="debugging", description="Debugging"),
        ],
    )


def trace(session_id, second_tag, followup):
    return InterviewTrace(
        session_id=session_id,
        role="Backend Engineer",
        turns=[
            Turn(
                id=f"{session_id}-q1",
                speaker=Speaker.INTERVIEWER,
                text="Tell me about Python.",
                rubric_tags=["python"],
            ),
            Turn(
                id=f"{session_id}-a1",
                speaker=Speaker.CANDIDATE,
                text="I built a Python service.",
                parent_turn_id=f"{session_id}-q1",
            ),
            Turn(
                id=f"{session_id}-q2",
                speaker=Speaker.INTERVIEWER,
                text="What happened next?",
                rubric_tags=[second_tag],
                parent_turn_id=(
                    f"{session_id}-a1"
                    if followup
                    else None
                ),
            ),
        ],
        metadata={
            "evidence_graph": {
                "python": {
                    "competency_id": "python",
                    "state": "demonstrated",
                    "confidence": 0.8,
                    "evidence": [],
                }
            }
        },
    )


def test_trace_diff_reports_path_and_followup_changes():
    left = trace("left", "debugging", True)
    right = trace("right", "python", False)

    result = compare_traces(
        left,
        right,
        rubric(),
    )

    assert result.left_session_id == "left"
    assert result.right_session_id == "right"
    assert result.question_path_similarity == 0.5
    assert result.followup_action_agreement == 0.5
    assert len(result.path_steps) == 2
    assert result.path_steps[1].tag_similarity == 0.0
    assert result.path_steps[1].followup_agreement is False
    assert result.metadata["comparison_direction"] == "right_minus_left"
    assert "does not select" in result.metadata["note"]


def test_trace_diff_reports_metric_deltas_without_overall_winner():
    left = trace("left", "python", False)
    right = trace("right", "debugging", False)

    result = compare_traces(
        left,
        right,
        rubric(),
    )

    coverage = next(
        item
        for item in result.metric_deltas
        if item.metric == "rubric_coverage"
    )
    assert coverage.left_value == 0.5
    assert coverage.right_value == 1.0
    assert coverage.delta == 0.5

    dumped = result.model_dump()
    assert "winner" not in dumped
    assert "ranking" not in dumped
    assert "score" not in dumped
