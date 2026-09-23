from __future__ import annotations

from pydantic import Field, model_validator

from .models import StrictModel


class MetricExpectation(StrictModel):
    metric: str
    min_value: float | None = None
    max_value: float | None = None
    passed: bool | None = None

    @model_validator(mode="after")
    def has_assertion(self) -> "MetricExpectation":
        if self.min_value is None and self.max_value is None and self.passed is None:
            raise ValueError("expectation must define min_value, max_value, or passed")
        return self


class BenchmarkCase(StrictModel):
    id: str = Field(min_length=1)
    description: str
    trace: str
    rubric: str
    expectations: list[MetricExpectation] = Field(min_length=1)


class BenchmarkSuite(StrictModel):
    id: str
    title: str
    cases: list[BenchmarkCase] = Field(min_length=1)


class CaseResult(StrictModel):
    case_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)


class SuiteResult(StrictModel):
    suite_id: str
    passed: bool
    cases: list[CaseResult]
