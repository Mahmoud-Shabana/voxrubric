from voxrubric.metrics import AsrPreservationMetric
from voxrubric.models import (
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)


def rubric() -> Rubric:
    return Rubric(
        id="asr",
        title="ASR Preservation",
        dimensions=[
            RubricDimension(
                id="communication",
                description="Technical communication",
            )
        ],
    )


def candidate(
    *,
    text: str,
    reference: str | None = None,
    critical_terms=None,
    turn_id: str = "a1",
) -> Turn:
    metadata = {}
    if reference is not None:
        metadata["asr_reference_text"] = reference
    if critical_terms is not None:
        metadata["asr_critical_terms"] = critical_terms
    return Turn(
        id=turn_id,
        speaker=Speaker.CANDIDATE,
        text=text,
        metadata=metadata,
    )


def trace(*turns: Turn) -> InterviewTrace:
    return InterviewTrace(
        session_id="asr-session",
        role="Backend Engineer",
        locale="ar-SA",
        turns=list(turns),
    )


def test_asr_preservation_accepts_normalized_code_switched_transcript():
    reference = (
        "واجهت مُشكلة في FastAPI service بسبب blocking database calls."
    )
    observed = (
        "واجهت مشكلة في fastapi service بسبب blocking database calls"
    )

    result = AsrPreservationMetric().evaluate(
        trace(
            candidate(
                text=observed,
                reference=reference,
                critical_terms=[
                    "FastAPI",
                    "blocking database calls",
                ],
            )
        ),
        rubric(),
    )

    assert result.value == 1.0
    assert result.passed is True
    assert result.details["mean_wer"] == 0.0
    assert result.details["critical_term_recall"] == 1.0
    assert result.details["code_switch_preservation"] == 1.0


def test_asr_preservation_fails_when_technical_terms_are_lost():
    reference = (
        "استخدمت FastAPI مع Redis و circuit breaker في الإنتاج"
    )
    observed = (
        "استخدمت FastAPI مع التخزين و circuit breaker في الإنتاج"
    )

    result = AsrPreservationMetric(
        max_mean_wer=0.5,
        min_critical_term_recall=1.0,
    ).evaluate(
        trace(
            candidate(
                text=observed,
                reference=reference,
                critical_terms=[
                    "FastAPI",
                    "Redis",
                    "circuit breaker",
                ],
            )
        ),
        rubric(),
    )

    assert result.passed is False
    assert result.details["critical_term_recall"] == 0.6667
    assert any(
        "critical-term recall" in problem
        for problem in result.details["problems"]
    )


def test_asr_preservation_can_isolate_code_switch_loss():
    reference = "حللت latency باستخدام OpenTelemetry"
    observed = "حللت زمن الاستجابة باستخدام القياس"

    result = AsrPreservationMetric(
        max_mean_wer=1.0,
        min_critical_term_recall=0.0,
        require_code_switch_preservation=True,
    ).evaluate(
        trace(
            candidate(
                text=observed,
                reference=reference,
                critical_terms=[],
            )
        ),
        rubric(),
    )

    assert result.passed is False
    assert result.details["mixed_language_references"] == 1
    assert result.details["mixed_language_preserved"] == 0
    assert result.details["code_switch_preservation"] == 0.0
    assert any(
        "code-switching" in problem
        for problem in result.details["problems"]
    )


def test_asr_preservation_aggregates_multiple_reference_turns():
    result = AsrPreservationMetric(
        max_mean_wer=0.2,
    ).evaluate(
        trace(
            candidate(
                turn_id="a1",
                text="I used FastAPI with Redis",
                reference="I used FastAPI with Redis",
                critical_terms=["FastAPI", "Redis"],
            ),
            candidate(
                turn_id="a2",
                text="ثم قست latency before deployment",
                reference="ثم قست latency before deployment",
                critical_terms=["latency"],
            ),
        ),
        rubric(),
    )

    assert result.passed is True
    assert result.details["samples"][0]["turn_id"] == "a1"
    assert result.details["samples"][1]["turn_id"] == "a2"
    assert result.details["critical_terms"] == 3
    assert result.details["critical_terms_preserved"] == 3


def test_asr_preservation_is_not_applicable_without_reference_text():
    result = AsrPreservationMetric().evaluate(
        trace(
            candidate(
                text="ordinary production transcript",
            )
        ),
        rubric(),
    )

    assert result.value is None
    assert result.passed is None
    assert result.details["applicable"] is False
