from __future__ import annotations

from itertools import combinations
from random import Random
from statistics import fmean, stdev
from time import perf_counter

from pydantic import Field

from .models import (
    EvaluationReport,
    InterviewTrace,
    Rubric,
    Speaker,
    StrictModel,
    Turn,
)
from .protocols import InterviewAgentFactory
from .runner import Evaluator, default_evaluator
from .synthetic import CandidatePersona, SyntheticCandidate


class ArenaScenario(StrictModel):
    id: str
    role: str
    rubric: Rubric
    persona: CandidatePersona
    locale: str = "en"
    max_candidate_turns: int = Field(default=12, ge=1, le=50)


class ArenaRun(StrictModel):
    agent_id: str
    run_index: int = Field(ge=0)
    completed: bool
    trace: InterviewTrace
    report: EvaluationReport


class MetricAggregate(StrictModel):
    metric: str
    samples: int
    mean: float
    minimum: float
    maximum: float
    standard_deviation: float | None = None
    ci95_low: float | None = None
    ci95_high: float | None = None
    ci_method: str | None = None


class AgentArenaAggregate(StrictModel):
    agent_id: str
    runs: int
    completion_rate: float
    mean_candidate_turns: float
    mean_interviewer_turns: float
    question_path_stability: float | None = None
    metrics: list[MetricAggregate] = Field(default_factory=list)


class ArenaResult(StrictModel):
    scenario_id: str
    repetitions: int
    runs: list[ArenaRun]
    aggregates: list[AgentArenaAggregate]


def _bootstrap_mean_ci(
    values: list[float],
    *,
    iterations: int = 2000,
    seed: int = 20260923,
) -> tuple[float | None, float | None]:
    if len(values) < 2:
        return None, None
    if iterations < 100:
        raise ValueError("bootstrap iterations must be >= 100")

    rng = Random(seed)
    sample_size = len(values)
    means: list[float] = []
    for _ in range(iterations):
        sample = [
            values[rng.randrange(sample_size)]
            for _ in range(sample_size)
        ]
        means.append(fmean(sample))

    means.sort()
    low_index = max(
        0,
        int(0.025 * iterations),
    )
    high_index = min(
        iterations - 1,
        int(0.975 * iterations) - 1,
    )
    return (
        round(means[low_index], 4),
        round(means[high_index], 4),
    )


def _evaluative_path(trace: InterviewTrace) -> list[set[str]]:
    return [
        set(turn.rubric_tags)
        for turn in trace.turns
        if turn.speaker is Speaker.INTERVIEWER
        and turn.metadata.get("question_lane") != "closing"
    ]


def _set_jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _path_similarity(left: InterviewTrace, right: InterviewTrace) -> float:
    a = _evaluative_path(left)
    b = _evaluative_path(right)
    length = max(len(a), len(b))
    if length == 0:
        return 1.0

    values: list[float] = []
    for index in range(length):
        if index >= len(a) or index >= len(b):
            values.append(0.0)
            continue
        values.append(_set_jaccard(a[index], b[index]))
    return fmean(values)


class ArenaRunner:
    def __init__(self, evaluator: Evaluator | None = None) -> None:
        self.evaluator = evaluator or default_evaluator()

    async def run(
        self,
        scenario: ArenaScenario,
        agents: list[InterviewAgentFactory],
        *,
        repetitions: int = 1,
    ) -> ArenaResult:
        if repetitions < 1:
            raise ValueError("repetitions must be >= 1")
        if not agents:
            raise ValueError("Arena requires at least one agent")

        ids = [agent.agent_id for agent in agents]
        if len(ids) != len(set(ids)):
            raise ValueError("Arena agent ids must be unique")

        runs: list[ArenaRun] = []
        for factory in agents:
            for run_index in range(repetitions):
                runs.append(
                    await self._run_once(
                        scenario,
                        factory,
                        run_index=run_index,
                    )
                )

        aggregates = [
            self._aggregate(
                agent_id,
                [run for run in runs if run.agent_id == agent_id],
            )
            for agent_id in ids
        ]
        return ArenaResult(
            scenario_id=scenario.id,
            repetitions=repetitions,
            runs=runs,
            aggregates=aggregates,
        )

    async def _run_once(
        self,
        scenario: ArenaScenario,
        factory: InterviewAgentFactory,
        *,
        run_index: int,
    ) -> ArenaRun:
        agent = factory.create()
        candidate = SyntheticCandidate(scenario.persona)
        turns: list[Turn] = []
        completed = False
        question_number = 0
        candidate_number = 0

        started = perf_counter()
        utterance = await agent.start(
            role=scenario.role,
            rubric=scenario.rubric,
            locale=scenario.locale,
        )
        latency = max(0, round((perf_counter() - started) * 1000))

        question_number += 1
        question_id = f"q{question_number}"
        turns.append(
            Turn(
                id=question_id,
                speaker=Speaker.INTERVIEWER,
                text=utterance.text,
                response_latency_ms=latency,
                rubric_tags=utterance.rubric_tags,
                metadata=utterance.metadata,
            )
        )
        if utterance.completes_interview:
            completed = True

        while not completed and candidate_number < scenario.max_candidate_turns:
            candidate_number += 1
            competency = (
                utterance.rubric_tags[0]
                if utterance.rubric_tags
                else None
            )
            answer = candidate.answer(
                utterance.text,
                competency=competency,
            )
            answer_id = f"a{candidate_number}"
            turns.append(
                Turn(
                    id=answer_id,
                    speaker=Speaker.CANDIDATE,
                    text=answer,
                    parent_turn_id=question_id,
                )
            )

            started = perf_counter()
            utterance = await agent.respond(answer)
            latency = max(0, round((perf_counter() - started) * 1000))

            question_number += 1
            question_id = f"q{question_number}"
            metadata = dict(utterance.metadata)
            if utterance.completes_interview:
                metadata.setdefault("question_lane", "closing")
            turns.append(
                Turn(
                    id=question_id,
                    speaker=Speaker.INTERVIEWER,
                    text=utterance.text,
                    response_latency_ms=latency,
                    parent_turn_id=(
                        answer_id
                        if utterance.is_followup
                        else None
                    ),
                    rubric_tags=utterance.rubric_tags,
                    metadata=metadata,
                )
            )
            completed = utterance.completes_interview

        trace = InterviewTrace(
            session_id=f"{scenario.id}:{factory.agent_id}:{run_index}",
            role=scenario.role,
            locale=scenario.locale,
            turns=turns,
            metadata={
                "arena_scenario_id": scenario.id,
                "arena_agent_id": factory.agent_id,
                "arena_run_index": run_index,
                "completed": completed,
            },
        )
        report = self.evaluator.run(trace, scenario.rubric)
        return ArenaRun(
            agent_id=factory.agent_id,
            run_index=run_index,
            completed=completed,
            trace=trace,
            report=report,
        )

    @staticmethod
    def _aggregate(
        agent_id: str,
        runs: list[ArenaRun],
    ) -> AgentArenaAggregate:
        completion_rate = fmean(float(run.completed) for run in runs)
        candidate_counts = [
            sum(
                turn.speaker is Speaker.CANDIDATE
                for turn in run.trace.turns
            )
            for run in runs
        ]
        interviewer_counts = [
            sum(
                turn.speaker is Speaker.INTERVIEWER
                for turn in run.trace.turns
            )
            for run in runs
        ]

        metric_values: dict[str, list[float]] = {}
        for run in runs:
            for metric in run.report.metrics:
                if metric.value is not None:
                    metric_values.setdefault(metric.metric, []).append(
                        float(metric.value)
                    )

        metrics: list[MetricAggregate] = []
        for name, values in sorted(metric_values.items()):
            ci_low, ci_high = _bootstrap_mean_ci(values)
            metrics.append(
                MetricAggregate(
                    metric=name,
                    samples=len(values),
                    mean=round(fmean(values), 4),
                    minimum=round(min(values), 4),
                    maximum=round(max(values), 4),
                    standard_deviation=(
                        round(stdev(values), 4)
                        if len(values) >= 2
                        else None
                    ),
                    ci95_low=ci_low,
                    ci95_high=ci_high,
                    ci_method=(
                        "percentile_bootstrap_2000"
                        if ci_low is not None
                        else None
                    ),
                )
            )

        stability: float | None = None
        if len(runs) >= 2:
            similarities = [
                _path_similarity(left.trace, right.trace)
                for left, right in combinations(runs, 2)
            ]
            stability = round(fmean(similarities), 4)

        return AgentArenaAggregate(
            agent_id=agent_id,
            runs=len(runs),
            completion_rate=round(completion_rate, 4),
            mean_candidate_turns=round(fmean(candidate_counts), 4),
            mean_interviewer_turns=round(fmean(interviewer_counts), 4),
            question_path_stability=stability,
            metrics=metrics,
        )
