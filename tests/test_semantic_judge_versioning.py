from voxrubric.metrics import (
    EvidenceProvenanceMetric,
    SemanticJudgeIntegrityMetric,
)
from voxrubric.models import (
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)


def rubric():
    return Rubric(
        id="r",
        title="Backend",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Production debugging",
            )
        ],
    )


def test_superseded_historical_quote_does_not_fail_current_provenance():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the incident and compared metrics.",
                parent_turn_id="q1",
            ),
        ],
        metadata={
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "claimed",
                    "confidence": None,
                    "evidence": [
                        {
                            "id": "old-evidence",
                            "turn_id": "a1",
                            "state": "demonstrated",
                            "confidence": 0.9,
                            "quote": "compared traces",
                            "note": "Valid before transcript correction.",
                            "source": "semantic_judge:judge-a",
                            "judge_run_id": "run-1",
                            "active": False,
                        }
                    ],
                }
            }
        },
    )

    result = EvidenceProvenanceMetric().evaluate(trace, rubric())
    assert result.passed is True
    assert result.value == 1.0


def test_current_versioned_semantic_evidence_passes():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the incident and compared metrics.",
                parent_turn_id="q1",
            ),
        ],
        metadata={
            "transcript_revisions": [
                {
                    "id": "rev-1",
                    "turn_id": "a1",
                    "original_text": "I compared traces.",
                    "corrected_text": (
                        "I reproduced the incident and compared metrics."
                    ),
                    "reason": "candidate correction",
                }
            ],
            "evidence_judge_runs": [
                {
                    "id": "run-2",
                    "judge_id": "judge-a",
                    "question_turn_id": "q1",
                    "answer_turn_id": "a1",
                    "competency_ids": ["debugging"],
                    "created_at": "2026-09-23T12:00:00+00:00",
                    "transcript_revision_count": 1,
                    "observation_ids": ["e2"],
                    "audit": {},
                    "error_type": None,
                    "error": None,
                    "supersedes_run_id": "run-1",
                }
            ],
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "demonstrated",
                    "confidence": 0.91,
                    "evidence": [
                        {
                            "id": "e2",
                            "turn_id": "a1",
                            "state": "demonstrated",
                            "confidence": 0.91,
                            "quote": "compared metrics",
                            "note": "Current grounded evidence.",
                            "source": "semantic_judge:judge-a",
                            "judge_run_id": "run-2",
                            "active": True,
                        }
                    ],
                }
            },
            "evidence_judge_failures": [],
        },
    )

    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is True
    assert result.value == 1.0
    assert result.details["judge_runs"] == 1


def test_stale_latest_judge_run_fails_integrity():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the incident and compared metrics.",
                parent_turn_id="q1",
            ),
        ],
        metadata={
            "transcript_revisions": [
                {
                    "id": "rev-1",
                    "turn_id": "a1",
                    "original_text": "I compared traces.",
                    "corrected_text": (
                        "I reproduced the incident and compared metrics."
                    ),
                    "reason": "candidate correction",
                }
            ],
            "evidence_judge_runs": [
                {
                    "id": "run-1",
                    "judge_id": "judge-a",
                    "question_turn_id": "q1",
                    "answer_turn_id": "a1",
                    "competency_ids": ["debugging"],
                    "created_at": "2026-09-23T11:00:00+00:00",
                    "transcript_revision_count": 0,
                    "observation_ids": ["e1"],
                    "audit": {},
                    "error_type": None,
                    "error": None,
                    "supersedes_run_id": None,
                }
            ],
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "claimed",
                    "confidence": None,
                    "evidence": [
                        {
                            "id": "e1",
                            "turn_id": "a1",
                            "state": "demonstrated",
                            "confidence": 0.9,
                            "quote": "compared traces",
                            "note": "Historical evidence.",
                            "source": "semantic_judge:judge-a",
                            "judge_run_id": "run-1",
                            "active": False,
                        }
                    ],
                }
            },
            "evidence_judge_failures": [],
        },
    )

    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert any(
        "is stale" in problem
        for problem in result.details["problems"]
    )


def test_active_evidence_cannot_point_to_failed_judge_run():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I compared traces.",
                parent_turn_id="q1",
            ),
        ],
        metadata={
            "transcript_revisions": [],
            "evidence_judge_runs": [
                {
                    "id": "run-bad",
                    "judge_id": "judge-a",
                    "question_turn_id": "q1",
                    "answer_turn_id": "a1",
                    "competency_ids": ["debugging"],
                    "created_at": "2026-09-23T11:00:00+00:00",
                    "transcript_revision_count": 0,
                    "observation_ids": ["e1"],
                    "audit": {},
                    "error_type": "EvidenceJudgeError",
                    "error": "provider failed",
                    "supersedes_run_id": None,
                }
            ],
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": "demonstrated",
                    "confidence": 0.8,
                    "evidence": [
                        {
                            "id": "e1",
                            "turn_id": "a1",
                            "state": "demonstrated",
                            "confidence": 0.8,
                            "quote": "compared traces",
                            "note": "Invalid active evidence fixture.",
                            "source": "semantic_judge:judge-a",
                            "judge_run_id": "run-bad",
                            "active": True,
                        }
                    ],
                }
            },
            "evidence_judge_failures": [],
        },
    )

    result = SemanticJudgeIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    problems = " ".join(result.details["problems"])
    assert "latest judge run for a1 failed" in problems
    assert "failed judge run" in problems
