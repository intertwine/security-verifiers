#!/usr/bin/env python3
"""Build public mini datasets for E1 and E2.

Creates deterministic, small JSONL subsets that are safe to run locally and
small enough for quick baselines (50–200 items).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Iterable


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _write_jsonl(path: Path, items: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item) + "\n")


def _label_from_answer(answer: Any) -> str | None:
    if isinstance(answer, str):
        return answer
    if isinstance(answer, dict):
        label = answer.get("label")
        if isinstance(label, str):
            return label
    return None


def _sample_balanced_e1(items: list[dict[str, Any]], n: int, rng: random.Random) -> list[dict[str, Any]]:
    benign = [item for item in items if _label_from_answer(item.get("answer")) == "Benign"]
    malicious = [item for item in items if _label_from_answer(item.get("answer")) == "Malicious"]

    if benign and malicious:
        target = n // 2
        rng.shuffle(benign)
        rng.shuffle(malicious)
        sampled = benign[:target] + malicious[: target if n % 2 == 0 else target + 1]
        rng.shuffle(sampled)
        return sampled[:n]

    rng.shuffle(items)
    return items[:n]


def _sample_e2(items: list[dict[str, Any]], n: int, rng: random.Random) -> list[dict[str, Any]]:
    items = list(items)
    rng.shuffle(items)
    return items[:n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build public mini datasets for E1 and E2.")
    parser.add_argument(
        "--e1-source",
        type=Path,
        default=Path("environments/sv-env-network-logs/data/iot23-train-dev-test-v1.jsonl"),
        help="Source JSONL for E1 (default: IoT-23 v1)",
    )
    parser.add_argument(
        "--e2-k8s-source",
        type=Path,
        default=Path("environments/sv-env-config-verification/data/k8s-labeled-v1.jsonl"),
        help="Source JSONL for E2 K8s (default: k8s-labeled-v1.jsonl)",
    )
    parser.add_argument(
        "--e2-tf-source",
        type=Path,
        default=Path("environments/sv-env-config-verification/data/terraform-labeled-v1.jsonl"),
        help="Source JSONL for E2 Terraform (default: terraform-labeled-v1.jsonl)",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("datasets/public_mini"),
        help="Output directory (default: datasets/public_mini)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--e1-count", type=int, default=100, help="Number of E1 samples (default: 100)")
    parser.add_argument("--e2-k8s-count", type=int, default=80, help="Number of E2 K8s samples (default: 80)")
    parser.add_argument("--e2-tf-count", type=int, default=20, help="Number of E2 TF samples (default: 20)")

    args = parser.parse_args()
    rng = random.Random(args.seed)

    if not args.e1_source.exists():
        raise SystemExit(f"E1 source not found: {args.e1_source}")
    if not args.e2_k8s_source.exists():
        raise SystemExit(f"E2 k8s source not found: {args.e2_k8s_source}")
    if not args.e2_tf_source.exists():
        raise SystemExit(f"E2 tf source not found: {args.e2_tf_source}")

    e1_items = _load_jsonl(args.e1_source)
    e1_sample = _sample_balanced_e1(e1_items, args.e1_count, rng)
    for item in e1_sample:
        meta = item.get("meta")
        if isinstance(meta, dict):
            meta["public_mini"] = True
            meta["source_dataset"] = args.e1_source.name

    e2_k8s_items = _load_jsonl(args.e2_k8s_source)
    e2_tf_items = _load_jsonl(args.e2_tf_source)
    e2_sample = _sample_e2(e2_k8s_items, args.e2_k8s_count, rng) + _sample_e2(
        e2_tf_items, args.e2_tf_count, rng
    )
    rng.shuffle(e2_sample)
    for item in e2_sample:
        meta = item.get("meta")
        if isinstance(meta, dict):
            meta["public_mini"] = True
            meta["source_dataset"] = (
                args.e2_k8s_source.name if meta.get("lang") == "k8s" else args.e2_tf_source.name
            )

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    e1_path = outdir / "e1.jsonl"
    e2_path = outdir / "e2.jsonl"
    _write_jsonl(e1_path, e1_sample)
    _write_jsonl(e2_path, e2_sample)

    sampling = {
        "seed": args.seed,
        "e1": {"source": str(args.e1_source), "count": len(e1_sample)},
        "e2": {
            "k8s_source": str(args.e2_k8s_source),
            "tf_source": str(args.e2_tf_source),
            "k8s_count": args.e2_k8s_count,
            "tf_count": args.e2_tf_count,
            "count": len(e2_sample),
        },
    }
    (outdir / "sampling-public-mini.json").write_text(json.dumps(sampling, indent=2), encoding="utf-8")

    print(f"✓ Wrote {len(e1_sample)} E1 samples to {e1_path}")
    print(f"✓ Wrote {len(e2_sample)} E2 samples to {e2_path}")


if __name__ == "__main__":
    main()
