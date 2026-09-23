from voxrubric.metrics import EvidenceGroundingMetric
from voxrubric.models import (
    DimensionScore, EvidenceRef, InterviewScorecard, InterviewTrace,
    Rubric, RubricDimension, Speaker, Turn,
)


def rubric():
    return Rubric(id="r", title="r", dimensions=[RubricDimension(id="python", description="Python")])


def test_grounded_quote_passes():
    trace = InterviewTrace(
        session_id="s", role="dev", turns=[Turn(id="a", speaker=Speaker.CANDIDATE, text="I used FastAPI and asyncio.")],
        scorecards=[InterviewScorecard(judge_id="j", dimensions=[DimensionScore(dimension="python", score=8, evidence=[EvidenceRef(turn_id="a", quote="FastAPI and asyncio")])])],
    )
    result = EvidenceGroundingMetric().evaluate(trace, rubric())
    assert result.value == 1.0
    assert result.passed is True


def test_hallucinated_quote_fails():
    trace = InterviewTrace(
        session_id="s", role="dev", turns=[Turn(id="a", speaker=Speaker.CANDIDATE, text="I used Flask.")],
        scorecards=[InterviewScorecard(judge_id="j", dimensions=[DimensionScore(dimension="python", score=8, evidence=[EvidenceRef(turn_id="a", quote="I used FastAPI")])])],
    )
    result = EvidenceGroundingMetric().evaluate(trace, rubric())
    assert result.value == 0.0
    assert result.passed is False
    assert result.details["quote_mismatches"]


def test_no_scorecards_is_not_applicable():
    trace = InterviewTrace(session_id="s", role="dev", turns=[Turn(id="a", speaker=Speaker.CANDIDATE, text="answer")])
    result = EvidenceGroundingMetric().evaluate(trace, rubric())
    assert result.value is None
    assert result.passed is None
    assert result.details["scorecards"] == 0
