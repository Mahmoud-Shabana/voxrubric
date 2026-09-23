from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field

from .arena import ArenaResult, ArenaRunner, ArenaScenario
from .arena_agents import ScriptedAgentFactory, ScriptedQuestion
from .models import Rubric, StrictModel
from .synthetic import CandidatePersona


class ScriptedAgentConfig(StrictModel):
    id: str
    questions: list[ScriptedQuestion] = Field(min_length=1)


class ArenaFileConfig(StrictModel):
    id: str
    role: str
    locale: str = "en"
    rubric: Rubric
    persona: CandidatePersona
    max_candidate_turns: int = Field(default=12, ge=1, le=50)
    repetitions: int = Field(default=1, ge=1, le=50)
    agents: list[ScriptedAgentConfig] = Field(min_length=1)


def load_arena_config(path: str | Path) -> ArenaFileConfig:
    path = Path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ArenaFileConfig.model_validate(payload)


async def run_scripted_arena(
    path: str | Path,
    *,
    runner: ArenaRunner | None = None,
) -> ArenaResult:
    config = load_arena_config(path)
    scenario = ArenaScenario(
        id=config.id,
        role=config.role,
        locale=config.locale,
        rubric=config.rubric,
        persona=config.persona,
        max_candidate_turns=config.max_candidate_turns,
    )
    agents = [
        ScriptedAgentFactory(
            item.id,
            item.questions,
        )
        for item in config.agents
    ]
    return await (runner or ArenaRunner()).run(
        scenario,
        agents,
        repetitions=config.repetitions,
    )
