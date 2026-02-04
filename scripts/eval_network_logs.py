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
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Imports below rely on the repo root being on sys.path (see bootstrap above).
from bench.report import generate_report_md, generate_summary, load_results  # noqa: E402
from eval_utils import (  # noqa: E402
    EarlyStopError,
    ErrorTracker,
    build_base_metadata,
)
from model_router import get_client_for_model  # noqa: E402
from sv_shared import (  # type: ignore  # noqa: F401, E402
    reward_accuracy,
    reward_asymmetric_cost,
    reward_calibration,
    weave_init,
)

# Import E1 environment, falling back to source path when not installed as a package
try:
    from sv_env_network_logs import load_environment  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(REPO_ROOT / "environments" / "sv-env-network-logs"))
    from sv_env_network_logs import load_environment  # type: ignore

# OpenAI client is imported in model_router.py


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
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: None, non-deterministic)",
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

        # Resolve dataset path for revision hash
        env_root = REPO_ROOT / "environments" / "sv-env-network-logs"
        dataset_path = env_root / "data" / args.dataset
        if not dataset_path.exists():
            dataset_path = Path(args.dataset)  # Try absolute path

        metadata = build_base_metadata(
            environment="sv-env-network-logs",
            model=model,
            effective_model=effective_model,
            dataset=args.dataset,
            timestamp=ts,
            num_examples=len(dataset),
            repo_root=REPO_ROOT,
            dataset_path=dataset_path if dataset_path.exists() else None,
            seed=args.seed,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            max_consecutive_errors=args.max_consecutive_errors,
        )
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

        # Generate schema-stable report artifacts (WP1)
        print("  Generating summary.json + report.md (svbench_report)...")
        try:
            results, meta = load_results(run_dir)
            summary = generate_summary("e1", results, meta, run_id=run_dir.name, strict=False)
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            (run_dir / "report.md").write_text(generate_report_md(summary), encoding="utf-8")
        except Exception as exc:
            print(f"  ✗ Failed to generate report artifacts: {exc}")


if __name__ == "__main__":
    main()
