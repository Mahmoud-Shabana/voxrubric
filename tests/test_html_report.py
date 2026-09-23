from pathlib import Path

from voxrubric.arena import (
    AgentArenaAggregate,
    ArenaResult,
    ArenaRun,
    MetricAggregate,
)
from voxrubric.html_report import render_arena_html, write_arena_html
from voxrubric.models import EvaluationReport, InterviewTrace


def fixture():
    aggregate = AgentArenaAggregate(
        agent_id="<script>alert('x')</script>",
        runs=2,
        completion_rate=1.0,
        mean_candidate_turns=3.0,
        mean_interviewer_turns=4.0,
        question_path_stability=0.75,
        metrics=[
            MetricAggregate(
                metric="rubric_coverage",
                samples=2,
                mean=0.9,
                minimum=0.8,
                maximum=1.0,
            )
        ],
    )
    run = ArenaRun(
        agent_id=aggregate.agent_id,
        run_index=0,
        completed=True,
        trace=InterviewTrace(
            session_id="s",
            role="System fixture",
            turns=[],
        ),
        report=EvaluationReport(
            session_id="s",
            role="System fixture",
            metrics=[],
        ),
    )
    return ArenaResult(
        scenario_id="html-report-fixture",
        repetitions=2,
        runs=[run],
        aggregates=[aggregate],
    )


def test_html_report_is_self_contained_and_escapes_agent_ids():
    html = render_arena_html(fixture())

    assert "<style>" in html
    assert "VoxRubric Arena Report" in html
    assert "rubric_coverage" in html
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "does not select a winner" in html


def test_html_report_can_be_written(tmp_path: Path):
    output = tmp_path / "arena.html"
    returned = write_arena_html(
        fixture(),
        output,
    )

    assert returned == output
    assert output.exists()
    assert "html-report-fixture" in output.read_text(
        encoding="utf-8"
    )
