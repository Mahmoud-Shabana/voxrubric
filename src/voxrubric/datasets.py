from __future__ import annotations

import json
from pathlib import Path

from .models import InterviewTrace


def load_jsonl(path: str | Path) -> list[InterviewTrace]:
    traces: list[InterviewTrace] = []
    for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            traces.append(InterviewTrace.model_validate(json.loads(raw)))
        except Exception as exc:  # preserve source line for benchmark debugging
            raise ValueError(f"Invalid JSONL record at line {line_no}: {exc}") from exc
    return traces
