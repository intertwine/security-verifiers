#!/usr/bin/env python3
"""SV-Bench v0.1 release package checker."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH) PRIVATE KEY)")
REQUIRED_FILES = [
    "SVBENCH_STATUS.md",
    "SVBENCH.md",
    "plans/ROADMAP-2026-SUITE.md",
    "bench/schemas/run_manifest.schema.json",
    "bench/fixtures/e1_run_manifest.json",
    "bench/fixtures/e2_run_manifest.json",
    "bench/leaderboard/v0.1.schema.json",
    "bench/leaderboard/v0.1.json",
    "datasets/HELDOUT_POLICY.md",
    "results/v0.1_baselines.md",
    "results/v0.1_training.md",
    "reports/SVBENCH_v0.1_technical_report.md",
]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _check_required_files(errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")


def _check_scope_docs(errors: list[str]) -> None:
    docs = "\n".join(_read(rel) for rel in ("README.md", "SVBENCH_STATUS.md", "SVBENCH.md"))
    lowered = docs.lower()
    if "v0.1" not in lowered or "e1" not in lowered or "e2" not in lowered:
        errors.append("docs do not clearly describe v0.1 E1/E2 scope")
    if "e5/e6" not in lowered and "e5" not in lowered:
        errors.append("docs do not mention E5/E6 publication guardrails")
    if "only e1/e2" not in lowered and "e1/e2 only" not in lowered and "e1 and e2 only" not in lowered:
        errors.append("docs do not explicitly state v0.1 includes only E1/E2")


def _check_leaderboard(errors: list[str]) -> None:
    schema_path = REPO_ROOT / "bench/leaderboard/v0.1.schema.json"
    data_path = REPO_ROOT / "bench/leaderboard/v0.1.json"
    if not schema_path.exists() or not data_path.exists():
        return
    try:
        jsonschema.validate(
            json.loads(data_path.read_text(encoding="utf-8")),
            json.loads(schema_path.read_text(encoding="utf-8")),
        )
    except jsonschema.ValidationError as exc:
        errors.append(f"leaderboard schema validation failed: {exc.message}")


def _check_public_data(errors: list[str]) -> None:
    for rel in (
        "datasets/public_mini/e5_sanitized.jsonl",
        "datasets/public_mini/e6_sanitized.jsonl",
        "docs/redteam-data-publication-policy.md",
    ):
        path = REPO_ROOT / rel
        if not path.exists():
            errors.append(f"missing safety/publication file: {rel}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "sanitized" not in text:
            errors.append(f"{rel} does not state sanitized handling")
    unsafe_public = [
        "raw harmful corpus",
        "weaponized payload",
        "real exploit instructions",
        "malware payload",
        "ransomware",
        "backdoor",
        "botnet",
        "explosive",
        "credential theft",
        "phishing kit",
        "ddos",
    ]
    for path in (REPO_ROOT / "datasets/public_mini").glob("e[56]*.jsonl"):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in unsafe_public:
            if phrase in text:
                errors.append(f"public mini data contains forbidden phrase `{phrase}` in {path}")


def _check_secrets(errors: list[str]) -> None:
    scan_roots = [
        "README.md",
        "SVBENCH_STATUS.md",
        "SVBENCH.md",
        "configs",
        "bench",
        "datasets",
        "docs",
        "results",
        "reports",
    ]
    for rel in scan_roots:
        path = REPO_ROOT / rel
        paths = [path] if path.is_file() else list(path.glob("**/*"))
        for item in paths:
            if not item.is_file() or item.suffix in {".pyc", ".png", ".jpg", ".jpeg"}:
                continue
            text = item.read_text(encoding="utf-8", errors="ignore")
            if SECRET_RE.search(text):
                errors.append(f"possible secret in {item.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SV-Bench v0.1 release package.")
    parser.add_argument("--strict", action="store_true", help="Reserved for CI; currently same checks.")
    args = parser.parse_args()
    del args

    errors: list[str] = []
    _check_required_files(errors)
    if not errors:
        _check_scope_docs(errors)
        _check_leaderboard(errors)
        _check_public_data(errors)
        _check_secrets(errors)

    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1
    print("✓ SV-Bench v0.1 release package checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
