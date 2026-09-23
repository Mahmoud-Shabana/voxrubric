from __future__ import annotations

from .models import EvaluationReport


def to_markdown(report: EvaluationReport) -> str:
    lines = [
        f"# VoxRubric report — `{report.session_id}`",
        "",
        f"**Role:** {report.role}  ",
        f"**Locale:** {report.locale}  ",
        f"**Rubric:** {report.metadata.get('rubric_id', 'unknown')}",
        "",
        "| Metric | Value | Status | Summary |",
        "|---|---:|:---:|---|",
    ]
    for metric in report.metrics:
        value = "—" if metric.value is None else f"{metric.value:g} {metric.unit or ''}".strip()
        status = "—" if metric.passed is None else ("PASS" if metric.passed else "FAIL")
        lines.append(f"| `{metric.metric}` | {value} | {status} | {metric.summary} |")
    lines.extend(["", "## Machine-readable details", "", "```json", report.model_dump_json(indent=2), "```", ""])
    return "\n".join(lines)
