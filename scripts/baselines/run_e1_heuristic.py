#!/usr/bin/env python3
"""Run a heuristic baseline for E1 (network logs) and write SV-Bench artifacts."""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from bench.report import generate_report_md, generate_summary
from scripts.eval_utils import build_base_metadata

REPO_ROOT = Path(__file__).resolve().parents[2]


SUSPICIOUS_KEYWORDS = {
    "TOR",
    "C2",
    "SYN_SCAN",
    "BRUTE",
    "AUTH_FAILED",
    "MALWARE",
    "BEACON",
    "PORTS=",
}

BENIGN_KEYWORDS = {
    "STATUS=OK",
    "AUTH_SUCCESS",
    "DNS",
    "ICMP",
}

SUSPICIOUS_PORTS = {22, 23, 445, 3389, 4444, 9001, 5900}
BENIGN_PORTS = {53, 80, 443}


def _parse_dest_port(text: str) -> int | None:
    match = re.search(r"→\s*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"->\s*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"PORT=(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _heuristic_label(question: str) -> tuple[str, float]:
    upper = question.upper()
    if any(keyword in upper for keyword in SUSPICIOUS_KEYWORDS):
        return "Malicious", 0.8
    if any(keyword in upper for keyword in BENIGN_KEYWORDS):
        return "Benign", 0.6

    dest_port = _parse_dest_port(question)
    if dest_port is not None:
        if dest_port in SUSPICIOUS_PORTS:
            return "Malicious", 0.7
        if dest_port in BENIGN_PORTS:
            return "Benign", 0.55

        if dest_port == 22 and ("FLAGS [S]" in upper or "AUTH_FAILED" in upper):
            return "Malicious", 0.65

    return "Abstain", 0.3


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Heuristic baseline for E1.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/public_mini/e1.jsonl"),
        help="Path to E1 dataset JSONL (default: datasets/public_mini/e1.jsonl)",
    )
    parser.add_argument("--num-examples", type=int, default=None, help="Limit examples (default: all)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (unused, for metadata)")
    parser.add_argument("--baseline-name", type=str, default="e1-heuristic", help="Baseline name")
    parser.add_argument("--run-id", type=str, default=None, help="Run id (default: random)")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Output directory (default: outputs/evals/sv-env-network-logs--heuristic/<run_id>)",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found: {args.dataset}")

    items = _load_jsonl(args.dataset)
    if args.num_examples is not None:
        items = items[: args.num_examples]

    run_id = args.run_id or uuid.uuid4().hex[:8]
    outdir = args.outdir or (REPO_ROOT / "outputs" / "evals" / "sv-env-network-logs--heuristic" / run_id)
    outdir.mkdir(parents=True, exist_ok=True)

    metadata = build_base_metadata(
        environment="sv-env-network-logs",
        model="heuristic",
        effective_model="heuristic",
        dataset=str(args.dataset),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        num_examples=len(items),
        repo_root=REPO_ROOT,
        dataset_path=args.dataset,
        seed=args.seed,
        baseline_name=args.baseline_name,
        baseline_type="heuristic",
    )
    (outdir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        question = str(item.get("question", ""))
        answer = item.get("answer", "")
        pred_label, confidence = _heuristic_label(question)
        results.append(
            {
                "index": idx,
                "prompt": question,
                "answer": answer,
                "predicted_label": pred_label,
                "confidence": confidence,
            }
        )

    with (outdir / "results.jsonl").open("w", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record) + "\n")

    summary = generate_summary("e1", results, metadata, run_id=run_id, strict=False)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (outdir / "report.md").write_text(generate_report_md(summary), encoding="utf-8")

    print(f"✓ Wrote heuristic baseline to {outdir}")


if __name__ == "__main__":
    main()
