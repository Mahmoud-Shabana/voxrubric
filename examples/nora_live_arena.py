from __future__ import annotations

import asyncio
from pathlib import Path

from voxrubric.adapters import NoraHttpAgentFactory
from voxrubric.arena import ArenaRunner, ArenaScenario
from voxrubric.html_report import write_arena_html
from voxrubric.models import Rubric, RubricDimension
from voxrubric.synthetic import AnswerStyle, CandidatePersona


async def main() -> None:
    """Run a controlled repeated Arena experiment against live Nora.

    Start Nora first:
        uvicorn nora_interviewer.api:app --reload
    """

    rubric = Rubric(
        id="nora-live-backend-v1",
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
        id="nora-live-backend",
        role="Backend Engineer",
        locale="ar-SA",
        rubric=rubric,
        max_candidate_turns=10,
        persona=CandidatePersona(
            id="controlled-code-switch",
            skill_level=4,
            answer_style=AnswerStyle.CODE_SWITCHED,
            known_topics=[
                "python",
                "debugging",
                "systems",
            ],
        ),
    )

    nora = NoraHttpAgentFactory(
        base_url="http://127.0.0.1:8000",
        agent_id="nora-local",
    )

    result = await ArenaRunner().run(
        scenario,
        [nora],
        repetitions=3,
    )

    Path("nora-arena-result.json").write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    write_arena_html(
        result,
        "nora-arena-report.html",
    )

    aggregate = result.aggregates[0]
    print(
        "Nora Arena completed:",
        {
            "runs": aggregate.runs,
            "completion_rate": aggregate.completion_rate,
            "question_path_stability": aggregate.question_path_stability,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
