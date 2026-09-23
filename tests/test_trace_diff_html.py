from voxrubric.html_report import render_trace_diff_html
from voxrubric.trace_diff import (
    CompetencyEvidenceDelta,
    MetricDelta,
    QuestionPathStep,
    TraceDiffReport,
)


def test_trace_diff_html_renders_and_escapes_without_ranking():
    report = TraceDiffReport(
        left_session_id="left<script>",
        right_session_id="right",
        question_path_similarity=0.5,
        followup_action_agreement=0.75,
        interviewer_turn_delta=1,
        candidate_turn_delta=0,
        path_steps=[
            QuestionPathStep(
                index=0,
                left_turn_id="q<1>",
                right_turn_id="q2",
                left_tags=["python"],
                right_tags=["debugging"],
                tag_similarity=0.0,
                left_followup=False,
                right_followup=True,
                followup_agreement=False,
            )
        ],
        metric_deltas=[
            MetricDelta(
                metric="rubric_coverage",
                left_value=0.5,
                right_value=1.0,
                delta=0.5,
                left_passed=False,
                right_passed=True,
            )
        ],
        evidence_deltas=[
            CompetencyEvidenceDelta(
                competency_id="debugging",
                left_state="claimed",
                right_state="demonstrated",
                left_confidence=None,
                right_confidence=0.9,
                changed=True,
            )
        ],
        metadata={"rubric_id": "backend"},
    )

    html = render_trace_diff_html(report)

    assert "left&lt;script&gt;" in html
    assert "q&lt;1&gt;" in html
    assert "<script>" not in html
    assert "Question-path similarity" in html
    assert "rubric_coverage" in html
    assert "debugging" in html
    assert "does not rank" in html
    assert "winner" in html
