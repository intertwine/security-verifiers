#!/usr/bin/env python3
"""Descriptive, offline analysis of imported legacy Prime training records.

Does not infer held-out provenance, restore historical rewards, or execute tools.
Run with --input outputs/prime_legacy --output outputs/prime_legacy_analysis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

RUN_IDS = (
    "bp6qd19u06wzeqkdrf0h24xx",
    "j1i1ys9rpdcluvtqneql2o4l",
    "iiy65ubvx5xwke4dfb9vos64",
    "hu1j9b61il8dydv2bh1aj97d",
    "h4y9hb6fjom4xfbclitb2938",
    "hzu95jfm266370x9kr9wwgkz",
    "kvyp3sz2afit54dv3apgoozp",
    "me9uybbrnbsjv1yw681wn52g",
    "pi7okyqnetp5w1jsga8al28y",
    "covnxc26qu84nb7wqcohv7ed",
)


def rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def completion_text(record: dict[str, Any], reasoning_fallback: bool = False) -> str:
    value = record.get("completion")
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Match the historical last-message convention, rather than scraping a tool observation.
        last = value[-1] if value else {}
        if isinstance(last, dict) and last.get("role") == "assistant":
            text = last.get("content")
            if isinstance(text, str) and text.strip():
                return text
            if reasoning_fallback and isinstance(last.get("reasoning_content"), str):
                return last["reasoning_content"]
    return ""


def json_object(text: str) -> dict[str, Any] | None:
    # Accept JSON wrappers/prefixes, but never repair malformed JSON or regex-extract fields.
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start >= 0:
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except ValueError:
            return None
        if isinstance(obj, dict):
            return obj
    return None


def e1_record(record: dict[str, Any], reasoning_fallback: bool) -> dict[str, Any] | None:
    obj = json_object(completion_text(record, reasoning_fallback))
    answer = record.get("answer")
    if isinstance(answer, dict):
        answer = answer.get("label")
    if not isinstance(answer, str) or answer.lower() not in {"benign", "malicious"}:
        return None
    if not obj or obj.get("label") not in {"Benign", "Malicious", "Abstain"}:
        return None
    confidence = obj.get("confidence")
    if not finite(confidence) or not 0 <= confidence <= 1:
        return None
    return {"prediction": obj["label"].lower(), "answer": answer.lower(), "confidence": confidence}


def ratio(a: float, b: float) -> float | None:
    return a / b if b else None


def case_digest(record: dict[str, Any]) -> str:
    """Diagnostic prompt/answer identity; does not establish independent examples."""
    payload = json.dumps({"prompt": record.get("prompt"), "answer": record.get("answer")}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def e1_metrics(samples: list[dict[str, Any]], reasoning_fallback: bool = False) -> dict[str, Any]:
    parsed = [p for r in samples if (p := e1_record(r, reasoning_fallback)) is not None]
    accepted = [p for p in parsed if p["prediction"] != "abstain"]
    counts = {
        "tp": sum(p["prediction"] == "malicious" and p["answer"] == "malicious" for p in accepted),
        "tn": sum(p["prediction"] == "benign" and p["answer"] == "benign" for p in accepted),
        "fp": sum(p["prediction"] == "malicious" and p["answer"] == "benign" for p in accepted),
        "fn": sum(p["prediction"] == "benign" and p["answer"] == "malicious" for p in accepted),
    }
    correct = [p["prediction"] == p["answer"] for p in accepted]
    ece = 0.0
    for b in range(10):
        group = [p for p in accepted if min(int(p["confidence"] * 10), 9) == b]
        if group:
            ece += (
                len(group)
                / len(accepted)
                * abs(
                    fmean(p["confidence"] for p in group)
                    - fmean(p["prediction"] == p["answer"] for p in group)
                )
            )
    risk_coverage = []
    for threshold in (0.0, 0.5, 0.7, 0.9, 0.95, 1.0):
        group = [p for p in accepted if p["confidence"] >= threshold]
        risk_coverage.append(
            {
                "threshold": threshold,
                "n": len(group),
                "coverage_all_samples": ratio(len(group), len(samples)),
                "risk": ratio(sum(p["prediction"] != p["answer"] for p in group), len(group)),
            }
        )
    return {
        "n_samples": len(samples),
        "n_parseable_labeled": len(parsed),
        "n_non_abstained": len(accepted),
        "n_unparseable_or_unlabeled": len(samples) - len(parsed),
        "n_abstained": len(parsed) - len(accepted),
        "confusion": counts,
        "accuracy_non_abstained": ratio(sum(correct), len(accepted)),
        "correct_fraction_all_samples": ratio(sum(correct), len(samples)),
        "tpr_non_abstained": ratio(counts["tp"], counts["tp"] + counts["fn"]),
        "fpr_non_abstained": ratio(counts["fp"], counts["fp"] + counts["tn"]),
        "ece_non_abstained": ece if accepted else None,
        "brier_correctness_non_abstained": fmean(
            (p["confidence"] - int(p["prediction"] == p["answer"])) ** 2 for p in accepted
        )
        if accepted
        else None,
        "cost_total_non_abstained": 10 * counts["fn"] + counts["fp"],
        "cost_per_non_abstained": ratio(10 * counts["fn"] + counts["fp"], len(accepted)),
        "risk_coverage": risk_coverage,
    }


def summarize_run(path: Path) -> dict[str, Any]:
    metadata = json.loads((path / "metadata.json").read_text())
    samples = rows(path / "results.jsonl")
    logged = sorted(rows(path / "metrics.jsonl"), key=lambda r: (r.get("step", -1), r.get("timestamp") or ""))
    environments = metadata.get("environments", [])
    is_e1 = any("network-logs" in e.get("id", "") or "netlogs" in e.get("id", "") for e in environments)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[sample["step"]].append(sample)
    sample_curve = []
    for step, group in sorted(grouped.items()):
        rewards = [r["reward"] for r in group if finite(r.get("reward"))]
        point: dict[str, Any] = {
            "step": step,
            "n_samples": len(group),
            "unique_problem_ids": len({r.get("problem_id") for r in group}),
            "unique_prompt_answer_digests": len({case_digest(r) for r in group}),
            "mean_archived_reward": fmean(rewards) if rewards else None,
        }
        if is_e1:
            point["content_only"] = e1_metrics(group)
            point["reasoning_fallback_diagnostic"] = e1_metrics(group, True)
        sample_curve.append(point)
    # Preserve logged curves as recorded: no interpolation and no cross-source reward comparisons.
    logged_curve = [
        {
            "step": r.get("step"),
            "timestamp": r.get("timestamp"),
            "values": {
                k: v
                for k, v in r.items()
                if finite(v)
                and (
                    k.startswith("eval/")
                    or k.startswith("reward/")
                    or k.startswith("metrics/")
                    or k in {"progress/ckpt_step", "progress/total_tokens", "progress/total_samples"}
                )
            },
        }
        for r in logged
    ]
    metrics_keys = sorted({k for r in samples for k in (r.get("metrics") or {})})
    observations = Counter()
    for sample in samples:
        for message in sample.get("completion") or []:
            if isinstance(message, dict) and message.get("role") == "tool":
                observations["tool_messages"] += 1
                if "tool_backend" in str(message.get("content", "")):
                    observations["tool_messages_with_backend_text"] += 1
    summary: dict[str, Any] = {
        "run_id": metadata.get("id"),
        "workspace": path.parent.parent.name,
        "environment": "e1" if is_e1 else "e2",
        "status": metadata.get("status"),
        "model": metadata.get("baseModel"),
        "environments": environments,
        "max_steps": metadata.get("maxSteps"),
        "n_samples": len(samples),
        "unique_problem_ids": len({r.get("problem_id") for r in samples}),
        "unique_prompt_answer_digests": len({case_digest(r) for r in samples}),
        "n_metric_rows": len(logged),
        "sample_curve": sample_curve,
        "logged_curve": logged_curve,
        "sample_metric_keys": metrics_keys,
        "tool_observation_counts": dict(observations),
        "source_sha256": {
            f: hashlib.sha256((path / f).read_bytes()).hexdigest()
            for f in ("metadata.json", "results.jsonl", "metrics.jsonl")
            if (path / f).exists()
        },
        "heldout_evidence": False,
    }
    if is_e1:
        summary["content_only"] = e1_metrics(samples)
        summary["reasoning_fallback_diagnostic"] = e1_metrics(samples, True)
    else:
        summary["limitations"] = [
            "No tools were re-executed; archived scalar rewards are not common operational metrics.",
            "Patch success/semantic preservation and historical backend truth are not inferred.",
            "Oracle labels and hosted fixture paths require independent validation before scoring patches.",
        ]
    return summary


def render_report(data: dict[str, Any]) -> str:
    lines = [
        "# Recovered Prime training evidence",
        "",
        "Descriptive training-record analysis only. No independent held-out improvement is established.",
        "",
        "E1 extracts JSON objects with valid label/confidence fields. Content-only and reasoning",
        "fallback diagnostics are separate; neither reproduces the historical reward implementation.",
        "Counts include repeated training completions; no independence assumption or confidence intervals.",
        "",
        "E1 cost uses FN=10/FP=1 and excludes abstained/unparseable cases; inspect counts alongside cost.",
        "Calibration uses confidence in correctness, not probability of the malicious class.",
        "",
        "Problem IDs can collide: prompt/answer digests provide a separate diagnostic case count.",
        "Different steps may sample different cases, so endpoint changes are not paired improvements.",
        "",
        "| Run | Env | Samples | Problem IDs | Prompt/answer digests | Metric rows | Samples per step |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for run in data["runs"]:
        counts = ", ".join(f"{p['step']}:{p['n_samples']}" for p in run["sample_curve"])
        lines.append(
            f"| {run['run_id']} | {run['environment']} | {run['n_samples']} | "
            f"{run['unique_problem_ids']} | {run['unique_prompt_answer_digests']} | "
            f"{run['n_metric_rows']} | {counts} |"
        )
    for run in data["runs"]:
        lines += ["", f"## {run['run_id']}", "", f"Model: {run['model']}; status: {run['status']}.", ""]
        if run["environment"] == "e1":
            lines += [
                "| Step | N | Content N | Content acc | Salvage N | Salvage acc | Salvage cost |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
            for p in run["sample_curve"]:
                a, b = p["content_only"], p["reasoning_fallback_diagnostic"]
                vals = [
                    p["step"],
                    p["n_samples"],
                    a["n_parseable_labeled"],
                    a["accuracy_non_abstained"],
                    b["n_parseable_labeled"],
                    b["accuracy_non_abstained"],
                    b["cost_per_non_abstained"],
                ]
                lines.append(
                    "| "
                    + " | ".join(
                        "n/a" if v is None else f"{v:.4f}" if isinstance(v, float) else str(v) for v in vals
                    )
                    + " |"
                )
        else:
            lines.extend(f"- {limitation}" for limitation in run["limitations"])
    lines += [
        "",
        "Full per-step logged reward/evaluation curves and operational diagnostics are in analysis.json.",
        "Logged evaluation scalars lack independently established held-out identity and may be persisted",
        "across steps. No interpolation is applied; metric rows are not new independent evaluations.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    found = []
    missing = []
    for run_id in RUN_IDS:
        matches = [args.input / workspace / "training_runs" / run_id for workspace in ("personal", "team")]
        matches = [p for p in matches if (p / "metadata.json").exists()]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous duplicate run {run_id}; reconcile workspaces before analysis")
        if matches:
            found.append(summarize_run(matches[0]))
        else:
            missing.append(run_id)
    data = {
        "analysis_kind": "descriptive_training_records",
        "heldout_evidence": False,
        "missing_runs": missing,
        "runs": found,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    (args.output / "report.md").write_text(render_report(data))
    with (args.output / "sample_curves.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["run_id", "environment", "step", "n_samples", "unique_problem_ids", "mean_archived_reward"]
        )
        for run in found:
            for p in run["sample_curve"]:
                writer.writerow(
                    [
                        run["run_id"],
                        run["environment"],
                        p["step"],
                        p["n_samples"],
                        p["unique_problem_ids"],
                        p["mean_archived_reward"],
                    ]
                )
    print(f"Analyzed {len(found)} runs; {len(missing)} missing. Outputs: {args.output}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
