from pathlib import Path

from voxrubric.config import load_rubric, load_trace
from voxrubric.runner import default_evaluator


ROOT = Path(__file__).parents[1]


def test_realistic_nora_export_evaluates_across_integration_boundaries():
    trace = load_trace(
        ROOT / "benchmarks/nora-integration/nora-export.json"
    )
    rubric = load_rubric(
        ROOT / "benchmarks/nora-integration/rubric.yaml"
    )

    report = default_evaluator().run(trace, rubric)
    metrics = {
        item.metric: item
        for item in report.metrics
    }

    assert trace.metadata["source"] == "nora-interviewer"
    assert report.session_id == "nora-regression-001"

    for name in [
        "rubric_coverage",
        "follow_up_integrity",
        "response_latency",
        "dual_lane_balance",
        "evidence_provenance",
        "candidate_control_recovery",
        "tool_artifact_integrity",
        "audit_chain_integrity",
        "audit_correlation_integrity",
    ]:
        assert metrics[name].passed is True, (
            name,
            metrics[name].summary,
            metrics[name].details,
        )

    assert metrics["rubric_coverage"].value == 1.0
    assert metrics["follow_up_integrity"].value == 1.0
    assert metrics["candidate_control_recovery"].value == 1.0
    assert metrics["tool_artifact_integrity"].value == 1.0
    assert metrics["audit_chain_integrity"].value == 1.0
    assert metrics["audit_correlation_integrity"].value == 1.0

    assert metrics["asr_preservation"].passed is None
    assert metrics["asr_preservation"].details["applicable"] is False


def test_nora_export_audit_fixture_detects_tampering():
    trace = load_trace(
        ROOT / "benchmarks/nora-integration/nora-export.json"
    )
    rubric = load_rubric(
        ROOT / "benchmarks/nora-integration/rubric.yaml"
    )

    events = [
        dict(item)
        for item in trace.metadata["audit_events"]
    ]
    events[2] = {
        **events[2],
        "payload": {
            **events[2]["payload"],
            "tampered": True,
        },
    }
    tampered = trace.model_copy(
        update={
            "metadata": {
                **trace.metadata,
                "audit_events": events,
            }
        }
    )

    report = default_evaluator().run(tampered, rubric)
    metrics = {
        item.metric: item
        for item in report.metrics
    }

    assert metrics["audit_chain_integrity"].passed is False
    assert any(
        "event hash mismatch" in problem
        for problem in metrics["audit_chain_integrity"].details["problems"]
    )
