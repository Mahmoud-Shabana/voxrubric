from __future__ import annotations

from pathlib import Path

import yaml

from .benchmark_models import BenchmarkCase, BenchmarkSuite, CaseResult, SuiteResult
from .config import load_rubric, load_trace
from .runner import default_evaluator


def load_suite(path: str | Path) -> BenchmarkSuite:
    path = Path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return BenchmarkSuite.model_validate(payload)


def _metric_map(report):
    return {metric.metric: metric for metric in report.metrics}


def run_case(case: BenchmarkCase, *, base_dir: Path, latency_budget_ms: int = 2000) -> CaseResult:
    trace = load_trace(base_dir / case.trace)
    rubric = load_rubric(base_dir / case.rubric)
    report = default_evaluator(latency_budget_ms=latency_budget_ms).run(trace, rubric)
    metrics = _metric_map(report)
    failures: list[str] = []

    for expected in case.expectations:
        actual = metrics.get(expected.metric)
        if actual is None:
            failures.append(f"{expected.metric}: metric missing")
            continue
        if expected.passed is not None and actual.passed is not expected.passed:
            failures.append(f"{expected.metric}: expected passed={expected.passed}, got {actual.passed}")
        if expected.min_value is not None:
            if actual.value is None or actual.value < expected.min_value:
                failures.append(f"{expected.metric}: expected value >= {expected.min_value}, got {actual.value}")
        if expected.max_value is not None:
            if actual.value is None or actual.value > expected.max_value:
                failures.append(f"{expected.metric}: expected value <= {expected.max_value}, got {actual.value}")

    return CaseResult(case_id=case.id, passed=not failures, failures=failures)


def run_suite(path: str | Path, *, latency_budget_ms: int = 2000) -> SuiteResult:
    path = Path(path)
    suite = load_suite(path)
    results = [
        run_case(case, base_dir=path.parent, latency_budget_ms=latency_budget_ms)
        for case in suite.cases
    ]
    return SuiteResult(suite_id=suite.id, passed=all(case.passed for case in results), cases=results)
