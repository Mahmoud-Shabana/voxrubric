from __future__ import annotations

from enum import Enum
from hashlib import sha256

from pydantic import Field

from .models import StrictModel


class AnswerStyle(str, Enum):
    TERSE = "terse"
    CONCRETE = "concrete"
    RAMBLING = "rambling"
    CODE_SWITCHED = "code_switched"


class CandidatePersona(StrictModel):
    id: str
    skill_level: int = Field(ge=1, le=5)
    answer_style: AnswerStyle = AnswerStyle.CONCRETE
    known_topics: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)


class SyntheticCandidate:
    """Deterministic synthetic-candidate fixture for repeatable benchmark runs.

    This is intentionally model-free. It generates controlled behavior profiles so
    agent regressions can be reproduced exactly before adding stochastic simulators.
    """

    def __init__(self, persona: CandidatePersona) -> None:
        self.persona = persona

    def answer(self, question: str, competency: str | None = None) -> str:
        key = competency or "general"
        confident = key in self.persona.known_topics or self.persona.skill_level >= 4
        weak = key in self.persona.weak_topics or self.persona.skill_level <= 2

        if self.persona.answer_style is AnswerStyle.TERSE:
            return "I handled it directly." if confident else "I am not sure."

        if self.persona.answer_style is AnswerStyle.CODE_SWITCHED:
            if weak:
                return f"في موضوع {key} خبرتي محدودة، فكنت بسأل الفريق وأراجع الـ docs قبل التنفيذ."
            return (
                f"في {key} بدأت بقياس المشكلة، وبعدها عملت implementation صغير، "
                "وقارنت الـ metrics قبل وبعد التغيير وراجعت النتيجة مع الفريق."
            )

        if self.persona.answer_style is AnswerStyle.RAMBLING:
            seed = sha256((self.persona.id + question).encode()).hexdigest()[:6]
            return (
                f"We had several moving parts and a lot of context ({seed}). "
                "I discussed options with the team, explored alternatives, and eventually "
                "implemented a change. The main lesson was to validate assumptions."
            )

        if weak:
            return (
                f"My exposure to {key} is limited. I would first reproduce the issue, "
                "read the relevant documentation, and ask for review before making a risky change."
            )
        return (
            f"For {key}, I first established a measurable baseline, changed one variable at a time, "
            "validated the result under realistic load, and documented the trade-off and rollback plan."
        )
