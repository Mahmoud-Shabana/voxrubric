from voxrubric.models import Rubric, RubricDimension
from voxrubric.review_bundle import audit_review_bundle


def rubric():
    return Rubric(
        id="backend",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(
                id="debugging",
                description="Production debugging",
            )
        ],
    )


def bundle():
    return {
        "schema_version": "1.0",
        "report": {
            "session_id": "session-1",
            "job_id": "job-1",
            "role": "Backend Engineer",
            "candidate_ref": "candidate",
            "status": "completed",
            "competencies": [],
            "evidence_judge_runs": [
                {
                    "id": "run-2",
                    "judge_id": "judge-a",
                    "answer_turn_id": "a1",
                    "created_at": "2026-09-23T12:00:00+00:00",
                    "transcript_revision_count": 1,
                    "current_transcript_revision_count": 1,
                    "observation_count": 1,
                    "failed": False,
                    "stale": False,
                    "supersedes_run_id": "run-1",
                }
            ],
            "reasons": [],
            "appeals": [],
            "integrity": [],
            "pending_appeals": 0,
            "integrity_signals": 0,
            "unresolved_tools": 0,
            "transcript_revisions": 1,
            "requires_human_review": False,
            "note": "Evidence summary only.",
        },
        "trace": {
            "session_id": "session-1",
            "role": "Backend Engineer",
            "locale": "en",
            "turns": [
                {
                    "id": "q1",
                    "speaker": "interviewer",
                    "text": "Describe a production incident.",
                    "rubric_tags": ["debugging"],
                    "metadata": {"question_lane": "anchor"},
                },
                {
                    "id": "a1",
                    "speaker": "candidate",
                    "text": "I reproduced the issue and compared metrics.",
                    "parent_turn_id": "q1",
                    "rubric_tags": [],
                    "metadata": {},
                },
            ],
            "scorecards": [],
            "metadata": {
                "job_id": "job-1",
                "status": "completed",
                "transcript_revisions": [
                    {
                        "id": "rev-1",
                        "turn_id": "a1",
                        "original_text": "I compared traces.",
                        "corrected_text": (
                            "I reproduced the issue and compared metrics."
                        ),
                        "reason": "candidate correction",
                    }
                ],
                "appeals": [],
                "integrity_signals": [],
                "audit_chain": {
                    "verified": True,
                    "head_hash": "a" * 64,
                    "event_count": 8,
                    "hash_version": 1,
                },
                "evidence_graph": {},
                "evidence_judge_runs": [],
            },
        },
        "audit": {
            "verified": True,
            "head_hash": "a" * 64,
            "event_count": 8,
            "hash_version": 1,
        },
    }


def test_review_bundle_integrity_passes_when_report_matches_trace():
    result = audit_review_bundle(
        bundle(),
        rubric(),
    )
    assert result.session_id == "session-1"
    assert result.bundle_integrity.passed is True
    assert result.bundle_integrity.value == 1.0
    assert result.evaluation.session_id == "session-1"


def test_review_bundle_detects_report_trace_mismatch():
    payload = bundle()
    payload["report"]["job_id"] = "wrong-job"
    payload["report"]["pending_appeals"] = 2

    result = audit_review_bundle(
        payload,
        rubric(),
    )
    assert result.bundle_integrity.passed is False
    problems = " ".join(
        result.bundle_integrity.details["problems"]
    )
    assert "job_id" in problems
    assert "pending appeal count" in problems


def test_review_bundle_requires_stale_judge_reason():
    payload = bundle()
    payload["report"]["evidence_judge_runs"][0]["stale"] = True
    payload["report"]["evidence_judge_runs"][0][
        "current_transcript_revision_count"
    ] = 2
    payload["report"]["requires_human_review"] = True
    payload["report"]["reasons"] = [
        {
            "code": "insufficient_evidence",
            "summary": "Evidence needs review.",
            "severity": "attention",
        }
    ]

    result = audit_review_bundle(
        payload,
        rubric(),
    )
    assert result.bundle_integrity.passed is False
    assert any(
        "stale evidence judge run" in problem
        for problem in result.bundle_integrity.details["problems"]
    )
