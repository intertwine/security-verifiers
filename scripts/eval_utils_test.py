#!/usr/bin/env python3
"""Tests for eval_utils.py shared evaluation utilities."""

import pytest
from eval_utils import EarlyStopError, ErrorTracker


class TestErrorTracker:
    """Test suite for ErrorTracker class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        tracker = ErrorTracker()
        assert tracker.max_consecutive_errors == 3
        assert tracker.window_size == 5
        assert tracker.consecutive_errors == 0
        assert tracker.total_errors == 0
        assert tracker.total_samples == 0

    def test_initialization_custom(self):
        """Test custom initialization."""
        tracker = ErrorTracker(max_consecutive_errors=5, window_size=10)
        assert tracker.max_consecutive_errors == 5
        assert tracker.window_size == 10

    def test_initialization_validation(self):
        """Test parameter validation."""
        with pytest.raises(ValueError, match="max_consecutive_errors must be at least 1"):
            ErrorTracker(max_consecutive_errors=0)

        with pytest.raises(ValueError, match="window_size must be >= max_consecutive_errors"):
            ErrorTracker(max_consecutive_errors=5, window_size=3)

    def test_record_success(self):
        """Test recording successful completions."""
        tracker = ErrorTracker()
        tracker.record_success()
        assert tracker.consecutive_errors == 0
        assert tracker.total_errors == 0
        assert tracker.total_samples == 1

    def test_record_error_basic(self):
        """Test recording errors without triggering early stop."""
        tracker = ErrorTracker(max_consecutive_errors=3)

        # Record 2 errors - should not raise
        tracker.record_error("Error 1", index=0)
        assert tracker.consecutive_errors == 1
        assert tracker.total_errors == 1
        assert tracker.total_samples == 1

        tracker.record_error("Error 2", index=1)
        assert tracker.consecutive_errors == 2
        assert tracker.total_errors == 2
        assert tracker.total_samples == 2

    def test_early_stop_on_consecutive_errors(self):
        """Test early stopping when consecutive error threshold is hit."""
        tracker = ErrorTracker(max_consecutive_errors=3)

        # Record 2 errors - should not raise
        tracker.record_error("Error 1", index=0)
        tracker.record_error("Error 2", index=1)

        # 3rd consecutive error should raise
        with pytest.raises(EarlyStopError, match="3 consecutive errors"):
            tracker.record_error("Error 3", index=2)

    def test_reset_consecutive_on_success(self):
        """Test that consecutive counter resets on success."""
        tracker = ErrorTracker(max_consecutive_errors=3)

        # Record 2 errors
        tracker.record_error("Error 1", index=0)
        tracker.record_error("Error 2", index=1)
        assert tracker.consecutive_errors == 2

        # Success resets consecutive counter
        tracker.record_success()
        assert tracker.consecutive_errors == 0
        assert tracker.total_errors == 2  # Total errors unchanged
        assert tracker.total_samples == 3

        # Can now have 2 more errors without hitting threshold
        tracker.record_error("Error 3", index=3)
        tracker.record_error("Error 4", index=4)
        assert tracker.consecutive_errors == 2

    def test_error_message_in_exception(self):
        """Test that error message is included in exception."""
        tracker = ErrorTracker(max_consecutive_errors=2)
        tracker.record_error("First error", index=0)

        with pytest.raises(EarlyStopError, match="Test error message"):
            tracker.record_error("Test error message", index=1)

    def test_get_stats(self):
        """Test statistics retrieval."""
        tracker = ErrorTracker()

        # Initial stats
        stats = tracker.get_stats()
        assert stats["total_samples"] == 0
        assert stats["total_errors"] == 0
        assert stats["error_rate"] == 0.0

        # After some successes and errors
        tracker.record_success()
        tracker.record_success()
        tracker.record_error("Error 1", index=2)
        tracker.record_success()

        stats = tracker.get_stats()
        assert stats["total_samples"] == 4
        assert stats["total_errors"] == 1
        assert stats["error_rate"] == 0.25
        assert stats["consecutive_errors"] == 0  # Reset by last success

    def test_should_warn(self):
        """Test warning threshold detection."""
        tracker = ErrorTracker()

        # Not enough samples yet
        tracker.record_error("Error 1", index=0)
        assert not tracker.should_warn()

        # Add more samples with high error rate
        tracker.record_error("Error 2", index=1)
        tracker.record_success()
        tracker.record_error("Error 3", index=3)
        tracker.record_error("Error 4", index=4)

        # Now we have 5 samples with 4 errors (80% error rate)
        assert tracker.should_warn(warning_threshold=0.5)
        assert not tracker.should_warn(warning_threshold=0.9)

    def test_window_tracking(self):
        """Test that error window is properly maintained."""
        tracker = ErrorTracker(max_consecutive_errors=3, window_size=5)

        # Fill the window with successes
        for i in range(5):
            tracker.record_success()

        assert len(tracker.recent_errors) == 5
        assert all(not err for err in tracker.recent_errors)

        # Add one more - should drop the oldest
        tracker.record_error("Error", index=5)
        assert len(tracker.recent_errors) == 5
        assert tracker.recent_errors[-1] is True

    def test_last_error_message_tracking(self):
        """Test that last error message is tracked."""
        tracker = ErrorTracker()

        assert tracker.last_error_message is None

        tracker.record_error("First error", index=0)
        assert tracker.last_error_message == "First error"

        tracker.record_error("Second error", index=1)
        assert tracker.last_error_message == "Second error"

        tracker.record_success()
        assert tracker.last_error_message == "Second error"  # Unchanged by success

    def test_high_threshold_no_early_stop(self):
        """Test that high threshold allows many consecutive errors."""
        tracker = ErrorTracker(max_consecutive_errors=10, window_size=10)

        # Can record 9 errors without raising
        for i in range(9):
            tracker.record_error(f"Error {i}", index=i)

        assert tracker.consecutive_errors == 9

        # 10th error triggers stop
        with pytest.raises(EarlyStopError):
            tracker.record_error("Error 10", index=10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
