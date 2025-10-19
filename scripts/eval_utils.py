#!/usr/bin/env python3
"""
Shared utilities for evaluation scripts.

Provides common functionality like early failure detection to prevent
costly runs with misconfigured models or API keys.
"""

from __future__ import annotations


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
