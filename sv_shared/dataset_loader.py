"""Multi-tiered dataset loading for Security Verifiers environments.

This module provides a flexible dataset loading strategy that works both locally
and when deployed to Prime Intellect's Environments Hub. It supports:

1. Local JSONL files (built with `make data-e1` or `make data-e2-local`)
2. HuggingFace Hub datasets (public or private with HF_TOKEN)
3. User's own HuggingFace repositories (configurable via environment variables)
4. Synthetic fixtures for testing without data dependencies

Loading priority (when source="auto"):
    1. Local JSONL files (environments/sv-env-*/data/*.jsonl)
    2. HuggingFace Hub (with HF_TOKEN)
    3. Synthetic fixtures (for testing)

Environment Variables:
    HF_TOKEN: HuggingFace API token (required for private datasets)
    E1_HF_REPO: Custom HF repo for E1 datasets (default: intertwine-ai/security-verifiers-e1-private)
    E2_HF_REPO: Custom HF repo for E2 datasets (default: intertwine-ai/security-verifiers-e2-private)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Dict, Literal, Optional

from datasets import Dataset

# Default HuggingFace repositories (intertwine's private repos)
DEFAULT_E1_HF_REPO = "intertwine-ai/security-verifiers-e1-private"
DEFAULT_E2_HF_REPO = "intertwine-ai/security-verifiers-e2-private"

# Mapping of dataset names to HuggingFace dataset names and splits
HF_DATASET_MAP = {
    # E1 datasets
    "iot23-train-dev-test-v1.jsonl": {
        "split": "train",
        "env": "e1",
        "description": "IoT-23 primary dataset (N=1800)",
    },
    "cic-ids-2017-ood-v1.jsonl": {
        "split": "cic_ood",
        "env": "e1",
        "description": "CIC-IDS-2017 OOD dataset (N=600)",
    },
    "unsw-nb15-ood-v1.jsonl": {
        "split": "unsw_ood",
        "env": "e1",
        "description": "UNSW-NB15 OOD dataset (N=600)",
    },
    # E2 datasets
    "k8s-labeled-v1.jsonl": {
        "split": "k8s",
        "env": "e2",
        "description": "Kubernetes labeled dataset (N=444)",
    },
    "terraform-labeled-v1.jsonl": {
        "split": "terraform",
        "env": "e2",
        "description": "Terraform labeled dataset (N=115)",
    },
    "combined": {
        "split": "train",  # Combined split
        "env": "e2",
        "description": "Combined K8s + Terraform dataset (N=559)",
    },
}


DatasetSource = Literal["auto", "local", "hub", "synthetic"]


def _get_hf_repo(env: str) -> str:
    """Get HuggingFace repository name for the given environment.

    Users can override default repos by setting environment variables:
    - E1_HF_REPO: Custom repo for E1 datasets
    - E2_HF_REPO: Custom repo for E2 datasets

    Args:
        env: Environment name ("e1" or "e2")

    Returns:
        HuggingFace repository name
    """
    if env == "e1":
        return os.environ.get("E1_HF_REPO", DEFAULT_E1_HF_REPO)
    elif env == "e2":
        return os.environ.get("E2_HF_REPO", DEFAULT_E2_HF_REPO)
    else:
        raise ValueError(f"Unknown environment: {env}")


def _has_hf_credentials() -> bool:
    """Check if HuggingFace credentials are available."""
    return bool(os.environ.get("HF_TOKEN"))


def _local_dataset_exists(dataset_path: Path) -> bool:
    """Check if a local dataset file exists."""
    return dataset_path.exists() and dataset_path.is_file()


def _load_local_jsonl(
    dataset_path: Path,
    max_examples: Optional[int] = None,
    field_mapping: Optional[Dict[str, str]] = None,
) -> Dataset:
    """Load dataset from local JSONL file.

    Args:
        dataset_path: Path to JSONL file
        max_examples: Maximum number of examples to load
        field_mapping: Optional dict to rename fields (e.g., {"prompt": "question"})

    Returns:
        HuggingFace Dataset object
    """
    print(f"Loading local dataset from {dataset_path}")
    examples = []

    with open(dataset_path, "r") as f:
        for line in f:
            if line.strip():
                example = json.loads(line)

                # Apply field mapping if provided
                if field_mapping:
                    for old_field, new_field in field_mapping.items():
                        if old_field in example and new_field not in example:
                            example[new_field] = example[old_field]

                examples.append(example)

                if max_examples and len(examples) >= max_examples:
                    break

    return Dataset.from_list(examples)


def _load_from_hub(
    dataset_name: str,
    max_examples: Optional[int] = None,
    field_mapping: Optional[Dict[str, str]] = None,
) -> Dataset:
    """Load dataset from HuggingFace Hub.

    Args:
        dataset_name: Dataset name (e.g., "iot23-train-dev-test-v1.jsonl")
        max_examples: Maximum number of examples to load
        field_mapping: Optional dict to rename fields (e.g., {"prompt": "question"})

    Returns:
        HuggingFace Dataset object

    Raises:
        ValueError: If dataset name is not recognized or HF_TOKEN is not set
    """
    if not _has_hf_credentials():
        raise ValueError(
            "HF_TOKEN not found in environment. To load datasets from HuggingFace Hub:\n"
            "1. Set HF_TOKEN in your .env file or export it as an environment variable\n"
            "2. Request access to the dataset at https://github.com/intertwine/security-verifiers/issues\n"
            "3. Or build and push datasets to your own HF repo (see docs/hub-deployment.md)"
        )

    # Look up dataset metadata
    if dataset_name not in HF_DATASET_MAP:
        raise ValueError(f"Unknown dataset: {dataset_name}\nAvailable datasets: {', '.join(HF_DATASET_MAP.keys())}")

    metadata = HF_DATASET_MAP[dataset_name]
    hf_repo = _get_hf_repo(metadata["env"])
    split = metadata["split"]

    print(f"Loading dataset from HuggingFace Hub: {hf_repo} (split: {split})")

    try:
        from datasets import load_dataset

        # Load dataset with authentication
        dataset = load_dataset(
            hf_repo,
            split=split,
            token=os.environ.get("HF_TOKEN"),
        )

        # Apply max_examples limit
        if max_examples and len(dataset) > max_examples:
            dataset = dataset.select(range(max_examples))

        # Apply field mapping if provided
        if field_mapping:

            def map_fields(example):
                for old_field, new_field in field_mapping.items():
                    if old_field in example and new_field not in example:
                        example[new_field] = example[old_field]
                return example

            dataset = dataset.map(map_fields)

        return dataset

    except Exception as e:
        raise ValueError(
            f"Failed to load dataset from HuggingFace Hub: {e}\n"
            f"Repository: {hf_repo}\n"
            f"Split: {split}\n"
            "Troubleshooting:\n"
            "1. Verify HF_TOKEN is set and valid\n"
            "2. Request access to the dataset (see README.md)\n"
            "3. Or build datasets locally with 'make data-e1' or 'make data-e2-local'\n"
            "4. Or push datasets to your own HF repo and set E1_HF_REPO or E2_HF_REPO"
        ) from e


def load_dataset_with_fallback(
    dataset_name: str,
    env_root: Path,
    dataset_source: DatasetSource = "auto",
    max_examples: Optional[int] = None,
    field_mapping: Optional[Dict[str, str]] = None,
    synthetic_generator: Optional[Callable[[], Dataset]] = None,
) -> tuple[Dataset, str]:
    """Load dataset with multi-tiered fallback strategy.

    Loading priority (when source="auto"):
        1. Local JSONL files (env_root/data/*.jsonl)
        2. HuggingFace Hub (requires HF_TOKEN)
        3. Synthetic fixtures (if generator provided)

    Args:
        dataset_name: Dataset name (e.g., "iot23-train-dev-test-v1.jsonl", "builtin", "synthetic")
        env_root: Root directory of the environment (for resolving local paths)
        dataset_source: Source strategy ("auto", "local", "hub", or "synthetic")
        max_examples: Maximum number of examples to load
        field_mapping: Optional dict to rename fields (e.g., {"prompt": "question"})
        synthetic_generator: Optional function to generate synthetic dataset

    Returns:
        Tuple of (Dataset, resolved_dataset_name)

    Raises:
        FileNotFoundError: If dataset cannot be loaded from any source
    """
    original_dataset_name = dataset_name

    # Handle explicit synthetic request
    if dataset_name in ("synthetic", "test") or dataset_source == "synthetic":
        if synthetic_generator is None:
            raise ValueError(
                "Synthetic dataset requested but no generator provided. "
                "Environment must implement a synthetic dataset generator."
            )
        print(f"Using synthetic dataset (requested: {dataset_name})")
        dataset = synthetic_generator()
        return dataset, f"synthetic::{dataset_name}"

    # Determine local dataset path
    dataset_path = None
    if dataset_name.endswith((".jsonl", ".json")):
        # Try as absolute path first
        candidate = Path(dataset_name)
        if candidate.is_file():
            dataset_path = candidate
        else:
            # Try relative to environment root
            candidate = env_root / "data" / dataset_name
            if candidate.is_file():
                dataset_path = candidate

    # Try loading based on source strategy
    if dataset_source == "auto":
        # Strategy 1: Try local first
        if dataset_path and _local_dataset_exists(dataset_path):
            dataset = _load_local_jsonl(dataset_path, max_examples, field_mapping)
            return dataset, dataset_name

        # Strategy 2: Try HuggingFace Hub
        if _has_hf_credentials():
            try:
                dataset = _load_from_hub(dataset_name, max_examples, field_mapping)
                return dataset, f"hub::{dataset_name}"
            except (ValueError, Exception) as e:
                print(f"Warning: Failed to load from Hub: {e}")
                # Continue to fallback

        # Strategy 3: Fall back to synthetic if available
        if synthetic_generator:
            print(
                f"Warning: Dataset '{dataset_name}' not found locally or on Hub. Using synthetic dataset for testing."
            )
            dataset = synthetic_generator()
            return dataset, f"synthetic::{original_dataset_name}"

        # No fallback available
        raise FileNotFoundError(
            f"Dataset '{dataset_name}' not found.\n"
            f"Tried:\n"
            f"  1. Local file: {dataset_path or env_root / 'data' / dataset_name}\n"
            f"  2. HuggingFace Hub: {'Available' if _has_hf_credentials() else 'No HF_TOKEN set'}\n"
            f"  3. Synthetic fallback: {'Available' if synthetic_generator else 'Not available'}\n\n"
            "To fix this:\n"
            "  - Build datasets locally: make data-e1 or make data-e2-local\n"
            "  - Set HF_TOKEN to use Hub datasets (see README.md)\n"
            "  - Use dataset_source='synthetic' for testing"
        )

    elif dataset_source == "local":
        if not dataset_path or not _local_dataset_exists(dataset_path):
            raise FileNotFoundError(
                f"Local dataset not found: {dataset_path or env_root / 'data' / dataset_name}\n"
                "Build datasets with: make data-e1 or make data-e2-local"
            )
        dataset = _load_local_jsonl(dataset_path, max_examples, field_mapping)
        return dataset, dataset_name

    elif dataset_source == "hub":
        dataset = _load_from_hub(dataset_name, max_examples, field_mapping)
        return dataset, f"hub::{dataset_name}"

    else:
        raise ValueError(f"Unknown dataset_source: {dataset_source}")


__all__ = [
    "DatasetSource",
    "load_dataset_with_fallback",
    "HF_DATASET_MAP",
    "DEFAULT_E1_HF_REPO",
    "DEFAULT_E2_HF_REPO",
]
