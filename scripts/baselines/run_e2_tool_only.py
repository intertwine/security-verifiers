#!/usr/bin/env python3
"""Run a tool-only baseline for E2 (config verification) and write SV-Bench artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from bench.report import generate_report_md, generate_summary  # noqa: E402
from scripts.eval_utils import build_base_metadata  # noqa: E402


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _normalize_violations(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        vid = item.get("id")
        rule_id = item.get("rule_id")
        tool = item.get("tool")
        if not vid:
            if rule_id and tool:
                vid = f"{tool}/{rule_id}"
            else:
                vid = rule_id
        if not vid:
            continue
        normalized.append({"id": str(vid), "severity": item.get("severity", "med")})
    return normalized


def _oracle_from_answer(answer: Any) -> list[dict[str, Any]]:
    if isinstance(answer, str):
        try:
            answer_obj = json.loads(answer)
        except json.JSONDecodeError:
            return []
    elif isinstance(answer, dict):
        answer_obj = answer
    else:
        return []
    oracle = answer_obj.get("oracle")
    if oracle is None:
        oracle = answer_obj.get("violations")
    return _normalize_violations(oracle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool-only baseline for E2.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/public_mini/e2.jsonl"),
        help="Path to E2 dataset JSONL (default: datasets/public_mini/e2.jsonl)",
    )
    parser.add_argument("--num-examples", type=int, default=None, help="Limit examples (default: all)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (unused, for metadata)")
    parser.add_argument("--baseline-name", type=str, default="e2-tool-only", help="Baseline name")
    parser.add_argument("--run-id", type=str, default=None, help="Run id (default: random)")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Output directory (default: outputs/evals/sv-env-config-verification--tool-only/<run_id>)",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found: {args.dataset}")

    items = _load_jsonl(args.dataset)
    if args.num_examples is not None:
        items = items[: args.num_examples]

    run_id = args.run_id or uuid.uuid4().hex[:8]
    outdir = args.outdir or (
        REPO_ROOT / "outputs" / "evals" / "sv-env-config-verification--tool-only" / run_id
    )
    outdir.mkdir(parents=True, exist_ok=True)

    metadata = build_base_metadata(
        environment="sv-env-config-verification",
        model="tool-only",
        effective_model="tool-only",
        dataset=str(args.dataset),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        num_examples=len(items),
        repo_root=REPO_ROOT,
        dataset_path=args.dataset,
        seed=args.seed,
        baseline_name=args.baseline_name,
        baseline_type="tool-only",
    )
    (outdir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        question = str(item.get("question", ""))
        answer = item.get("answer")
        if answer is None and "info" in item:
            answer = json.dumps(item.get("info", {}))
        oracle = _oracle_from_answer(answer)
        results.append(
            {
                "index": idx,
                "prompt": question,
                "answer": answer or "",
                "predicted_violations": oracle,
                "oracle_violations": oracle,
                "patch": "",
                "patch_applied": False,
                "post_patch_violations": [],
                "valid_json": True,
                "turns": 1,
            }
        )

    with (outdir / "results.jsonl").open("w", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record) + "\n")

    summary = generate_summary("e2", results, metadata, run_id=run_id, strict=False)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (outdir / "report.md").write_text(generate_report_md(summary), encoding="utf-8")

    print(f"✓ Wrote tool-only baseline to {outdir}")


if __name__ == "__main__":
    main()
