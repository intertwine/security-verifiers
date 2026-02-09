#!/usr/bin/env python3
"""
Cold-Start Analysis for SOAR Feasibility Assessment.

Analyzes existing evaluation runs to quantify the cold-start problem:
- What fraction of examples have zero pass rate at various K?
- How does cold-start severity vary by difficulty, label type, and dataset?
- Is the cold-start gap severe enough to warrant SOAR-style curriculum generation?

This script reads from existing eval outputs (outputs/evals/) and does NOT
require running new evaluations. It re-analyzes stored results to identify
fail@K subsets.

Usage:
    # Analyze all existing E1 runs
    python research/experiments/soar/cold_start_analysis.py --env e1

    # Analyze specific runs with custom K values
    python research/experiments/soar/cold_start_analysis.py \
        --env e1 \
        --run-dirs outputs/evals/sv-env-network-logs--gpt-5-mini/abc123 \
        --k-values 1,4,8,16,32

    # Analyze E2 runs
    python research/experiments/soar/cold_start_analysis.py --env e2

Output:
    research/experiments/soar/results/cold_start_{env}_{timestamp}.json
    research/experiments/soar/results/cold_start_{env}_{timestamp}.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def load_run_results(run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load results.jsonl and metadata.json from a run directory."""
    results_path = run_dir / "results.jsonl"
    meta_path = run_dir / "metadata.json"

    results = []
    if results_path.exists():
        with results_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))

    metadata = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    return results, metadata


def find_run_dirs(env: str, evals_root: Path) -> list[Path]:
    """Find all run directories for a given environment."""
    prefix = f"sv-env-{env}--" if env in ("network-logs", "config-verification") else f"sv-env-{env}--"
    run_dirs = []
    for model_dir in sorted(evals_root.iterdir()):
        if model_dir.is_dir() and model_dir.name.startswith(prefix):
            for run_dir in sorted(model_dir.iterdir()):
                if run_dir.is_dir() and (run_dir / "results.jsonl").exists():
                    run_dirs.append(run_dir)
    return run_dirs


def extract_accuracy(result: dict[str, Any], env: str) -> float | None:
    """Extract the binary accuracy signal from a result record."""
    rewards = result.get("rewards", {})
    if env == "e1":
        return rewards.get("reward_accuracy")
    elif env == "e2":
        # E2 uses different reward keys; check for detection F1 or mean_reward
        if "mean_reward" in rewards:
            return 1.0 if rewards["mean_reward"] > 0.5 else 0.0
        if "reward_config_auditing" in rewards:
            return 1.0 if rewards["reward_config_auditing"] > 0.5 else 0.0
        # Fall back to checking if any positive reward
        total = sum(v for v in rewards.values() if isinstance(v, (int, float)))
        return 1.0 if total > 0.5 else 0.0
    return None


def compute_cold_start_stats(
    results_by_prompt: dict[str, list[float]],
    k_values: list[int],
) -> dict[str, Any]:
    """Compute cold-start statistics across prompts.

    For each prompt, we have multiple results (from different models/runs).
    We compute fail@K = fraction of prompts where ALL K attempts fail.
    """
    stats: dict[str, Any] = {
        "total_unique_prompts": len(results_by_prompt),
        "k_analysis": {},
    }

    for k in k_values:
        fail_at_k = 0
        eligible = 0
        pass_rates = []

        for prompt_key, accuracies in results_by_prompt.items():
            if len(accuracies) < 1:
                continue
            eligible += 1
            # Compute pass rate from available samples
            pass_rate = sum(1 for a in accuracies if a > 0.5) / len(accuracies)
            pass_rates.append(pass_rate)

            # Estimate fail@K: probability that all K samples fail
            # = (1 - pass_rate)^K
            fail_prob = (1.0 - pass_rate) ** k
            if fail_prob > 0.99:  # Effectively zero pass@K
                fail_at_k += 1

        if eligible > 0:
            stats["k_analysis"][str(k)] = {
                "k": k,
                "eligible_prompts": eligible,
                "fail_at_k_count": fail_at_k,
                "fail_at_k_fraction": fail_at_k / eligible,
                "mean_pass_rate": sum(pass_rates) / len(pass_rates) if pass_rates else 0.0,
                "median_pass_rate": sorted(pass_rates)[len(pass_rates) // 2] if pass_rates else 0.0,
                "zero_pass_rate_count": sum(1 for p in pass_rates if p == 0.0),
                "zero_pass_rate_fraction": sum(1 for p in pass_rates if p == 0.0) / eligible,
            }

    return stats


def compute_difficulty_breakdown(
    results: list[dict[str, Any]],
    env: str,
) -> dict[str, Any]:
    """Break down accuracy by answer type / difficulty proxy."""
    breakdown: dict[str, list[float]] = defaultdict(list)

    for r in results:
        acc = extract_accuracy(r, env)
        if acc is None:
            continue

        if env == "e1":
            answer = r.get("answer", "unknown").lower()
            breakdown[f"label:{answer}"].append(acc)
        elif env == "e2":
            # Use number of oracle violations as difficulty proxy
            oracle = r.get("oracle", {})
            n_violations = len(oracle.get("violations", []))
            if n_violations == 0:
                breakdown["violations:0 (clean)"].append(acc)
            elif n_violations <= 2:
                breakdown["violations:1-2 (easy)"].append(acc)
            elif n_violations <= 5:
                breakdown["violations:3-5 (medium)"].append(acc)
            else:
                breakdown["violations:6+ (hard)"].append(acc)

        breakdown["overall"].append(acc)

    result = {}
    for key, accs in sorted(breakdown.items()):
        result[key] = {
            "count": len(accs),
            "mean_accuracy": sum(accs) / len(accs) if accs else 0.0,
            "zero_rate": sum(1 for a in accs if a == 0.0) / len(accs) if accs else 0.0,
        }
    return result


def generate_report_md(stats: dict[str, Any], env: str) -> str:
    """Generate a human-readable markdown report."""
    lines = [
        f"# Cold-Start Analysis: {env.upper()}",
        "",
        f"**Generated:** {stats.get('timestamp', 'N/A')}",
        f"**Runs analyzed:** {stats.get('num_runs', 0)}",
        f"**Models:** {', '.join(stats.get('models', []))}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "This report quantifies the cold-start problem for SOAR feasibility assessment.",
        "A high fail@K fraction indicates that many problems receive zero gradient signal",
        "under standard RLVR, making them candidates for SOAR stepping-stone curriculum.",
        "",
        "## fail@K Analysis",
        "",
        "| K | Eligible Prompts | fail@K Count | fail@K % | Mean Pass Rate | Zero-Pass % |",
        "|---|-----------------|-------------|----------|----------------|-------------|",
    ]

    k_analysis = stats.get("cold_start", {}).get("k_analysis", {})
    for k_str in sorted(k_analysis.keys(), key=lambda x: int(x)):
        ka = k_analysis[k_str]
        lines.append(
            f"| {ka['k']} | {ka['eligible_prompts']} | {ka['fail_at_k_count']} | "
            f"{ka['fail_at_k_fraction']:.1%} | {ka['mean_pass_rate']:.3f} | "
            f"{ka['zero_pass_rate_fraction']:.1%} |"
        )

    lines.extend([
        "",
        "## Difficulty Breakdown",
        "",
        "| Category | Count | Mean Accuracy | Zero-Rate |",
        "|----------|-------|---------------|-----------|",
    ])

    for cat, vals in sorted(stats.get("difficulty_breakdown", {}).items()):
        lines.append(
            f"| {cat} | {vals['count']} | {vals['mean_accuracy']:.3f} | {vals['zero_rate']:.1%} |"
        )

    lines.extend([
        "",
        "## SOAR Feasibility Assessment",
        "",
    ])

    # Compute assessment
    k_analysis_vals = list(k_analysis.values())
    if k_analysis_vals:
        worst_fail = max(ka["fail_at_k_fraction"] for ka in k_analysis_vals)
        zero_pass = k_analysis_vals[0].get("zero_pass_rate_fraction", 0) if k_analysis_vals else 0

        if worst_fail > 0.5 or zero_pass > 0.3:
            lines.append(
                "**Assessment: HIGH cold-start severity.** "
                f"fail@K fraction reaches {worst_fail:.1%} and {zero_pass:.1%} of prompts have "
                "zero pass rate. SOAR curriculum generation is strongly recommended."
            )
        elif worst_fail > 0.2 or zero_pass > 0.1:
            lines.append(
                "**Assessment: MODERATE cold-start severity.** "
                f"fail@K fraction reaches {worst_fail:.1%}. SOAR may help but direct GRPO "
                "with sufficient rollouts could also work."
            )
        else:
            lines.append(
                "**Assessment: LOW cold-start severity.** "
                "Most problems have non-zero pass rates. Direct GRPO should produce learning signal. "
                "SOAR may still help for the hardest subset but is lower priority."
            )
    else:
        lines.append("**Assessment: Insufficient data.** No runs found to analyze.")

    lines.extend([
        "",
        "## Per-Model Breakdown",
        "",
        "| Model | Samples | Mean Accuracy | Zero-Reward % |",
        "|-------|---------|---------------|---------------|",
    ])

    for model, model_stats in sorted(stats.get("per_model", {}).items()):
        lines.append(
            f"| {model} | {model_stats['count']} | "
            f"{model_stats['mean_accuracy']:.3f} | {model_stats['zero_rate']:.1%} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "*Generated by research/experiments/soar/cold_start_analysis.py*",
        "*See SOAR investigation: research/future-experiments/SOAR-INVESTIGATION.md*",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cold-start analysis for SOAR feasibility")
    parser.add_argument(
        "--env",
        choices=["e1", "e2"],
        required=True,
        help="Environment to analyze (e1=network-logs, e2=config-verification)",
    )
    parser.add_argument(
        "--run-dirs",
        nargs="*",
        help="Specific run directories to analyze (default: all runs for env)",
    )
    parser.add_argument(
        "--k-values",
        type=str,
        default="1,4,8,16,32,64,128",
        help="Comma-separated K values for fail@K analysis",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: research/experiments/soar/results/)",
    )
    args = parser.parse_args()

    env_map = {"e1": "network-logs", "e2": "config-verification"}
    env_name = env_map[args.env]
    k_values = [int(k) for k in args.k_values.split(",")]

    evals_root = REPO_ROOT / "outputs" / "evals"
    default_output = REPO_ROOT / "research" / "experiments" / "soar" / "results"
    output_dir = Path(args.output_dir) if args.output_dir else default_output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find runs
    if args.run_dirs:
        run_dirs = [Path(d) for d in args.run_dirs]
    else:
        run_dirs = find_run_dirs(env_name, evals_root)

    if not run_dirs:
        print(f"No evaluation runs found for {args.env} ({env_name})")
        print(f"  Searched in: {evals_root}")
        print("  Run evaluations first with: make eval-e1 or make eval-e2")
        sys.exit(1)

    print(f"Analyzing {len(run_dirs)} runs for {args.env} ({env_name})...")

    # Collect all results, grouped by prompt
    results_by_prompt: dict[str, list[float]] = defaultdict(list)
    all_results: list[dict[str, Any]] = []
    per_model: dict[str, dict[str, Any]] = defaultdict(lambda: {"accuracies": [], "count": 0})
    models_seen: set[str] = set()

    for run_dir in run_dirs:
        results, metadata = load_run_results(run_dir)
        model = metadata.get("model", run_dir.parent.name)
        models_seen.add(model)

        for r in results:
            acc = extract_accuracy(r, args.env)
            if acc is not None:
                prompt_key = r.get("prompt", str(r.get("index", "")))[:200]
                results_by_prompt[prompt_key].append(acc)
                all_results.append(r)
                per_model[model]["accuracies"].append(acc)
                per_model[model]["count"] += 1

    # Compute statistics
    cold_start_stats = compute_cold_start_stats(results_by_prompt, k_values)
    difficulty_breakdown = compute_difficulty_breakdown(all_results, args.env)

    # Per-model summary
    per_model_summary = {}
    for model, ms in per_model.items():
        accs = ms["accuracies"]
        per_model_summary[model] = {
            "count": ms["count"],
            "mean_accuracy": sum(accs) / len(accs) if accs else 0.0,
            "zero_rate": sum(1 for a in accs if a == 0.0) / len(accs) if accs else 0.0,
        }

    # Assemble output
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output = {
        "env": args.env,
        "env_name": env_name,
        "timestamp": timestamp,
        "num_runs": len(run_dirs),
        "models": sorted(models_seen),
        "k_values": k_values,
        "total_results": len(all_results),
        "cold_start": cold_start_stats,
        "difficulty_breakdown": difficulty_breakdown,
        "per_model": per_model_summary,
        "run_dirs": [str(d) for d in run_dirs],
    }

    # Write outputs
    ts_short = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    json_path = output_dir / f"cold_start_{args.env}_{ts_short}.json"
    md_path = output_dir / f"cold_start_{args.env}_{ts_short}.md"

    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    md_path.write_text(generate_report_md(output, args.env), encoding="utf-8")

    print("\nResults written to:")
    print(f"  JSON: {json_path}")
    print(f"  Report: {md_path}")

    # Print summary
    print(f"\n--- Cold-Start Summary ({args.env}) ---")
    print(f"Total unique prompts: {cold_start_stats['total_unique_prompts']}")
    for k_str, ka in sorted(cold_start_stats.get("k_analysis", {}).items(), key=lambda x: int(x[0])):
        fail_frac = ka['fail_at_k_fraction']
        print(f"  fail@{ka['k']:>3d}: {fail_frac:.1%} ({ka['fail_at_k_count']}/{ka['eligible_prompts']})")


if __name__ == "__main__":
    main()
