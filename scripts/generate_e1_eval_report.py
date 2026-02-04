#!/usr/bin/env python3
"""Generate evaluation report from E1 (network-logs) results.

Calculates metrics across all eval runs:
- Accuracy (Acc)
- Expected Calibration Error (ECE)
- False Negative % (FN%)
- False Positive % (FP%)
- Abstain %
- Sample count (N)
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add repo root to path for sv_shared imports when running as script
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sv_shared.parsers import extract_json_from_markdown  # noqa: E402


def parse_completion(completion: str) -> tuple[str | None, float | None]:
    """Extract label and confidence from completion JSON.

    Handles both raw JSON and markdown-wrapped JSON (```json ... ```).
    """
    # Try raw JSON first
    try:
        data = json.loads(completion)
        label = data.get("label", "").lower()
        confidence = data.get("confidence", 0.0)
        return label, confidence
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try extracting from markdown code blocks
    extracted = extract_json_from_markdown(completion)
    if extracted != completion:
        try:
            data = json.loads(extracted)
            label = data.get("label", "").lower()
            confidence = data.get("confidence", 0.0)
            return label, confidence
        except (json.JSONDecodeError, AttributeError):
            pass

    return None, None


def calculate_ece(predictions: list[tuple[str, str, float]], n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error.

    Args:
        predictions: List of (predicted, actual, confidence) tuples
        n_bins: Number of calibration bins (default: 10)

    Returns:
        ECE score (0.0 to 1.0, lower is better)
    """
    # Filter out abstentions and invalid predictions
    valid_preds = [
        (pred, actual, conf) for pred, actual, conf in predictions if pred and pred != "abstain" and actual
    ]

    if not valid_preds:
        return 0.0

    # Create bins
    bins = defaultdict(list)
    for pred, actual, conf in valid_preds:
        bin_idx = min(int(conf * n_bins), n_bins - 1)
        correct = 1.0 if pred == actual else 0.0
        bins[bin_idx].append((conf, correct))

    # Calculate ECE
    ece = 0.0
    n_total = len(valid_preds)

    for bin_idx in range(n_bins):
        if bin_idx not in bins:
            continue

        bin_items = bins[bin_idx]
        n_bin = len(bin_items)

        avg_confidence = sum(conf for conf, _ in bin_items) / n_bin
        avg_accuracy = sum(correct for _, correct in bin_items) / n_bin

        ece += (n_bin / n_total) * abs(avg_confidence - avg_accuracy)

    return ece


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
    if "iot23" in dataset.lower():
        split = "ID (IoT-23)"
    elif "cic-ids-2017" in dataset.lower():
        split = "OOD (CIC-IDS-2017)"
    elif "unsw-nb15" in dataset.lower():
        split = "OOD (UNSW-NB15)"
    else:
        split = f"Unknown ({dataset})"

    # Parse results
    predictions = []
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0
    abstentions = 0
    total = 0

    with open(results_file) as f:
        for line in f:
            result = json.loads(line)
            actual = result["answer"].lower()
            predicted_label, confidence = parse_completion(result["completion"])

            if predicted_label is None:
                continue

            total += 1

            if predicted_label == "abstain":
                abstentions += 1
                continue

            # Store for ECE calculation
            predictions.append((predicted_label, actual, confidence or 0.0))

            # Confusion matrix
            if predicted_label == "malicious" and actual == "malicious":
                true_positives += 1
            elif predicted_label == "benign" and actual == "benign":
                true_negatives += 1
            elif predicted_label == "malicious" and actual == "benign":
                false_positives += 1
            elif predicted_label == "benign" and actual == "malicious":
                false_negatives += 1

    # Calculate metrics
    n_classified = total - abstentions

    if n_classified > 0:
        accuracy = (true_positives + true_negatives) / n_classified

        # FN% and FP% as percentages of the classified samples
        fn_rate = (false_negatives / n_classified) * 100
        fp_rate = (false_positives / n_classified) * 100
    else:
        accuracy = 0.0
        fn_rate = 0.0
        fp_rate = 0.0

    abstain_rate = (abstentions / total * 100) if total > 0 else 0.0
    ece = calculate_ece(predictions)

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
        "Acc": round(accuracy, 4),
        "ECE": round(ece, 4),
        "FN%": round(fn_rate, 2),
        "FP%": round(fp_rate, 2),
        "Abstain%": round(abstain_rate, 2),
        "N": total,
        "run_datetime": run_datetime_str,
        "run_id": run_dir.name,
    }

    # Write summary.json to the run directory if requested
    if write_summary:
        summary_file = run_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation report from E1 (network-logs) results")
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
        default=False,
        help="Write summary.json to each run directory (default: False)",
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
        args.output = Path(f"outputs/evals/report-network-logs-{timestamp}.json")

    # Find all run directories
    # Note: OpenRouter models use org/model naming (e.g., qwen/qwen-2.5-7b-instruct)
    # which creates nested directories, so we use recursive glob to find all metadata.json
    if args.run_ids:
        # Use specified run IDs - search recursively for matching run_id directories
        run_dirs = []
        for pattern in ["sv-env-network-logs--*"]:
            for model_dir in args.eval_dir.glob(pattern):
                if not model_dir.is_dir() or model_dir.name == "archived":
                    continue
                # Search recursively for run_id directories containing metadata.json
                for metadata_file in model_dir.rglob("metadata.json"):
                    run_dir = metadata_file.parent
                    if run_dir.name in args.run_ids:
                        run_dirs.append(run_dir)
    else:
        # Find all non-archived runs - search recursively for metadata.json
        run_dirs = []
        for pattern in ["sv-env-network-logs--*"]:
            for model_dir in args.eval_dir.glob(pattern):
                if not model_dir.is_dir() or model_dir.name == "archived":
                    continue
                # Find all metadata.json files recursively
                for metadata_file in model_dir.rglob("metadata.json"):
                    run_dirs.append(metadata_file.parent)

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
    print("\n" + "=" * 120)
    print(
        f"{'Split':<25} {'Model':<20} {'Acc':>6} {'ECE':>6} {'FN%':>6} "
        f"{'FP%':>6} {'Abstain%':>8} {'N':>5} {'Run Date':<20}"
    )
    print("=" * 120)
    for r in results:
        print(
            f"{r['Split']:<25} {r['Model']:<20} {r['Acc']:>6.4f} {r['ECE']:>6.4f} "
            f"{r['FN%']:>6.2f} {r['FP%']:>6.2f} {r['Abstain%']:>8.2f} "
            f"{r['N']:>5} {r['run_datetime']:<20}"
        )
    print("=" * 120)


if __name__ == "__main__":
    main()
