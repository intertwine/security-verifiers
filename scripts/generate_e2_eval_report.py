#!/usr/bin/env python3
"""Generate evaluation report from E2 (config-verification) results.

Calculates metrics across all eval runs:
- Mean reward (reward_config_auditing)
- Format success rate (format_reward)
- Tool usage stats (tools called, avg turns)
- Sample count (N)
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def analyze_run(run_dir: Path, write_summary: bool = True) -> dict[str, Any] | None:
    """Analyze a single eval run and calculate metrics.

    Args:
        run_dir: Path to the run directory
        write_summary: If True, write summary.json to the run directory

    Returns:
        Dictionary with calculated metrics, or None if files missing
    """
    metadata_file = run_dir / "metadata.json"
    results_file = run_dir / "results.jsonl"

    if not metadata_file.exists() or not results_file.exists():
        return None

    # Load metadata
    with open(metadata_file) as f:
        metadata = json.load(f)

    # Determine split name
    dataset = metadata.get("dataset", "unknown")
    if "k8s" in dataset.lower():
        split = "K8s"
    elif "terraform" in dataset.lower():
        split = "Terraform"
    elif "combined" in dataset.lower():
        split = "Combined"
    elif "builtin" in dataset.lower():
        split = "Fixtures"
    else:
        split = f"Unknown ({dataset})"

    # Parse results
    total = 0
    reward_sum = 0.0
    format_success_count = 0
    completion_errors = 0
    total_tools_called = 0
    total_turns = 0
    samples_with_tools = 0

    with open(results_file) as f:
        for line in f:
            result = json.loads(line)
            total += 1

            # Track completion errors
            if "completion_error" in result:
                completion_errors += 1

            # Accumulate rewards
            rewards = result.get("rewards", {})
            reward_sum += rewards.get("reward_config_auditing", 0.0)

            # Track format success (1.0 = success, 0.0 = failure)
            if rewards.get("format_reward", 0.0) >= 0.99:
                format_success_count += 1

            # Track tool usage
            tool_interactions = result.get("tool_interactions", [])
            if tool_interactions:
                samples_with_tools += 1
                total_tools_called += len(tool_interactions)

            turns_used = result.get("turns_used", 0)
            if turns_used > 0:
                total_turns += turns_used

    # Calculate metrics
    mean_reward = reward_sum / total if total > 0 else 0.0
    format_success_rate = (format_success_count / total * 100) if total > 0 else 0.0
    error_rate = (completion_errors / total * 100) if total > 0 else 0.0
    avg_tools_per_sample = total_tools_called / samples_with_tools if samples_with_tools > 0 else 0.0
    avg_turns_per_sample = total_turns / total if total > 0 else 0.0

    # Parse timestamp
    timestamp = metadata.get("timestamp", "")
    try:
        run_datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        run_datetime_str = run_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        run_datetime_str = timestamp

    result = {
        "Split": split,
        "Model": metadata.get("model", "unknown"),
        "MeanReward": round(mean_reward, 4),
        "FormatSuccess%": round(format_success_rate, 2),
        "Error%": round(error_rate, 2),
        "AvgTools": round(avg_tools_per_sample, 2),
        "AvgTurns": round(avg_turns_per_sample, 2),
        "N": total,
        "run_datetime": run_datetime_str,
        "run_id": run_dir.name,
        "include_tools": metadata.get("include_tools", False),
    }

    # Write summary.json to the run directory if requested
    if write_summary:
        summary_file = run_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate evaluation report from E2 (config-verification) results"
    )
    parser.add_argument(
        "--eval-dir",
        type=Path,
        default=Path("outputs/evals"),
        help="Directory containing eval results (default: outputs/evals)",
    )
    parser.add_argument(
        "--run-ids",
        nargs="+",
        help="Specific run IDs to analyze (default: all non-archived runs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output report file (default: auto-generated with timestamp)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--write-summaries",
        action="store_true",
        default=True,
        help="Write summary.json to each run directory (default: True)",
    )
    parser.add_argument(
        "--no-write-summaries",
        action="store_false",
        dest="write_summaries",
        help="Don't write summary.json to run directories",
    )

    args = parser.parse_args()

    # Generate default output filename with timestamp if not specified
    if args.output is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        args.output = Path(f"outputs/evals/report-config-verification-{timestamp}.json")

    # Find all run directories
    if args.run_ids:
        # Use specified run IDs
        run_dirs = []
        for pattern in ["sv-env-config-verification--*"]:
            for model_dir in args.eval_dir.glob(pattern):
                if not model_dir.is_dir():
                    continue
                for run_id in args.run_ids:
                    run_dir = model_dir / run_id
                    if run_dir.exists():
                        run_dirs.append(run_dir)
    else:
        # Find all non-archived runs
        run_dirs = []
        for pattern in ["sv-env-config-verification--*"]:
            for model_dir in args.eval_dir.glob(pattern):
                if model_dir.name == "archived" or not model_dir.is_dir():
                    continue
                for run_dir in model_dir.iterdir():
                    if run_dir.is_dir() and (run_dir / "metadata.json").exists():
                        run_dirs.append(run_dir)

    # Analyze each run
    results = []
    for run_dir in sorted(run_dirs):
        print(f"Analyzing {run_dir}...", flush=True)
        result = analyze_run(run_dir, write_summary=args.write_summaries)
        if result:
            results.append(result)

    # Sort results by Split, then Model
    results.sort(key=lambda x: (x["Split"], x["Model"]))

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        if args.pretty:
            json.dump(results, f, indent=2)
        else:
            json.dump(results, f)

    print(f"\nGenerated report with {len(results)} runs")
    print(f"Output: {args.output}")

    # Print summary table
    print("\n" + "=" * 130)
    print(
        f"{'Split':<15} {'Model':<20} {'MeanReward':>11} {'Format%':>8} "
        f"{'Error%':>7} {'AvgTools':>8} {'AvgTurns':>8} {'N':>5} {'Run Date':<20}"
    )
    print("=" * 130)
    for r in results:
        print(
            f"{r['Split']:<15} {r['Model']:<20} {r['MeanReward']:>11.4f} {r['FormatSuccess%']:>8.2f} "
            f"{r['Error%']:>7.2f} {r['AvgTools']:>8.2f} {r['AvgTurns']:>8.2f} "
            f"{r['N']:>5} {r['run_datetime']:<20}"
        )
    print("=" * 130)


if __name__ == "__main__":
    main()
