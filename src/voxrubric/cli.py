from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .benchmark import run_suite
from .config import load_rubric, load_trace
from .datasets import load_jsonl
from .report import to_markdown
from .runner import default_evaluator

app = typer.Typer(help="Evidence-grounded evaluation for AI interview and voice agents.", no_args_is_help=True)
console = Console()


@app.command("eval")
def evaluate(
    trace: Path = typer.Option(..., exists=True, readable=True, help="Interview trace JSON/YAML."),
    rubric: Path = typer.Option(..., exists=True, readable=True, help="Rubric JSON/YAML."),
    output: Path | None = typer.Option(None, "--out", help="Write report as .json or .md."),
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
        else:
            raise typer.BadParameter("--out must end in .json or .md")
        console.print(f"Wrote {output}")


@app.command("benchmark")
def benchmark(
    suite: Path = typer.Argument(..., exists=True, readable=True, help="Benchmark suite YAML."),
    latency_budget_ms: int = typer.Option(2000, min=1),
    output: Path | None = typer.Option(None, "--out", help="Optional JSON result path."),
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
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("validate-dataset")
def validate_dataset(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    traces = load_jsonl(path)
    turns = sum(len(t.turns) for t in traces)
    console.print(f"Valid: {len(traces)} sessions, {turns} turns")


if __name__ == "__main__":
    app()
