from voxrubric.metrics import CodeSwitchMetric
from voxrubric.models import InterviewTrace, Rubric, RubricDimension, Speaker, Turn


def test_arabic_english_code_switch():
    trace = InterviewTrace(session_id="s", role="x", turns=[
        Turn(id="a", speaker=Speaker.CANDIDATE, text="اشتغلت على FastAPI service"),
        Turn(id="b", speaker=Speaker.CANDIDATE, text="إجابة عربية فقط"),
    ])
    rubric = Rubric(id="r", title="r", dimensions=[RubricDimension(id="x", description="x")])
    result = CodeSwitchMetric().evaluate(trace, rubric)
    assert result.value == 0.5
    assert result.details["mixed_turn_ids"] == ["a"]
