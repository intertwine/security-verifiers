from __future__ import annotations

import json
from pathlib import Path

import pytest
from bench.run_manifest import validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_fixtures_validate() -> None:
    for rel in ("bench/fixtures/e1_run_manifest.json", "bench/fixtures/e2_run_manifest.json"):
        validate_manifest(json.loads((REPO_ROOT / rel).read_text(encoding="utf-8")))


def test_manifest_missing_required_field_has_useful_error() -> None:
    manifest = json.loads((REPO_ROOT / "bench/fixtures/e1_run_manifest.json").read_text(encoding="utf-8"))
    manifest.pop("run_id")
    with pytest.raises(ValueError, match="run_id"):
        validate_manifest(manifest)


def test_hosted_manifest_requires_hosted_fields() -> None:
    manifest = json.loads((REPO_ROOT / "bench/fixtures/e1_run_manifest.json").read_text(encoding="utf-8"))
    manifest["platform_mode"] = "hosted"
    with pytest.raises(ValueError, match="prime_run_id"):
        validate_manifest(manifest)
