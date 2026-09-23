from voxrubric.html_report import render_evaluation_html
from voxrubric.models import EvaluationReport, MetricResult


def test_evaluation_html_report_renders_statuses_and_escapes_content():
    report = EvaluationReport(
        session_id="session<script>",
        role="Backend <Engineer>",
        locale="en",
        metrics=[
            MetricResult(
                metric="rubric_coverage",
                value=1.0,
                unit="ratio",
                passed=True,
                summary="All <required> dimensions covered.",
                details={"covered": ["python"]},
            ),
            MetricResult(
                metric="barge_in_recovery",
                value=0.0,
                unit="ratio",
                passed=False,
                summary="Recovery failed.",
                details={"missing": ["response_ready"]},
            ),
            MetricResult(
                metric="judge_agreement",
                value=None,
                passed=None,
                summary="Not enough judges.",
                details={},
            ),
        ],
        metadata={"rubric_id": "backend"},
    )

    html = render_evaluation_html(report)

    assert "PASS" in html
    assert "FAIL" in html
    assert "N/A" in html
    assert "session&lt;script&gt;" in html
    assert "Backend &lt;Engineer&gt;" in html
    assert "All &lt;required&gt; dimensions covered." in html
    assert "<script>" not in html
    assert "does not compute a universal" in html
