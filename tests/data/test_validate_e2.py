#!/usr/bin/env python3
"""Tests for E2 Pydantic validator."""

import subprocess

import pytest


def test_e2_validator_runs():
    """Test that E2 validator runs successfully on canonical data."""
    p = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/data/validate_splits_e2.py",
            "--dir",
            "environments/sv-env-config-verification/data",
        ],
        capture_output=True,
        text=True,
    )

    # Should succeed (exit code 0)
    assert p.returncode == 0, f"Validator failed:\nstdout: {p.stdout}\nstderr: {p.stderr}"

    # Check output contains expected files
    assert "k8s-labeled-v1.jsonl" in p.stdout
    assert "terraform-labeled-v1.jsonl" in p.stdout
    assert "BAD=0" in p.stdout, "Should have no validation errors"


def test_e2_validator_reports_bad_data(tmp_path):
    """Test that E2 validator detects invalid data."""
    # Create a bad JSONL file (missing required fields)
    bad_file = tmp_path / "bad.jsonl"
    bad_file.write_text('{"prompt":"test","info":{"violations":[],"patch":null},"meta":{"lang":"invalid"}}\n')

    p = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/data/validate_splits_e2.py",
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    # Should fail (exit code 1)
    assert p.returncode == 1, "Validator should fail on bad data"
    assert "BAD=1" in p.stdout, "Should report bad rows"


def test_e2_validator_handles_missing_dir():
    """Test that E2 validator handles missing directory gracefully."""
    p = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/data/validate_splits_e2.py",
            "--dir",
            "/nonexistent/path",
        ],
        capture_output=True,
        text=True,
    )

    # Should fail with clear error
    assert p.returncode == 1
    assert "Directory not found" in p.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
