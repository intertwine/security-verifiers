#!/usr/bin/env python3
"""
Tests for E1 flat metadata schema export.

Validates that:
1. All metadata rows have exactly 6 required keys
2. payload_json contains valid JSON
3. Schema is consistent across all rows
4. Generated JSONL can be loaded by HuggingFace datasets
"""

import json

# Import the export function
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "hf"))
from export_metadata_flat import HF_FLAT_FEATURES, export_metadata_flat


def test_e1_metadata_export_basic():
    """Test that E1 metadata export produces valid output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        rows = export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        # Check we got rows
        assert len(rows) > 0, "Should generate at least one metadata row"

        # Check file was created
        assert out_path.exists(), "Output JSONL file should exist"


def test_e1_metadata_schema_consistency():
    """Test that all E1 metadata rows have consistent schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        rows = export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        required_keys = {"section", "name", "description", "payload_json", "version", "created_at"}

        for i, row in enumerate(rows):
            # Check all required keys present
            assert set(row.keys()) == required_keys, (
                f"Row {i} has incorrect keys: expected {required_keys}, got {set(row.keys())}"
            )

            # Check all values are strings
            for key, value in row.items():
                assert isinstance(value, str), f"Row {i} key '{key}' is not a string: {type(value)}"

            # Check payload_json is valid JSON
            try:
                payload = json.loads(row["payload_json"])
                assert isinstance(payload, (dict, list)), (
                    f"Row {i} payload_json should be dict or list, got {type(payload)}"
                )
            except json.JSONDecodeError as e:
                pytest.fail(f"Row {i} has invalid JSON in payload_json: {e}")


def test_e1_metadata_jsonl_format():
    """Test that E1 metadata JSONL file is valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        # Read JSONL and validate each line
        lines = out_path.read_text().strip().split("\n")
        assert len(lines) > 0, "JSONL file should have at least one line"

        required_keys = {"section", "name", "description", "payload_json", "version", "created_at"}

        for i, line in enumerate(lines):
            # Parse JSON
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i + 1} is not valid JSON: {e}")

            # Validate schema
            assert set(row.keys()) == required_keys, (
                f"Line {i + 1} has incorrect keys: expected {required_keys}, got {set(row.keys())}"
            )

            # Validate payload_json
            try:
                json.loads(row["payload_json"])
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i + 1} has invalid payload_json: {e}")


def test_e1_metadata_hf_dataset_compatible():
    """Test that E1 metadata can be loaded by HuggingFace datasets."""
    from datasets import Dataset

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        # Load with explicit schema
        dataset = Dataset.from_json(str(out_path), features=HF_FLAT_FEATURES)

        # Validate
        assert len(dataset) > 0, "Dataset should have at least one row"
        assert set(dataset.features.keys()) == set(HF_FLAT_FEATURES.keys()), (
            "Dataset features should match schema"
        )

        # Check a few rows
        for i, row in enumerate(dataset):
            assert set(row.keys()) == set(HF_FLAT_FEATURES.keys()), (
                f"Row {i} missing keys: {set(HF_FLAT_FEATURES.keys()) - set(row.keys())}"
            )

            # Validate payload_json
            try:
                json.loads(row["payload_json"])
            except json.JSONDecodeError as e:
                pytest.fail(f"Row {i} has invalid payload_json: {e}")


def test_e1_metadata_sections():
    """Test that E1 metadata includes expected sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        rows = export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        sections = {row["section"] for row in rows}

        # Expected sections for E1
        expected_sections = {"sampling", "ood", "provenance", "notes"}
        assert expected_sections.issubset(sections), (
            f"Missing expected sections: {expected_sections - sections}"
        )


def test_e1_metadata_created_at_override():
    """Test that created_at can be overridden."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        custom_timestamp = "2024-01-01T12:00:00Z"

        rows = export_metadata_flat(env="e1", out_path=out_path, created_at=custom_timestamp)

        for row in rows:
            assert row["created_at"] == custom_timestamp, (
                f"created_at should be '{custom_timestamp}', got '{row['created_at']}'"
            )


def test_e1_metadata_payload_json_minified():
    """Test that payload_json is minified (no extra whitespace)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "e1_meta.jsonl"
        created_at = "2025-10-13T00:00:00Z"

        rows = export_metadata_flat(env="e1", out_path=out_path, created_at=created_at)

        for i, row in enumerate(rows):
            payload_json = row["payload_json"]

            # Check no newlines or extra spaces
            assert "\n" not in payload_json, f"Row {i} payload_json contains newlines"
            assert "  " not in payload_json, f"Row {i} payload_json contains double spaces"

            # Verify it's valid JSON
            payload = json.loads(payload_json)

            # Re-serialize with same settings and compare
            expected = json.dumps(payload, separators=(",", ":"))
            assert payload_json == expected, f"Row {i} payload_json not properly minified"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
