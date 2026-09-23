from __future__ import annotations

import hashlib
import json

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


def _compute_hash(
    event: dict,
    *,
    prev_hash: str | None,
) -> str:
    payload = {
        "hash_version": 1,
        "seq": event.get("seq"),
        "type": event.get("type"),
        "turn_id": event.get("turn_id"),
        "payload": event.get("payload", {}),
        "created_at": event.get("created_at"),
        "prev_hash": prev_hash,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditChainIntegrityMetric(Metric):
    name = "audit_chain_integrity"

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        events = trace.metadata.get("audit_events")
        summary = trace.metadata.get("audit_chain")

        if not isinstance(events, list):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose an audit event chain.",
                details={"applicable": False},
            )

        if not events:
            return MetricResult(
                metric=self.name,
                summary="Audit event chain is empty.",
                details={"applicable": False},
            )

        problems: list[str] = []
        valid_events = 0
        expected_prev: str | None = None

        for index, event in enumerate(events):
            if not isinstance(event, dict):
                problems.append(
                    f"audit_event[{index}] is not an object"
                )
                continue

            expected_seq = index + 1
            if event.get("seq") != expected_seq:
                problems.append(
                    f"audit_event[{index}] has seq {event.get('seq')!r}; "
                    f"expected {expected_seq}"
                )

            if event.get("hash_version") != 1:
                problems.append(
                    f"audit_event[{index}] has unsupported hash version"
                )

            if event.get("prev_hash") != expected_prev:
                problems.append(
                    f"audit_event[{index}] previous hash mismatch"
                )

            expected_hash = _compute_hash(
                event,
                prev_hash=expected_prev,
            )
            actual_hash = event.get("event_hash")
            if actual_hash != expected_hash:
                problems.append(
                    f"audit_event[{index}] event hash mismatch"
                )
            else:
                valid_events += 1

            if isinstance(actual_hash, str):
                expected_prev = actual_hash
            else:
                expected_prev = None

        if isinstance(summary, dict):
            declared_count = summary.get("event_count")
            if declared_count != len(events):
                problems.append(
                    "audit summary event_count does not match exported events"
                )

            if summary.get("head_hash") != expected_prev:
                problems.append(
                    "audit summary head_hash does not match chain head"
                )

            if summary.get("verified") is not True:
                problems.append(
                    "audit summary does not declare a verified sealed chain"
                )
        else:
            problems.append(
                "audit chain summary is missing"
            )

        ratio = valid_events / len(events)
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_audit_event_ratio",
            passed=not problems,
            summary=(
                f"{valid_events}/{len(events)} audit events "
                "match the exported hash chain."
            ),
            details={
                "events": len(events),
                "head_hash": expected_prev,
                "problems": problems,
            },
        )
