#!/usr/bin/env python3
"""
Push canonical splits for E1/E2 to PRIVATE HF repos with explicit Features.

This script:
1. Loads canonical JSONL files from environment data directories
2. Applies explicit HuggingFace Features for consistent nested rendering
3. Pushes train/dev/test/ood splits to PRIVATE repos

IMPORTANT: This never modifies schema or touches metadata-only repos.

Target PRIVATE repos:
- E1: intertwine-ai/security-verifiers-e1
- E2: intertwine-ai/security-verifiers-e2

Usage:
    # Dry run (no push)
    uv run python scripts/hf/push_canonical_with_features.py --env e1 \\
        --repo intertwine-ai/security-verifiers-e1 \\
        --data-dir environments/sv-env-network-logs/data

    # Actually push
    uv run python scripts/hf/push_canonical_with_features.py --env e1 \\
        --repo intertwine-ai/security-verifiers-e1 \\
        --data-dir environments/sv-env-network-logs/data \\
        --push

Requirements:
    - HF_TOKEN in .env file or environment variable
    - datasets, huggingface_hub packages
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed. Run: uv add python-dotenv")
    sys.exit(1)

try:
    from datasets import Dataset, Features, Value
except ImportError:
    print("Error: datasets not installed. Run: uv add datasets")
    sys.exit(1)


# ========== E1 Features ==========
E1_FEATURES = Features(
    {
        "prompt": Value("string"),
        "answer": Value("string"),  # Keep as string to match JSONL format (Benign/Malicious)
        "meta": {
            "source": Value("string"),
            "scenario": Value("string"),
            "attack_family": Value("string"),
            "hash": Value("string"),
            "split": Value("string"),
        },
    }
)

# ========== E2 Features ==========
# Note: For list of dicts, HF uses [dict_schema] syntax (not Sequence)
E2_FEATURES = Features(
    {
        "prompt": Value("string"),
        "info": {
            "violations": [
                {
                    "tool": Value("string"),
                    "rule_id": Value("string"),
                    "severity": Value("string"),
                    "msg": Value("string"),
                    "loc": Value("string"),
                }
            ],
            "patch": Value("string"),
        },
        "meta": {
            "lang": Value("string"),
            "source": Value("string"),
            "hash": Value("string"),
        },
    }
)


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file into list of dicts."""
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def discover_splits(data_dir: Path, env: str) -> dict[str, Path]:
    """
    Discover canonical split files in data directory.

    Returns dict mapping split names to file paths.
    Only includes production files (not demo files).
    """
    mapping = {}

    # Define production file patterns
    if env == "e1":
        # E1: iot23-train-dev-test-v1.jsonl, cic-ids-2017-ood-v1.jsonl, unsw-nb15-ood-v1.jsonl
        # Map to splits: train, dev, test (from iot23), ood (from cic/unsw combined)
        iot23_file = data_dir / "iot23-train-dev-test-v1.jsonl"
        cic_file = data_dir / "cic-ids-2017-ood-v1.jsonl"
        unsw_file = data_dir / "unsw-nb15-ood-v1.jsonl"

        # For E1, we split the iot23 file by 'split' field
        # And combine OOD files
        if iot23_file.exists():
            mapping["iot23-combined"] = iot23_file
        if cic_file.exists() or unsw_file.exists():
            mapping["ood"] = (cic_file, unsw_file)
    else:  # e2
        # E2: k8s-labeled-v1.jsonl, terraform-labeled-v1.jsonl
        # These are combined into a single 'train' split
        k8s_file = data_dir / "k8s-labeled-v1.jsonl"
        tf_file = data_dir / "terraform-labeled-v1.jsonl"

        if k8s_file.exists() or tf_file.exists():
            mapping["train"] = (k8s_file, tf_file)

    return mapping


def prepare_e1_splits(data_dir: Path) -> dict[str, list[dict]]:
    """
    Prepare E1 splits from canonical files.

    E1 structure:
    - iot23-train-dev-test-v1.jsonl contains rows with meta.split = train/dev/test
    - cic-ids-2017-ood-v1.jsonl and unsw-nb15-ood-v1.jsonl are OOD data
    """
    splits = {"train": [], "dev": [], "test": [], "ood": []}

    # Load and split iot23 file by meta.split
    iot23_file = data_dir / "iot23-train-dev-test-v1.jsonl"
    if iot23_file.exists():
        rows = load_jsonl(iot23_file)
        for row in rows:
            split = row.get("meta", {}).get("split", "unknown")
            if split in splits:
                splits[split].append(row)

    # Load OOD files
    for ood_file in [
        data_dir / "cic-ids-2017-ood-v1.jsonl",
        data_dir / "unsw-nb15-ood-v1.jsonl",
    ]:
        if ood_file.exists():
            splits["ood"].extend(load_jsonl(ood_file))

    # Remove empty splits
    return {k: v for k, v in splits.items() if v}


def prepare_e2_splits(data_dir: Path) -> dict[str, list[dict]]:
    """
    Prepare E2 splits from canonical files.

    E2 structure:
    - k8s-labeled-v1.jsonl and terraform-labeled-v1.jsonl combine into single 'train' split
    - Coerce info.patch None → "" to match Features
    """
    splits = {"train": []}

    for labeled_file in [
        data_dir / "k8s-labeled-v1.jsonl",
        data_dir / "terraform-labeled-v1.jsonl",
    ]:
        if labeled_file.exists():
            rows = load_jsonl(labeled_file)
            # Coerce patch None → ""
            for row in rows:
                if isinstance(row, dict):
                    info = row.get("info", {})
                    if isinstance(info, dict) and info.get("patch") is None:
                        row["info"]["patch"] = ""
            splits["train"].extend(rows)

    # Remove empty splits
    return {k: v for k, v in splits.items() if v}


def push_splits(env: str, repo_id: str, data_dir: Path, do_push: bool, token: str | None = None):
    """Build datasets with explicit Features and push to HF."""
    print(f"\n{'=' * 60}")
    print(f"Environment: {env}")
    print(f"Repo: {repo_id}")
    print(f"Data dir: {data_dir}")
    print(f"Push: {do_push}")
    print(f"{'=' * 60}\n")

    # Prepare splits
    if env == "e1":
        splits_data = prepare_e1_splits(data_dir)
        features = E1_FEATURES
    else:  # e2
        splits_data = prepare_e2_splits(data_dir)
        features = E2_FEATURES

    if not splits_data:
        print(f"⚠️  No canonical data found in {data_dir}")
        return

    # Build and push each split
    for split, rows in splits_data.items():
        print(f"\n--- Split: {split} ---")
        print(f"Rows: {len(rows)}")

        if not rows:
            print(f"⚠️  No rows for split '{split}', skipping")
            continue

        # Create dataset with explicit Features
        try:
            dataset = Dataset.from_list(rows, features=features)
            print(f"✓ Dataset created with features: {list(dataset.features.keys())}")
            print(f"  Sample keys: {list(rows[0].keys())}")
        except Exception as e:
            import traceback

            print(f"✗ Failed to create dataset: {e}")
            print(f"  Full error:\n{traceback.format_exc()}")
            continue

        # Push to hub
        if do_push:
            try:
                dataset.push_to_hub(
                    repo_id=repo_id,
                    split=split,
                    token=token,
                )
                print(f"✓ Pushed to {repo_id} split={split}")
            except Exception as e:
                print(f"✗ Failed to push: {e}")
        else:
            print(f"[DRY RUN] Would push {len(rows)} rows to {repo_id} split={split}")


def main():
    ap = argparse.ArgumentParser(
        description="Push canonical splits with explicit Features to PRIVATE HF repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--env",
        choices=["e1", "e2"],
        required=True,
        help="Environment (e1=network-logs, e2=config-verification)",
    )
    ap.add_argument(
        "--repo",
        required=True,
        help="HuggingFace repo ID (e.g., intertwine-ai/security-verifiers-e1)",
    )
    ap.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing canonical JSONL files",
    )
    ap.add_argument(
        "--push",
        action="store_true",
        help="Actually push to HuggingFace (default: dry run)",
    )
    args = ap.parse_args()

    # Validate data directory exists
    if not args.data_dir.exists():
        print(f"Error: Data directory not found: {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    # Load environment variables
    load_dotenv()

    # Check for token if pushing
    token = None
    if args.push:
        token = os.environ.get("HF_TOKEN")
        if not token:
            print("Error: HF_TOKEN not found in .env file or environment")
            print("Please add it to .env: HF_TOKEN=your_token_here")
            sys.exit(1)

    # Push splits
    push_splits(
        env=args.env,
        repo_id=args.repo,
        data_dir=args.data_dir,
        do_push=args.push,
        token=token,
    )

    print(f"\n{'=' * 60}")
    if args.push:
        print("✅ Push complete!")
        print(f"View at: https://huggingface.co/datasets/{args.repo}")
    else:
        print("✓ Dry run complete. Use --push to actually push to HuggingFace.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
