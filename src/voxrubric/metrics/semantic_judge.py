from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


class SemanticJudgeIntegrityMetric(Metric):
    """Validate semantic-judge evidence exported by interview agents."""

    name = "semantic_judge_integrity"

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        graph = trace.metadata.get("evidence_graph")
        failures = trace.metadata.get("evidence_judge_failures", [])

        if not isinstance(graph, dict) and not isinstance(failures, list):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose semantic-judge evidence metadata.",
                details={"applicable": False},
            )

        failures = failures if isinstance(failures, list) else []
        known_turns = {turn.id: turn for turn in trace.turns}
        semantic_items = 0
        checks = 0
        valid = 0
        problems: list[str] = []

        if isinstance(graph, dict):
            for competency_id, node in graph.items():
                if not isinstance(node, dict):
                    continue
                evidence = node.get("evidence", [])
                if not isinstance(evidence, list):
                    continue

                for index, item in enumerate(evidence):
                    if not isinstance(item, dict):
                        continue
                    source = item.get("source")
                    if not (
                        isinstance(source, str)
                        and source.startswith("semantic_judge:")
                    ):
                        continue

                    semantic_items += 1
                    turn_id = item.get("turn_id")
                    state = item.get("state")
                    quote = item.get("quote")
                    confidence = item.get("confidence")
                    turn = known_turns.get(turn_id)

                    checks += 1
                    item_problems: list[str] = []

                    if turn is None:
                        item_problems.append("unknown turn")
                    elif turn.speaker is not Speaker.CANDIDATE:
                        item_problems.append(
                            "semantic evidence must reference a candidate turn"
                        )

                    if state == "verified":
                        item_problems.append(
                            "transcript semantic judge emitted verified evidence"
                        )

                    if state in {"demonstrated", "contradicted"}:
                        if not isinstance(quote, str) or not quote:
                            item_problems.append(
                                f"{state} evidence is missing a literal quote"
                            )
                        elif turn is not None and quote not in turn.text:
                            item_problems.append(
                                "quote is not a literal substring of the referenced turn"
                            )
                    elif quote is not None:
                        if not isinstance(quote, str):
                            item_problems.append("quote is not a string")
                        elif turn is not None and quote not in turn.text:
                            item_problems.append(
                                "quote is not a literal substring of the referenced turn"
                            )

                    if not isinstance(confidence, (int, float)):
                        item_problems.append("missing confidence")
                    elif not 0 <= float(confidence) <= 1:
                        item_problems.append("confidence is outside [0, 1]")

                    if item_problems:
                        problems.append(
                            f"{competency_id}[{index}]: "
                            + ", ".join(item_problems)
                        )
                    else:
                        valid += 1

        for index, failure in enumerate(failures):
            checks += 1
            if not isinstance(failure, dict):
                problems.append(
                    f"judge_failure[{index}] is not an object"
                )
                continue

            payload = failure.get("payload")
            if not isinstance(payload, dict):
                problems.append(
                    f"judge_failure[{index}] is missing payload"
                )
                continue

            judge_id = payload.get("judge_id")
            error = payload.get("error")
            if not isinstance(judge_id, str) or not judge_id:
                problems.append(
                    f"judge_failure[{index}] is missing judge_id"
                )
            elif not isinstance(error, str) or not error:
                problems.append(
                    f"judge_failure[{index}] is missing error"
                )
            else:
                problems.append(
                    f"judge_failure[{index}] {judge_id}: {error}"
                )

        if semantic_items == 0 and not failures:
            return MetricResult(
                metric=self.name,
                summary="No semantic-judge evidence or failures were recorded.",
                details={"applicable": False},
            )

        ratio = valid / checks if checks else 1.0
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_semantic_judge_check_ratio",
            passed=not problems,
            summary=(
                f"{valid}/{checks} semantic-judge integrity checks hold."
            ),
            details={
                "semantic_evidence_items": semantic_items,
                "judge_failures": len(failures),
                "problems": problems,
            },
        )
