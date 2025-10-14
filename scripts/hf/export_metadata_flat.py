#!/usr/bin/env python3
"""
Export metadata in a flat, standardized schema for HuggingFace Dataset Viewer.

This script normalizes all metadata splits into a uniform six-column schema:
- section: Category of metadata (sampling/ood/tools/provenance/notes)
- name: Short identifier key
- description: 1-2 sentence summary
- payload_json: JSON-serialized details (minified)
- version: Dataset version (e.g., "v1")
- created_at: ISO-8601 UTC timestamp

Usage:
    # Build E1 metadata locally
    python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl

    # Build and push to public metadata repo
    python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl \\
        --repo intertwine-ai/security-verifiers-e1-metadata --split meta --push

    # Build and push to private full dataset repo (only updates meta split)
    python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl \\
        --repo intertwine-ai/security-verifiers-e1 --split meta --push --private

Requirements:
    - HF_TOKEN in .env file or environment variable (for --push)
    - huggingface_hub package: uv add huggingface_hub
    - python-dotenv package: uv add python-dotenv
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed. Run: uv add python-dotenv")
    sys.exit(1)

try:
    from datasets import Dataset, Features, Value
    from huggingface_hub import HfApi
except ImportError:
    print("Error: huggingface_hub or datasets not installed.")
    print("Run: uv add huggingface_hub datasets")
    sys.exit(1)


# Flat schema for all metadata splits
HF_FLAT_FEATURES = Features(
    {
        "section": Value("string"),
        "name": Value("string"),
        "description": Value("string"),
        "payload_json": Value("string"),
        "version": Value("string"),
        "created_at": Value("string"),
    }
)


def load_json_file(path: Path) -> dict[str, Any]:
    """Load JSON file or return empty dict if not found."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}")
        return {}


def build_e1_metadata(data_dir: Path, created_at: str) -> list[dict[str, str]]:
    """Build E1 metadata rows in flat schema."""
    rows = []

    # Sampling: IoT-23 primary dataset
    sampling_iot23 = load_json_file(data_dir / "sampling-iot23-v1.json")
    if sampling_iot23:
        rows.append(
            {
                "section": "sampling",
                "name": "iot23-train-dev-test",
                "description": "IoT-23 primary dataset sampling metadata (train/dev/test splits)",
                "payload_json": json.dumps(sampling_iot23, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # Sampling: E1 OOD datasets
    sampling_ood = load_json_file(data_dir / "sampling-e1-ood-v1.json")
    if sampling_ood:
        rows.append(
            {
                "section": "sampling",
                "name": "e1-ood-datasets",
                "description": "Out-of-distribution datasets sampling metadata (CIC-IDS-2017, UNSW-NB15)",
                "payload_json": json.dumps(sampling_ood, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # OOD: CIC-IDS-2017 details
    if sampling_ood and "datasets" in sampling_ood and "cic-ids-2017" in sampling_ood["datasets"]:
        cic_data = sampling_ood["datasets"]["cic-ids-2017"]
        rows.append(
            {
                "section": "ood",
                "name": "cic-ids-2017-ood",
                "description": "CIC-IDS-2017 out-of-distribution test set (600 samples)",
                "payload_json": json.dumps(cic_data, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # OOD: UNSW-NB15 details
    if sampling_ood and "datasets" in sampling_ood and "unsw-nb15" in sampling_ood["datasets"]:
        unsw_data = sampling_ood["datasets"]["unsw-nb15"]
        rows.append(
            {
                "section": "ood",
                "name": "unsw-nb15-ood",
                "description": "UNSW-NB15 out-of-distribution test set (600 samples)",
                "payload_json": json.dumps(unsw_data, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # Provenance
    rows.append(
        {
            "section": "provenance",
            "name": "dataset-sources",
            "description": "Original dataset sources and references",
            "payload_json": json.dumps(
                {
                    "iot23": {
                        "source": "Avast AIC IoT-23 dataset",
                        "url": "https://www.stratosphereips.org/datasets-iot23",
                        "hf_id": "stratosphereips/iot-23",
                    },
                    "cic-ids-2017": {
                        "source": "Canadian Institute for Cybersecurity IDS 2017",
                        "url": "https://www.unb.ca/cic/datasets/ids-2017.html",
                        "hf_id": "bvk/CICIDS-2017",
                    },
                    "unsw-nb15": {
                        "source": "UNSW-NB15 Network Intrusion Dataset",
                        "url": "https://research.unsw.edu.au/projects/unsw-nb15-dataset",
                        "hf_id": "Mireu-Lab/UNSW-NB15",
                    },
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    # Notes
    rows.append(
        {
            "section": "notes",
            "name": "privacy-rationale",
            "description": "Explanation of private dataset hosting to prevent training contamination",
            "payload_json": json.dumps(
                {
                    "reason": "Training contamination prevention",
                    "details": (
                        "Datasets are private to preserve benchmark validity and enable "
                        "fair model comparisons over time."
                    ),
                    "access": "Request access via GitHub Issues: https://github.com/intertwine/security-verifiers/issues",
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    return rows


def build_e2_metadata(data_dir: Path, created_at: str) -> list[dict[str, str]]:
    """Build E2 metadata rows in flat schema."""
    rows = []

    # Sampling: E2 K8s and Terraform
    sampling_e2 = load_json_file(data_dir / "sampling-e2-v1.json")
    if sampling_e2:
        rows.append(
            {
                "section": "sampling",
                "name": "e2-k8s-terraform",
                "description": "E2 config verification dataset sampling metadata (K8s and Terraform)",
                "payload_json": json.dumps(sampling_e2, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # Tools: Versions
    tools_versions = load_json_file(data_dir / "tools-versions.json")
    if tools_versions:
        rows.append(
            {
                "section": "tools",
                "name": "tool-versions",
                "description": "Pinned security tool versions for reproducible scanning",
                "payload_json": json.dumps(tools_versions, separators=(",", ":")),
                "version": "v1",
                "created_at": created_at,
            }
        )

    # Tools: Descriptions
    rows.append(
        {
            "section": "tools",
            "name": "tool-descriptions",
            "description": "Security tools used for ground-truth violation detection",
            "payload_json": json.dumps(
                {
                    "kube-linter": {
                        "description": "Kubernetes YAML linting and security checks",
                        "url": "https://github.com/stackrox/kube-linter",
                    },
                    "semgrep": {
                        "description": "Pattern-based static analysis for K8s and Terraform",
                        "url": "https://semgrep.dev",
                    },
                    "opa": {
                        "description": "Policy-as-code validation with Rego",
                        "url": "https://www.openpolicyagent.org",
                    },
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    # Provenance
    rows.append(
        {
            "section": "provenance",
            "name": "dataset-sources",
            "description": "Source repositories for Kubernetes and Terraform configurations",
            "payload_json": json.dumps(
                {
                    "k8s": {
                        "description": "Real-world K8s manifests from popular open-source projects",
                        "examples": ["kubernetes/examples", "kubernetes/kubernetes"],
                        "scanning": "KubeLinter, Semgrep, OPA/Rego policies",
                    },
                    "terraform": {
                        "description": "Infrastructure-as-code from real projects",
                        "examples": ["hashicorp/terraform-provider-aws"],
                        "scanning": "Semgrep, OPA/Rego policies",
                    },
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    # Notes
    rows.append(
        {
            "section": "notes",
            "name": "privacy-rationale",
            "description": "Explanation of private dataset hosting to prevent training contamination",
            "payload_json": json.dumps(
                {
                    "reason": "Training contamination prevention",
                    "details": (
                        "Datasets are private to preserve benchmark validity and enable "
                        "fair model comparisons over time."
                    ),
                    "access": "Request access via GitHub Issues: https://github.com/intertwine/security-verifiers/issues",
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    # Notes: Multi-turn performance
    rows.append(
        {
            "section": "notes",
            "name": "multi-turn-performance",
            "description": "Performance comparison with and without tool calling",
            "payload_json": json.dumps(
                {
                    "with_tools": 0.93,
                    "without_tools": 0.62,
                    "note": (
                        "Models achieve significantly higher reward when using tool calling for verification"
                    ),
                },
                separators=(",", ":"),
            ),
            "version": "v1",
            "created_at": created_at,
        }
    )

    return rows


def export_metadata_flat(
    env: str,
    out_path: Path,
    created_at: str | None = None,
) -> list[dict[str, str]]:
    """Export metadata in flat schema to JSONL file."""
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if env == "e1":
        data_dir = Path("environments/sv-env-network-logs/data")
        rows = build_e1_metadata(data_dir, created_at)
    elif env == "e2":
        data_dir = Path("environments/sv-env-config-verification/data")
        rows = build_e2_metadata(data_dir, created_at)
    else:
        raise ValueError(f"Unknown environment: {env}")

    if not rows:
        print(f"Warning: No metadata rows generated for {env}")
        return []

    # Validate all rows have the required keys
    required_keys = {"section", "name", "description", "payload_json", "version", "created_at"}
    for i, row in enumerate(rows):
        if set(row.keys()) != required_keys:
            raise ValueError(f"Row {i} has invalid keys: {set(row.keys())} != {required_keys}")
        # Validate payload_json is valid JSON
        try:
            json.loads(row["payload_json"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Row {i} has invalid JSON in payload_json: {e}")

    # Write JSONL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"✓ Exported {len(rows)} metadata rows to {out_path}")
    return rows


def push_to_hub(
    repo_id: str,
    split: str,
    jsonl_path: Path,
    token: str,
) -> None:
    """Push metadata to HuggingFace Hub."""
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    print(f"\n=== Pushing {split} split to {repo_id} ===")

    # Load dataset with explicit schema
    dataset = Dataset.from_json(str(jsonl_path), features=HF_FLAT_FEATURES)

    # Verify schema
    print(f"Dataset features: {dataset.features}")
    print(f"Dataset size: {len(dataset)} rows")

    # Validate all rows
    for i, row in enumerate(dataset):
        # Check all keys present
        if set(row.keys()) != set(HF_FLAT_FEATURES.keys()):
            raise ValueError(f"Row {i} missing keys: {set(HF_FLAT_FEATURES.keys()) - set(row.keys())}")
        # Validate payload_json
        try:
            json.loads(row["payload_json"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Row {i} has invalid JSON in payload_json: {e}")

    # Push to hub (only the specified split)
    api = HfApi(token=token)
    try:
        # Check if repo exists
        api.repo_info(repo_id=repo_id, repo_type="dataset", token=token)
        print(f"✓ Found existing repo: {repo_id}")
    except Exception:
        print(f"✗ Repository not found: {repo_id}")
        print("Please create the repository first or check permissions.")
        sys.exit(1)

    # Push the dataset
    try:
        dataset.push_to_hub(
            repo_id=repo_id,
            split=split,
            token=token,
        )
        print(f"✓ Pushed {split} split to {repo_id}")
        print(f"  View at: https://huggingface.co/datasets/{repo_id}")
    except Exception as e:
        print(f"✗ Failed to push to hub: {e}")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(
        description="Export metadata in flat schema for HuggingFace Dataset Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--env",
        required=True,
        choices=["e1", "e2"],
        help="Environment to export metadata for",
    )
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSONL file path (e.g., build/hf/e1/meta.jsonl)",
    )
    ap.add_argument(
        "--repo",
        help="HuggingFace repo ID (e.g., intertwine-ai/security-verifiers-e1-metadata)",
    )
    ap.add_argument(
        "--split",
        default="meta",
        help="Split name for HuggingFace dataset (default: meta)",
    )
    ap.add_argument(
        "--push",
        action="store_true",
        help="Push to HuggingFace Hub after exporting",
    )
    ap.add_argument(
        "--private",
        action="store_true",
        help="Flag for logging only (private repos must be created manually)",
    )
    ap.add_argument(
        "--created-at",
        help="Override created_at timestamp (ISO-8601 UTC, e.g., 2025-10-13T00:00:00Z)",
    )
    args = ap.parse_args()

    # Validate arguments
    if args.push and not args.repo:
        print("Error: --repo is required when using --push")
        sys.exit(1)

    # Load environment variables
    load_dotenv()

    # Export metadata locally
    rows = export_metadata_flat(
        env=args.env,
        out_path=args.out,
        created_at=args.created_at,
    )

    if not rows:
        print("No metadata rows to export")
        sys.exit(1)

    # Push to hub if requested
    if args.push:
        token = os.environ.get("HF_TOKEN")
        if not token:
            print("Error: HF_TOKEN not found in .env file or environment")
            print("Please add it to .env: HF_TOKEN=your_token_here")
            sys.exit(1)

        visibility = "PRIVATE" if args.private else "PUBLIC"
        print(f"\nPushing to {visibility} repo: {args.repo}")

        push_to_hub(
            repo_id=args.repo,
            split=args.split,
            jsonl_path=args.out,
            token=token,
        )

        print(f"\n✅ Successfully pushed {args.split} split to {args.repo}")
    else:
        print(f"\n✓ Metadata exported to {args.out}")
        print("Run with --push --repo <repo-id> to upload to HuggingFace")


if __name__ == "__main__":
    main()
