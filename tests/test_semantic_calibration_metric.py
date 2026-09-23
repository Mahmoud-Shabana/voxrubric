from voxrubric.metrics import SemanticEvidenceCalibrationMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


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


def trace(*, state="demonstrated", confidence=0.9, active=True):
    return InterviewTrace(
        session_id="s",
        role="Backend Engineer",
        turns=[
            Turn(
                id="q1",
                speaker=Speaker.INTERVIEWER,
                text="Describe a production incident.",
                rubric_tags=["debugging"],
            ),
            Turn(
                id="a1",
                speaker=Speaker.CANDIDATE,
                text="I reproduced the issue and compared metrics.",
                parent_turn_id="q1",
            ),
        ],
        metadata={
            "semantic_calibration_targets": [
                {
                    "competency_id": "debugging",
                    "turn_id": "a1",
                    "expected_state": "demonstrated",
                    "min_confidence": 0.8,
                    "max_confidence": 0.95,
                }
            ],
            "evidence_graph": {
                "debugging": {
                    "competency_id": "debugging",
                    "state": state,
                    "confidence": confidence,
                    "evidence": [
                        {
                            "id": "e1",
                            "turn_id": "a1",
                            "state": state,
                            "confidence": confidence,
                            "quote": "compared metrics",
                            "note": "semantic observation",
                            "source": "semantic_judge:judge-a",
                            "active": active,
                        }
                    ],
                }
            },
        },
    )


def test_semantic_calibration_passes_exact_state_and_confidence_band():
    result = SemanticEvidenceCalibrationMetric().evaluate(
        trace(),
        rubric(),
    )

    assert result.passed is True
    assert result.value == 1.0
    assert result.details["correct"] == 1
    assert result.details["confidence_valid"] == 1


def test_semantic_calibration_fails_overclaim():
    result = SemanticEvidenceCalibrationMetric().evaluate(
        trace(state="claimed", confidence=0.91),
        rubric(),
    )

    assert result.passed is False
    assert result.value == 0.0
    assert any(
        "expected state demonstrated, got claimed" in problem
        for problem in result.details["problems"]
    )


def test_semantic_calibration_fails_confidence_outside_gold_band():
    result = SemanticEvidenceCalibrationMetric().evaluate(
        trace(confidence=0.99),
        rubric(),
    )

    assert result.passed is False
    assert result.value == 1.0
    assert any(
        "above 0.95" in problem
        for problem in result.details["problems"]
    )


def test_semantic_calibration_ignores_superseded_evidence():
    fixture = trace(active=False)
    fixture.metadata["evidence_graph"]["debugging"]["evidence"].append(
        {
            "id": "e2",
            "turn_id": "a1",
            "state": "demonstrated",
            "confidence": 0.88,
            "quote": "compared metrics",
            "note": "current observation",
            "source": "semantic_judge:judge-a",
            "active": True,
        }
    )

    result = SemanticEvidenceCalibrationMetric().evaluate(
        fixture,
        rubric(),
    )

    assert result.passed is True
    assert result.value == 1.0


def test_semantic_calibration_rejects_multiple_active_observations():
    fixture = trace()
    fixture.metadata["evidence_graph"]["debugging"]["evidence"].append(
        {
            "id": "e2",
            "turn_id": "a1",
            "state": "demonstrated",
            "confidence": 0.87,
            "quote": "reproduced the issue",
            "note": "duplicate current observation",
            "source": "semantic_judge:judge-b",
            "active": True,
        }
    )

    result = SemanticEvidenceCalibrationMetric().evaluate(
        fixture,
        rubric(),
    )

    assert result.passed is False
    assert any(
        "multiple active semantic evidence items" in problem
        for problem in result.details["problems"]
    )


def test_semantic_calibration_is_not_applicable_without_gold_targets():
    fixture = trace()
    fixture.metadata.pop("semantic_calibration_targets")

    result = SemanticEvidenceCalibrationMetric().evaluate(
        fixture,
        rubric(),
    )

    assert result.value is None
    assert result.passed is None
    assert result.details["applicable"] is False
