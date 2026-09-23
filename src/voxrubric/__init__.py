"""VoxRubric public API."""

from .arena import (
    AgentArenaAggregate,
    ArenaResult,
    ArenaRun,
    ArenaRunner,
    ArenaScenario,
    MetricAggregate,
)
from .arena_agents import ScriptedAgentFactory, ScriptedQuestion
from .judging import JudgeEnsemble
from .models import (
    AgentUtterance,
    DimensionScore,
    EvidenceRef,
    InterviewScorecard,
    InterviewTrace,
    MetricResult,
    Rubric,
    RubricDimension,
    Speaker,
    Turn,
)
from .runner import Evaluator, default_evaluator

__all__ = [
    "AgentArenaAggregate",
    "AgentUtterance",
    "ArenaResult",
    "ArenaRun",
    "ArenaRunner",
    "ArenaScenario",
    "DimensionScore",
    "EvidenceRef",
    "Evaluator",
    "InterviewScorecard",
    "InterviewTrace",
    "JudgeEnsemble",
    "MetricAggregate",
    "MetricResult",
    "Rubric",
    "RubricDimension",
    "ScriptedAgentFactory",
    "ScriptedQuestion",
    "Speaker",
    "Turn",
    "default_evaluator",
]

__version__ = "0.4.0"
