from pathlib import Path

from typer.testing import CliRunner

from voxrubric.cli import app


ROOT = Path(__file__).parents[1]
runner = CliRunner()


def test_release_cli_smoke_covers_eval_benchmark_arena_and_html(tmp_path: Path):
    evaluation_html = tmp_path / "evaluation.html"
    eval_result = runner.invoke(
        app,
        [
            "eval",
            "--trace",
            str(ROOT / "benchmarks/nora-integration/nora-export.json"),
            "--rubric",
            str(ROOT / "benchmarks/nora-integration/rubric.yaml"),
            "--out",
            str(evaluation_html),
        ],
    )
    assert eval_result.exit_code == 0, eval_result.stdout
    assert evaluation_html.is_file()
    assert "<html" in evaluation_html.read_text(
        encoding="utf-8"
    ).lower()

    benchmark_json = tmp_path / "benchmark.json"
    benchmark_html = tmp_path / "benchmark.html"
    benchmark_result = runner.invoke(
        app,
        [
            "benchmark",
            str(ROOT / "benchmarks/adversarial/suite.yaml"),
            "--out",
            str(benchmark_json),
            "--html-out",
            str(benchmark_html),
        ],
    )
    assert benchmark_result.exit_code == 0, benchmark_result.stdout
    assert benchmark_json.is_file()
    assert benchmark_html.is_file()
    assert '"passed": true' in benchmark_json.read_text(
        encoding="utf-8"
    ).lower()
    assert "<html" in benchmark_html.read_text(
        encoding="utf-8"
    ).lower()

    arena_json = tmp_path / "arena.json"
    arena_html = tmp_path / "arena.html"
    arena_result = runner.invoke(
        app,
        [
            "arena",
            str(ROOT / "examples/arena.yaml"),
            "--out",
            str(arena_json),
            "--html-out",
            str(arena_html),
        ],
    )
    assert arena_result.exit_code == 0, arena_result.stdout
    assert arena_json.is_file()
    assert arena_html.is_file()
    assert '"scenario_id": "backend-baselines-v1"' in (
        arena_json.read_text(encoding="utf-8")
    )
    assert "<html" in arena_html.read_text(
        encoding="utf-8"
    ).lower()
