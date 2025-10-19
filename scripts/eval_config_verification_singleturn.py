#!/usr/bin/env python3
"""
Reproducible evaluator for sv-env-config-verification.

- Runs the E2 environment with a list of models
- Writes artifacts under outputs/evals/sv-env-config-verification--<model>/<run_id>/
  - metadata.json
  - results.jsonl

Usage:
  python scripts/eval_config_verification.py \
    --models gpt-5-mini,gpt-4.1-mini \
    --num-examples 2 \
    --include-tools true
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, cast

# Ensure local repo modules are importable (sv_shared etc.)
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Import eval utilities for early stopping
from scripts.eval_utils import EarlyStopError, ErrorTracker  # noqa: E402
from scripts.model_router import get_client_for_model  # noqa: E402

# pylint: disable=wrong-import-position
from sv_env_config_verification import (  # type: ignore[import]  # noqa: E402
    load_environment,
    reward_config_auditing,
)

# OpenAI client is imported in model_router.py


# pylint: disable=broad-exception-caught
def _which(cmd: str) -> str | None:
    try:
        res = subprocess.run(
            ["bash", "-lc", f"command -v {cmd}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip() or None
    except Exception:
        return None


def _cmd_version(cmd: str, args: List[str]) -> str | None:
    if not _which(cmd):
        return None
    try:
        res = subprocess.run([cmd, *args], capture_output=True, text=True, check=False)
        return (res.stdout or res.stderr).strip() or None
    except Exception:
        return None


def _git_commit() -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
        )
        return res.stdout.strip() or None
    except Exception:
        return None


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def parse_models(s: str) -> List[str]:
    """Parse comma-separated list of models."""
    return [m.strip() for m in s.replace(" ", "").split(",") if m.strip()]


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate sv-env-config-verification across models and save artifacts"
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated list of model ids (e.g., gpt-5-mini,gpt-4.1-mini)",
    )
    parser.add_argument(
        "--num-examples",
        type=int,
        default=2,
        help="Number of examples to evaluate (max 2 in builtin dataset)",
    )
    parser.add_argument(
        "--include-tools",
        type=str,
        default="true",
        help="Whether to include tools (true/false)",
    )
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature (optional)")
    parser.add_argument("--max-tokens", type=int, default=None, help="Max tokens per completion (optional)")
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=3,
        help="Stop evaluation after this many consecutive errors (default: 3). "
        "Set to 0 to disable early stopping.",
    )
    args = parser.parse_args()

    include_tools = str(args.include_tools).lower() in {"1", "true", "yes"}
    models = parse_models(args.models)

    # Load environment
    env = load_environment(max_examples=args.num_examples, include_tools=include_tools)
    dataset = env.dataset  # type: ignore[attr-defined]
    # Convert Dataset to list for iteration
    if hasattr(dataset, "to_list"):
        dataset = dataset.to_list()  # type: ignore[attr-defined]
    assert dataset is not None, "Dataset should not be None"
    dataset = cast(List[Dict[str, Any]], dataset)
    format_reward = env.parser.get_format_reward_func()  # type: ignore[attr-defined]

    # Output base
    out_base = REPO_ROOT / "outputs" / "evals"
    ensure_dir(out_base)

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Tool versions metadata
    kube_linter_ver = _cmd_version("kube-linter", ["version"]) or None
    semgrep_ver = _cmd_version("semgrep", ["--version"]) or None
    opa_ver = _cmd_version("opa", ["version"]) or None

    for model in models:
        # Get appropriate client for this model
        try:
            client, effective_model = get_client_for_model(model)
        except SystemExit as e:
            print(f"✗ Skipping {model}: {e}")
            continue

        run_id = uuid.uuid4().hex[:8]
        run_dir = out_base / f"sv-env-config-verification--{model}" / run_id
        ensure_dir(run_dir)
        meta_path = run_dir / "metadata.json"
        results_path = run_dir / "results.jsonl"

        metadata: Dict[str, Any] = {
            "environment": "sv-env-config-verification",
            "model": model,
            "effective_model": effective_model,  # Track the actual model name used (e.g., OpenRouter path)
            "timestamp": ts,
            "num_examples": len(dataset),
            "include_tools": include_tools,
            "max_consecutive_errors": args.max_consecutive_errors,
            "git_commit": _git_commit(),
            "tool_versions": {
                "kube_linter": kube_linter_ver,
                "semgrep": semgrep_ver,
                "opa": opa_ver,
            },
        }
        if args.temperature is not None:
            metadata["temperature"] = args.temperature
        if args.max_tokens is not None:
            metadata["max_tokens"] = args.max_tokens
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Initialize error tracker for early stopping
        error_tracker = None
        if args.max_consecutive_errors > 0:
            window_size = max(5, args.max_consecutive_errors)
            error_tracker = ErrorTracker(
                max_consecutive_errors=args.max_consecutive_errors, window_size=window_size
            )

        with results_path.open("w", encoding="utf-8") as f:
            for i, sample in enumerate(dataset):
                question = str(sample.get("question", ""))
                answer = sample.get("answer")  # may be string (JSON) or dict
                system_prompt = getattr(env, "system_prompt", "")

                record: Dict[str, Any] = {
                    "index": i,
                    "prompt": question,
                    "answer": answer,
                }
                try:
                    try:
                        # Build kwargs with only provided parameters
                        kwargs = {
                            "model": effective_model,  # Use the effective model name (mapped for OpenRouter)
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": question},
                            ],
                        }

                        # Only add optional parameters if explicitly provided
                        if args.temperature is not None:
                            kwargs["temperature"] = args.temperature
                        if args.max_tokens is not None:
                            kwargs["max_tokens"] = args.max_tokens

                        resp = client.chat.completions.create(**kwargs)
                        text = resp.choices[0].message.content if resp.choices else ""
                        record["completion"] = text

                        # Track success
                        if error_tracker:
                            error_tracker.record_success()

                    except Exception as e:  # network or auth error
                        record["completion_error"] = str(e)
                        record["completion"] = ""
                        text = ""

                        # Track the error for early stopping (may raise EarlyStopError)
                        if error_tracker:
                            error_tracker.record_error(str(e), index=i)

                except EarlyStopError as e:
                    print(f"\n✗ Early stopping triggered for {model}:")
                    print(f"  {e}")
                    if error_tracker:
                        stats = error_tracker.get_stats()
                        print(f"  Stats: {stats['total_errors']}/{stats['total_samples']} samples failed")
                    break  # Exit the dataset loop

                # Rewards
                try:
                    r_main = float(reward_config_auditing(text, answer))
                except Exception as e:
                    r_main = 0.0
                    record["reward_error"] = str(e)
                try:
                    r_format = float(format_reward(text, answer=answer))
                except Exception:
                    r_format = 0.0
                record["rewards"] = {
                    "reward_config_auditing": r_main,
                    "format_reward": r_format,
                }

                f.write(json.dumps(record) + "\n")

        print(f"✓ Saved artifacts for {model} -> {run_dir}")


if __name__ == "__main__":
    main()
