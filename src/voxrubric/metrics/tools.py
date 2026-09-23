from __future__ import annotations

from ..models import InterviewTrace, MetricResult, Rubric
from .base import Metric


_FORBIDDEN_PUBLIC_KEYS = {
    "hidden_tests",
    "private_tests",
    "answer_key",
    "expected_solution",
    "gold_solution",
}


class ToolArtifactIntegrityMetric(Metric):
    name = "tool_artifact_integrity"

    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        tools = trace.metadata.get("tools")
        submissions = trace.metadata.get("tool_submissions")
        evaluations = trace.metadata.get("tool_evaluations")
        if not any(isinstance(value, list) for value in (tools, submissions, evaluations)):
            return MetricResult(
                metric=self.name,
                summary="Trace does not expose interview tool artifacts.",
                details={"applicable": False},
            )

        tools = tools if isinstance(tools, list) else []
        submissions = submissions if isinstance(submissions, list) else []
        evaluations = evaluations if isinstance(evaluations, list) else []

        checks = 0
        valid = 0
        problems: list[str] = []

        tool_by_id: dict[str, dict] = {}
        for index, tool in enumerate(tools):
            checks += 1
            if not isinstance(tool, dict):
                problems.append(f"tool[{index}] is not an object")
                continue
            tool_id = str(tool.get("id", ""))
            if not tool_id or tool_id in tool_by_id:
                problems.append(f"tool[{index}] has missing or duplicate id")
                continue
            payload = tool.get("payload", {})
            if isinstance(payload, dict):
                leaked = sorted(_FORBIDDEN_PUBLIC_KEYS & set(payload))
                if leaked:
                    problems.append(
                        f"tool[{index}] public payload exposes private keys: {leaked}"
                    )
                    continue
            tool_by_id[tool_id] = tool
            valid += 1

        submission_by_id: dict[str, dict] = {}
        submissions_by_tool: dict[str, int] = {}
        for index, submission in enumerate(submissions):
            checks += 1
            if not isinstance(submission, dict):
                problems.append(f"submission[{index}] is not an object")
                continue
            submission_id = str(submission.get("id", ""))
            tool_id = str(submission.get("tool_id", ""))
            if not submission_id or submission_id in submission_by_id:
                problems.append(f"submission[{index}] has missing or duplicate id")
                continue
            if tool_id not in tool_by_id:
                problems.append(f"submission[{index}] references unknown tool {tool_id!r}")
                continue
            submission_by_id[submission_id] = submission
            submissions_by_tool[tool_id] = submissions_by_tool.get(tool_id, 0) + 1
            valid += 1

        evaluations_by_tool: dict[str, int] = {}
        for index, evaluation in enumerate(evaluations):
            checks += 1
            if not isinstance(evaluation, dict):
                problems.append(f"evaluation[{index}] is not an object")
                continue
            tool_id = str(evaluation.get("tool_id", ""))
            submission_id = str(evaluation.get("submission_id", ""))
            if tool_id not in tool_by_id:
                problems.append(f"evaluation[{index}] references unknown tool {tool_id!r}")
                continue
            submission = submission_by_id.get(submission_id)
            if submission is None:
                problems.append(
                    f"evaluation[{index}] references unknown submission {submission_id!r}"
                )
                continue
            if submission.get("tool_id") != tool_id:
                problems.append(f"evaluation[{index}] submission belongs to a different tool")
                continue

            evidence = evaluation.get("evidence", {})
            if (
                isinstance(evidence, dict)
                and evidence.get("review_required") is True
                and evaluation.get("score") is not None
            ):
                problems.append(
                    f"evaluation[{index}] assigns a score while declaring manual review required"
                )
                continue

            evaluations_by_tool[tool_id] = evaluations_by_tool.get(tool_id, 0) + 1
            valid += 1

        for tool_id, tool in tool_by_id.items():
            status = tool.get("status")
            if status == "evaluated":
                checks += 1
                if evaluations_by_tool.get(tool_id, 0) >= 1:
                    valid += 1
                else:
                    problems.append(f"evaluated tool {tool_id} has no evaluation")
            elif status == "submitted":
                checks += 1
                if submissions_by_tool.get(tool_id, 0) >= 1:
                    valid += 1
                else:
                    problems.append(f"submitted tool {tool_id} has no submission")

        if checks == 0:
            return MetricResult(
                metric=self.name,
                value=1.0,
                unit="valid_tool_check_ratio",
                passed=True,
                summary="No tool artifacts required validation.",
                details={"problems": []},
            )

        ratio = valid / checks
        return MetricResult(
            metric=self.name,
            value=round(ratio, 4),
            unit="valid_tool_check_ratio",
            passed=not problems,
            summary=f"{valid}/{checks} tool-artifact integrity checks hold.",
            details={
                "tools": len(tools),
                "submissions": len(submissions),
                "evaluations": len(evaluations),
                "problems": problems,
            },
        )
