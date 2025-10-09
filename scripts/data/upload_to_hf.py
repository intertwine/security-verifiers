#!/usr/bin/env python3
"""
Build and upload all datasets to HuggingFace Hub.

This script:
1. Builds full production datasets using all build scripts
2. Uploads them to HuggingFace under the specified organization
3. Creates dataset cards with metadata

Usage:
    python scripts/data/upload_to_hf.py --hf-org intertwine-ai --dataset-name security-verifiers-e1-e2

Requirements:
    - HF_TOKEN in .env file or environment variable
    - huggingface_hub package: uv add huggingface_hub
    - python-dotenv package: uv add python-dotenv
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed. Run: uv add python-dotenv")
    sys.exit(1)

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("Error: huggingface_hub not installed. Run: uv add huggingface_hub")
    sys.exit(1)


def run_build_script(script: Path, args: List[str]) -> int:
    """Run a build script and return exit code."""
    cmd = [sys.executable, str(script)] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode


def build_e1_datasets() -> Dict[str, Path]:
    """Build E1 datasets and return paths."""
    print("\n=== Building E1 datasets ===")
    data_dir = Path("environments/sv-env-network-logs/data")

    # Build IoT-23 primary dataset
    rc = run_build_script(Path("scripts/data/build_e1_iot23.py"), ["--mode", "full"])
    if rc != 0:
        raise RuntimeError(f"Failed to build E1 IoT-23 dataset (exit code {rc})")

    # Build OOD datasets
    rc = run_build_script(Path("scripts/data/build_e1_ood.py"), ["--mode", "full"])
    if rc != 0:
        raise RuntimeError(f"Failed to build E1 OOD datasets (exit code {rc})")

    return {
        "iot23-train-dev-test": data_dir / "iot23-train-dev-test-v1.jsonl",
        "cic-ids-2017-ood": data_dir / "cic-ids-2017-ood-v1.jsonl",
        "unsw-nb15-ood": data_dir / "unsw-nb15-ood-v1.jsonl",
        "sampling-iot23": data_dir / "sampling-iot23-v1.json",
        "sampling-e1-ood": data_dir / "sampling-e1-ood-v1.json",
    }


def build_e2_datasets(k8s_root: Path, tf_root: Path) -> Dict[str, Path]:
    """Build E2 datasets and return paths."""
    print("\n=== Building E2 datasets ===")
    data_dir = Path("environments/sv-env-config-verification/data")

    rc = run_build_script(
        Path("scripts/data/build_e2_k8s_tf.py"),
        [
            "--k8s-root",
            str(k8s_root),
            "--tf-root",
            str(tf_root),
            "--mode",
            "full",
        ],
    )
    if rc != 0:
        raise RuntimeError(f"Failed to build E2 datasets (exit code {rc})")

    return {
        "k8s-labeled": data_dir / "k8s-labeled-v1.jsonl",
        "terraform-labeled": data_dir / "terraform-labeled-v1.jsonl",
        "tools-versions": data_dir / "tools-versions.json",
        "sampling-e2": data_dir / "sampling-e2-v1.json",
    }


def create_dataset_card(dataset_name: str, description: str, files: Dict[str, Path]) -> str:
    """Generate a dataset card in markdown format."""
    card = f"""---
license: mit
task_categories:
- text-classification
- token-classification
language:
- en
tags:
- security
- rl
- verifiers
- network-security
- config-verification
size_categories:
- 1K<n<10K
---

# {dataset_name}

{description}

## Dataset Structure

This dataset contains the following files:

"""
    for name, path in files.items():
        if path.exists():
            size_kb = path.stat().st_size / 1024
            card += f"- **{name}**: {path.name} ({size_kb:.1f} KB)\n"

    card += """

## Usage

```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("YOUR_ORG/YOUR_DATASET", data_files="iot23-train-dev-test-v1.jsonl")
```

## Citation

If you use this dataset, please cite:

```bibtex
@misc{security-verifiers,
  title={Open Security Verifiers: Composable RL Environments for AI Safety},
  author={intertwine},
  year={2025},
  url={https://github.com/intertwine/security-verifiers}
}
```

## License

MIT License

## Dataset Card Contact

For questions or issues, please open an issue at: https://github.com/intertwine/security-verifiers/issues
"""
    return card


def upload_to_huggingface(
    dataset_name: str, hf_org: str, files: Dict[str, Path], description: str, token: str
) -> str:
    """Upload dataset files to HuggingFace Hub."""
    repo_id = f"{hf_org}/{dataset_name}"
    print(f"\n=== Uploading to {repo_id} ===")

    # Create or get repo
    api = HfApi(token=token)
    try:
        create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=True, exist_ok=True)
        print(f"Created/found repo: {repo_id}")
    except Exception as e:
        print(f"Warning: Could not create repo: {e}")

    # Upload files
    for name, path in files.items():
        if not path.exists():
            print(f"Warning: Skipping {name} (file not found: {path})")
            continue

        try:
            api.upload_file(
                path_or_fileobj=str(path),
                path_in_repo=path.name,
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
            )
            print(f"  ✓ Uploaded {path.name}")
        except Exception as e:
            print(f"  ✗ Failed to upload {path.name}: {e}")

    # Create and upload dataset card
    card_content = create_dataset_card(dataset_name, description, files)
    card_path = Path("/tmp/README.md")
    card_path.write_text(card_content)

    try:
        api.upload_file(
            path_or_fileobj=str(card_path),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
        )
        print("  ✓ Uploaded dataset card")
    except Exception as e:
        print(f"  ✗ Failed to upload dataset card: {e}")

    return f"https://huggingface.co/datasets/{repo_id}"


def main():
    ap = argparse.ArgumentParser(description="Build and upload datasets to HuggingFace")
    ap.add_argument(
        "--hf-org",
        default="intertwine-ai",
        help="HuggingFace organization name",
    )
    ap.add_argument(
        "--dataset-name",
        default="security-verifiers",
        help="Base dataset name on HF Hub",
    )
    ap.add_argument(
        "--k8s-root",
        type=Path,
        default=Path("scripts/data/sources/kubernetes"),
        help="Path to K8s source files for E2",
    )
    ap.add_argument(
        "--tf-root",
        type=Path,
        default=Path("scripts/data/sources/terraform"),
        help="Path to Terraform source files for E2",
    )
    ap.add_argument(
        "--e1-only",
        action="store_true",
        help="Only build and upload E1 datasets",
    )
    ap.add_argument(
        "--e2-only",
        action="store_true",
        help="Only build and upload E2 datasets",
    )
    args = ap.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Check for HF_TOKEN
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN not found in .env file or environment")
        print("Please add it to .env: HF_TOKEN=your_token_here")
        print("Or set it with: export HF_TOKEN=your_token_here")
        sys.exit(1)

    try:
        # Build and upload E1
        if not args.e2_only:
            e1_files = build_e1_datasets()
            e1_url = upload_to_huggingface(
                dataset_name=f"{args.dataset_name}-e1",
                hf_org=args.hf_org,
                files=e1_files,
                description=(
                    "E1 (Network Log Anomaly Detection): IoT-23, CIC-IDS-2017, and UNSW-NB15 "
                    "datasets for calibrated classification with abstention."
                ),
                token=token,
            )
            print(f"\n✓ E1 uploaded: {e1_url}")

        # Build and upload E2
        if not args.e1_only:
            if not args.k8s_root.exists() or not args.tf_root.exists():
                print("\nWarning: Source directories not found:")
                print(f"  K8s: {args.k8s_root} (exists: {args.k8s_root.exists()})")
                print(f"  TF:  {args.tf_root} (exists: {args.tf_root.exists()})")
                print("\nRun 'make clone-e2-sources' first to clone source repositories.")
                if not args.e1_only:
                    sys.exit(1)
            else:
                e2_files = build_e2_datasets(args.k8s_root, args.tf_root)
                e2_url = upload_to_huggingface(
                    dataset_name=f"{args.dataset_name}-e2",
                    hf_org=args.hf_org,
                    files=e2_files,
                    description=(
                        "E2 (Security Config Verification): Kubernetes and Terraform configs "
                        "scanned with KubeLinter, Semgrep, and OPA for tool-grounded auditing."
                    ),
                    token=token,
                )
                print(f"\n✓ E2 uploaded: {e2_url}")

        print("\n✅ All datasets built and uploaded successfully!")
        print(f"\nView datasets at: https://huggingface.co/{args.hf_org}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
