from voxrubric.metrics import GovernanceAuditMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def _rubric():
    return Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])


def test_governance_audit_accepts_candidate_correction_appeal_and_review_signal():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(id="q1", speaker=Speaker.INTERVIEWER, text="Question"),
            Turn(id="a1", speaker=Speaker.CANDIDATE, text="Corrected answer"),
        ],
        metadata={
            "transcript_revisions": [{
                "id": "rev",
                "turn_id": "a1",
                "original_text": "Wrong transcript",
                "corrected_text": "Corrected answer",
                "reason": "STT error",
            }],
            "appeals": [{
                "id": "ap",
                "message": "Review this turn",
                "turn_ids": ["a1"],
                "status": "pending",
            }],
            "integrity_signals": [{
                "id": "sig",
                "kind": "possible_external_assistance",
                "confidence": 0.67,
                "note": "Review only",
                "evidence": {},
                "requires_human_review": True,
            }],
        },
    )
    result = GovernanceAuditMetric().evaluate(trace, _rubric())
    assert result.passed is True
    assert result.value == 1.0


def test_integrity_signal_without_human_review_fails_governance():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={
            "transcript_revisions": [],
            "appeals": [],
            "integrity_signals": [{
                "kind": "flag",
                "confidence": 0.8,
                "requires_human_review": False,
            }],
        },
    )
    result = GovernanceAuditMetric().evaluate(trace, _rubric())
    assert result.passed is False
    assert "human-review-only" in result.details["problems"][0]
