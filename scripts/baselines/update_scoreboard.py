#!/usr/bin/env python3
"""Update SV-Bench scoreboards from run directories."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from bench.report import generate_report_md, generate_summary, load_results  # noqa: E402


def _load_summary(run_dir: Path) -> dict[str, Any]:
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))

    results, metadata = load_results(run_dir)
    env = metadata.get("environment", "")
    env_key = "e1" if "network-logs" in env else "e2"
    summary = generate_summary(env_key, results, metadata, run_id=run_dir.name, strict=False)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(generate_report_md(summary), encoding="utf-8")
    return summary


def _load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _load_metadata(run_dir: Path) -> dict[str, Any]:
    metadata_path = run_dir / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    return {}


def _save_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def _format_float(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "n/a"


def _render_e1(entries: list[dict[str, Any]]) -> str:
    rows = [
        "| Baseline | Model | Dataset | N | Acc | F1 | ECE | Abstain | Cost-Acc | Run |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for entry in entries:
        row = (
            f"| {entry['baseline']} | {entry['model']} | {entry['dataset']} | {entry['n']} | "
            f"{entry['acc']} | {entry['f1']} | {entry['ece']} | {entry['abstain']} | "
            f"{entry['cost_acc']} | {entry['run_id']} |"
        )
        rows.append(row)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "\n".join(
        [
            "# E1 Scoreboard (Public Mini Set)",
            "",
            f"Updated: {updated}",
            "",
            *rows,
            "",
        ]
    )


def _render_e2(entries: list[dict[str, Any]]) -> str:
    rows = [
        "| Baseline | Model | Dataset | N | F1(w) | F1+(w) | Patch Success | "
        "Clean Pass | FP on Clean | Run |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for entry in entries:
        row = (
            f"| {entry['baseline']} | {entry['model']} | {entry['dataset']} | {entry['n']} | "
            f"{entry['f1']} | {entry['f1_pos']} | {entry['patch_success']} | "
            f"{entry['clean_pass']} | {entry['fp_clean']} | {entry['run_id']} |"
        )
        rows.append(row)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "\n".join(
        [
            "# E2 Scoreboard (Public Mini Set)",
            "",
            f"Updated: {updated}",
            "",
            *rows,
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Update SV-Bench scoreboards from run dirs.")
    parser.add_argument("--env", choices=["e1", "e2"], required=True, help="Environment (e1 or e2)")
    parser.add_argument("--run-dirs", nargs="+", required=True, help="Run directories to include/update")
    args = parser.parse_args()

    scoreboard_dir = REPO_ROOT / "bench" / "scoreboards"
    json_path = scoreboard_dir / f"{args.env}_scoreboard.json"
    md_path = scoreboard_dir / f"{args.env}_scoreboard.md"

    entries = _load_entries(json_path)
    new_entries: list[dict[str, Any]] = []

    for run_dir in args.run_dirs:
        run_path = Path(run_dir)
        summary = _load_summary(run_path)
        metrics = summary.get("metrics", {})
        metadata = summary.get("metadata", {}) or {}
        if "baseline_name" not in metadata:
            metadata = {**_load_metadata(run_path), **metadata}

        baseline = metadata.get("baseline_name") or metadata.get("baseline") or summary.get("model")
        model = summary.get("model")
        dataset = summary.get("dataset")
        n = summary.get("n_examples")
        run_id = summary.get("run_id")

        if args.env == "e1":
            detection = metrics.get("detection", {})
            calibration = metrics.get("calibration", {})
            abstention = metrics.get("abstention", {})
            cost = metrics.get("cost", {})
            entry = {
                "baseline": baseline,
                "model": model,
                "dataset": dataset,
                "n": n,
                "acc": _format_float(detection.get("accuracy")),
                "f1": _format_float(detection.get("f1")),
                "ece": _format_float(calibration.get("ece")),
                "abstain": _format_float(abstention.get("abstain_rate")),
                "cost_acc": _format_float(cost.get("cost_weighted_accuracy")),
                "run_id": run_id,
            }
        else:
            fq = metrics.get("finding_quality", {})
            patch = metrics.get("patch", {})
            episode = metrics.get("episode", {})
            entry = {
                "baseline": baseline,
                "model": model,
                "dataset": dataset,
                "n": n,
                "f1": _format_float(fq.get("f1_weighted")),
                "f1_pos": _format_float(fq.get("f1_weighted_positive_only")),
                "patch_success": _format_float(patch.get("patch_success_rate")),
                "clean_pass": _format_float(episode.get("clean_pass_rate")),
                "fp_clean": _format_float(episode.get("false_positive_rate_on_clean")),
                "run_id": run_id,
            }

        new_entries.append(entry)

    new_baselines = {entry["baseline"] for entry in new_entries}
    new_run_ids = {entry["run_id"] for entry in new_entries}
    filtered_entries = [
        entry
        for entry in entries
        if entry.get("baseline") not in new_baselines and entry.get("run_id") not in new_run_ids
    ]
    merged_entries = filtered_entries + new_entries
    merged_entries.sort(key=lambda item: item["baseline"])
    _save_entries(json_path, merged_entries)

    if args.env == "e1":
        md_path.write_text(_render_e1(merged_entries), encoding="utf-8")
    else:
        md_path.write_text(_render_e2(merged_entries), encoding="utf-8")

    print(f"✓ Updated {md_path}")


if __name__ == "__main__":
    main()
