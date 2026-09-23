from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Speaker(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    SYSTEM = "system"


class Turn(StrictModel):
    id: str = Field(min_length=1)
    speaker: Speaker
    text: str = ""
    started_at_ms: int | None = Field(default=None, ge=0)
    ended_at_ms: int | None = Field(default=None, ge=0)
    response_latency_ms: int | None = Field(default=None, ge=0)
    parent_turn_id: str | None = None
    rubric_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_times(self) -> "Turn":
        if self.started_at_ms is not None and self.ended_at_ms is not None:
            if self.ended_at_ms < self.started_at_ms:
                raise ValueError("ended_at_ms must be >= started_at_ms")
        return self


class EvidenceRef(StrictModel):
    turn_id: str
    quote: str = Field(min_length=1)
    rationale: str | None = None


class DimensionScore(StrictModel):
    dimension: str
    score: float = Field(ge=0)
    max_score: float = Field(default=10, gt=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    rationale: str | None = None

    @model_validator(mode="after")
    def score_within_range(self) -> "DimensionScore":
        if self.score > self.max_score:
            raise ValueError("score cannot exceed max_score")
        return self


class InterviewScorecard(StrictModel):
    judge_id: str = "unknown"
    dimensions: list[DimensionScore]
    metadata: dict[str, Any] = Field(default_factory=dict)


class RubricDimension(StrictModel):
    id: str = Field(min_length=1)
    description: str
    weight: float = Field(default=1.0, gt=0)
    required: bool = True


class Rubric(StrictModel):
    id: str
    title: str
    dimensions: list[RubricDimension]

    @model_validator(mode="after")
    def unique_dimensions(self) -> "Rubric":
        ids = [d.id for d in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric dimension ids must be unique")
        return self


class InterviewTrace(StrictModel):
    session_id: str
    role: str
    locale: str = "en"
    turns: list[Turn]
    scorecards: list[InterviewScorecard] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_turn_graph(self) -> "InterviewTrace":
        ids = [t.id for t in self.turns]
        if len(ids) != len(set(ids)):
            raise ValueError("turn ids must be unique")
        id_set = set(ids)
        for turn in self.turns:
            if turn.parent_turn_id and turn.parent_turn_id not in id_set:
                raise ValueError(f"unknown parent_turn_id: {turn.parent_turn_id}")
        return self


class AgentUtterance(StrictModel):
    text: str
    rubric_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_followup: bool = False
    completes_interview: bool = False


class MetricResult(StrictModel):
    metric: str
    value: float | None = None
    unit: str | None = None
    passed: bool | None = None
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(StrictModel):
    schema_version: str = "1.0"
    session_id: str
    role: str
    locale: str
    metrics: list[MetricResult]
    metadata: dict[str, Any] = Field(default_factory=dict)
