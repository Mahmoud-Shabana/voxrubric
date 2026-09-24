import pytest

from voxrubric.metrics import SemanticFollowUpQualityMetric
from voxrubric.models import (
    DimensionScore,
    EvidenceRef,
    InterviewScorecard,
    InterviewTrace,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)


class StaticFollowUpJudge:
    def __init__(
        self,
        *,
        score: float = 8.0,
        evidence_mode: str = "parent",
        fail: bool = False,
    ) -> None:
        self.score_value = score
        self.evidence_mode = evidence_mode
        self.fail = fail

    @property
    def judge_id(self) -> str:
        return "static-follow-up-judge"

    def score(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> InterviewScorecard:
        if self.fail:
            raise RuntimeError("judge unavailable")

        parent = trace.turns[0]
        followup = trace.turns[1]
        evidence = []
        if self.evidence_mode == "parent":
            evidence = [
                EvidenceRef(
                    turn_id=parent.id,
                    quote="database latency",
                )
            ]
        elif self.evidence_mode == "followup":
            evidence = [
                EvidenceRef(
                    turn_id=followup.id,
                    quote="database timing",
                )
            ]

        return InterviewScorecard(
            judge_id=self.judge_id,
            dimensions=[
                DimensionScore(
                    dimension="follow_up_quality",
                    score=self.score_value,
                    max_score=10,
                    evidence=evidence,
                    rationale="Semantic follow-up assessment.",
                )
            ],
        )


def rubric() -> Rubric:
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


def trace(*, include_followup: bool = True) -> InterviewTrace:
    turns = [
        Turn(
            id="q1",
            speaker=Speaker.INTERVIEWER,
            text="Describe a production incident.",
            rubric_tags=["debugging"],
        ),
        Turn(
            id="a1",
            speaker=Speaker.CANDIDATE,
            text=(
                "I compared event-loop lag with database latency "
                "and found the database driver was blocking."
            ),
            parent_turn_id="q1",
        ),
    ]
    if include_followup:
        turns.append(
            Turn(
                id="q2",
                speaker=Speaker.INTERVIEWER,
                text=(
                    "What database timing evidence ruled out "
                    "the event loop as the primary cause?"
                ),
                parent_turn_id="a1",
                rubric_tags=["debugging"],
            )
        )
    return InterviewTrace(
        session_id="session-followup",
        role="Backend Engineer",
        turns=turns,
    )


def test_semantic_followup_passes_grounded_high_quality_followup():
    metric = SemanticFollowUpQualityMetric(
        StaticFollowUpJudge(score=9),
    )

    result = metric.evaluate(trace(), rubric())

    assert result.value == 9.0
    assert result.passed is True
    assert result.details["judge_id"] == "static-follow-up-judge"
    item = result.details["followups"][0]
    assert item["turn_id"] == "q2"
    assert item["parent_turn_id"] == "a1"
    assert item["grounded"] is True
    assert item["passed"] is True
    assert item["evidence_quotes"] == ["database latency"]


def test_semantic_followup_fails_low_quality_score():
    metric = SemanticFollowUpQualityMetric(
        StaticFollowUpJudge(score=3),
        minimum_score=6,
    )

    result = metric.evaluate(trace(), rubric())

    assert result.value == 3.0
    assert result.passed is False
    assert result.details["followups"][0]["grounded"] is True
    assert result.details["followups"][0]["passed"] is False


def test_semantic_followup_requires_evidence_from_parent_answer():
    metric = SemanticFollowUpQualityMetric(
        StaticFollowUpJudge(
            score=9,
            evidence_mode="followup",
        )
    )

    result = metric.evaluate(trace(), rubric())

    assert result.value == 9.0
    assert result.passed is False
    item = result.details["followups"][0]
    assert item["grounded"] is False
    assert item["passed"] is False
    assert "no literal evidence" in result.details["problems"][0]


def test_semantic_followup_records_provider_failure_without_crashing():
    metric = SemanticFollowUpQualityMetric(
        StaticFollowUpJudge(fail=True),
    )

    result = metric.evaluate(trace(), rubric())

    assert result.value == 0.0
    assert result.passed is False
    assert "judge unavailable" in result.details["problems"][0]


def test_semantic_followup_is_not_applicable_without_followups():
    metric = SemanticFollowUpQualityMetric(
        StaticFollowUpJudge(),
    )

    result = metric.evaluate(
        trace(include_followup=False),
        rubric(),
    )

    assert result.value is None
    assert result.passed is None
    assert result.details["applicable"] is False


def test_semantic_followup_validates_score_threshold():
    with pytest.raises(
        ValueError,
        match="minimum_score",
    ):
        SemanticFollowUpQualityMetric(
            StaticFollowUpJudge(),
            minimum_score=11,
        )
