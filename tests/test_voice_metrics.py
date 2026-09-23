from voxrubric.metrics import (
    BargeInRecoveryMetric,
    VoiceEventIntegrityMetric,
    VoiceLatencyBreakdownMetric,
)
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def rubric():
    return Rubric(
        id="r",
        title="r",
        dimensions=[RubricDimension(id="x", description="x")],
    )


def good_voice_trace():
    return InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Question one",
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="Answer one",
                parent_turn_id="q1",
            ),
            Turn(
                id="q2",
                speaker=Speaker.INTERVIEWER,
                text="Question two",
                parent_turn_id="a1",
            ),
        ],
        metadata={
            "status": "running",
            "voice_events": [
                {
                    "seq": 1,
                    "type": "voice_tts_started",
                    "turn_id": "q1",
                    "payload": {
                        "generation": 0,
                        "response_to_tts_ms": 80,
                    },
                },
                {
                    "seq": 2,
                    "type": "voice_barge_in",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                        "interrupted_turn_id": "q1",
                    },
                },
                {
                    "seq": 3,
                    "type": "voice_tts_cancelled",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                        "turn_id": "q1",
                        "reason": "barge_in",
                    },
                },
                {
                    "seq": 4,
                    "type": "voice_speech_started",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                    },
                },
                {
                    "seq": 5,
                    "type": "voice_transcript_partial",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                        "text": "partial",
                    },
                },
                {
                    "seq": 6,
                    "type": "voice_transcript_final",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                        "text": "Answer one",
                        "speech_to_final_ms": 500,
                    },
                },
                {
                    "seq": 7,
                    "type": "voice_response_ready",
                    "turn_id": "q2",
                    "payload": {
                        "generation": 1,
                        "final_to_response_ms": 700,
                    },
                },
                {
                    "seq": 8,
                    "type": "voice_tts_started",
                    "turn_id": "q2",
                    "payload": {
                        "generation": 1,
                        "response_to_tts_ms": 200,
                    },
                },
                {
                    "seq": 9,
                    "type": "voice_tts_completed",
                    "turn_id": "q2",
                    "payload": {
                        "generation": 1,
                    },
                },
            ],
        },
    )


def test_voice_lifecycle_and_barge_in_recovery_pass():
    trace = good_voice_trace()
    integrity = VoiceEventIntegrityMetric().evaluate(trace, rubric())
    recovery = BargeInRecoveryMetric().evaluate(trace, rubric())
    latency = VoiceLatencyBreakdownMetric(
        end_to_end_budget_ms=2000
    ).evaluate(trace, rubric())

    assert integrity.passed is True
    assert recovery.passed is True
    assert recovery.value == 1.0
    assert latency.passed is True
    assert latency.value == 1400.0
    assert latency.details["speech_to_final_p95_ms"] == 500.0
    assert latency.details["final_to_response_p95_ms"] == 700.0
    assert latency.details["response_to_tts_p95_ms"] == 200.0


def test_barge_in_without_recovery_fails():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Question",
            )
        ],
        metadata={
            "voice_events": [
                {
                    "seq": 1,
                    "type": "voice_tts_started",
                    "turn_id": "q1",
                    "payload": {"generation": 0},
                },
                {
                    "seq": 2,
                    "type": "voice_barge_in",
                    "turn_id": None,
                    "payload": {"generation": 1},
                },
                {
                    "seq": 3,
                    "type": "voice_tts_cancelled",
                    "turn_id": None,
                    "payload": {
                        "generation": 1,
                        "turn_id": "q1",
                    },
                },
                {
                    "seq": 4,
                    "type": "voice_speech_started",
                    "turn_id": None,
                    "payload": {"generation": 1},
                },
            ]
        },
    )
    result = BargeInRecoveryMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert result.value == 0.0
    assert result.details["failures"][1] == [
        "final_transcript",
        "response_ready",
    ]


def test_voice_event_integrity_rejects_stale_tts_completion():
    trace = InterviewTrace(
        session_id="s",
        role="Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Question",
            )
        ],
        metadata={
            "voice_events": [
                {
                    "seq": 1,
                    "type": "voice_tts_completed",
                    "turn_id": "q1",
                    "payload": {"generation": 0},
                }
            ]
        },
    )
    result = VoiceEventIntegrityMetric().evaluate(trace, rubric())
    assert result.passed is False
    assert "without active TTS" in result.details["problems"][0]
