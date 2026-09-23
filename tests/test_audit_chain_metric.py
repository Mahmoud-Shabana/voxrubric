import hashlib
import json

from voxrubric.metrics import AuditChainIntegrityMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension


def hash_event(event, prev_hash):
    payload = {
        "hash_version": 1,
        "seq": event["seq"],
        "type": event["type"],
        "turn_id": event["turn_id"],
        "payload": event["payload"],
        "created_at": event["created_at"],
        "prev_hash": prev_hash,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fixture_trace():
    first = {
        "seq": 1,
        "type": "session_created",
        "turn_id": None,
        "payload": {"job_id": "job"},
        "created_at": "2026-09-23T12:00:00+00:00",
        "hash_version": 1,
        "prev_hash": None,
        "event_hash": None,
    }
    first["event_hash"] = hash_event(
        first,
        None,
    )

    second = {
        "seq": 2,
        "type": "interview_started",
        "turn_id": None,
        "payload": {},
        "created_at": "2026-09-23T12:00:01+00:00",
        "hash_version": 1,
        "prev_hash": first["event_hash"],
        "event_hash": None,
    }
    second["event_hash"] = hash_event(
        second,
        first["event_hash"],
    )

    return InterviewTrace(
        session_id="s",
        role="System fixture",
        turns=[],
        metadata={
            "audit_events": [first, second],
            "audit_chain": {
                "verified": True,
                "head_hash": second["event_hash"],
                "event_count": 2,
                "hash_version": 1,
            },
        },
    )


def rubric():
    return Rubric(
        id="r",
        title="r",
        dimensions=[
            RubricDimension(
                id="x",
                description="x",
            )
        ],
    )


def test_valid_exported_audit_chain_passes():
    result = AuditChainIntegrityMetric().evaluate(
        fixture_trace(),
        rubric(),
    )
    assert result.passed is True
    assert result.value == 1.0


def test_tampered_exported_event_fails():
    trace = fixture_trace()
    trace.metadata["audit_events"][0]["payload"]["job_id"] = "tampered"

    result = AuditChainIntegrityMetric().evaluate(
        trace,
        rubric(),
    )
    assert result.passed is False
    assert any(
        "event hash mismatch" in problem
        for problem in result.details["problems"]
    )
