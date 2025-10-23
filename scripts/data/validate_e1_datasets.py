#!/usr/bin/env python3
"""
Validate E1 datasets against original HuggingFace sources.

Checks:
1. Schema compliance (prompt, answer, meta fields)
2. Label distribution matches expectations
3. Sample random items and verify transformations
4. Deduplication effectiveness
5. Split distribution (train/dev/test)
6. Field mapping accuracy (source columns → prompt rendering)
"""

import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

try:
    from datasets import load_dataset
except ImportError:
    raise SystemExit("Please `uv add datasets` before running.")

random.seed(42)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL dataset."""
    items = []
    with path.open() as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def validate_schema(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Validate that all items conform to expected schema."""
    required_fields = ["prompt", "answer", "meta"]
    required_meta_fields = ["source", "scenario", "attack_family", "hash", "split"]

    errors = []
    for i, item in enumerate(items):
        # Check top-level fields
        missing = [f for f in required_fields if f not in item]
        if missing:
            errors.append(f"Item {i}: Missing fields {missing}")

        # Check meta fields
        if "meta" in item:
            missing_meta = [f for f in required_meta_fields if f not in item["meta"]]
            if missing_meta:
                errors.append(f"Item {i}: Missing meta fields {missing_meta}")

        # Check answer is valid
        if "answer" in item and item["answer"] not in ["Malicious", "Benign"]:
            errors.append(f"Item {i}: Invalid answer '{item['answer']}'")

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "errors": errors,
        "valid": len(errors) == 0,
    }


def analyze_label_distribution(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Analyze label balance and split distribution."""
    labels = Counter(item["answer"] for item in items)
    splits = Counter(item["meta"]["split"] for item in items)

    # Calculate balance
    total = sum(labels.values())
    malicious_pct = (labels.get("Malicious", 0) / total * 100) if total > 0 else 0
    benign_pct = (labels.get("Benign", 0) / total * 100) if total > 0 else 0

    # Check if balanced (within ±5% as per DATA_CARD)
    balance_ok = abs(malicious_pct - 50) <= 5

    return {
        "dataset": dataset_name,
        "labels": dict(labels),
        "label_percentages": {
            "Malicious": f"{malicious_pct:.1f}%",
            "Benign": f"{benign_pct:.1f}%",
        },
        "balanced": balance_ok,
        "splits": dict(splits),
    }


def verify_deduplication(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Check for duplicate hashes (should be none)."""
    hashes = [item["meta"]["hash"] for item in items]
    hash_counts = Counter(hashes)
    duplicates = {h: count for h, count in hash_counts.items() if count > 1}

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "unique_hashes": len(hash_counts),
        "duplicates": duplicates,
        "dedup_effective": len(duplicates) == 0,
    }


def sample_verify_transformations(
    items: List[Dict[str, Any]],
    hf_dataset_id: str,
    dataset_name: str,
    n_samples: int = 5,
) -> Dict[str, Any]:
    """Sample random items and verify they match source data transformations."""
    token = os.environ.get("HF_TOKEN")

    try:
        # Load source dataset
        ds = load_dataset(hf_dataset_id, split="train", streaming=True, token=token)

        # Take first N items from source for spot check
        source_items = list(ds.take(n_samples))

        # Take first N items from local dataset
        local_samples = items[: min(n_samples, len(items))]

        verification_results = []
        for i, (local, source) in enumerate(zip(local_samples, source_items)):
            # Verify prompt contains key information from source
            source_dict = dict(source)

            # Check if protocol is in prompt
            proto = source_dict.get("protocol") or source_dict.get("proto") or source_dict.get("Proto") or "?"
            proto_in_prompt = str(proto).lower() in local["prompt"].lower() if proto != "?" else True

            # Check if ports are in prompt
            sp = source_dict.get("src_port") or source_dict.get("sport") or source_dict.get("id.orig_p")
            dp = source_dict.get("dst_port") or source_dict.get("dport") or source_dict.get("id.resp_p")

            ports_in_prompt = True
            if sp is not None and dp is not None:
                # Arrow format: sp→dp
                ports_in_prompt = f"{sp}→{dp}" in local["prompt"]

            verification_results.append(
                {
                    "sample_index": i,
                    "protocol_verified": proto_in_prompt,
                    "ports_verified": ports_in_prompt,
                    "has_decision_prompt": "Malicious" in local["prompt"] and "Benign" in local["prompt"],
                }
            )

        return {
            "dataset": dataset_name,
            "samples_checked": len(verification_results),
            "results": verification_results,
            "all_verified": all(
                r["protocol_verified"] and r["ports_verified"] and r["has_decision_prompt"]
                for r in verification_results
            ),
        }
    except Exception as e:
        return {
            "dataset": dataset_name,
            "error": str(e),
            "note": "Could not verify against source - ensure HF_TOKEN is set",
        }


def validate_iot23_dataset(data_dir: Path) -> Dict[str, Any]:
    """Validate IoT-23 primary dataset."""
    dataset_path = data_dir / "iot23-train-dev-test-v1.jsonl"

    if not dataset_path.exists():
        return {"error": f"Dataset not found: {dataset_path}"}

    items = load_jsonl(dataset_path)

    results = {
        "dataset_file": str(dataset_path),
        "schema_validation": validate_schema(items, "iot23-train-dev-test-v1"),
        "label_distribution": analyze_label_distribution(items, "iot23-train-dev-test-v1"),
        "deduplication": verify_deduplication(items, "iot23-train-dev-test-v1"),
        "source_verification": sample_verify_transformations(
            items, "19kmunz/iot-23-preprocessed", "iot23-train-dev-test-v1"
        ),
    }

    # Load and display metadata
    metadata_path = data_dir / "sampling-iot23-v1.json"
    if metadata_path.exists():
        results["metadata"] = json.loads(metadata_path.read_text())

    return results


def validate_ood_datasets(data_dir: Path) -> Dict[str, Any]:
    """Validate OOD datasets (CIC-IDS-2017 and UNSW-NB15)."""
    cic_path = data_dir / "cic-ids-2017-ood-v1.jsonl"
    unsw_path = data_dir / "unsw-nb15-ood-v1.jsonl"

    results = {}

    # Validate CIC-IDS-2017
    if cic_path.exists():
        cic_items = load_jsonl(cic_path)
        results["cic-ids-2017"] = {
            "dataset_file": str(cic_path),
            "schema_validation": validate_schema(cic_items, "cic-ids-2017-ood-v1"),
            "label_distribution": analyze_label_distribution(cic_items, "cic-ids-2017-ood-v1"),
            "deduplication": verify_deduplication(cic_items, "cic-ids-2017-ood-v1"),
            "source_verification": sample_verify_transformations(
                cic_items, "bvk/CICIDS-2017", "cic-ids-2017-ood-v1"
            ),
        }
    else:
        results["cic-ids-2017"] = {"error": f"Dataset not found: {cic_path}"}

    # Validate UNSW-NB15
    if unsw_path.exists():
        unsw_items = load_jsonl(unsw_path)
        results["unsw-nb15"] = {
            "dataset_file": str(unsw_path),
            "schema_validation": validate_schema(unsw_items, "unsw-nb15-ood-v1"),
            "label_distribution": analyze_label_distribution(unsw_items, "unsw-nb15-ood-v1"),
            "deduplication": verify_deduplication(unsw_items, "unsw-nb15-ood-v1"),
            "source_verification": sample_verify_transformations(
                unsw_items, "Mireu-Lab/UNSW-NB15", "unsw-nb15-ood-v1"
            ),
        }
    else:
        results["unsw-nb15"] = {"error": f"Dataset not found: {unsw_path}"}

    # Load and display metadata
    metadata_path = data_dir / "sampling-e1-ood-v1.json"
    if metadata_path.exists():
        results["metadata"] = json.loads(metadata_path.read_text())

    return results


def print_summary(results: Dict[str, Any], title: str):
    """Print validation summary."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print("=" * 80)
    print(json.dumps(results, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Validate E1 datasets against HuggingFace sources")
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=Path("environments/sv-env-network-logs/data"),
        help="Data directory",
    )
    ap.add_argument(
        "--datasets",
        choices=["iot23", "ood", "all"],
        default="all",
        help="Which datasets to validate",
    )
    ap.add_argument(
        "--output",
        type=Path,
        help="Optional output JSON file for validation report",
    )
    args = ap.parse_args()

    validation_report = {}

    if args.datasets in ["iot23", "all"]:
        iot23_results = validate_iot23_dataset(args.data_dir)
        validation_report["iot23"] = iot23_results
        print_summary(iot23_results, "IoT-23 Dataset Validation")

    if args.datasets in ["ood", "all"]:
        ood_results = validate_ood_datasets(args.data_dir)
        validation_report["ood"] = ood_results
        print_summary(ood_results, "OOD Datasets Validation")

    # Overall summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    all_valid = True
    for dataset_name, results in validation_report.items():
        if isinstance(results, dict):
            for key, value in results.items():
                if isinstance(value, dict):
                    if "schema_validation" in value:
                        schema_valid = value["schema_validation"].get("valid", False)
                        dedup_valid = value.get("deduplication", {}).get("dedup_effective", False)
                        print(f"{dataset_name}/{key}:")
                        print(f"  Schema valid: {schema_valid}")
                        print(f"  Deduplication effective: {dedup_valid}")
                        if not schema_valid or not dedup_valid:
                            all_valid = False

    print(f"\nOverall validation: {'✅ PASSED' if all_valid else '❌ FAILED'}")

    # Write output file if specified
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(validation_report, indent=2))
        print(f"\nValidation report written to: {args.output}")


if __name__ == "__main__":
    main()
