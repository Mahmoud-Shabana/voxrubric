from __future__ import annotations

import re

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


_ALLOWED = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$"
)


class AuditCorrelationIntegrityMetric(Metric):
    """Validate correlation metadata without requiring it on legacy traces."""

    name = "audit_correlation_integrity"

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        events = trace.metadata.get(
            "audit_events"
        )
        if not isinstance(events, list):
            return MetricResult(
                metric=self.name,
                summary=(
                    "Trace does not expose audit events "
                    "for correlation analysis."
                ),
                details={"applicable": False},
            )

        traced = 0
        valid = 0
        problems: list[str] = []

        forbidden_values = {
            value
            for value in (
                trace.session_id,
                trace.metadata.get("job_id"),
                trace.metadata.get("candidate_ref"),
            )
            if isinstance(value, str)
            and value
        }

        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue

            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            trace_meta = payload.get("_trace")
            if not isinstance(trace_meta, dict):
                continue

            correlation_id = trace_meta.get(
                "correlation_id"
            )
            if correlation_id is None:
                continue

            traced += 1
            event_problems: list[str] = []

            if not isinstance(
                correlation_id,
                str,
            ):
                event_problems.append(
                    "correlation_id is not a string"
                )
            else:
                if not _ALLOWED.fullmatch(
                    correlation_id
                ):
                    event_problems.append(
                        "correlation_id is outside the "
                        "bounded safe format"
                    )
                if correlation_id in forbidden_values:
                    event_problems.append(
                        "correlation_id reuses a session, "
                        "job, or candidate identifier"
                    )

            if event_problems:
                problems.append(
                    f"audit_event[{index}]: "
                    + ", ".join(event_problems)
                )
            else:
                valid += 1

        if traced == 0:
            return MetricResult(
                metric=self.name,
                summary=(
                    "No audit correlation metadata was "
                    "recorded; legacy/non-request trace."
                ),
                details={
                    "applicable": False,
                    "audit_events": len(events),
                },
            )

        coverage = (
            traced / len(events)
            if events
            else 0.0
        )
        validity = valid / traced

        return MetricResult(
            metric=self.name,
            value=round(validity, 4),
            unit="valid_correlation_id_ratio",
            passed=not problems,
            summary=(
                f"{valid}/{traced} recorded audit correlation "
                "IDs are structurally valid and distinct from "
                "session/job/candidate identifiers."
            ),
            details={
                "audit_events": len(events),
                "traced_events": traced,
                "correlation_coverage": round(
                    coverage,
                    4,
                ),
                "problems": problems,
            },
        )
