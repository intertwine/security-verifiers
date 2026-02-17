#!/usr/bin/env python3
"""Normalize hosted eval metadata into SV-Bench report-compatible layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Hosted metadata.json path")
    parser.add_argument("--output", required=True, help="Output metadata.json path")
    parser.add_argument(
        "--environment", required=True, help="sv-env-network-logs or sv-env-config-verification"
    )
    parser.add_argument("--dataset", required=True, help="Dataset name")
    args = parser.parse_args()

    source = load_json(Path(args.input))

    normalized = {
        "environment": args.environment,
        "env_version": source.get("env_version") or source.get("environment_version"),
        "model": source.get("model") or source.get("model_id"),
        "effective_model": source.get("effective_model") or source.get("model_revision"),
        "dataset": args.dataset,
        "dataset_revision": source.get("dataset_revision") or source.get("dataset_sha"),
        "timestamp": source.get("timestamp") or source.get("created_at"),
        "num_examples": source.get("num_examples") or source.get("n_examples"),
        "git_commit": source.get("git_commit") or source.get("repo_sha"),
        "python_version": source.get("python_version"),
        "verifiers_version": source.get("verifiers_version"),
        "run_id": source.get("run_id"),
        "platform_metadata": {
            "image": source.get("image"),
            "compute": source.get("compute"),
            "loader_mode": source.get("loader_mode"),
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
