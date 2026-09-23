from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    EvaluationReport,
    InterviewTrace,
    MetricResult,
    Rubric,
    StrictModel,
)
from .runner import Evaluator, default_evaluator


class ReviewBundleAuditResult(StrictModel):
    schema_version: str = "1.0"
    session_id: str
    bundle_integrity: MetricResult
    evaluation: EvaluationReport


def load_review_bundle(
    path: str | Path,
) -> dict[str, Any]:
    payload = json.loads(
        Path(path).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise ValueError("review bundle root must be a JSON object")
    return payload


def audit_review_bundle(
    payload: dict[str, Any],
    rubric: Rubric,
    *,
    evaluator: Evaluator | None = None,
) -> ReviewBundleAuditResult:
    report = payload.get("report")
    trace_payload = payload.get("trace")
    audit = payload.get("audit")

    if not isinstance(report, dict):
        raise ValueError("review bundle is missing report object")
    if not isinstance(trace_payload, dict):
        raise ValueError("review bundle is missing trace object")
    if not isinstance(audit, dict):
        raise ValueError("review bundle is missing audit object")

    trace = InterviewTrace.model_validate(trace_payload)
    checks = 0
    valid = 0
    problems: list[str] = []

    def check(condition: bool, message: str) -> None:
        nonlocal checks, valid
        checks += 1
        if condition:
            valid += 1
        else:
            problems.append(message)

    check(
        report.get("session_id") == trace.session_id,
        "report.session_id does not match trace.session_id",
    )
    check(
        report.get("role") == trace.role,
        "report.role does not match trace.role",
    )
    check(
        report.get("job_id") == trace.metadata.get("job_id"),
        "report.job_id does not match trace metadata job_id",
    )
    check(
        report.get("status") == trace.metadata.get("status"),
        "report.status does not match trace metadata status",
    )

    revisions = trace.metadata.get("transcript_revisions", [])
    revisions = revisions if isinstance(revisions, list) else []
    check(
        report.get("transcript_revisions") == len(revisions),
        "report transcript revision count does not match trace",
    )

    appeals = trace.metadata.get("appeals", [])
    appeals = appeals if isinstance(appeals, list) else []
    pending_appeals = sum(
        isinstance(item, dict)
        and item.get("status") == "pending"
        for item in appeals
    )
    check(
        report.get("pending_appeals") == pending_appeals,
        "report pending appeal count does not match trace",
    )

    integrity = trace.metadata.get("integrity_signals", [])
    integrity = integrity if isinstance(integrity, list) else []
    pending_integrity = sum(
        isinstance(item, dict)
        and item.get("review_status", "pending") == "pending"
        for item in integrity
    )
    check(
        report.get("integrity_signals") == pending_integrity,
        "report pending integrity count does not match trace",
    )

    trace_audit = trace.metadata.get("audit_chain", {})
    trace_audit = trace_audit if isinstance(trace_audit, dict) else {}
    check(
        audit.get("verified") == trace_audit.get("verified"),
        "bundle audit verified flag does not match trace audit metadata",
    )
    check(
        audit.get("head_hash") == trace_audit.get("head_hash"),
        "bundle audit head hash does not match trace audit metadata",
    )
    check(
        audit.get("event_count") == trace_audit.get("event_count"),
        "bundle audit event count does not match trace audit metadata",
    )
    check(
        audit.get("hash_version") == trace_audit.get("hash_version"),
        "bundle audit hash version does not match trace audit metadata",
    )

    reasons = report.get("reasons", [])
    reasons = reasons if isinstance(reasons, list) else []
    reason_codes = {
        item.get("code")
        for item in reasons
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
    }
    attention_reason = any(
        isinstance(item, dict)
        and item.get("severity") in {"attention", "high"}
        for item in reasons
    )
    check(
        bool(report.get("requires_human_review")) == attention_reason,
        "requires_human_review does not match active review reasons",
    )

    judge_runs = report.get("evidence_judge_runs", [])
    judge_runs = judge_runs if isinstance(judge_runs, list) else []
    stale_runs = [
        run
        for run in judge_runs
        if isinstance(run, dict)
        and run.get("stale") is True
    ]
    failed_runs = [
        run
        for run in judge_runs
        if isinstance(run, dict)
        and run.get("failed") is True
    ]
    if stale_runs:
        check(
            "evidence_reevaluation_needed" in reason_codes,
            "stale evidence judge run is missing review reason",
        )
    if failed_runs:
        check(
            "evidence_judge_failed" in reason_codes,
            "failed evidence judge run is missing review reason",
        )

    ratio = valid / checks if checks else 1.0
    bundle_integrity = MetricResult(
        metric="review_bundle_integrity",
        value=round(ratio, 4),
        unit="valid_bundle_check_ratio",
        passed=not problems,
        summary=f"{valid}/{checks} review bundle integrity checks hold.",
        details={
            "checks": checks,
            "problems": problems,
            "stale_judge_runs": len(stale_runs),
            "failed_judge_runs": len(failed_runs),
        },
    )

    evaluation = (evaluator or default_evaluator()).run(
        trace,
        rubric,
    )
    return ReviewBundleAuditResult(
        session_id=trace.session_id,
        bundle_integrity=bundle_integrity,
        evaluation=evaluation,
    )
