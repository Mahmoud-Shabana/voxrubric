from __future__ import annotations

from typing import Protocol

from .models import (
    AgentUtterance,
    InterviewScorecard,
    InterviewTrace,
    Rubric,
)


class JudgeProvider(Protocol):
    """Provider-neutral contract for semantic judging."""

    @property
    def judge_id(self) -> str: ...

    def score(
        self,
        trace: InterviewTrace,
        rubric: Rubric,
    ) -> InterviewScorecard: ...


class InterviewAgentSession(Protocol):
    """One isolated interview run for an agent under test."""

    async def start(
        self,
        *,
        role: str,
        rubric: Rubric,
        locale: str,
    ) -> AgentUtterance: ...

    async def respond(
        self,
        candidate_text: str,
    ) -> AgentUtterance: ...


class InterviewAgentFactory(Protocol):
    """Factory used by Arena so every repetition starts from clean state."""

    @property
    def agent_id(self) -> str: ...

    def create(self) -> InterviewAgentSession: ...
