from __future__ import annotations

import asyncio

from voxrubric.arena import ArenaRunner, ArenaScenario
from voxrubric.arena_agents import ScriptedAgentFactory, ScriptedQuestion
from voxrubric.models import Rubric, RubricDimension
from voxrubric.synthetic import AnswerStyle, CandidatePersona


async def main() -> None:
    rubric = Rubric(
        id="backend-v1",
        title="Backend Engineer",
        dimensions=[
            RubricDimension(
                id="python",
                description="Python engineering",
            ),
            RubricDimension(
                id="debugging",
                description="Production debugging",
            ),
            RubricDimension(
                id="systems",
                description="Systems reasoning",
            ),
        ],
    )
    scenario = ArenaScenario(
        id="backend-demo",
        role="Backend Engineer",
        locale="ar-SA",
        rubric=rubric,
        persona=CandidatePersona(
            id="code-switched-senior",
            skill_level=4,
            answer_style=AnswerStyle.CODE_SWITCHED,
            known_topics=["python", "debugging", "systems"],
        ),
    )

    balanced = ScriptedAgentFactory(
        "balanced-fixed",
        [
            ScriptedQuestion(
                text="Describe a Python service you owned.",
                rubric_tags=["python"],
            ),
            ScriptedQuestion(
                text="Walk me through a production incident you debugged.",
                rubric_tags=["debugging"],
            ),
            ScriptedQuestion(
                text="Explain a scaling trade-off you had to make.",
                rubric_tags=["systems"],
            ),
        ],
    )

    result = await ArenaRunner().run(
        scenario,
        [balanced],
        repetitions=3,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
