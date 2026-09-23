from pathlib import Path

from voxrubric.arena_config import load_arena_config


ROOT = Path(__file__).parents[1]


def test_example_arena_yaml_is_valid():
    config = load_arena_config(ROOT / "examples/arena.yaml")
    assert config.id == "backend-baselines-v1"
    assert config.repetitions == 3
    assert len(config.agents) == 2
    assert config.persona.answer_style.value == "code_switched"
    assert {d.id for d in config.rubric.dimensions} == {
        "python",
        "debugging",
        "systems",
    }
