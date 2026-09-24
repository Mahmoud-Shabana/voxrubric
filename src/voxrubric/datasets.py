from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from .models import InterviewTrace, StrictModel


_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class BenchmarkDatasetFile(StrictModel):
    path: str = Field(min_length=1)
    role: Literal[
        "suite",
        "trace",
        "rubric",
        "documentation",
        "data",
    ]
    sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def safe_relative_path(self) -> "BenchmarkDatasetFile":
        path = Path(self.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(
                "dataset file paths must be relative and may not traverse parents"
            )
        return self


class BenchmarkDatasetManifest(StrictModel):
    schema_version: str = "1.0"
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    license: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    domains: list[str] = Field(min_length=1)
    intended_use: list[str] = Field(min_length=1)
    out_of_scope: list[str] = Field(min_length=1)
    source_policy: str = Field(min_length=1)
    known_limitations: list[str] = Field(min_length=1)
    card: str = "DATASET_CARD.md"
    files: list[BenchmarkDatasetFile] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_manifest(self) -> "BenchmarkDatasetManifest":
        if not _SEMVER.match(self.version):
            raise ValueError(
                "dataset version must use semantic versioning"
            )
        card = Path(self.card)
        if card.is_absolute() or ".." in card.parts:
            raise ValueError(
                "dataset card path must be relative and may not traverse parents"
            )
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError(
                "dataset file paths must be unique"
            )
        return self


class DatasetValidationResult(StrictModel):
    dataset_id: str
    version: str
    valid: bool
    files_checked: int
    content_sha256: str
    problems: list[str] = Field(default_factory=list)


def load_jsonl(path: str | Path) -> list[InterviewTrace]:
    traces: list[InterviewTrace] = []
    for line_no, raw in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            traces.append(
                InterviewTrace.model_validate(
                    json.loads(raw)
                )
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid JSONL record at line {line_no}: {exc}"
            ) from exc
    return traces


def load_dataset_manifest(
    path: str | Path,
) -> BenchmarkDatasetManifest:
    manifest_path = Path(path)
    payload = yaml.safe_load(
        manifest_path.read_text(encoding="utf-8")
    )
    return BenchmarkDatasetManifest.model_validate(payload)


def validate_dataset_manifest(
    path: str | Path,
) -> DatasetValidationResult:
    manifest_path = Path(path)
    manifest = load_dataset_manifest(manifest_path)
    root = manifest_path.parent.resolve()
    problems: list[str] = []
    digest = hashlib.sha256()

    digest.update(
        manifest.model_dump_json(
            exclude_none=False,
        ).encode("utf-8")
    )

    card_path = (root / manifest.card).resolve()
    if not _within_root(root, card_path):
        problems.append(
            f"dataset card escapes dataset root: {manifest.card}"
        )
    elif not card_path.is_file():
        problems.append(
            f"dataset card is missing: {manifest.card}"
        )
    else:
        digest.update(manifest.card.encode("utf-8"))
        digest.update(card_path.read_bytes())

    files_checked = 0
    for item in sorted(
        manifest.files,
        key=lambda value: value.path,
    ):
        candidate = (root / item.path).resolve()
        if not _within_root(root, candidate):
            problems.append(
                f"dataset file escapes dataset root: {item.path}"
            )
            continue
        if not candidate.is_file():
            problems.append(
                f"dataset file is missing: {item.path}"
            )
            continue

        data = candidate.read_bytes()
        files_checked += 1
        digest.update(item.path.encode("utf-8"))
        digest.update(data)

        if item.sha256 is not None:
            actual = hashlib.sha256(data).hexdigest()
            if actual != item.sha256:
                problems.append(
                    f"sha256 mismatch for {item.path}: "
                    f"expected {item.sha256}, got {actual}"
                )

    return DatasetValidationResult(
        dataset_id=manifest.id,
        version=manifest.version,
        valid=not problems,
        files_checked=files_checked,
        content_sha256=digest.hexdigest(),
        problems=problems,
    )


def _within_root(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True
