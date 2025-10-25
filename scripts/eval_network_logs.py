#!/usr/bin/env python3
"""
Reproducible evaluator for sv-env-network-logs (E1).

- Runs the E1 environment with a list of models
- Writes artifacts under outputs/evals/sv-env-network-logs--<model>/<run_id>/
  - metadata.json
  - results.jsonl
  - summary.json (aggregated metrics: Acc, ECE, FN%, FP%, Abstain%)

Usage:
  python scripts/eval_network_logs.py \
    --models gpt-5-mini,gpt-5-mini \
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
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Import eval utilities (must be before environment imports to avoid circular deps)
from eval_utils import EarlyStopError, ErrorTracker  # noqa: E402
from generate_e1_eval_report import analyze_run  # noqa: E402
from model_router import get_client_for_model  # noqa: E402

# Initialize Weave before importing environments for automatic tracing
# Note: weave_init is imported but its initialization happens automatically
from sv_shared import weave_init  # type: ignore  # noqa: F401, E402

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
        help="Comma-separated list of model ids (e.g., gpt-5-mini,gpt-5-mini)",
    )
    parser.add_argument("--num-examples", type=int, default=10, help="Number of examples to evaluate")
    parser.add_argument(
        "--dataset",
        type=str,
        default="iot23-train-dev-test-v1.jsonl",
        help=(
            "Local JSONL dataset file (absolute or relative to env root). "
            "Build datasets with 'make data-e1' before use. "
            "Available: iot23-train-dev-test-v1.jsonl (N=1800), "
            "cic-ids-2017-ood-v1.jsonl (N=600), unsw-nb15-ood-v1.jsonl (N=600)"
        ),
    )
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max tokens per completion")
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=3,
        help="Stop evaluation after this many consecutive errors (default: 3). "
        "Set to 0 to disable early stopping.",
    )
    args = parser.parse_args()

    models = parse_models(args.models)

    # Load environment
    env = load_environment(dataset_name=args.dataset, max_examples=args.num_examples)
    dataset = env.dataset  # type: ignore[attr-defined]
    # Convert Dataset to list for iteration
    if hasattr(dataset, "to_list"):
        dataset = dataset.to_list()  # type: ignore[attr-defined]
    assert dataset is not None, "Dataset should not be None"
    dataset = cast(List[Dict[str, Any]], dataset)
    parser_cls = env.parser  # type: ignore[attr-defined]
    format_reward = parser_cls.get_format_reward_func()

    out_base = REPO_ROOT / "outputs" / "evals"
    ensure_dir(out_base)

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for model in models:
        # Get appropriate client for this model
        try:
            client, effective_model = get_client_for_model(model)
        except SystemExit as e:
            print(f"✗ Skipping {model}: {e}")
            continue

        run_id = uuid.uuid4().hex[:8]
        run_dir = out_base / f"sv-env-network-logs--{model}" / run_id
        ensure_dir(run_dir)
        meta_path = run_dir / "metadata.json"
        results_path = run_dir / "results.jsonl"

        metadata: Dict[str, Any] = {
            "environment": "sv-env-network-logs",
            "model": model,
            "effective_model": effective_model,  # Track the actual model name used (e.g., OpenRouter path)
            "dataset": args.dataset,
            "timestamp": ts,
            "num_examples": len(dataset),
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "max_consecutive_errors": args.max_consecutive_errors,
            "git_commit": _git_commit(),
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Initialize error tracker for early stopping
        error_tracker = None
        if args.max_consecutive_errors > 0:
            window_size = max(5, args.max_consecutive_errors)
            error_tracker = ErrorTracker(
                max_consecutive_errors=args.max_consecutive_errors, window_size=window_size
            )

        with results_path.open("w", encoding="utf-8") as f:
            try:
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
                        # Build base kwargs
                        base_kwargs = {
                            "model": effective_model,  # Use effective model name
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": question},
                            ],
                        }

                        # GPT-5 and o1 series models have restricted parameter support
                        # - temperature: not supported (only default: 1)
                        # - max_tokens: not supported, use max_completion_tokens instead
                        is_reasoning_model = effective_model.startswith(("gpt-5", "o1-", "o3-"))

                        # Add temperature only for non-reasoning models
                        if not is_reasoning_model:
                            base_kwargs["temperature"] = args.temperature

                        # Add token limit with appropriate parameter name
                        if is_reasoning_model:
                            # Reasoning models require max_completion_tokens
                            base_kwargs["max_completion_tokens"] = args.max_tokens
                        else:
                            # Legacy models use max_tokens
                            base_kwargs["max_tokens"] = args.max_tokens

                        # Make API call with proper parameters
                        resp = client.chat.completions.create(**base_kwargs)
                        text = resp.choices[0].message.content if resp.choices else ""
                        record["completion"] = text

                        # Track success
                        if error_tracker:
                            error_tracker.record_success()

                    except Exception as e:
                        error_msg = str(e)
                        record["completion_error"] = error_msg
                        record["completion"] = ""
                        text = ""

                        # Track error and check for early stop
                        if error_tracker:
                            error_tracker.record_error(error_msg, index=i)

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
                        r_cost = float(
                            reward_asymmetric_cost(completion=text, answer=answer, parser=parser_cls)
                        )  # noqa: E501
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

            except EarlyStopError as e:
                print(f"\n✗ Early stopping triggered for {model}:")
                print(f"  {e}")
                if error_tracker:
                    stats = error_tracker.get_stats()
                    print(f"  Stats: {stats['total_errors']}/{stats['total_samples']} samples failed")
                continue

        print(f"✓ Saved artifacts for {model} -> {run_dir}")

        # Generate summary.json with aggregated metrics
        print("  Generating summary.json...")
        summary = analyze_run(run_dir, write_summary=True)
        if summary:
            print(
                f"  ✓ Summary: Acc={summary['Acc']:.4f}, ECE={summary['ECE']:.4f}, "
                f"FN%={summary['FN%']:.2f}, FP%={summary['FP%']:.2f}, Abstain%={summary['Abstain%']:.2f}"
            )


if __name__ == "__main__":
    main()
