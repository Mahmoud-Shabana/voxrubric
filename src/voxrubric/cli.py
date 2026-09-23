from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .arena_config import run_scripted_arena
from .benchmark import run_suite
from .html_report import (
    write_arena_html,
    write_benchmark_html,
    write_evaluation_html,
)
from .config import load_rubric, load_trace
from .datasets import load_jsonl
from .report import to_markdown
from .review_bundle import audit_review_bundle, load_review_bundle
from .runner import default_evaluator
from .trace_diff import compare_traces

app = typer.Typer(help="Evidence-grounded evaluation for AI interview and voice agents.", no_args_is_help=True)
console = Console()


@app.command("eval")
def evaluate(
    trace: Path = typer.Option(..., exists=True, readable=True, help="Interview trace JSON/YAML."),
    rubric: Path = typer.Option(..., exists=True, readable=True, help="Rubric JSON/YAML."),
    output: Path | None = typer.Option(None, "--out", help="Write report as .json, .md, or .html."),
    latency_budget_ms: int = typer.Option(2000, min=1),
) -> None:
    report = default_evaluator(latency_budget_ms=latency_budget_ms).run(load_trace(trace), load_rubric(rubric))
    table = Table(title=f"VoxRubric — {report.session_id}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Status")
    table.add_column("Summary")
    for metric in report.metrics:
        value = "—" if metric.value is None else f"{metric.value:g} {metric.unit or ''}".strip()
        status = "—" if metric.passed is None else ("PASS" if metric.passed else "FAIL")
        table.add_row(metric.metric, value, status, metric.summary)
    console.print(table)

    if output:
        if output.suffix.lower() == ".md":
            output.write_text(to_markdown(report), encoding="utf-8")
        elif output.suffix.lower() == ".json":
            output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        elif output.suffix.lower() == ".html":
            write_evaluation_html(report, output)
        else:
            raise typer.BadParameter("--out must end in .json, .md, or .html")
        console.print(f"Wrote {output}")


@app.command("benchmark")
def benchmark(
    suite: Path = typer.Argument(..., exists=True, readable=True, help="Benchmark suite YAML."),
    latency_budget_ms: int = typer.Option(2000, min=1),
    output: Path | None = typer.Option(None, "--out", help="Optional JSON result path."),
    html_output: Path | None = typer.Option(
        None,
        "--html-out",
        help="Optional self-contained HTML benchmark report path.",
    ),
) -> None:
    result = run_suite(suite, latency_budget_ms=latency_budget_ms)
    table = Table(title=f"VoxRubric benchmark — {result.suite_id}")
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Failures")
    for case in result.cases:
        table.add_row(case.case_id, "PASS" if case.passed else "FAIL", "\n".join(case.failures) or "—")
    console.print(table)
    console.print(f"Suite status: {'PASS' if result.passed else 'FAIL'}")
    if output:
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"Wrote {output}")
    if html_output:
        write_benchmark_html(
            result,
            html_output,
        )
        console.print(f"Wrote {html_output}")
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("arena")
def arena(
    config: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Arena YAML containing a scenario and scripted baseline agents.",
    ),
    output: Path | None = typer.Option(
        None,
        "--out",
        help="Optional JSON result path.",
    ),
    html_output: Path | None = typer.Option(
        None,
        "--html-out",
        help="Optional self-contained HTML Arena report path.",
    ),
) -> None:
    result = asyncio.run(run_scripted_arena(config))
    table = Table(title=f"VoxRubric Arena — {result.scenario_id}")
    table.add_column("Agent")
    table.add_column("Runs", justify="right")
    table.add_column("Completion", justify="right")
    table.add_column("Candidate turns", justify="right")
    table.add_column("Interviewer turns", justify="right")
    table.add_column("Path stability", justify="right")

    for item in result.aggregates:
        stability = (
            "—"
            if item.question_path_stability is None
            else f"{item.question_path_stability:.3f}"
        )
        table.add_row(
            item.agent_id,
            str(item.runs),
            f"{item.completion_rate:.3f}",
            f"{item.mean_candidate_turns:.2f}",
            f"{item.mean_interviewer_turns:.2f}",
            stability,
        )
    console.print(table)
    console.print(
        "Arena reports descriptive measurements only; it does not select a winner."
    )

    if output:
        output.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        console.print(f"Wrote {output}")

    if html_output:
        write_arena_html(
            result,
            html_output,
        )
        console.print(f"Wrote {html_output}")


@app.command("diff")
def diff(
    left: Path = typer.Option(
        ...,
        "--left",
        exists=True,
        readable=True,
        help="Baseline interview trace JSON/YAML.",
    ),
    right: Path = typer.Option(
        ...,
        "--right",
        exists=True,
        readable=True,
        help="Comparison interview trace JSON/YAML.",
    ),
    rubric: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Rubric JSON/YAML.",
    ),
    output: Path | None = typer.Option(
        None,
        "--out",
        help="Optional JSON diff result path.",
    ),
    latency_budget_ms: int = typer.Option(
        2000,
        min=1,
    ),
) -> None:
    evaluator = default_evaluator(
        latency_budget_ms=latency_budget_ms
    )
    result = compare_traces(
        load_trace(left),
        load_trace(right),
        load_rubric(rubric),
        evaluator=evaluator,
    )

    console.print(
        f"Question-path similarity: "
        f"{result.question_path_similarity:.3f}"
    )
    console.print(
        f"Follow-up action agreement: "
        f"{result.followup_action_agreement:.3f}"
    )

    table = Table(
        title=(
            f"VoxRubric diff — "
            f"{result.left_session_id} → {result.right_session_id}"
        )
    )
    table.add_column("Metric")
    table.add_column("Left", justify="right")
    table.add_column("Right", justify="right")
    table.add_column("Δ", justify="right")
    table.add_column("Status change")
    for item in result.metric_deltas:
        left_value = (
            "—"
            if item.left_value is None
            else f"{item.left_value:g}"
        )
        right_value = (
            "—"
            if item.right_value is None
            else f"{item.right_value:g}"
        )
        delta = (
            "—"
            if item.delta is None
            else f"{item.delta:+g}"
        )
        status_change = (
            f"{item.left_passed} → {item.right_passed}"
        )
        table.add_row(
            item.metric,
            left_value,
            right_value,
            delta,
            status_change,
        )
    console.print(table)
    console.print(
        "Diff is descriptive; it does not select a better interview agent."
    )

    if output:
        output.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        console.print(f"Wrote {output}")


@app.command("review-bundle")
def review_bundle(
    bundle: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Nora review bundle JSON.",
    ),
    rubric: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Rubric JSON/YAML used to evaluate the embedded trace.",
    ),
    output: Path | None = typer.Option(
        None,
        "--out",
        help="Optional combined JSON audit result path.",
    ),
    latency_budget_ms: int = typer.Option(
        2000,
        min=1,
    ),
) -> None:
    result = audit_review_bundle(
        load_review_bundle(bundle),
        load_rubric(rubric),
        evaluator=default_evaluator(
            latency_budget_ms=latency_budget_ms
        ),
    )

    integrity = result.bundle_integrity
    status = (
        "PASS"
        if integrity.passed is True
        else "FAIL"
        if integrity.passed is False
        else "—"
    )
    console.print(
        f"Review bundle integrity: {status} — {integrity.summary}"
    )

    table = Table(
        title=f"Embedded trace evaluation — {result.session_id}"
    )
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Status")
    table.add_column("Summary")
    for metric in result.evaluation.metrics:
        value = (
            "—"
            if metric.value is None
            else f"{metric.value:g} {metric.unit or ''}".strip()
        )
        metric_status = (
            "—"
            if metric.passed is None
            else "PASS"
            if metric.passed
            else "FAIL"
        )
        table.add_row(
            metric.metric,
            value,
            metric_status,
            metric.summary,
        )
    console.print(table)

    if output:
        output.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        console.print(f"Wrote {output}")

    if integrity.passed is False:
        raise typer.Exit(code=1)


@app.command("validate-dataset")
def validate_dataset(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    traces = load_jsonl(path)
    turns = sum(len(t.turns) for t in traces)
    console.print(f"Valid: {len(traces)} sessions, {turns} turns")


if __name__ == "__main__":
    app()
