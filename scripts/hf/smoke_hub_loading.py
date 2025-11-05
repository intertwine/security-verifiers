#!/usr/bin/env python3
"""Smoke test for gated HuggingFace dataset loading.

This script verifies that gated datasets can be loaded from HuggingFace Hub
with proper authentication and access permissions.

Usage:
    # Ensure environment variables are set
    export HF_TOKEN=hf_your_token_here
    export E1_HF_REPO=intertwine-ai/security-verifiers-e1
    export E2_HF_REPO=intertwine-ai/security-verifiers-e2

    # Run smoke test
    uv run python scripts/hf/smoke_hub_loading.py

    # Or with make
    make hub-test-datasets

Requirements:
    - HF_TOKEN: Must have access to the gated repositories
    - E1_HF_REPO: E1 dataset repository (default: intertwine-ai/security-verifiers-e1)
    - E2_HF_REPO: E2 dataset repository (default: intertwine-ai/security-verifiers-e2)
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sv_shared.dataset_loader import DEFAULT_E1_HF_REPO, DEFAULT_E2_HF_REPO


def check_prerequisites():
    """Check that HF_TOKEN is set."""
    if not os.environ.get("HF_TOKEN"):
        print("❌ Error: HF_TOKEN not set\n")
        print("To fix this:")
        print("  1. Add to .env file: HF_TOKEN=hf_your_token_here")
        print("  2. Or export it: export HF_TOKEN=hf_your_token_here")
        print()
        print("Get your token at: https://huggingface.co/settings/tokens")
        return False
    return True


def test_hub_loading(repo_id: str, split: str, env_name: str) -> bool:
    """Test loading a dataset split from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repository ID
        split: Dataset split name
        env_name: Environment name (for display)

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 70}")
    print(f"Testing {env_name}: {repo_id} (split: {split})")
    print(f"{'=' * 70}")

    try:
        from datasets import load_dataset

        # Load with authentication
        dataset = load_dataset(
            repo_id,
            split=split,
            token=os.environ.get("HF_TOKEN"),
        )

        # Print basic info
        print(f"✅ Successfully loaded {len(dataset)} examples")
        print(f"\nFeatures: {list(dataset.features.keys())}")

        # Show first example
        if len(dataset) > 0:
            print(f"\nFirst example keys: {list(dataset[0].keys())}")

        return True

    except Exception as e:
        print("❌ Failed to load dataset\n")
        print(f"Error: {e}\n")
        print("Troubleshooting:")
        print(f"  1. Visit: https://huggingface.co/datasets/{repo_id}")
        print("  2. Click 'Request access' if you haven't already")
        print("  3. Wait for manual approval")
        print("  4. Verify HF_TOKEN is set correctly")
        return False


def main():
    """Run smoke tests for all datasets."""
    if not check_prerequisites():
        sys.exit(1)

    # Get repository names from environment or use defaults
    e1_repo = os.environ.get("E1_HF_REPO", DEFAULT_E1_HF_REPO)
    e2_repo = os.environ.get("E2_HF_REPO", DEFAULT_E2_HF_REPO)

    print("=" * 70)
    print("HuggingFace Gated Dataset Smoke Test")
    print("=" * 70)
    print(f"\nE1 Repository: {e1_repo}")
    print(f"E2 Repository: {e2_repo}")

    # Test E1 datasets
    results = []
    results.append(test_hub_loading(e1_repo, "train", "E1 (Network Logs) - Primary"))

    # Test E2 datasets
    results.append(test_hub_loading(e2_repo, "train", "E2 (Config Verification) - Combined"))

    # Summary
    print(f"\n{'=' * 70}")
    print("Summary")
    print(f"{'=' * 70}")

    passed = sum(results)
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")

    if all(results):
        print("\n✅ All smoke tests passed!")
        print("\nYour HF_TOKEN has access to the gated datasets.")
        print("You can now use dataset_source='hub' in your environments.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed")
        print("\nCommon issues:")
        print("  - You haven't requested access to the datasets yet")
        print("  - Your access request hasn't been approved yet")
        print("  - HF_TOKEN doesn't have the right permissions")
        print("\nPlease request access and wait for approval:")
        print(f"  - E1: https://huggingface.co/datasets/{e1_repo}")
        print(f"  - E2: https://huggingface.co/datasets/{e2_repo}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
