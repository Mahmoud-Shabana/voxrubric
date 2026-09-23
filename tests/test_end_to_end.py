from pathlib import Path

from voxrubric.config import load_rubric, load_trace
from voxrubric.report import to_markdown
from voxrubric.runner import default_evaluator

ROOT = Path(__file__).parents[1]


def test_example_end_to_end():
    trace = load_trace(ROOT / "examples/session.json")
    rubric = load_rubric(ROOT / "examples/python_engineer.yaml")
    report = default_evaluator().run(trace, rubric)
    names = {m.metric for m in report.metrics}
    assert "evidence_grounding" in names
    assert "rubric_coverage" in names
    assert "judge_agreement" in names
    md = to_markdown(report)
    assert "VoxRubric report" in md
