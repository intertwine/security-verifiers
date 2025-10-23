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


def content_hash_key(row) -> str:
    """
    Generate content-based hash for deduplication.
    Uses flow metadata beyond just 5-tuple to reduce false duplicates.
    """
    import hashlib as H

    src = str(row.get("src_ip") or row.get("srcip") or "?")
    dst = str(row.get("dst_ip") or row.get("dstip") or "?")
    sp = str(row.get("sport") or row.get("src_port") or row.get("Src Port") or "?")
    dp = str(row.get("dport") or row.get("dst_port") or row.get("Dst Port") or "?")
    proto = str(row.get("proto") or row.get("Protocol Type") or row.get("Protocol") or "?")

    # Add content-based fields to reduce false duplicates
    sbytes = str(row.get("sbytes") or row.get("Tot Fwd Pkts") or row.get("Fwd Pkt Len Tot") or "?")
    dbytes = str(row.get("dbytes") or row.get("Tot Bwd Pkts") or row.get("Bwd Pkt Len Tot") or "?")
    dur = str(row.get("duration") or row.get("flow_duration") or row.get("Flow Duration") or "?")
    state = str(row.get("state") or row.get("conn_state") or "?")
    service = str(row.get("service") or row.get("Service") or "?")

    key = f"{src}|{dst}|{sp}|{dp}|{proto}|{sbytes}|{dbytes}|{dur}|{state}|{service}"
    return H.sha256(key.encode()).hexdigest()[:16]


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

    # Use content-based hash for deduplication
    content_hash = content_hash_key(row)

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
            "hash": content_hash,
            "split": split,
        },
    }


def dedup_by_hash(items):
    """Remove duplicate items by hash, keeping first occurrence."""
    seen = set()
    unique = []
    for item in items:
        h = item["meta"]["hash"]
        if h not in seen:
            seen.add(h)
            unique.append(item)
    return unique


def stratified_sample_cic(dataset, n_target: int, token=None):
    """
    Sample CIC-IDS-2017 with stratified approach to ensure label diversity.
    CIC-IDS-2017 has temporal clustering (benign first, attacks later), so we need
    to fetch a much larger pool to ensure we get attack samples.
    """
    from collections import Counter

    # CIC-IDS-2017 has severe temporal clustering - fetch 10x samples to reach attacks
    fetch_size = n_target * 10
    print(f"  Fetching {fetch_size} samples to ensure label diversity...")
    sampled = list(dataset.shuffle(seed=42).take(fetch_size))

    # Convert to items and dedup
    items = [to_item(dict(r), "cic-ids-2017") for r in sampled]
    items = dedup_by_hash(items)

    # Log label distribution before selection
    label_counts = Counter(item["answer"] for item in items)
    attack_counts = Counter(item["meta"]["attack_family"] for item in items)
    print(f"  After dedup: {len(items)} items")
    print(f"    Labels: {dict(label_counts)}")
    print(f"    Attack families: {dict(attack_counts)}")

    # Separate by label
    malicious = [x for x in items if x["answer"] == "Malicious"]
    benign = [x for x in items if x["answer"] == "Benign"]

    # Target 50/50 balance if we have attacks, otherwise warn
    if not malicious:
        print("  ⚠️  WARNING: No malicious samples found! Fetching more...")
        # Try fetching even more
        fetch_size = n_target * 30
        sampled = list(dataset.shuffle(seed=43).take(fetch_size))  # Different seed
        items = [to_item(dict(r), "cic-ids-2017") for r in sampled]
        items = dedup_by_hash(items)
        malicious = [x for x in items if x["answer"] == "Malicious"]
        benign = [x for x in items if x["answer"] == "Benign"]

    if not malicious:
        print("  ❌ Still no attacks found - returning benign-only dataset")
        return benign[:n_target]

    # Balanced sampling: 50% malicious, 50% benign
    n_malicious = min(n_target // 2, len(malicious))
    n_benign = n_target - n_malicious

    random.shuffle(malicious)
    random.shuffle(benign)

    result = malicious[:n_malicious] + benign[:n_benign]
    random.shuffle(result)

    print(f"  Final sample: {len(result)} items ({n_malicious} malicious, {n_benign} benign)")
    return result


def stratified_sample_unsw(dataset, n_target: int, token=None):
    """
    Sample UNSW-NB15 with stratified approach and deduplication.
    """
    from collections import Counter

    # Fetch 3x samples to account for deduplication
    fetch_size = min(n_target * 3, len(dataset))
    sampled = dataset.shuffle(seed=42).select(range(fetch_size))

    # Convert to items and dedup
    items = [to_item(dict(r), "unsw-nb15") for r in sampled]
    items = dedup_by_hash(items)

    # Log stats
    label_counts = Counter(item["answer"] for item in items)
    attack_counts = Counter(item["meta"]["attack_family"] for item in items)
    print(f"UNSW-NB15 after dedup: {len(items)} items")
    print(f"  Labels: {dict(label_counts)}")
    print(f"  Attack categories: {dict(attack_counts)}")

    # Simple random sample from deduped pool (already has natural balance)
    random.shuffle(items)
    return items[:n_target]


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
    print(f"Building CIC-IDS-2017 OOD dataset (target: {args.n} samples)...")
    cic: Dataset = load_dataset(args.cic_id, split="train", streaming=True, token=token)  # type: ignore[assignment]
    cic_items = stratified_sample_cic(cic, args.n, token)
    (outdir / f"cic-ids-2017-ood{suffix}.jsonl").write_text("\n".join(map(json.dumps, cic_items)) + "\n")

    # UNSW-NB15 OOD (has labels)
    print(f"\nBuilding UNSW-NB15 OOD dataset (target: {args.n} samples)...")
    unsw: Dataset = load_dataset(args.unsw_id, split="train", token=token)  # type: ignore[assignment]
    unsw_items = stratified_sample_unsw(unsw, args.n, token)
    (outdir / f"unsw-nb15-ood{suffix}.jsonl").write_text("\n".join(map(json.dumps, unsw_items)) + "\n")

    # Write sampling metadata
    from collections import Counter

    cic_attack_counts = Counter(x["meta"]["attack_family"] for x in cic_items)
    unsw_attack_counts = Counter(x["meta"]["attack_family"] for x in unsw_items)

    sampling_path = outdir / f"sampling-e1-ood{suffix}.json"
    stats = {
        "mode": args.mode,
        "seed": 42,
        "n_requested": args.n,
        "deduplication": "content-based (5-tuple + bytes + duration + state + service)",
        "datasets": {
            "cic-ids-2017": {
                "hf_id": args.cic_id,
                "total": len(cic_items),
                "labels": {
                    "Malicious": sum(1 for x in cic_items if x["answer"] == "Malicious"),
                    "Benign": sum(1 for x in cic_items if x["answer"] == "Benign"),
                },
                "attack_families": dict(cic_attack_counts),
                "unique_hashes": len(set(x["meta"]["hash"] for x in cic_items)),
            },
            "unsw-nb15": {
                "hf_id": args.unsw_id,
                "total": len(unsw_items),
                "labels": {
                    "Malicious": sum(1 for x in unsw_items if x["answer"] == "Malicious"),
                    "Benign": sum(1 for x in unsw_items if x["answer"] == "Benign"),
                },
                "attack_families": dict(unsw_attack_counts),
                "unique_hashes": len(set(x["meta"]["hash"] for x in unsw_items)),
            },
        },
    }
    if args.mode == "test":
        stats["warning"] = "CI fixture only - not for evaluation"

    sampling_path.write_text(json.dumps(stats, indent=2))
    print(f"\n✅ Wrote OOD datasets to {outdir}")
    print("Sampling metadata:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
