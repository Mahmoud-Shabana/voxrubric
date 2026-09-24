from pathlib import Path

from voxrubric.benchmark import (
    discover_pack,
    load_suite,
    run_pack,
    run_suite,
)

ROOT = Path(__file__).parents[1]


def test_adversarial_suite_passes_expected_failures():
    path = ROOT / "benchmarks/adversarial/suite.yaml"
    suite = load_suite(path)
    assert len(suite.cases) == 6

    result = run_suite(path)
    assert result.passed is True
    assert all(case.passed for case in result.cases)



def test_semantic_calibration_pack_passes_expected_controls_and_failures():
    directory = ROOT / "benchmarks/semantic-calibration"
    suites = discover_pack(directory)

    assert [path.name for path in suites] == [
        "freshness-pack.yaml",
        "state-pack.yaml",
    ]

    result = run_pack(directory)
    assert result.pack_id == "semantic-calibration"
    assert result.passed is True
    assert len(result.suites) == 2
    assert sum(
        len(suite.cases)
        for suite in result.suites
    ) == 10
    assert all(
        case.passed
        for suite in result.suites
        for case in suite.cases
    )



def test_asr_preservation_pack_passes_expected_controls_and_failures():
    directory = ROOT / "benchmarks/asr-preservation"
    suites = discover_pack(directory)

    assert [path.name for path in suites] == [
        "asr-pack.yaml",
    ]

    result = run_pack(directory)
    assert result.pack_id == "asr-preservation"
    assert result.passed is True
    assert len(result.suites) == 1
    assert len(result.suites[0].cases) == 4
    assert all(
        case.passed
        for case in result.suites[0].cases
    )



def test_role_domain_pack_passes_controls_and_expected_failures():
    directory = ROOT / "benchmarks/role-domains"
    suites = discover_pack(directory)

    assert [path.name for path in suites] == [
        "customer-support-pack.yaml",
        "data-analyst-pack.yaml",
        "sre-pack.yaml",
    ]

    result = run_pack(directory)
    assert result.pack_id == "role-domains"
    assert result.passed is True
    assert len(result.suites) == 3
    assert sum(
        len(suite.cases)
        for suite in result.suites
    ) == 6
    assert all(
        case.passed
        for suite in result.suites
        for case in suite.cases
    )
