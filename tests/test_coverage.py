from voxrubric.metrics import RubricCoverageMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_weighted_coverage_and_missing_required():
    rubric = Rubric(id="r", title="r", dimensions=[
        RubricDimension(id="a", description="A", weight=2),
        RubricDimension(id="b", description="B", weight=1),
    ])
    trace = InterviewTrace(session_id="s", role="x", turns=[Turn(id="q", speaker=Speaker.INTERVIEWER, text="?", rubric_tags=["a"])])
    result = RubricCoverageMetric().evaluate(trace, rubric)
    assert result.value == 0.6667
    assert result.details["missing_required"] == ["b"]
