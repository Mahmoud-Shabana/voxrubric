from __future__ import annotations

from html import escape
from pathlib import Path

from .arena import AgentArenaAggregate, ArenaResult, ArenaRun
from .models import EvaluationReport


_CSS = """
:root {
  color-scheme: dark;
  --bg: #0b1020;
  --panel: #121a2e;
  --panel-2: #17213a;
  --text: #ecf2ff;
  --muted: #94a3bd;
  --line: #26334f;
  --accent: #7dd3fc;
  --good: #86efac;
  --warn: #fde68a;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 15% -10%, #1e3a5f 0, transparent 34rem),
    var(--bg);
  color: var(--text);
  font: 14px/1.55 Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
}
main { max-width: 1180px; margin: 0 auto; padding: 46px 22px 80px; }
.hero { margin-bottom: 32px; }
.eyebrow {
  color: var(--accent);
  letter-spacing: .14em;
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 700;
}
h1 { margin: 8px 0 8px; font-size: clamp(32px, 5vw, 58px); line-height: 1.05; }
h2 { margin: 0 0 16px; font-size: 22px; }
h3 { margin: 0 0 6px; font-size: 17px; }
p { color: var(--muted); }
.note {
  border: 1px solid var(--line);
  background: rgba(125, 211, 252, .06);
  border-radius: 14px;
  padding: 12px 14px;
  color: #c7d8ef;
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
.card {
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,.01)), var(--panel);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 18px 50px rgba(0,0,0,.18);
}
.kpis { display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px; margin-top: 16px; }
.kpi { background: var(--panel-2); border: 1px solid var(--line); border-radius: 12px; padding: 10px; }
.kpi span { display: block; color: var(--muted); font-size: 11px; }
.kpi strong { font-size: 20px; }
section { margin-top: 36px; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 16px; }
table { width: 100%; border-collapse: collapse; min-width: 720px; background: var(--panel); }
th, td { text-align: left; padding: 11px 13px; border-bottom: 1px solid var(--line); }
th { color: #cbd8ed; background: #111a2d; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; }
td { color: #dbe7fa; }
tr:last-child td { border-bottom: 0; }
.muted { color: var(--muted); }
.ok { color: var(--good); }
.bar {
  height: 7px;
  background: #26334f;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 7px;
}
.bar > i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #86efac);
}
.code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
footer { margin-top: 56px; color: var(--muted); font-size: 12px; }
"""


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _num(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def _bar(value: float | None) -> str:
    if value is None:
        return ""
    bounded = max(0.0, min(1.0, value))
    width = bounded * 100
    return f'<div class="bar"><i style="width:{width:.1f}%"></i></div>'


def _agent_card(item: AgentArenaAggregate) -> str:
    return f"""
    <article class="card">
      <div class="eyebrow">Agent</div>
      <h3>{escape(item.agent_id)}</h3>
      <div class="kpis">
        <div class="kpi">
          <span>Completion rate</span>
          <strong>{_pct(item.completion_rate)}</strong>
          {_bar(item.completion_rate)}
        </div>
        <div class="kpi">
          <span>Path stability</span>
          <strong>{_num(item.question_path_stability)}</strong>
          {_bar(item.question_path_stability)}
        </div>
        <div class="kpi">
          <span>Candidate turns</span>
          <strong>{item.mean_candidate_turns:.2f}</strong>
        </div>
        <div class="kpi">
          <span>Interviewer turns</span>
          <strong>{item.mean_interviewer_turns:.2f}</strong>
        </div>
      </div>
    </article>
    """


def _metric_rows(item: AgentArenaAggregate) -> str:
    rows: list[str] = []
    for metric in item.metrics:
        rows.append(
            "<tr>"
            f"<td class='code'>{escape(metric.metric)}</td>"
            f"<td>{metric.samples}</td>"
            f"<td>{metric.mean:.4f}</td>"
            f"<td>{metric.minimum:.4f}</td>"
            f"<td>{metric.maximum:.4f}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(
            "<tr><td colspan='5' class='muted'>No numeric metric samples.</td></tr>"
        )
    return "".join(rows)


def _run_rows(runs: list[ArenaRun]) -> str:
    rows: list[str] = []
    for run in runs:
        candidate_turns = sum(
            turn.speaker.value == "candidate"
            for turn in run.trace.turns
        )
        interviewer_turns = sum(
            turn.speaker.value == "interviewer"
            for turn in run.trace.turns
        )
        failed_metrics = [
            metric.metric
            for metric in run.report.metrics
            if metric.passed is False
        ]
        rows.append(
            "<tr>"
            f"<td>{escape(run.agent_id)}</td>"
            f"<td>{run.run_index}</td>"
            f"<td class='{'ok' if run.completed else ''}'>{'yes' if run.completed else 'no'}</td>"
            f"<td>{candidate_turns}</td>"
            f"<td>{interviewer_turns}</td>"
            f"<td class='code'>{escape(', '.join(failed_metrics) or '—')}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_arena_html(result: ArenaResult) -> str:
    cards = "".join(_agent_card(item) for item in result.aggregates)

    metric_sections: list[str] = []
    for item in result.aggregates:
        metric_sections.append(
            f"""
            <div class="card">
              <h3>{escape(item.agent_id)}</h3>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Samples</th>
                      <th>Mean</th>
                      <th>Min</th>
                      <th>Max</th>
                    </tr>
                  </thead>
                  <tbody>{_metric_rows(item)}</tbody>
                </table>
              </div>
            </div>
            """
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VoxRubric Arena — {escape(result.scenario_id)}</title>
  <style>{_CSS}</style>
</head>
<body>
<main>
  <header class="hero">
    <div class="eyebrow">VoxRubric Arena Report</div>
    <h1>{escape(result.scenario_id)}</h1>
    <p>
      {result.repetitions} repeated run(s) per configured agent.
      Every agent is evaluated on the same controlled scenario.
    </p>
    <div class="note">
      This report is descriptive. VoxRubric does not select a winner,
      produce an overall hiring verdict, or collapse unrelated metrics
      into one universal quality score.
    </div>
  </header>

  <section>
    <h2>Agent overview</h2>
    <div class="grid">{cards}</div>
  </section>

  <section>
    <h2>Metric distributions</h2>
    <div class="grid">{''.join(metric_sections)}</div>
  </section>

  <section>
    <h2>Run-by-run audit</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th>Run</th>
            <th>Completed</th>
            <th>Candidate turns</th>
            <th>Interviewer turns</th>
            <th>Failed system metrics</th>
          </tr>
        </thead>
        <tbody>{_run_rows(result.runs)}</tbody>
      </table>
    </div>
  </section>

  <footer>
    Generated by VoxRubric · scenario {escape(result.scenario_id)}
  </footer>
</main>
</body>
</html>
"""


def write_arena_html(
    result: ArenaResult,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.write_text(
        render_arena_html(result),
        encoding="utf-8",
    )
    return output



def _metric_status_class(passed: bool | None) -> str:
    if passed is True:
        return "metric-pass"
    if passed is False:
        return "metric-fail"
    return "metric-na"


def _metric_status_label(passed: bool | None) -> str:
    if passed is True:
        return "PASS"
    if passed is False:
        return "FAIL"
    return "N/A"


def render_evaluation_html(report: EvaluationReport) -> str:
    metric_cards: list[str] = []
    for metric in report.metrics:
        value = "—"
        if metric.value is not None:
            value = escape(
                f"{metric.value:g} {metric.unit or ''}".strip()
            )
        details = escape(
            __import__("json").dumps(
                metric.details,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        metric_cards.append(
            f"""
            <article class="card metric-card">
              <div class="metric-head">
                <div>
                  <div class="eyebrow">Metric</div>
                  <h3 class="code">{escape(metric.metric)}</h3>
                </div>
                <span class="metric-status {_metric_status_class(metric.passed)}">
                  {_metric_status_label(metric.passed)}
                </span>
              </div>
              <div class="metric-value">{value}</div>
              <p>{escape(metric.summary)}</p>
              <details>
                <summary>Machine-readable details</summary>
                <pre>{details}</pre>
              </details>
            </article>
            """
        )

    pass_count = sum(metric.passed is True for metric in report.metrics)
    fail_count = sum(metric.passed is False for metric in report.metrics)
    na_count = sum(metric.passed is None for metric in report.metrics)

    extra_css = """
.metric-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}
.metric-status{font-size:10px;font-weight:800;letter-spacing:.08em;border:1px solid var(--line);border-radius:999px;padding:5px 8px}
.metric-pass{color:var(--good);border-color:#28543a}.metric-fail{color:#fda4af;border-color:#5e2f39}.metric-na{color:var(--muted)}
.metric-value{font-size:30px;font-weight:800;margin:14px 0 4px}.metric-card details{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
.metric-card summary{cursor:pointer;color:#cbd8ed;font-size:11px}.metric-card pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0a0f1d;border:1px solid var(--line);border-radius:10px;padding:10px;color:#b9c8dd;font-size:11px}
.summary-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;max-width:520px;margin-top:20px}
.summary-row>div{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--panel)}
.summary-row span{display:block;color:var(--muted);font-size:10px}.summary-row strong{font-size:24px}
"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VoxRubric Evaluation — {escape(report.session_id)}</title>
  <style>{_CSS}{extra_css}</style>
</head>
<body>
<main>
  <header class="hero">
    <div class="eyebrow">VoxRubric Evaluation Report</div>
    <h1>{escape(report.session_id)}</h1>
    <p>
      Role: <strong>{escape(report.role)}</strong> ·
      Locale: <strong>{escape(report.locale)}</strong> ·
      Rubric: <strong>{escape(str(report.metadata.get("rubric_id", "unknown")))}</strong>
    </p>
    <div class="note">
      Metrics remain independent. This report does not compute a universal
      interview quality score or make a hiring decision.
    </div>
    <div class="summary-row">
      <div><span>Passed metrics</span><strong>{pass_count}</strong></div>
      <div><span>Failed metrics</span><strong>{fail_count}</strong></div>
      <div><span>Not applicable</span><strong>{na_count}</strong></div>
    </div>
  </header>

  <section>
    <h2>Metric results</h2>
    <div class="grid">{''.join(metric_cards)}</div>
  </section>

  <footer>
    Generated by VoxRubric · session {escape(report.session_id)}
  </footer>
</main>
</body>
</html>
"""


def write_evaluation_html(
    report: EvaluationReport,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.write_text(
        render_evaluation_html(report),
        encoding="utf-8",
    )
    return output
