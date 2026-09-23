from voxrubric.metrics import VoiceEndpointingRecoveryMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension


def rubric():
    return Rubric(
        id="voice",
        title="Voice Interview",
        dimensions=[
            RubricDimension(
                id="communication",
                description="Clear communication",
            )
        ],
    )


def evaluate(events):
    return VoiceEndpointingRecoveryMetric().evaluate(
        InterviewTrace(
            session_id="s",
            role="Engineer",
            turns=[],
            metadata={"voice_events": events},
        ),
        rubric(),
    )


def test_vad_endpoint_recovery_passes_with_same_generation_final():
    result = evaluate([
        {
            "seq": 10,
            "type": "voice_vad_endpoint",
            "payload": {
                "generation": 2,
                "state": "speech_ended",
                "utterance_ms": 1840.0,
                "silence_ms": 700.0,
                "frame_ms": 20.0,
                "auto_commit_recommended": True,
            },
        },
        {
            "seq": 11,
            "type": "voice_transcript_final",
            "payload": {
                "generation": 2,
                "speech_to_final_ms": 1950,
            },
        },
    ])

    assert result.passed is True
    assert result.value == 1.0
    assert result.details["endpoints"][0]["recovered"] is True


def test_vad_endpoint_without_final_transcript_fails():
    result = evaluate([
        {
            "seq": 4,
            "type": "voice_vad_endpoint",
            "payload": {
                "generation": 1,
                "state": "speech_ended",
                "utterance_ms": 900.0,
                "silence_ms": 700.0,
                "frame_ms": 20.0,
                "auto_commit_recommended": True,
            },
        },
    ])

    assert result.passed is False
    assert result.value == 0.0
    assert any(
        "no later final transcript" in problem
        for problem in result.details["problems"]
    )


def test_vad_endpoint_cannot_recover_from_different_generation_final():
    result = evaluate([
        {
            "seq": 2,
            "type": "voice_vad_endpoint",
            "payload": {
                "generation": 3,
                "state": "max_duration",
                "utterance_ms": 120000.0,
                "silence_ms": 0.0,
                "frame_ms": 20.0,
                "auto_commit_recommended": True,
            },
        },
        {
            "seq": 3,
            "type": "voice_transcript_final",
            "payload": {
                "generation": 4,
                "speech_to_final_ms": 120100,
            },
        },
    ])

    assert result.passed is False
    assert result.value == 0.0


def test_vad_endpoint_requires_auto_commit_contract():
    result = evaluate([
        {
            "seq": 5,
            "type": "voice_vad_endpoint",
            "payload": {
                "generation": 0,
                "state": "speech_ended",
                "utterance_ms": 500.0,
                "silence_ms": 700.0,
                "frame_ms": 20.0,
                "auto_commit_recommended": False,
            },
        },
        {
            "seq": 6,
            "type": "voice_transcript_final",
            "payload": {
                "generation": 0,
            },
        },
    ])

    assert result.passed is False
    assert any(
        "auto_commit_recommended" in problem
        for problem in result.details["problems"]
    )
