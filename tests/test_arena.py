import asyncio

from voxrubric.arena import ArenaRunner, ArenaScenario
from voxrubric.arena_agents import ScriptedAgentFactory, ScriptedQuestion
from voxrubric.models import Rubric, RubricDimension
from voxrubric.synthetic import AnswerStyle, CandidatePersona


def run(coro):
    return asyncio.run(coro)


def scenario():
    return ArenaScenario(
        id="python-arena",
        role="Python Engineer",
        locale="ar-SA",
        max_candidate_turns=6,
        rubric=Rubric(
            id="python-rubric",
            title="Python Engineer",
            dimensions=[
                RubricDimension(
                    id="python",
                    description="Python engineering",
                ),
                RubricDimension(
                    id="debugging",
                    description="Production debugging",
                ),
            ],
        ),
        persona=CandidatePersona(
            id="senior-code-switch",
            skill_level=4,
            answer_style=AnswerStyle.CODE_SWITCHED,
            known_topics=["python", "debugging"],
        ),
    )


def test_arena_runs_same_scenario_across_agents_without_ranking():
    broad = ScriptedAgentFactory(
        "broad-fixed",
        [
            ScriptedQuestion(
                text="Tell me about a Python system you built.",
                rubric_tags=["python"],
            ),
            ScriptedQuestion(
                text="How did you debug a difficult production issue?",
                rubric_tags=["debugging"],
            ),
        ],
    )
    narrow = ScriptedAgentFactory(
        "narrow-fixed",
        [
            ScriptedQuestion(
                text="Tell me about Python.",
                rubric_tags=["python"],
            ),
            ScriptedQuestion(
                text="Give another Python example.",
                rubric_tags=["python"],
            ),
        ],
    )

    result = run(
        ArenaRunner().run(
            scenario(),
            [broad, narrow],
            repetitions=2,
        )
    )

    assert result.scenario_id == "python-arena"
    assert len(result.runs) == 4
    assert [item.agent_id for item in result.aggregates] == [
        "broad-fixed",
        "narrow-fixed",
    ]

    by_agent = {item.agent_id: item for item in result.aggregates}
    assert by_agent["broad-fixed"].question_path_stability == 1.0
    assert by_agent["narrow-fixed"].question_path_stability == 1.0

    broad_metrics = {
        item.metric: item
        for item in by_agent["broad-fixed"].metrics
    }
    narrow_metrics = {
        item.metric: item
        for item in by_agent["narrow-fixed"].metrics
    }
    assert broad_metrics["rubric_coverage"].mean == 1.0
    assert narrow_metrics["rubric_coverage"].mean == 0.5

    dumped = result.model_dump()
    assert "winner" not in dumped
    assert "ranking" not in dumped


def test_arena_factory_state_is_isolated_between_repetitions():
    factory = ScriptedAgentFactory(
        "isolated",
        [
            ScriptedQuestion(
                text="First question",
                rubric_tags=["python"],
            ),
            ScriptedQuestion(
                text="Second question",
                rubric_tags=["debugging"],
            ),
        ],
    )
    result = run(
        ArenaRunner().run(
            scenario(),
            [factory],
            repetitions=2,
        )
    )

    first_questions = [
        run.trace.turns[0].text
        for run in result.runs
    ]
    assert first_questions == ["First question", "First question"]
