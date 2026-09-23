from voxrubric.metrics import VoiceTransportContinuityMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension


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


def evaluate(events):
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[],
        metadata={"voice_events": events},
    )
    return VoiceTransportContinuityMetric().evaluate(
        trace,
        rubric(),
    )


def test_server_transports_without_failures_pass():
    result = evaluate([
        {
            "seq": 1,
            "type": "voice_transport_selected",
            "payload": {
                "direction": "stt",
                "transport": "server",
                "provider_id": "stt-a",
            },
        },
        {
            "seq": 2,
            "type": "voice_transport_selected",
            "payload": {
                "direction": "tts",
                "transport": "server",
                "provider_id": "tts-a",
            },
        },
    ])

    assert result.passed is True
    assert result.value == 1.0
    assert result.details["fallbacks"] == 0


def test_provider_failure_with_browser_recovery_passes():
    result = evaluate([
        {
            "seq": 1,
            "type": "voice_transport_selected",
            "payload": {
                "direction": "stt",
                "transport": "server",
                "provider_id": "stt-a",
            },
        },
        {
            "seq": 2,
            "type": "voice_provider_failed",
            "payload": {
                "direction": "stt",
                "provider_id": "stt-a",
                "error_type": "TimeoutError",
                "message": "provider timeout",
            },
        },
        {
            "seq": 3,
            "type": "voice_transport_fallback",
            "payload": {
                "direction": "stt",
                "from_transport": "server",
                "to_transport": "browser",
                "reason": "provider timeout",
            },
        },
        {
            "seq": 4,
            "type": "voice_transport_selected",
            "payload": {
                "direction": "stt",
                "transport": "browser",
                "reason": "browser speech recognition",
            },
        },
    ])

    assert result.passed is True
    assert result.value == 1.0
    assert result.details["provider_failures"] == 1
    assert result.details["recovered_fallbacks"] == 1


def test_provider_failure_without_fallback_fails():
    result = evaluate([
        {
            "seq": 1,
            "type": "voice_provider_failed",
            "payload": {
                "direction": "tts",
                "provider_id": "tts-a",
                "error_type": "RuntimeError",
                "message": "stream failed",
            },
        },
    ])

    assert result.passed is False
    assert any(
        "has no recorded transport fallback" in problem
        for problem in result.details["problems"]
    )


def test_fallback_without_replacement_selection_fails():
    result = evaluate([
        {
            "seq": 1,
            "type": "voice_transport_fallback",
            "payload": {
                "direction": "tts",
                "from_transport": "server",
                "to_transport": "browser",
                "reason": "server unavailable",
            },
        },
    ])

    assert result.passed is False
    assert result.value == 0.0
    assert any(
        "has no later browser transport selection" in problem
        for problem in result.details["problems"]
    )


def test_server_selection_requires_provider_identity():
    result = evaluate([
        {
            "seq": 1,
            "type": "voice_transport_selected",
            "payload": {
                "direction": "stt",
                "transport": "server",
            },
        },
    ])

    assert result.passed is False
    assert any(
        "missing provider_id" in problem
        for problem in result.details["problems"]
    )
