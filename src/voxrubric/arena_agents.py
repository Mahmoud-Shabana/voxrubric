from __future__ import annotations

from pydantic import Field

from .models import AgentUtterance, Rubric, StrictModel


class ScriptedQuestion(StrictModel):
    text: str
    rubric_tags: list[str] = Field(default_factory=list)
    is_followup: bool = False


class ScriptedInterviewSession:
    def __init__(self, questions: list[ScriptedQuestion]) -> None:
        self.questions = [item.model_copy(deep=True) for item in questions]
        self.index = 0

    async def start(
        self,
        *,
        role: str,
        rubric: Rubric,
        locale: str,
    ) -> AgentUtterance:
        first = self.questions[0]
        return AgentUtterance(
            text=first.text,
            rubric_tags=first.rubric_tags,
            is_followup=first.is_followup,
            metadata={"baseline": "scripted"},
        )

    async def respond(self, candidate_text: str) -> AgentUtterance:
        self.index += 1
        if self.index >= len(self.questions):
            return AgentUtterance(
                text="Thank you. The scripted interview is complete.",
                completes_interview=True,
                metadata={
                    "baseline": "scripted",
                    "question_lane": "closing",
                },
            )
        item = self.questions[self.index]
        return AgentUtterance(
            text=item.text,
            rubric_tags=item.rubric_tags,
            is_followup=item.is_followup,
            metadata={"baseline": "scripted"},
        )


class ScriptedAgentFactory:
    def __init__(
        self,
        agent_id: str,
        questions: list[ScriptedQuestion],
    ) -> None:
        if not questions:
            raise ValueError("scripted agent requires at least one question")
        self._agent_id = agent_id
        self.questions = [item.model_copy(deep=True) for item in questions]

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def create(self) -> ScriptedInterviewSession:
        return ScriptedInterviewSession(self.questions)
