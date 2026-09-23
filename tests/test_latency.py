from voxrubric.metrics.latency import LatencyMetric, percentile
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_percentile_interpolates():
    assert percentile([100, 200, 300, 400], 0.5) == 250


def test_latency_budget():
    trace = InterviewTrace(session_id="s", role="x", turns=[
        Turn(id="q1", speaker=Speaker.INTERVIEWER, text="1", response_latency_ms=500),
        Turn(id="q2", speaker=Speaker.INTERVIEWER, text="2", response_latency_ms=800),
    ])
    rubric = Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])
    result = LatencyMetric(p95_budget_ms=1000).evaluate(trace, rubric)
    assert result.passed is True
    assert result.details["p95_ms"] == 785.0
