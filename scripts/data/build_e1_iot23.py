#!/usr/bin/env python3
"""
Build E1 dataset splits from IoT-23 (or CICIoT2023 variant) into the SV JSONL schema.

Output files (under environments/sv-env-network-logs/data/):
  - iot23-train-dev-test-v1.jsonl
  - sampling-iot23-v1.json

Schema per item:
{
  "question": "<short natural language summary of the flow>",
  "answer": "Malicious" | "Benign",
  "meta": {
    "source": "iot23",
    "scenario": "<scenario-id>",
    "attack_family": "<family-or-NA>",
    "hash": "<dedup-hash>",
    "split": "train|dev|test"
  }
}

Note: We use "question" instead of "prompt" because when message_type="chat",
Verifiers will automatically convert "question" into a "prompt" field containing
a list of chat messages. If we include "prompt" as a string, it won't be converted.
"""

import argparse
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from datasets import load_dataset
except Exception as e:
    raise SystemExit("Please `uv add datasets` (HF Datasets) before running.") from e

RANDOM_SEED = 42
random.seed(RANDOM_SEED)


def five_tuple_key(row: Dict[str, Any]) -> str:
    # Works with common IoT-23 HF variants; fall back gracefully
    src = str(row.get("src_ip") or row.get("source_ip") or row.get("src") or row.get("id.orig_h") or "?")
    dst = str(row.get("dst_ip") or row.get("destination_ip") or row.get("dst") or row.get("id.resp_h") or "?")
    sp = str(
        row.get("src_port") or row.get("sport") or row.get("src_port_num") or row.get("id.orig_p") or "?"
    )
    dp = str(
        row.get("dst_port") or row.get("dport") or row.get("dst_port_num") or row.get("id.resp_p") or "?"
    )
    proto = str(row.get("protocol") or row.get("proto") or "?")
    t = f"{src}|{dst}|{sp}|{dp}|{proto}"
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def get_port(row: Dict[str, Any], port_type: str) -> str:
    """Extract port with fallback for multiple column names."""
    if port_type == "src":
        candidates = ["src_port", "sport", "id.orig_p", "Src Port"]
    else:
        candidates = ["dst_port", "dport", "id.resp_p", "Dst Port"]

    for col in candidates:
        if col in row and row[col] is not None:
            val = row[col]
            # Handle the case where port might be 0 or negative
            if isinstance(val, (int, float)) and val >= 0:
                return str(int(val))
            elif isinstance(val, str) and val.strip() and val != "-":
                return val.strip()
    return "?"


def render_prompt(row: Dict[str, Any]) -> str:
    proto = row.get("protocol") or row.get("proto") or "?"
    sp = get_port(row, "src")
    dp = get_port(row, "dst")
    dur = row.get("duration") or row.get("flow_duration") or "?"
    # For 19kmunz/iot-23-preprocessed: orig_bytes + resp_bytes
    orig_b = row.get("orig_bytes") or 0
    resp_b = row.get("resp_bytes") or 0
    byt = row.get("total_bytes") or row.get("bytes") or (orig_b + resp_b if orig_b or resp_b else "?")
    flags = row.get("flags") or row.get("tcp_flags") or row.get("history") or ""
    dev = row.get("device") or row.get("hostname") or "unknown-device"
    return (
        f"Device {dev} observed {proto} {sp}→{dp}, duration {dur}, bytes {byt}, flags [{flags}]. "
        f"Decide: Malicious or Benign (you may Abstain if unsure)."
    )


def normalize_label(row: Dict[str, Any]) -> str:
    lbl = str(row.get("label") or row.get("binary_label") or row.get("Attack_label") or "").lower()
    if "malicious" in lbl or "mal" in lbl or lbl == "1":
        return "Malicious"
    return "Benign"


def stratified_sample(rows: List[Dict[str, Any]], n_per_class: int) -> List[Dict[str, Any]]:
    by_class = {"Malicious": [], "Benign": []}
    for r in rows:
        by_class[normalize_label(r)].append(r)
    out = []
    for c in ("Malicious", "Benign"):
        pool = by_class[c]
        random.shuffle(pool)
        out.extend(pool[:n_per_class])
    return out


def dedup(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for r in rows:
        h = five_tuple_key(r)
        if h in seen:
            continue
        seen.add(h)
        r["_hash"] = h
        out.append(r)
    return out


def split_by_scenario(
    rows: List[Dict[str, Any]], train_p=0.70, dev_p=0.15
) -> List[Tuple[Dict[str, Any], str]]:
    """
    Split dataset into train/dev/test with proper distribution.
    Default: 70% train, 15% dev, 15% test

    Uses stratified split within each scenario to handle imbalanced scenarios.
    """
    from collections import defaultdict

    # Group by scenario and label to maintain balance
    by_scn_label = defaultdict(list)
    for r in rows:
        scn = str(
            r.get("scenario")
            or r.get("Scenario")
            or r.get("Label")
            or r.get("conn_state")
            or r.get("service")
            or "unknown"
        )
        label = r.get("label") or r.get("binary_label") or "unknown"
        key = f"{scn}:{label}"
        by_scn_label[key].append(r)

    # Split each scenario:label group proportionally
    paired = []
    for group_rows in by_scn_label.values():
        random.shuffle(group_rows)
        n = len(group_rows)
        train_cut = int(n * train_p)
        dev_cut = int(n * (train_p + dev_p))

        for i, r in enumerate(group_rows):
            if i < train_cut:
                split = "train"
            elif i < dev_cut:
                split = "dev"
            else:
                split = "test"
            paired.append((r, split))

    # Final shuffle to mix scenarios
    random.shuffle(paired)
    return paired


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hf-id",
        default="19kmunz/iot-23-preprocessed",
        help="HF dataset id for IoT-23 preprocessed",
    )
    ap.add_argument("--limit", type=int, default=1800, help="total rows target after dedup (balanced)")
    ap.add_argument("--outdir", default="environments/sv-env-network-logs/data")
    ap.add_argument(
        "--mode",
        choices=["full", "test"],
        default="full",
        help="Build mode: 'full' for production (uploaded to HF), 'test' for CI fixtures",
    )
    args = ap.parse_args()

    # Test mode uses smaller limits for CI
    if args.mode == "test":
        args.limit = 20  # Small but realistic

    # Use HF_TOKEN from environment if available
    token = os.environ.get("HF_TOKEN")
    ds = load_dataset(args.hf_id, split="train", token=token)  # many HF variants expose a 'train' split
    # Convert dataset items to Dict[str, Any], handling potential bytes values
    rows: List[Dict[str, Any]] = []
    for x in ds:
        # HF datasets return dict-like objects; ensure we normalize to Dict[str, Any]
        row_dict = {str(k): (v.decode() if isinstance(v, bytes) else v) for k, v in dict(x).items()}  # type: ignore[arg-type]
        rows.append(row_dict)

    rows = dedup(rows)
    # Balance classes for a compact baseline
    n_per = max(1, min(args.limit // 2, len(rows) // 2))
    rows_bal = stratified_sample(rows, n_per_class=n_per)

    # Tag scenario if available (use conn_state or service as proxy)
    for r in rows_bal:
        r["scenario"] = (
            r.get("scenario") or r.get("Label") or r.get("conn_state") or r.get("service") or "unknown"
        )

    paired = split_by_scenario(rows_bal)

    out = []
    for r, split in paired:
        item = {
            "question": render_prompt(r),
            "answer": normalize_label(r),
            "meta": {
                "source": "iot23",
                "scenario": str(r.get("scenario")),
                "attack_family": str(r.get("attack_type") or r.get("family") or "NA"),
                "hash": r["_hash"],
                "split": split,
            },
        }
        out.append(item)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Choose filename based on mode
    suffix = "-test" if args.mode == "test" else "-v1"
    data_path = outdir / f"iot23-train-dev-test{suffix}.jsonl"
    sampling_path = outdir / f"sampling-iot23{suffix}.json"

    with data_path.open("w") as f:
        for ex in out:
            f.write(json.dumps(ex) + "\n")

    stats = {
        "mode": args.mode,
        "seed": RANDOM_SEED,
        "total": len(out),
        "by_split": {
            "train": sum(1 for x in out if x["meta"]["split"] == "train"),
            "dev": sum(1 for x in out if x["meta"]["split"] == "dev"),
            "test": sum(1 for x in out if x["meta"]["split"] == "test"),
        },
    }
    if args.mode == "test":
        stats["warning"] = "CI fixture only - not for evaluation"

    sampling_path.write_text(json.dumps(stats, indent=2))
    print(f"Wrote {data_path} ({stats})")


if __name__ == "__main__":
    main()
