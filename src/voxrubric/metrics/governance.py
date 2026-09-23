from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


class GovernanceAuditMetric(Metric):
    """Validate candidate-rights and integrity metadata exported by an agent."""

    name = "governance_audit"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        keys = {"transcript_revisions", "appeals", "integrity_signals"}
        if not any(key in trace.metadata for key in keys):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose governance audit metadata.",
                details={"applicable": False},
            )

        known_turns = {turn.id: turn for turn in trace.turns}
        revisions = trace.metadata.get("transcript_revisions", [])
        appeals = trace.metadata.get("appeals", [])
        signals = trace.metadata.get("integrity_signals", [])
        checks = 0
        passed_checks = 0
        problems: list[str] = []

        latest_revision_by_turn: dict[str, dict] = {}
        for index, revision in enumerate(revisions if isinstance(revisions, list) else []):
            checks += 1
            if not isinstance(revision, dict):
                problems.append(f"revision[{index}] is not an object")
                continue
            turn_id = revision.get("turn_id")
            if turn_id not in known_turns:
                problems.append(f"revision[{index}] references unknown turn")
                continue
            if known_turns[turn_id].speaker.value != "candidate":
                problems.append(f"revision[{index}] modifies a non-candidate turn")
                continue
            if not isinstance(revision.get("original_text"), str):
                problems.append(f"revision[{index}] is missing original_text")
                continue
            if not isinstance(revision.get("corrected_text"), str):
                problems.append(f"revision[{index}] is missing corrected_text")
                continue
            latest_revision_by_turn[turn_id] = revision
            passed_checks += 1

        for turn_id, revision in latest_revision_by_turn.items():
            checks += 1
            if known_turns[turn_id].text != revision.get("corrected_text"):
                problems.append(f"latest revision for {turn_id} does not match trace text")
            else:
                passed_checks += 1

        for index, appeal in enumerate(appeals if isinstance(appeals, list) else []):
            checks += 1
            if not isinstance(appeal, dict):
                problems.append(f"appeal[{index}] is not an object")
                continue
            unknown = [
                turn_id for turn_id in appeal.get("turn_ids", [])
                if turn_id not in known_turns
            ]
            if unknown:
                problems.append(f"appeal[{index}] references unknown turns: {unknown}")
                continue
            if appeal.get("status") not in {"pending", "reviewed"}:
                problems.append(f"appeal[{index}] has invalid status")
                continue
            passed_checks += 1

        for index, signal in enumerate(signals if isinstance(signals, list) else []):
            checks += 1
            if not isinstance(signal, dict):
                problems.append(f"integrity_signal[{index}] is not an object")
                continue
            if signal.get("requires_human_review") is not True:
                problems.append(
                    f"integrity_signal[{index}] is not explicitly human-review-only"
                )
                continue
            confidence = signal.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                problems.append(f"integrity_signal[{index}] has invalid confidence")
                continue
            passed_checks += 1

        if checks == 0:
            return MetricResult(
                metric=self.name,
                value=1.0,
                unit="valid_governance_check_ratio",
                passed=True,
                summary="Governance metadata is present with no revisions, appeals, or integrity flags.",
                details={"checks": 0, "problems": []},
            )

        ratio = passed_checks / checks
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_governance_check_ratio",
            passed=not problems,
            summary=f"{passed_checks}/{checks} governance invariants hold.",
            details={"checks": checks, "problems": problems},
        )
