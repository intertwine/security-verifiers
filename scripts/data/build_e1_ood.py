#!/usr/bin/env python3
"""
Create compact OOD JSONLs for E1 to validate generalization.

Outputs under environments/sv-env-network-logs/data/:
  - cic-ids-2017-ood-v1.jsonl
  - unsw-nb15-ood-v1.jsonl
  - sampling-e1-ood-v1.json
"""

import argparse
import json
import os
import random
from pathlib import Path

try:
    from datasets import Dataset, load_dataset
except Exception as e:
    raise SystemExit("Please `uv add datasets`.") from e

random.seed(42)


def norm_label(s: str) -> str:
    s = (s or "").lower()
    # Handle various label formats: BENIGN, benign, Normal, 0 → Benign; everything else → Malicious
    if s in {"benign", "normal", "0"}:
        return "Benign"
    return "Malicious"


def h(x: str) -> str:
    import hashlib as H

    return H.sha256(x.encode()).hexdigest()[:16]


def to_item(row, source: str, split="ood", force_malicious=False):
    proto = row.get("proto") or row.get("Protocol Type") or row.get("Protocol") or "?"
    sp = row.get("sport") or row.get("src_port") or row.get("Src Port") or "?"
    dp = row.get("dport") or row.get("dst_port") or row.get("Dst Port") or "?"
    # For UNSW: use sbytes + dbytes; for CIC-IDS: use Flow Bytes/s or packet stats
    sbytes = row.get("sbytes") or 0
    dbytes = row.get("dbytes") or 0
    flow_bytes = row.get("Flow Bytes/s") or row.get("Tot Fwd Pkts") or 0
    by = (
        row.get("bytes")
        or row.get("tot_bytes")
        or (sbytes + dbytes if sbytes or dbytes else (flow_bytes if flow_bytes else "?"))
    )
    dur = row.get("duration") or row.get("flow_duration") or row.get("dur") or "?"
    dev = row.get("device") or "unknown-device"
    prompt = f"Device {dev} observed {proto} {sp}→{dp}, duration {dur}, bytes {by}. Decide Malicious/Benign."
    key = f"{row.get('src_ip', '?')}|{row.get('dst_ip', '?')}|{sp}|{dp}|{proto}"

    # Handle label: force_malicious for DDoS-only datasets, otherwise try to extract label
    if force_malicious:
        answer = "Malicious"
    else:
        # Try various label column names (case-sensitive for HF datasets)
        label_val = (
            row.get("Label")  # CIC-IDS-2017
            or row.get("label")  # lowercase variant
            or row.get("attack_cat")  # UNSW-NB15
            or row.get("attack")
            or row.get("binary_label")
            or ""
        )
        answer = norm_label(str(label_val))

    return {
        "prompt": prompt,
        "answer": answer,
        "meta": {
            "source": source,
            "scenario": str(row.get("scenario") or row.get("attack_cat") or row.get("state") or "unknown"),
            "attack_family": str(row.get("attack_cat") or row.get("family") or "NA"),
            "hash": h(key),
            "split": split,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cic-id", default="bvk/CICIDS-2017", help="HF id for CIC-IDS-2017 dataset (labeled OOD)"
    )
    ap.add_argument("--unsw-id", default="Mireu-Lab/UNSW-NB15", help="HF id for UNSW-NB15 dataset")
    ap.add_argument("--n", type=int, default=600)
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
        args.n = 10  # Small but realistic

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Use HF_TOKEN from environment if available
    token = os.environ.get("HF_TOKEN")

    # Choose filename suffix based on mode
    suffix = "-test" if args.mode == "test" else "-v1"

    # CIC-IDS-2017 OOD (labeled dataset with benign + 15 attack categories)
    cic: Dataset = load_dataset(args.cic_id, split="train", streaming=True, token=token)  # type: ignore[assignment]
    cic_sampled = list(cic.shuffle(seed=42).take(args.n))
    cic_items = [to_item(dict(r), "cic-ids-2017") for r in cic_sampled]
    (outdir / f"cic-ids-2017-ood{suffix}.jsonl").write_text("\n".join(map(json.dumps, cic_items)) + "\n")

    # UNSW-NB15 OOD (has labels)
    unsw: Dataset = load_dataset(args.unsw_id, split="train", token=token)  # type: ignore[assignment]
    unsw = unsw.shuffle(seed=42).select(range(min(args.n, len(unsw))))
    unsw_items = [to_item(dict(r), "unsw-nb15") for r in unsw]
    (outdir / f"unsw-nb15-ood{suffix}.jsonl").write_text("\n".join(map(json.dumps, unsw_items)) + "\n")

    # Write sampling metadata
    sampling_path = outdir / f"sampling-e1-ood{suffix}.json"
    stats = {
        "mode": args.mode,
        "seed": 42,
        "n_requested": args.n,
        "datasets": {
            "cic-ids-2017": {
                "hf_id": args.cic_id,
                "total": len(cic_items),
                "labels": {
                    "Malicious": sum(1 for x in cic_items if x["answer"] == "Malicious"),
                    "Benign": sum(1 for x in cic_items if x["answer"] == "Benign"),
                },
            },
            "unsw-nb15": {
                "hf_id": args.unsw_id,
                "total": len(unsw_items),
                "labels": {
                    "Malicious": sum(1 for x in unsw_items if x["answer"] == "Malicious"),
                    "Benign": sum(1 for x in unsw_items if x["answer"] == "Benign"),
                },
            },
        },
    }
    if args.mode == "test":
        stats["warning"] = "CI fixture only - not for evaluation"

    sampling_path.write_text(json.dumps(stats, indent=2))
    print(f"Wrote OOD sets to {outdir}")
    print(f"Sampling metadata: {stats}")


if __name__ == "__main__":
    main()
