from pathlib import Path

import pytest

from voxrubric.arena_config import load_arena_config


def test_arena_yaml_can_mix_scripted_and_nora_agents(tmp_path: Path):
    config_path = tmp_path / "arena.yaml"
    config_path.write_text(
        """
id: mixed-arena
role: Backend Engineer
locale: en
repetitions: 2

rubric:
  id: backend
  title: Backend
  dimensions:
    - id: debugging
      description: Production debugging

persona:
  id: candidate
  skill_level: 4
  answer_style: concrete
  known_topics: [debugging]
  weak_topics: []

agents:
  - id: fixed-baseline
    questions:
      - text: Describe a production incident.
        rubric_tags: [debugging]

nora_agents:
  - id: nora-local
    base_url: http://localhost:8000
    role_description: Evaluate production debugging.
""",
        encoding="utf-8",
    )

    config = load_arena_config(config_path)
    factories = config.factories()

    assert [factory.agent_id for factory in factories] == [
        "fixed-baseline",
        "nora-local",
    ]


def test_arena_rejects_duplicate_ids_across_adapter_types(tmp_path: Path):
    config_path = tmp_path / "arena.yaml"
    config_path.write_text(
        """
id: duplicate-agents
role: Engineer
rubric:
  id: r
  title: r
  dimensions:
    - id: x
      description: x

persona:
  id: p
  skill_level: 3
  answer_style: concrete
  known_topics: [x]
  weak_topics: []

agents:
  - id: duplicate
    questions:
      - text: Question?
        rubric_tags: [x]

nora_agents:
  - id: duplicate
    base_url: http://localhost:8000
""",
        encoding="utf-8",
    )

    config = load_arena_config(config_path)
    with pytest.raises(ValueError, match="unique"):
        config.factories()
