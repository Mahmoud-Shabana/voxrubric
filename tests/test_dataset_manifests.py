from pathlib import Path

import pytest
import yaml

from voxrubric.datasets import (
    BenchmarkDatasetManifest,
    load_dataset_manifest,
    validate_dataset_manifest,
)


ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    "relative",
    [
        "benchmarks/adversarial/dataset.yaml",
        "benchmarks/semantic-calibration/dataset.yaml",
        "benchmarks/asr-preservation/dataset.yaml",
        "benchmarks/role-domains/dataset.yaml",
    ],
)
def test_bundled_benchmark_dataset_manifests_validate(relative):
    path = ROOT / relative

    manifest = load_dataset_manifest(path)
    result = validate_dataset_manifest(path)

    assert manifest.version == "1.0.0"
    assert result.dataset_id == manifest.id
    assert result.version == manifest.version
    assert result.valid is True
    assert result.files_checked == len(manifest.files)
    assert result.problems == []
    assert len(result.content_sha256) == 64


def _manifest_payload(*, file_path: str = "sample.json"):
    return {
        "schema_version": "1.0",
        "id": "fixture",
        "version": "1.0.0",
        "title": "Fixture Dataset",
        "description": "Test dataset manifest.",
        "license": "Apache-2.0",
        "languages": ["en"],
        "domains": ["test"],
        "intended_use": ["Regression testing."],
        "out_of_scope": ["Production decisions."],
        "source_policy": "Synthetic fixture.",
        "known_limitations": ["Tiny test fixture."],
        "card": "DATASET_CARD.md",
        "files": [
            {
                "path": file_path,
                "role": "trace",
            }
        ],
    }


def test_dataset_manifest_rejects_parent_traversal():
    with pytest.raises(
        ValueError,
        match="may not traverse parents",
    ):
        BenchmarkDatasetManifest.model_validate(
            _manifest_payload(
                file_path="../outside.json",
            )
        )


def test_dataset_manifest_reports_sha256_mismatch(tmp_path: Path):
    (tmp_path / "DATASET_CARD.md").write_text(
        "# Fixture\n",
        encoding="utf-8",
    )
    (tmp_path / "sample.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    payload = _manifest_payload()
    payload["files"][0]["sha256"] = "0" * 64
    manifest_path = tmp_path / "dataset.yaml"
    manifest_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    result = validate_dataset_manifest(manifest_path)

    assert result.valid is False
    assert result.files_checked == 1
    assert "sha256 mismatch" in result.problems[0]


def test_dataset_fingerprint_changes_with_file_content(tmp_path: Path):
    (tmp_path / "DATASET_CARD.md").write_text(
        "# Fixture\n",
        encoding="utf-8",
    )
    data_path = tmp_path / "sample.json"
    data_path.write_text(
        '{"value": 1}\n',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "dataset.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            _manifest_payload(),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    first = validate_dataset_manifest(manifest_path)
    data_path.write_text(
        '{"value": 2}\n',
        encoding="utf-8",
    )
    second = validate_dataset_manifest(manifest_path)

    assert first.valid is True
    assert second.valid is True
    assert first.content_sha256 != second.content_sha256
