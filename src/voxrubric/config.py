from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import InterviewTrace, Rubric


def _load(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def load_trace(path: str | Path) -> InterviewTrace:
    return InterviewTrace.model_validate(_load(path))


def load_rubric(path: str | Path) -> Rubric:
    return Rubric.model_validate(_load(path))
