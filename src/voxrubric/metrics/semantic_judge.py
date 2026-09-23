from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric, Speaker
from .base import Metric


class SemanticJudgeIntegrityMetric(Metric):
    """Validate semantic-judge evidence and versioned judge history."""

    name = "semantic_judge_integrity"

    def evaluate(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> MetricResult:
        graph = trace.metadata.get("evidence_graph")
        failures = trace.metadata.get("evidence_judge_failures", [])
        runs = trace.metadata.get("evidence_judge_runs", [])
        revisions = trace.metadata.get("transcript_revisions", [])

        if (
            not isinstance(graph, dict)
            and not isinstance(failures, list)
            and not isinstance(runs, list)
        ):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose semantic-judge evidence metadata.",
                details={"applicable": False},
            )

        failures = failures if isinstance(failures, list) else []
        runs = runs if isinstance(runs, list) else []
        revisions = revisions if isinstance(revisions, list) else []
        known_turns = {turn.id: turn for turn in trace.turns}
        semantic_items = 0
        checks = 0
        valid = 0
        problems: list[str] = []

        revisions_by_turn: dict[str, int] = {}
        for revision in revisions:
            if not isinstance(revision, dict):
                continue
            turn_id = revision.get("turn_id")
            if isinstance(turn_id, str):
                revisions_by_turn[turn_id] = (
                    revisions_by_turn.get(turn_id, 0) + 1
                )

        run_by_id: dict[str, dict] = {}
        latest_run_by_answer: dict[str, dict] = {}

        for index, run in enumerate(runs):
            checks += 1
            if not isinstance(run, dict):
                problems.append(f"judge_run[{index}] is not an object")
                continue

            run_id = run.get("id")
            judge_id = run.get("judge_id")
            answer_turn_id = run.get("answer_turn_id")
            question_turn_id = run.get("question_turn_id")
            revision_count = run.get("transcript_revision_count")
            observation_ids = run.get("observation_ids")
            error = run.get("error")

            run_problems: list[str] = []
            if not isinstance(run_id, str) or not run_id:
                run_problems.append("missing id")
            elif run_id in run_by_id:
                run_problems.append("duplicate id")

            if not isinstance(judge_id, str) or not judge_id:
                run_problems.append("missing judge_id")

            answer_turn = known_turns.get(answer_turn_id)
            if answer_turn is None:
                run_problems.append("unknown answer turn")
            elif answer_turn.speaker is not Speaker.CANDIDATE:
                run_problems.append("answer turn is not a candidate turn")

            question_turn = known_turns.get(question_turn_id)
            if question_turn is None:
                run_problems.append("unknown question turn")
            elif question_turn.speaker is not Speaker.INTERVIEWER:
                run_problems.append("question turn is not an interviewer turn")

            if not isinstance(revision_count, int) or revision_count < 0:
                run_problems.append("invalid transcript_revision_count")

            if not isinstance(observation_ids, list):
                run_problems.append("observation_ids is not a list")

            if error is not None and not isinstance(error, str):
                run_problems.append("error is not a string")

            if run_problems:
                problems.append(
                    f"judge_run[{index}]: " + ", ".join(run_problems)
                )
                continue

            valid += 1
            run_by_id[run_id] = run

            current = latest_run_by_answer.get(answer_turn_id)
            if current is None:
                latest_run_by_answer[answer_turn_id] = run
            else:
                current_created = str(current.get("created_at", ""))
                created = str(run.get("created_at", ""))
                if created > current_created:
                    latest_run_by_answer[answer_turn_id] = run

        for answer_turn_id, run in latest_run_by_answer.items():
            checks += 1
            current_revision_count = revisions_by_turn.get(
                answer_turn_id,
                0,
            )
            if run.get("error"):
                problems.append(
                    f"latest judge run for {answer_turn_id} failed"
                )
                continue
            if run.get("transcript_revision_count") != current_revision_count:
                problems.append(
                    f"latest judge run for {answer_turn_id} is stale "
                    f"({run.get('transcript_revision_count')} != "
                    f"{current_revision_count})"
                )
                continue
            valid += 1

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
                    active = item.get("active", True)
                    judge_run_id = item.get("judge_run_id")
                    turn = known_turns.get(turn_id)

                    checks += 1
                    item_problems: list[str] = []

                    if not isinstance(active, bool):
                        item_problems.append("active flag is not boolean")

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
                        elif (
                            active is True
                            and turn is not None
                            and quote not in turn.text
                        ):
                            item_problems.append(
                                "active quote is not a literal substring "
                                "of the referenced turn"
                            )
                    elif quote is not None:
                        if not isinstance(quote, str):
                            item_problems.append("quote is not a string")
                        elif (
                            active is True
                            and turn is not None
                            and quote not in turn.text
                        ):
                            item_problems.append(
                                "active quote is not a literal substring "
                                "of the referenced turn"
                            )

                    if not isinstance(confidence, (int, float)):
                        item_problems.append("missing confidence")
                    elif not 0 <= float(confidence) <= 1:
                        item_problems.append("confidence is outside [0, 1]")

                    if runs:
                        if not isinstance(judge_run_id, str) or not judge_run_id:
                            item_problems.append(
                                "versioned semantic evidence is missing judge_run_id"
                            )
                        else:
                            run = run_by_id.get(judge_run_id)
                            if run is None:
                                item_problems.append(
                                    "judge_run_id references unknown run"
                                )
                            else:
                                if run.get("answer_turn_id") != turn_id:
                                    item_problems.append(
                                        "judge run belongs to a different answer turn"
                                    )
                                if item.get("id") not in run.get("observation_ids", []):
                                    item_problems.append(
                                        "evidence id is absent from judge run observations"
                                    )
                                if active is True and run.get("error"):
                                    item_problems.append(
                                        "active evidence belongs to a failed judge run"
                                    )

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

        if semantic_items == 0 and not failures and not runs:
            return MetricResult(
                metric=self.name,
                summary="No semantic-judge evidence, runs, or failures were recorded.",
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
                "judge_runs": len(runs),
                "latest_answer_runs": len(latest_run_by_answer),
                "judge_failures": len(failures),
                "problems": problems,
            },
        )
