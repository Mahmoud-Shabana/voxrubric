from pathlib import Path

from voxrubric.benchmark import load_suite, run_suite

ROOT = Path(__file__).parents[1]


def test_adversarial_suite_passes_expected_failures():
    path = ROOT / "benchmarks/adversarial/suite.yaml"
    suite = load_suite(path)
    assert len(suite.cases) == 5

    result = run_suite(path)
    assert result.passed is True
    assert all(case.passed for case in result.cases)
