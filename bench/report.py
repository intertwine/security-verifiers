#!/usr/bin/env python3
"""SV-Bench Report Generator.

Generates summary.json and report.md from evaluation rollout results.

Usage:
    python -m bench.report --env e1 --input outputs/evals/network-logs--gpt-5-mini/run_123/
    python -m bench.report --env e2 --input outputs/evals/config-verification--gpt-5-mini/run_456/
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# ============================================================================
# E1 Metrics: Network Logs Anomaly Detection
# ============================================================================


def compute_e1_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute E1 metrics from rollout results."""

    # Extract predictions and ground truth
    predictions = []
    actuals = []
    confidences = []

    for r in results:
        pred = r.get("predicted_label", "").lower()
        actual = r.get("answer", "").lower()
        conf = r.get("confidence", 0.5)

        if pred and actual:
            predictions.append(pred)
            actuals.append(actual)
            confidences.append(conf)

    predictions = np.array(predictions)
    actuals = np.array(actuals)
    confidences = np.array(confidences, dtype=float)

    # Separate abstain predictions
    non_abstain_mask = predictions != "abstain"

    # Detection metrics (excluding abstain)
    pred_na = predictions[non_abstain_mask]
    actual_na = actuals[non_abstain_mask]

    # Binary classification metrics
    tp = np.sum((pred_na == "malicious") & (actual_na == "malicious"))
    tn = np.sum((pred_na == "benign") & (actual_na == "benign"))
    fp = np.sum((pred_na == "malicious") & (actual_na == "benign"))
    fn = np.sum((pred_na == "benign") & (actual_na == "malicious"))

    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = 1.0 - tpr
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    accuracy = (tp + tn) / len(pred_na) if len(pred_na) > 0 else 0.0
    f1 = 2 * precision * tpr / (precision + tpr) if (precision + tpr) > 0 else 0.0

    # Calibration metrics (on non-abstain)
    correct_na = pred_na == actual_na
    conf_na = confidences[non_abstain_mask]

    ece = _compute_ece(correct_na, conf_na)
    brier = _compute_brier(correct_na, conf_na)

    # Cost metrics
    fn_cost_weight = 10.0
    fp_cost_weight = 1.0
    total_cost = fn_cost_weight * fn + fp_cost_weight * fp
    max_cost = len(pred_na) * max(fn_cost_weight, fp_cost_weight)
    cost_weighted_accuracy = 1.0 - (total_cost / max_cost) if max_cost > 0 else 1.0

    # Abstention metrics
    n_abstain = np.sum(~non_abstain_mask)
    abstain_rate = n_abstain / len(predictions) if len(predictions) > 0 else 0.0
    accuracy_non_abstained = accuracy
    aurc = _compute_aurc(pred_na, actual_na, conf_na)

    return {
        "detection": {
            "tpr": float(tpr),
            "fpr": float(fpr),
            "fnr": float(fnr),
            "precision": float(precision),
            "f1": float(f1),
            "accuracy": float(accuracy),
        },
        "calibration": {
            "ece": float(ece),
            "brier": float(brier),
        },
        "cost": {
            "fn_cost_weight": fn_cost_weight,
            "fp_cost_weight": fp_cost_weight,
            "total_cost": float(total_cost),
            "cost_weighted_accuracy": float(cost_weighted_accuracy),
        },
        "abstention": {
            "abstain_rate": float(abstain_rate),
            "accuracy_non_abstained": float(accuracy_non_abstained),
            "aurc": float(aurc),
        },
        "confusion_matrix": {
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "abstain": int(n_abstain),
        },
    }


def _compute_ece(correct: np.ndarray, confidences: np.ndarray, num_bins: int = 10) -> float:
    """Compute Expected Calibration Error."""
    if len(correct) == 0:
        return 0.0

    bins = np.linspace(0, 1, num_bins + 1)
    ece = 0.0

    for i in range(num_bins):
        mask = (confidences >= bins[i]) & (confidences < bins[i + 1])
        if mask.sum() > 0:
            bin_acc = correct[mask].mean()
            bin_conf = confidences[mask].mean()
            ece += mask.sum() / len(correct) * abs(bin_acc - bin_conf)

    return ece


def _compute_brier(correct: np.ndarray, confidences: np.ndarray) -> float:
    """Compute Brier score."""
    if len(correct) == 0:
        return 0.0

    correct_float = correct.astype(float)
    return float(np.mean((confidences - correct_float) ** 2))


def _compute_aurc(predictions: np.ndarray, actuals: np.ndarray, confidences: np.ndarray) -> float:
    """Compute Area Under Risk-Coverage curve."""
    if len(predictions) == 0:
        return 0.0

    thresholds = np.linspace(0, 1, 101)
    coverages = []
    risks = []

    for tau in thresholds:
        mask = confidences >= tau
        coverage = mask.mean()
        if coverage > 0:
            risk = (predictions[mask] != actuals[mask]).mean()
        else:
            risk = 0.0
        coverages.append(coverage)
        risks.append(risk)

    return float(np.trapz(risks, coverages))


# ============================================================================
# E2 Metrics: Config Verification
# ============================================================================

SEV_WEIGHT = {"low": 0.3, "med": 0.6, "high": 1.0}


def compute_e2_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute E2 metrics from rollout results."""

    # Aggregate metrics
    precisions_w, recalls_w, f1s_w = [], [], []
    precisions_u, recalls_u, f1s_u = [], [], []
    patch_provided, patch_success = 0, 0
    violations_fixed = []
    new_violations = []
    tool_calls = []
    tool_times = []
    tool_usage = {
        "opa": {"calls": 0, "time_ms": 0},
        "kube-linter": {"calls": 0, "time_ms": 0},
        "semgrep": {"calls": 0, "time_ms": 0},
    }
    format_valid = 0
    turns = []

    for r in results:
        # Finding quality
        pred_violations = r.get("predicted_violations", [])
        oracle_violations = r.get("oracle_violations", [])

        p_w, r_w, f1_w = _score_detection_weighted(pred_violations, oracle_violations)
        p_u, r_u, f1_u = _score_detection_unweighted(pred_violations, oracle_violations)

        precisions_w.append(p_w)
        recalls_w.append(r_w)
        f1s_w.append(f1_w)
        precisions_u.append(p_u)
        recalls_u.append(r_u)
        f1s_u.append(f1_u)

        # Patch metrics
        if r.get("patch"):
            patch_provided += 1
            if r.get("patch_applied", False):
                patch_success += 1
                post_violations = r.get("post_patch_violations", [])
                fixed = _count_violations_fixed(oracle_violations, post_violations)
                violations_fixed.append(fixed)
                new = _count_new_violations(oracle_violations, post_violations)
                new_violations.append(new)

        # Tool economy
        calls = r.get("tool_calls", 0)
        time_ms = r.get("tool_time_ms", 0)
        tool_calls.append(calls)
        tool_times.append(time_ms)

        for tool_name in ["opa", "kube-linter", "semgrep"]:
            t_calls = r.get(f"{tool_name}_calls", 0)
            t_time = r.get(f"{tool_name}_time_ms", 0)
            tool_usage[tool_name]["calls"] += t_calls
            tool_usage[tool_name]["time_ms"] += t_time

        # Episode metrics
        if r.get("valid_json", True):
            format_valid += 1
        turns.append(r.get("turns", 1))

    n = len(results)
    n_findings = sum(len(r.get("predicted_violations", [])) for r in results)

    return {
        "finding_quality": {
            "precision_weighted": float(np.mean(precisions_w)) if precisions_w else 0.0,
            "recall_weighted": float(np.mean(recalls_w)) if recalls_w else 0.0,
            "f1_weighted": float(np.mean(f1s_w)) if f1s_w else 0.0,
            "precision_unweighted": float(np.mean(precisions_u)) if precisions_u else 0.0,
            "recall_unweighted": float(np.mean(recalls_u)) if recalls_u else 0.0,
            "f1_unweighted": float(np.mean(f1s_u)) if f1s_u else 0.0,
        },
        "patch": {
            "patch_provided_rate": patch_provided / n if n > 0 else 0.0,
            "patch_success_rate": patch_success / patch_provided if patch_provided > 0 else 0.0,
            "patch_fix_rate": float(np.mean(violations_fixed)) if violations_fixed else 0.0,
            "mean_violations_fixed": float(np.mean(violations_fixed)) if violations_fixed else 0.0,
            "new_violations_introduced": float(np.mean(new_violations)) if new_violations else 0.0,
        },
        "tool_economy": {
            "mean_tool_calls": float(np.mean(tool_calls)) if tool_calls else 0.0,
            "mean_tool_time_ms": float(np.mean(tool_times)) if tool_times else 0.0,
            "calls_per_finding": sum(tool_calls) / n_findings if n_findings > 0 else 0.0,
            "tool_distribution": tool_usage,
        },
        "episode": {
            "format_valid_rate": format_valid / n if n > 0 else 0.0,
            "mean_turns": float(np.mean(turns)) if turns else 0.0,
        },
    }


def _score_detection_weighted(pred: list[dict], oracle: list[dict]) -> tuple[float, float, float]:
    """Weighted precision/recall/F1."""
    o_ids = {v.get("id", v.get("rule_id", "")): SEV_WEIGHT.get(v.get("severity", "med"), 0.6) for v in oracle}
    p_ids = {v.get("id", v.get("rule_id", "")): SEV_WEIGHT.get(v.get("severity", "med"), 0.6) for v in pred}

    tp = sum(o_ids.get(vid, 0) for vid in p_ids if vid in o_ids)
    fp = sum(w for vid, w in p_ids.items() if vid not in o_ids)
    fn = sum(w for vid, w in o_ids.items() if vid not in p_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def _score_detection_unweighted(pred: list[dict], oracle: list[dict]) -> tuple[float, float, float]:
    """Unweighted precision/recall/F1."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in pred}

    tp = len(p_ids & o_ids)
    fp = len(p_ids - o_ids)
    fn = len(o_ids - p_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def _count_violations_fixed(oracle: list[dict], post: list[dict]) -> int:
    """Count violations fixed by patch."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in post}
    return len(o_ids - p_ids)


def _count_new_violations(oracle: list[dict], post: list[dict]) -> int:
    """Count new violations introduced by patch."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in post}
    return len(p_ids - o_ids)


# ============================================================================
# Report Generation
# ============================================================================


def load_results(input_path: Path) -> tuple[list[dict], dict]:
    """Load results.jsonl and metadata.json from input path."""
    results_file = input_path / "results.jsonl"
    metadata_file = input_path / "metadata.json"

    results = []
    if results_file.exists():
        with open(results_file) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))

    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    return results, metadata


def generate_summary(
    env: str,
    results: list[dict],
    metadata: dict,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Generate summary.json content."""

    if env in ("e1", "network-logs", "sv-env-network-logs"):
        env_name = "sv-env-network-logs"
        metrics = compute_e1_metrics(results)
    elif env in ("e2", "config-verification", "sv-env-config-verification"):
        env_name = "sv-env-config-verification"
        metrics = compute_e2_metrics(results)
    else:
        raise ValueError(f"Unknown environment: {env}")

    return {
        "environment": env_name,
        "version": "0.1.0",
        "run_id": run_id or metadata.get("run_id", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": metadata.get("model", "unknown"),
        "dataset": metadata.get("dataset", "unknown"),
        "n_examples": len(results),
        "metrics": metrics,
        "metadata": {
            "git_sha": metadata.get("git_sha"),
            "env_version": metadata.get("env_version"),
            "python_version": metadata.get("python_version"),
            "verifiers_version": metadata.get("verifiers_version"),
            "seed": metadata.get("seed"),
        },
    }


def generate_report_md(summary: dict[str, Any]) -> str:
    """Generate human-readable report.md content."""

    lines = [
        f"# SV-Bench Report: {summary['environment']}",
        "",
        "## Run Information",
        "",
        f"- **Model:** {summary['model']}",
        f"- **Dataset:** {summary['dataset']}",
        f"- **Examples:** {summary['n_examples']}",
        f"- **Run ID:** {summary['run_id']}",
        f"- **Timestamp:** {summary['timestamp']}",
        "",
    ]

    metrics = summary["metrics"]

    if summary["environment"] == "sv-env-network-logs":
        lines.extend(_format_e1_report(metrics))
    else:
        lines.extend(_format_e2_report(metrics))

    return "\n".join(lines)


def _format_e1_report(metrics: dict) -> list[str]:
    """Format E1 metrics as markdown."""
    d = metrics["detection"]
    c = metrics["calibration"]
    cost = metrics["cost"]
    a = metrics["abstention"]
    cm = metrics.get("confusion_matrix", {})

    return [
        "## Detection Performance",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| TPR (Recall) | {d['tpr']:.3f} |",
        f"| FPR | {d['fpr']:.3f} |",
        f"| FNR | {d['fnr']:.3f} |",
        f"| Precision | {d['precision']:.3f} |",
        f"| F1 Score | {d['f1']:.3f} |",
        f"| Accuracy | {d['accuracy']:.3f} |",
        "",
        "## Calibration",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| ECE | {c['ece']:.4f} |",
        f"| Brier Score | {c['brier']:.4f} |",
        "",
        "## Cost Analysis",
        "",
        f"- FN Cost Weight: {cost['fn_cost_weight']}",
        f"- FP Cost Weight: {cost['fp_cost_weight']}",
        f"- Total Cost: {cost['total_cost']:.1f}",
        f"- Cost-Weighted Accuracy: {cost['cost_weighted_accuracy']:.3f}",
        "",
        "## Abstention",
        "",
        f"- Abstain Rate: {a['abstain_rate']:.3f}",
        f"- Accuracy (non-abstained): {a['accuracy_non_abstained']:.3f}",
        f"- AURC: {a['aurc']:.4f}",
        "",
        "## Confusion Matrix",
        "",
        f"- TP: {cm.get('tp', 'N/A')}",
        f"- TN: {cm.get('tn', 'N/A')}",
        f"- FP: {cm.get('fp', 'N/A')}",
        f"- FN: {cm.get('fn', 'N/A')}",
        f"- Abstain: {cm.get('abstain', 'N/A')}",
        "",
    ]


def _format_e2_report(metrics: dict) -> list[str]:
    """Format E2 metrics as markdown."""
    fq = metrics["finding_quality"]
    p = metrics["patch"]
    te = metrics["tool_economy"]
    ep = metrics.get("episode", {})

    return (
        [
            "## Finding Quality",
            "",
            "| Metric | Weighted | Unweighted |",
            "|--------|----------|------------|",
            f"| Precision | {fq['precision_weighted']:.3f} | {fq['precision_unweighted']:.3f} |",
            f"| Recall | {fq['recall_weighted']:.3f} | {fq['recall_unweighted']:.3f} |",
            f"| F1 | {fq['f1_weighted']:.3f} | {fq['f1_unweighted']:.3f} |",
            "",
            "## Patch Analysis",
            "",
            f"- Patch Provided Rate: {p['patch_provided_rate']:.3f}",
            f"- Patch Success Rate: {p['patch_success_rate']:.3f}",
            f"- Patch Fix Rate: {p['patch_fix_rate']:.3f}",
            f"- Mean Violations Fixed: {p['mean_violations_fixed']:.2f}",
            f"- New Violations Introduced: {p['new_violations_introduced']:.2f}",
            "",
            "## Tool Economy",
            "",
            f"- Mean Tool Calls: {te['mean_tool_calls']:.2f}",
            f"- Mean Tool Time (ms): {te['mean_tool_time_ms']:.1f}",
            f"- Calls Per Finding: {te['calls_per_finding']:.2f}",
            "",
            "### Tool Distribution",
            "",
            "| Tool | Calls | Time (ms) |",
            "|------|-------|-----------|",
        ]
        + [
            f"| {tool} | {stats['calls']} | {stats['time_ms']:.0f} |"
            for tool, stats in te.get("tool_distribution", {}).items()
        ]
        + [
            "",
            "## Episode Metrics",
            "",
            f"- Format Valid Rate: {ep.get('format_valid_rate', 0):.3f}",
            f"- Mean Turns: {ep.get('mean_turns', 0):.2f}",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Generate SV-Bench evaluation reports")
    parser.add_argument(
        "--env",
        required=True,
        choices=["e1", "e2", "network-logs", "config-verification"],
        help="Environment type",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to evaluation output directory (contains results.jsonl and metadata.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if required fields are missing",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    results, metadata = load_results(input_path)

    if not results:
        print(f"Error: No results found in {input_path}/results.jsonl", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(results)} results from {input_path}")

    # Generate summary
    run_id = input_path.name if input_path.name != "." else None
    summary = generate_summary(args.env, results, metadata, run_id)

    # Generate report
    report_md = generate_report_md(summary)

    # Write outputs
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {summary_file}")

    report_file = output_path / "report.md"
    with open(report_file, "w") as f:
        f.write(report_md)
    print(f"Wrote {report_file}")


if __name__ == "__main__":
    main()
