#!/usr/bin/env python3
"""SV-Bench run manifest helpers and validator."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "bench" / "schemas" / "run_manifest.schema.json"

REQUIRED_FIELDS = {
    "run_id",
    "git_sha",
    "timestamp_utc",
    "environment_id",
    "environment_version",
    "dataset_id",
    "dataset_revision",
    "split",
    "model_id",
    "model_revision_or_digest",
    "sampling_params",
    "reward_config_id",
    "reward_config_hash",
    "seed",
    "platform_mode",
    "trainer",
    "max_steps",
    "rollouts_per_example",
    "max_tokens",
    "max_turns",
    "tool_budget",
    "input_artifacts",
    "output_artifacts",
    "metrics_summary_path",
    "results_jsonl_path",
    "metadata_json_path",
    "notes",
}

HOSTED_FIELDS = {"prime_run_id", "team", "compute_profile", "platform_image", "adapter_id"}


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def current_git_sha(repo_root: Path = REPO_ROOT) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_manifest(manifest: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - manifest.keys())
    if missing:
        raise ValueError(f"Manifest missing required fields: {', '.join(missing)}")

    try:
        jsonschema.validate(manifest, load_schema())
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        suffix = f" at {path}" if path else ""
        raise ValueError(f"Manifest schema validation failed{suffix}: {exc.message}") from exc

    if manifest.get("platform_mode") == "hosted":
        hosted_missing = sorted(field for field in HOSTED_FIELDS if not manifest.get(field))
        if hosted_missing:
            raise ValueError("Hosted manifest missing hosted-only fields: " + ", ".join(hosted_missing))


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    validate_manifest(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SV-Bench run manifests.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="Validate one or more manifest files")
    validate_parser.add_argument("paths", nargs="+", help="run_manifest.json paths")
    args = parser.parse_args()

    if args.command == "validate":
        failed = False
        for raw_path in args.paths:
            path = Path(raw_path)
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                validate_manifest(manifest)
            except Exception as exc:
                print(f"✗ {path}: {exc}")
                failed = True
            else:
                print(f"✓ {path}")
        return 1 if failed else 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
