from voxrubric.metrics import AuditCorrelationIntegrityMetric
from voxrubric.models import (
    InterviewTrace,
    Rubric,
    RubricDimension,
)


def rubric():
    return Rubric(
        id="r",
        title="Engineer",
        dimensions=[
            RubricDimension(
                id="x",
                description="systems",
            )
        ],
    )


def evaluate(events, **metadata):
    trace = InterviewTrace(
        session_id="session-1234",
        role="Engineer",
        turns=[],
        metadata={
            "audit_events": events,
            "job_id": "job-12345678",
            "candidate_ref": "candidate-1234",
            **metadata,
        },
    )
    return AuditCorrelationIntegrityMetric().evaluate(
        trace,
        rubric(),
    )


def test_valid_correlation_ids_pass_and_report_coverage():
    result = evaluate([
        {
            "seq": 1,
            "payload": {
                "_trace": {
                    "correlation_id": "req-abcd1234",
                }
            },
        },
        {
            "seq": 2,
            "payload": {},
        },
        {
            "seq": 3,
            "payload": {
                "_trace": {
                    "correlation_id": "ws-voice-5678",
                }
            },
        },
    ])

    assert result.passed is True
    assert result.value == 1.0
    assert result.details["traced_events"] == 2
    assert result.details["correlation_coverage"] == 0.6667


def test_correlation_id_must_not_reuse_session_or_candidate_identifier():
    result = evaluate([
        {
            "seq": 1,
            "payload": {
                "_trace": {
                    "correlation_id": "candidate-1234",
                }
            },
        }
    ])

    assert result.passed is False
    assert any(
        "reuses a session, job, or candidate identifier"
        in problem
        for problem in result.details["problems"]
    )


def test_invalid_correlation_format_fails():
    result = evaluate([
        {
            "seq": 1,
            "payload": {
                "_trace": {
                    "correlation_id": "contains spaces",
                }
            },
        }
    ])

    assert result.passed is False
    assert any(
        "bounded safe format" in problem
        for problem in result.details["problems"]
    )


def test_legacy_trace_without_correlation_is_not_applicable():
    result = evaluate([
        {
            "seq": 1,
            "payload": {},
        }
    ])

    assert result.passed is None
    assert result.value is None
    assert result.details["applicable"] is False
