from voxrubric.judging import JudgeEnsemble
from voxrubric.models import (
    DimensionScore,
    InterviewScorecard,
    InterviewTrace,
    Rubric,
    RubricDimension,
)


class FakeJudge:
    def __init__(self, judge_id: str, score: float):
        self._judge_id = judge_id
        self._score = score

    @property
    def judge_id(self):
        return self._judge_id

    def score(self, trace, rubric):
        return InterviewScorecard(
            judge_id=self._judge_id,
            dimensions=[DimensionScore(dimension="x", score=self._score)],
        )


def test_ensemble_keeps_independent_scorecards():
    trace = InterviewTrace(session_id="s", role="role", turns=[])
    rubric = Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])
    result = JudgeEnsemble([FakeJudge("a", 8), FakeJudge("b", 7)]).score(trace, rubric)
    assert [s.judge_id for s in result.scorecards] == ["a", "b"]
    assert trace.scorecards == []
