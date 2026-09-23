from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field

from .arena import ArenaResult, ArenaRunner, ArenaScenario
from .arena_agents import ScriptedAgentFactory, ScriptedQuestion
from .models import Rubric, StrictModel
from .nora_adapter import NoraAgentFactory
from .synthetic import CandidatePersona


class ScriptedAgentConfig(StrictModel):
    id: str
    questions: list[ScriptedQuestion] = Field(min_length=1)


class NoraAgentConfig(StrictModel):
    id: str
    base_url: str = Field(min_length=4)
    role_description: str = "Arena-controlled interview role."
    headers: dict[str, str] = Field(default_factory=dict)


class ArenaFileConfig(StrictModel):
    id: str
    role: str
    locale: str = "en"
    rubric: Rubric
    persona: CandidatePersona
    max_candidate_turns: int = Field(default=12, ge=1, le=50)
    repetitions: int = Field(default=1, ge=1, le=50)
    agents: list[ScriptedAgentConfig] = Field(default_factory=list)
    nora_agents: list[NoraAgentConfig] = Field(default_factory=list)

    def factories(self):
        factories = [
            ScriptedAgentFactory(
                item.id,
                item.questions,
            )
            for item in self.agents
        ]
        factories.extend(
            NoraAgentFactory(
                agent_id=item.id,
                base_url=item.base_url,
                role_description=item.role_description,
                headers=item.headers,
            )
            for item in self.nora_agents
        )
        if not factories:
            raise ValueError(
                "Arena config requires at least one scripted or Nora agent"
            )
        ids = [factory.agent_id for factory in factories]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "Arena agent ids must be unique across all adapter types"
            )
        return factories


def load_arena_config(path: str | Path) -> ArenaFileConfig:
    path = Path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ArenaFileConfig.model_validate(payload)


async def run_scripted_arena(
    path: str | Path,
    *,
    runner: ArenaRunner | None = None,
) -> ArenaResult:
    """Run a YAML-defined Arena.

    The historical function name is retained for CLI/API compatibility even
    though configs can now include remote Nora adapters as well as scripted
    agents.
    """

    config = load_arena_config(path)
    scenario = ArenaScenario(
        id=config.id,
        role=config.role,
        locale=config.locale,
        rubric=config.rubric,
        persona=config.persona,
        max_candidate_turns=config.max_candidate_turns,
    )
    return await (runner or ArenaRunner()).run(
        scenario,
        config.factories(),
        repetitions=config.repetitions,
    )
