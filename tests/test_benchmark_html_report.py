from voxrubric.benchmark_models import CaseResult, SuiteResult
from voxrubric.html_report import render_benchmark_html


def test_benchmark_html_report_renders_expectation_failures_safely():
    result = SuiteResult(
        suite_id="suite<script>",
        passed=False,
        cases=[
            CaseResult(
                case_id="grounded",
                passed=True,
            ),
            CaseResult(
                case_id="bad<case>",
                passed=False,
                failures=[
                    "rubric_coverage expected >= 1.0 <unsafe>",
                ],
            ),
        ],
    )

    html = render_benchmark_html(result)

    assert "suite&lt;script&gt;" in html
    assert "bad&lt;case&gt;" in html
    assert "&lt;unsafe&gt;" in html
    assert "<script>" not in html
    assert "Cases passing expectations" in html
    assert "Cases failing expectations" in html
    assert "known-bad behavior" in html
