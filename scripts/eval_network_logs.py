#!/usr/bin/env python3
"""
Reproducible evaluator for sv-env-network-logs (E1).

- Runs the E1 environment with a list of models
- Writes artifacts under outputs/evals/sv-env-network-logs--<model>/<run_id>/
  - metadata.json
  - results.jsonl

Usage:
  python scripts/eval_network_logs.py \
    --models gpt-5-mini,gpt-4.1-mini \
    --num-examples 10
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

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Import E1 environment, falling back to source path when not installed as a package
try:
    from sv_env_network_logs import load_environment  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(REPO_ROOT / "environments" / "sv-env-network-logs"))
    from sv_env_network_logs import load_environment  # type: ignore

from sv_shared import (  # noqa: E402
    reward_accuracy,
    reward_asymmetric_cost,
    reward_calibration,
)  # type: ignore

try:
    from openai import OpenAI
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"The 'openai' package is required: {exc}") from exc


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
        description="Evaluate sv-env-network-logs across models and save artifacts"
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated list of model ids (e.g., gpt-5-mini,gpt-4.1-mini)",
    )
    parser.add_argument("--num-examples", type=int, default=10, help="Number of examples to evaluate")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens per completion")
    args = parser.parse_args()

    models = parse_models(args.models)

    # Load environment
    env = load_environment(max_examples=args.num_examples)
    dataset = env.dataset  # type: ignore[attr-defined]
    # Convert Dataset to list for iteration
    if hasattr(dataset, "to_list"):
        dataset = dataset.to_list()  # type: ignore[attr-defined]
    assert dataset is not None, "Dataset should not be None"
    dataset = cast(List[Dict[str, Any]], dataset)
    parser_cls = env.parser  # type: ignore[attr-defined]
    format_reward = parser_cls.get_format_reward_func()

    # OpenAI client
    client = OpenAI()

    out_base = REPO_ROOT / "outputs" / "evals"
    ensure_dir(out_base)

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for model in models:
        run_id = uuid.uuid4().hex[:8]
        run_dir = out_base / f"sv-env-network-logs--{model}" / run_id
        ensure_dir(run_dir)
        meta_path = run_dir / "metadata.json"
        results_path = run_dir / "results.jsonl"

        metadata: Dict[str, Any] = {
            "environment": "sv-env-network-logs",
            "model": model,
            "timestamp": ts,
            "num_examples": len(dataset),
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "git_commit": _git_commit(),
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        with results_path.open("w", encoding="utf-8") as f:
            for i, sample in enumerate(dataset):
                question = str(sample.get("question", ""))
                answer = str(sample.get("answer", ""))
                system_prompt = getattr(env, "system_prompt", "You are a network security analyst...")

                record: Dict[str, Any] = {
                    "index": i,
                    "prompt": question,
                    "answer": answer,
                }

                try:
                    # Try max_tokens; if rejected, retry with max_completion_tokens
                    try:
                        resp = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": question},
                            ],
                            temperature=args.temperature,
                            max_tokens=args.max_tokens,
                        )
                    except Exception as e1:
                        if "max_tokens" in str(e1) and "max_completion_tokens" in str(e1):
                            resp = client.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": question},
                                ],
                                temperature=args.temperature,
                                max_completion_tokens=args.max_tokens,
                            )
                        else:
                            raise
                    text = resp.choices[0].message.content if resp.choices else ""
                    record["completion"] = text
                except Exception as e:
                    record["completion_error"] = str(e)
                    record["completion"] = ""
                    text = ""

                # Rewards
                try:
                    r_acc = float(reward_accuracy(completion=text, answer=answer, parser=parser_cls))
                except Exception:
                    r_acc = 0.0
                try:
                    r_cal = float(reward_calibration(completion=text, answer=answer, parser=parser_cls))
                except Exception:
                    r_cal = 0.0
                try:
                    r_cost = float(reward_asymmetric_cost(completion=text, answer=answer, parser=parser_cls))
                except Exception:
                    r_cost = 0.0
                try:
                    r_format = float(format_reward(text, answer=answer))
                except Exception:
                    r_format = 0.0

                record["rewards"] = {
                    "reward_accuracy": r_acc,
                    "reward_calibration": r_cal,
                    "reward_asymmetric_cost": r_cost,
                    "format_reward": r_format,
                }

                f.write(json.dumps(record) + "\n")

        print(f"✓ Saved artifacts for {model} -> {run_dir}")


if __name__ == "__main__":
    main()
