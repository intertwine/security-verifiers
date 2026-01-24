#!/usr/bin/env python3
"""
Shared utilities for evaluation scripts.

Provides common functionality like early failure detection to prevent
costly runs with misconfigured models or API keys, and metadata generation
for reproducibility.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_git_commit(repo_root: Path | None = None) -> str | None:
    """Get current git commit hash (short form)."""
    try:
        cwd = str(repo_root) if repo_root else None
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        return res.stdout.strip() or None
    except Exception:
        return None


def get_python_version() -> str:
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_package_version(package_name: str) -> str | None:
    """Get installed package version."""
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        return None


def get_verifiers_version() -> str | None:
    """Get verifiers library version."""
    return get_package_version("verifiers")


def get_env_version(env_name: str) -> str | None:
    """Get environment package version."""
    # Try hyphenated name first (package name), then underscored (import name)
    version = get_package_version(env_name)
    if version is None:
        version = get_package_version(env_name.replace("-", "_"))
    if version is None:
        version = get_package_version(env_name.replace("_", "-"))
    return version


def get_dataset_revision(dataset_path: Path) -> str | None:
    """
    Get dataset revision as SHA256 hash of file content.

    For large files, hashes first 1MB + last 1MB + file size for speed.
    """
    if not dataset_path.exists():
        return None

    try:
        file_size = dataset_path.stat().st_size
        # For small files (< 10MB), hash entire content
        if file_size < 10 * 1024 * 1024:
            content = dataset_path.read_bytes()
            return f"sha256:{hashlib.sha256(content).hexdigest()[:16]}"

        # For large files, hash first 1MB + last 1MB + size
        hasher = hashlib.sha256()
        with open(dataset_path, "rb") as f:
            hasher.update(f.read(1024 * 1024))  # First 1MB
            f.seek(-1024 * 1024, 2)  # Last 1MB
            hasher.update(f.read())
            hasher.update(str(file_size).encode())
        return f"sha256:{hasher.hexdigest()[:16]}"
    except Exception:
        return None


def get_tool_version(cmd: str, args: list[str]) -> str | None:
    """Get version of a CLI tool."""
    try:
        res = subprocess.run([cmd, *args], capture_output=True, text=True, check=False)
        return (res.stdout or res.stderr).strip() or None
    except Exception:
        return None


def build_base_metadata(
    environment: str,
    model: str,
    effective_model: str,
    dataset: str,
    timestamp: str,
    num_examples: int,
    repo_root: Path | None = None,
    dataset_path: Path | None = None,
    seed: int | None = None,
    **extra_fields: Any,
) -> dict[str, Any]:
    """
    Build base metadata dict with all required fields for benchmark integrity.

    Args:
        environment: Environment name (e.g., "sv-env-network-logs")
        model: Requested model name
        effective_model: Actual model name used (may differ for OpenRouter)
        dataset: Dataset name/identifier
        timestamp: ISO timestamp
        num_examples: Number of examples in evaluation
        repo_root: Repository root for git commit lookup
        dataset_path: Path to dataset file for revision hash
        seed: Random seed for reproducibility (None if not used)
        **extra_fields: Additional metadata fields

    Returns:
        Metadata dict with all required fields
    """
    # Extract env short name for version lookup
    env_short = environment.replace("sv-env-", "")
    env_package = f"sv-env-{env_short}"

    metadata: dict[str, Any] = {
        "environment": environment,
        "env_version": get_env_version(env_package),
        "model": model,
        "effective_model": effective_model,
        "dataset": dataset,
        "dataset_revision": get_dataset_revision(dataset_path) if dataset_path else None,
        "timestamp": timestamp,
        "num_examples": num_examples,
        "git_commit": get_git_commit(repo_root),
        "python_version": get_python_version(),
        "verifiers_version": get_verifiers_version(),
    }

    if seed is not None:
        metadata["seed"] = seed

    # Add any extra fields
    metadata.update(extra_fields)

    return metadata


class EarlyStopError(Exception):
    """Raised when early stopping threshold is exceeded during evaluation."""

    pass


class ErrorTracker:
    """
    Tracks consecutive errors during evaluation and triggers early stopping.

    This prevents expensive evaluation runs from continuing when the model
    or API is misconfigured.

    Args:
        max_consecutive_errors: Maximum number of consecutive errors before stopping.
            Default is 3, which allows for transient network issues but stops
            quickly for persistent configuration problems.
        window_size: Number of recent samples to track. If this many consecutive
            samples all have errors, early stopping is triggered.

    Example:
        >>> tracker = ErrorTracker(max_consecutive_errors=3)
        >>> for i, sample in enumerate(dataset):
        ...     try:
        ...         result = model.predict(sample)
        ...         tracker.record_success()
        ...     except Exception as e:
        ...         tracker.record_error(str(e), index=i)
        ...         # EarlyStopError raised if threshold exceeded
    """

    def __init__(self, max_consecutive_errors: int = 3, window_size: int = 5):
        """Initialize error tracker with threshold."""
        if max_consecutive_errors < 1:
            raise ValueError("max_consecutive_errors must be at least 1")
        if window_size < max_consecutive_errors:
            raise ValueError("window_size must be >= max_consecutive_errors")

        self.max_consecutive_errors = max_consecutive_errors
        self.window_size = window_size
        self.consecutive_errors = 0
        self.total_errors = 0
        self.total_samples = 0
        self.recent_errors: list[bool] = []  # Track recent error status (True = error)
        self.last_error_message: str | None = None

    def record_error(self, error_message: str, index: int | None = None) -> None:
        """
        Record an error and check if early stopping should be triggered.

        Args:
            error_message: The error message to record
            index: Optional sample index for better error reporting

        Raises:
            EarlyStopError: If consecutive error threshold is exceeded
        """
        self.consecutive_errors += 1
        self.total_errors += 1
        self.total_samples += 1
        self.last_error_message = error_message
        self.recent_errors.append(True)

        # Keep only the most recent window_size samples
        if len(self.recent_errors) > self.window_size:
            self.recent_errors.pop(0)

        # Check if we've hit the consecutive error threshold
        if self.consecutive_errors >= self.max_consecutive_errors:
            prefix = f"Sample {index}: " if index is not None else ""
            raise EarlyStopError(
                f"{prefix}Stopping evaluation after {self.consecutive_errors} "
                f"consecutive errors (threshold: {self.max_consecutive_errors}).\n"
                f"Last error: {error_message}\n\n"
                f"This usually indicates a model configuration issue (invalid model ID, "
                f"missing API key, etc.). Fix the issue and try again."
            )

        # Also check if all samples in the recent window were errors
        if len(self.recent_errors) >= self.max_consecutive_errors and all(
            self.recent_errors[-self.max_consecutive_errors :]
        ):
            prefix = f"Sample {index}: " if index is not None else ""
            raise EarlyStopError(
                f"{prefix}Stopping evaluation: {self.max_consecutive_errors} "
                f"errors in the last {len(self.recent_errors)} samples.\n"
                f"Last error: {error_message}\n\n"
                f"This usually indicates a model configuration issue (invalid model ID, "
                f"missing API key, etc.). Fix the issue and try again."
            )

    def record_success(self) -> None:
        """Record a successful completion (resets consecutive error counter)."""
        self.consecutive_errors = 0
        self.total_samples += 1
        self.recent_errors.append(False)

        # Keep only the most recent window_size samples
        if len(self.recent_errors) > self.window_size:
            self.recent_errors.pop(0)

    def get_stats(self) -> dict[str, int | float]:
        """Get error statistics."""
        error_rate = self.total_errors / self.total_samples if self.total_samples > 0 else 0.0
        return {
            "total_samples": self.total_samples,
            "total_errors": self.total_errors,
            "consecutive_errors": self.consecutive_errors,
            "error_rate": error_rate,
        }

    def should_warn(self, warning_threshold: float = 0.5) -> bool:
        """
        Check if error rate is high enough to warrant a warning.

        Args:
            warning_threshold: Error rate threshold for warnings (default: 0.5)

        Returns:
            True if error rate exceeds threshold and we have enough samples
        """
        if self.total_samples < 5:  # Need at least 5 samples for meaningful stats
            return False
        stats = self.get_stats()
        return stats["error_rate"] > warning_threshold
