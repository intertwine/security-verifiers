#!/usr/bin/env python3
"""Validate SV-Bench TOML config surfaces."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _validate_rl(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if path.name.endswith("_base.toml"):
        required = ["model", "max_steps", "rollouts_per_example", "trainer"]
    else:
        required = ["model", "max_steps", "rollouts_per_example", "reward_source", "reward_config_id"]
    for field in required:
        if field not in data:
            errors.append(f"missing `{field}`")
    if "sampling" in data and "max_tokens" not in data["sampling"]:
        errors.append("sampling table missing `max_tokens`")
    if path.name in {
        "e1_executable_reward.toml",
        "e1_llm_judge_reward.toml",
        "e1_hybrid_reward.toml",
        "e2_executable_reward.toml",
        "e2_llm_judge_reward.toml",
        "e2_hybrid_reward.toml",
    }:
        if "include" in data:
            errors.append("launchable Prime configs must be self-contained; remove bare include")
        for field in ("trainer", "batch_size", "budget_group"):
            if field not in data:
                errors.append(f"matched-budget config missing `{field}`")
        if "env" not in data:
            errors.append("hosted config missing [[env]] table")
    if path.name.startswith("e2_") and path.name.endswith("_reward.toml"):
        tooling = data.get("tooling", {})
        for field in ("max_turns", "tool_budget", "allowed_tools", "sandbox_mode"):
            if not isinstance(tooling, dict) or field not in tooling:
                errors.append(f"E2 reward config [tooling] missing `{field}`")
    reward_source = data.get("reward_source")
    if reward_source and reward_source not in {"executable", "llm_judge", "hybrid"}:
        errors.append("reward_source must be executable, llm_judge, or hybrid")
    return errors


def _validate_eval(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    eval_table = data.get("eval")
    if not isinstance(eval_table, dict):
        return ["missing [eval] table"]
    for field in ("environment", "seed"):
        if field not in eval_table:
            errors.append(f"[eval] missing `{field}`")
    if "dataset" not in eval_table and "datasets" not in eval_table:
        errors.append("[eval] missing `dataset` or `datasets`")
    return errors


def _validate_ablation(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ablation = data.get("ablation")
    if not isinstance(ablation, dict):
        return ["missing [ablation] table"]
    for field in ("environment", "name", "supported"):
        if field not in ablation:
            errors.append(f"[ablation] missing `{field}`")
    if ablation.get("supported") is False and not ablation.get("unsupported_reason"):
        errors.append("unsupported ablation must document unsupported_reason")
    return errors


def validate_path(path: Path) -> list[str]:
    data = _load(path)
    if "/rl/" in path.as_posix():
        return _validate_rl(path, data)
    if "/eval/" in path.as_posix():
        return _validate_eval(path, data)
    if "/ablations/" in path.as_posix():
        return _validate_ablation(path, data)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SV-Bench TOML configs.")
    parser.add_argument("paths", nargs="*", help="Config paths; defaults to configs/**/*.toml")
    args = parser.parse_args()

    paths = (
        [Path(path) for path in args.paths]
        if args.paths
        else sorted((REPO_ROOT / "configs").glob("**/*.toml"))
    )
    failed = False
    for path in paths:
        try:
            errors = validate_path(path)
        except Exception as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            for error in errors:
                print(f"✗ {path}: {error}")
        else:
            print(f"✓ {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
