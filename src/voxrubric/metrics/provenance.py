from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


class EvidenceProvenanceMetric(Metric):
    name = "evidence_provenance"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        graph = trace.metadata.get("evidence_graph")
        if not isinstance(graph, dict):
            return MetricResult(
                metric=self.name,
                summary="Trace does not include a skill evidence graph.",
                details={"applicable": False},
            )

        known_turns = {turn.id: turn for turn in trace.turns}
        total = 0
        valid = 0
        problems: list[str] = []

        for competency_id, node in graph.items():
            if not isinstance(node, dict):
                problems.append(f"{competency_id}: node is not an object")
                continue
            evidence = node.get("evidence", [])
            if not isinstance(evidence, list):
                problems.append(f"{competency_id}: evidence is not a list")
                continue

            for index, item in enumerate(evidence):
                total += 1
                if not isinstance(item, dict):
                    problems.append(f"{competency_id}[{index}]: evidence is not an object")
                    continue

                turn_id = item.get("turn_id")
                state = item.get("state")
                confidence = item.get("confidence")
                note = item.get("note")
                source = item.get("source")

                item_problems: list[str] = []
                turn = known_turns.get(turn_id)
                if turn is None:
                    item_problems.append("unknown turn")
                if state not in {
                    "claimed", "demonstrated", "verified",
                    "contradicted", "insufficient_evidence",
                }:
                    item_problems.append("invalid state")
                if not isinstance(note, str) or not note.strip():
                    item_problems.append("missing note")
                if source == "evaluator":
                    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                        item_problems.append("invalid evaluator confidence")

                quote = item.get("quote")
                if quote is not None:
                    if not isinstance(quote, str):
                        item_problems.append("quote is not a string")
                    elif turn is not None and quote not in turn.text:
                        item_problems.append(
                            "quote is not a literal substring of the referenced turn"
                        )

                if item_problems:
                    problems.append(
                        f"{competency_id}[{index}]: " + ", ".join(item_problems)
                    )
                else:
                    valid += 1

        if total == 0:
            return MetricResult(
                metric=self.name,
                summary="Evidence graph is present but contains no evidence observations yet.",
                details={"nodes": len(graph), "evidence_items": 0},
            )

        ratio = valid / total
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_evidence_ratio",
            passed=not problems,
            summary=f"{valid}/{total} evidence observations have valid provenance.",
            details={"problems": problems, "nodes": len(graph)},
        )
