from voxrubric.metrics import CandidateControlRecoveryMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def rubric():
    return Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])


def test_control_recovery_accepts_repeat_pause_resume_and_correction():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(id="q1", speaker=Speaker.INTERVIEWER, text="Question"),
            Turn(
                id="q1-repeat",
                speaker=Speaker.INTERVIEWER,
                text="Question",
                metadata={"candidate_control": "repeat"},
            ),
            Turn(id="a1", speaker=Speaker.CANDIDATE, text="Corrected answer"),
        ],
        metadata={
            "status": "running",
            "candidate_controls": [
                {"kind": "repeat", "target_turn_id": "q1", "text": None},
                {"kind": "thinking_time", "target_turn_id": "q1", "text": None},
                {"kind": "resume", "target_turn_id": "q1", "text": None},
                {
                    "kind": "correct_last_answer",
                    "target_turn_id": "a1",
                    "text": "Corrected answer",
                },
            ],
            "transcript_revisions": [{
                "turn_id": "a1",
                "original_text": "Wrong answer",
                "corrected_text": "Corrected answer",
            }],
        },
    )
    result = CandidateControlRecoveryMetric().evaluate(trace, rubric())
    assert result.passed is True
    assert result.value == 1.0


def test_completed_trace_cannot_end_paused():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={
            "status": "completed",
            "candidate_controls": [
                {"kind": "thinking_time", "target_turn_id": None, "text": None},
            ],
            "transcript_revisions": [],
        },
    )
    result = CandidateControlRecoveryMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "unmatched" in result.details["problems"][-1]
