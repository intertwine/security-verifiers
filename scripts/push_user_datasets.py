#!/usr/bin/env python3
"""Push Security Verifiers datasets to user's HuggingFace repositories.

This script pushes locally-built datasets to your own HuggingFace repositories,
allowing you to deploy fully functional environments to the Prime Intellect Hub.

Usage:
    # Set environment variables first
    export HF_TOKEN=hf_your_token_here
    export E1_HF_REPO=your-org/security-verifiers-e1-private
    export E2_HF_REPO=your-org/security-verifiers-e2-private

    # Run the script
    uv run python scripts/push_user_datasets.py

    # Or with specific repositories
    E1_HF_REPO=my-org/my-e1-data uv run python scripts/push_user_datasets.py

Requirements:
    - HF_TOKEN: HuggingFace API token with write permissions
    - E1_HF_REPO: Your HuggingFace repository for E1 datasets
    - E2_HF_REPO: Your HuggingFace repository for E2 datasets
    - Datasets must be built locally first (make data-e1, make data-e2-local)

See docs/user-dataset-guide.md for detailed instructions.
"""

import os
import sys
from pathlib import Path


def check_prerequisites():
    """Check that all prerequisites are met."""
    errors = []

    # Check HF_TOKEN
    if not os.environ.get("HF_TOKEN"):
        errors.append("❌ HF_TOKEN not set\n   Set it in .env file or: export HF_TOKEN=hf_your_token_here")

    # Check E1_HF_REPO
    if not os.environ.get("E1_HF_REPO"):
        errors.append(
            "❌ E1_HF_REPO not set\n"
            "   Set it in .env file or: export E1_HF_REPO=your-org/security-verifiers-e1-private"
        )

    # Check E2_HF_REPO
    if not os.environ.get("E2_HF_REPO"):
        errors.append(
            "❌ E2_HF_REPO not set\n"
            "   Set it in .env file or: export E2_HF_REPO=your-org/security-verifiers-e2-private"
        )

    if errors:
        print("Missing required configuration:\n")
        for error in errors:
            print(error)
        print()
        print("See docs/user-dataset-guide.md for setup instructions.")
        return False

    return True


def push_datasets():
    """Push datasets to HuggingFace."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ Error: 'datasets' package not installed")
        print("Install it with: uv pip install datasets")
        sys.exit(1)

    # Get repository names from environment
    E1_REPO = os.environ["E1_HF_REPO"]
    E2_REPO = os.environ["E2_HF_REPO"]

    print("=" * 70)
    print("Security Verifiers Dataset Upload")
    print("=" * 70)
    print("Target repositories:")
    print(f"  E1 (Network Logs):        {E1_REPO}")
    print(f"  E2 (Config Verification): {E2_REPO}")
    print()

    # E1 datasets
    print("=" * 70)
    print("Pushing E1 (Network Logs) datasets...")
    print("=" * 70)
    print()

    e1_data_dir = Path("environments/sv-env-network-logs/data")
    e1_datasets = [
        ("iot23-train-dev-test-v1.jsonl", "train", "IoT-23 primary dataset (N=1800)"),
        ("cic-ids-2017-ood-v1.jsonl", "cic_ood", "CIC-IDS-2017 OOD dataset (N=600)"),
        ("unsw-nb15-ood-v1.jsonl", "unsw_ood", "UNSW-NB15 OOD dataset (N=600)"),
    ]

    e1_success = 0
    e1_total = len(e1_datasets)

    for filename, split_name, description in e1_datasets:
        dataset_path = e1_data_dir / filename

        if not dataset_path.exists():
            print(f"⚠️  Skipping: {filename}")
            print(f"   Reason: File not found at {dataset_path}")
            print("   Build with: make data-e1")
            print()
            continue

        print(f"📤 Uploading: {filename}")
        print(f"   → Repository: {E1_REPO}")
        print(f"   → Split: {split_name}")
        print(f"   → Description: {description}")

        try:
            dataset = load_dataset("json", data_files=str(dataset_path), split="train")
            dataset.push_to_hub(
                E1_REPO,
                split=split_name,
                token=os.environ["HF_TOKEN"],
                private=True,
            )
            print(f"   ✅ Success! Pushed {len(dataset)} examples")
            e1_success += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

    # E2 datasets
    print("=" * 70)
    print("Pushing E2 (Config Verification) datasets...")
    print("=" * 70)
    print()

    e2_data_dir = Path("environments/sv-env-config-verification/data")
    e2_datasets = [
        ("k8s-labeled-v1.jsonl", "k8s", "Kubernetes configs (N=444)"),
        ("terraform-labeled-v1.jsonl", "terraform", "Terraform configs (N=115)"),
    ]

    e2_success = 0
    e2_total = len(e2_datasets)

    for filename, split_name, description in e2_datasets:
        dataset_path = e2_data_dir / filename

        if not dataset_path.exists():
            print(f"⚠️  Skipping: {filename}")
            print(f"   Reason: File not found at {dataset_path}")
            print("   Build with: make clone-e2-sources && make data-e2-local")
            print()
            continue

        print(f"📤 Uploading: {filename}")
        print(f"   → Repository: {E2_REPO}")
        print(f"   → Split: {split_name}")
        print(f"   → Description: {description}")

        try:
            dataset = load_dataset("json", data_files=str(dataset_path), split="train")
            dataset.push_to_hub(
                E2_REPO,
                split=split_name,
                token=os.environ["HF_TOKEN"],
                private=True,
            )
            print(f"   ✅ Success! Pushed {len(dataset)} examples")
            e2_success += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

    # Summary
    print("=" * 70)
    print("Upload Summary")
    print("=" * 70)
    print(f"E1 datasets: {e1_success}/{e1_total} successful")
    print(f"E2 datasets: {e2_success}/{e2_total} successful")
    print()

    if e1_success == e1_total and e2_success == e2_total:
        print("✅ All datasets uploaded successfully!")
        print()
        print("Next steps:")
        print()
        print("1. Verify uploads in your HuggingFace repositories:")
        print(f"   E1: https://huggingface.co/datasets/{E1_REPO}")
        print(f"   E2: https://huggingface.co/datasets/{E2_REPO}")
        print()
        print("2. Test loading from Hub:")
        print(f"   export E1_HF_REPO={E1_REPO}")
        print(f"   export E2_HF_REPO={E2_REPO}")
        print('   uv run python -c "from sv_env_network_logs import load_environment; \\')
        print("     env = load_environment(dataset_source='hub', max_examples=10); \\")
        print("     print(f'Loaded {len(env.dataset)} examples')\"")
        print()
        print("3. Deploy environments to Prime Intellect Hub:")
        print("   make deploy E=network-logs")
        print("   make deploy E=config-verification")
        print()
        print("See docs/hub-deployment.md for more information.")
    else:
        print("⚠️  Some datasets failed to upload.")
        print()
        print("Common issues:")
        print("- Missing datasets: Build with 'make data-e1' or 'make data-e2-local'")
        print("- Authentication: Verify HF_TOKEN has write permissions")
        print("- Network issues: Check your internet connection")
        print()
        print("See docs/user-dataset-guide.md for troubleshooting.")
        sys.exit(1)


def main():
    """Main entry point."""
    if not check_prerequisites():
        sys.exit(1)

    try:
        push_datasets()
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("\nPlease file an issue at:")
        print("https://github.com/intertwine/security-verifiers/issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
