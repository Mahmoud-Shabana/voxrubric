from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import InterviewTrace, MetricResult, Rubric


class Metric(ABC):
    name: str

    @abstractmethod
    def evaluate(self, trace: InterviewTrace, rubric: Rubric) -> MetricResult:
        raise NotImplementedError
