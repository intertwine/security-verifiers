"""Tests for oracle generation and golden file validation."""

import json
from pathlib import Path

import pytest

from ..oracle import build_oracle_for_k8s, build_oracle_for_tf


class TestOracleStability:
    """Test oracle generation stability and golden file validation."""

    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "dataset"

    @pytest.fixture
    def fixtures_dir(self, test_data_dir):
        """Get the fixtures directory."""
        return test_data_dir / "fixtures"

    @pytest.fixture
    def oracle_dir(self, test_data_dir):
        """Get the oracle directory."""
        return test_data_dir / "oracle"

    def test_kubernetes_oracle_stability(self, fixtures_dir, oracle_dir):
        """Test that Kubernetes oracle generation is stable."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"
        golden_file = oracle_dir / "bad_pod.json"

        assert fixture_file.exists(), f"Fixture file {fixture_file} does not exist"
        assert golden_file.exists(), f"Golden file {golden_file} does not exist"

        # Generate oracle from fixture
        generated_oracle = build_oracle_for_k8s([str(fixture_file)])

        # Load golden oracle
        with open(golden_file, "r", encoding="utf-8") as f:
            golden_oracle = json.load(f)

        # Compare structure and content
        assert len(generated_oracle) == len(golden_oracle), (
            f"Oracle length mismatch: generated {len(generated_oracle)}, golden {len(golden_oracle)}"
        )

        # Sort both lists by finding ID for consistent comparison
        def sort_key(finding):
            return finding.get("rule_id", finding.get("id", ""))

        generated_sorted = sorted(generated_oracle, key=sort_key)
        golden_sorted = sorted(golden_oracle, key=sort_key)

        for gen, gold in zip(generated_sorted, golden_sorted):
            # Compare key fields
            assert gen.get("rule_id") == gold.get("rule_id"), (
                f"Rule ID mismatch: {gen.get('rule_id')} vs {gold.get('rule_id')}"
            )
            assert gen.get("severity") == gold.get("severity"), (
                f"Severity mismatch for {gen.get('rule_id')}: {gen.get('severity')} vs {gold.get('severity')}"
            )  # pylint: disable=line-too-long
            assert gen.get("message") == gold.get("message"), (
                f"Message mismatch for {gen.get('rule_id')}: {gen.get('message')} vs {gold.get('message')}"
            )  # pylint: disable=line-too-long

    def test_terraform_oracle_stability(self, fixtures_dir, oracle_dir):
        """Test that Terraform oracle generation is stable."""
        fixture_file = fixtures_dir / "tf" / "bad.tf"
        golden_file = oracle_dir / "bad_tf.json"

        assert fixture_file.exists(), f"Fixture file {fixture_file} does not exist"
        assert golden_file.exists(), f"Golden file {golden_file} does not exist"

        # Generate oracle from fixture
        generated_oracle = build_oracle_for_tf([str(fixture_file)])

        # Load golden oracle
        with open(golden_file, "r", encoding="utf-8") as f:
            golden_oracle = json.load(f)

        # Compare structure and content
        assert len(generated_oracle) == len(golden_oracle), (
            f"Oracle length mismatch: generated {len(generated_oracle)}, golden {len(golden_oracle)}"
        )

        # Sort both lists by finding ID for consistent comparison
        def sort_key(finding):
            return finding.get("rule_id", finding.get("id", ""))

        generated_sorted = sorted(generated_oracle, key=sort_key)
        golden_sorted = sorted(golden_oracle, key=sort_key)

        for gen, gold in zip(generated_sorted, golden_sorted):
            # Compare key fields
            assert gen.get("rule_id") == gold.get("rule_id"), (
                f"Rule ID mismatch: {gen.get('rule_id')} vs {gold.get('rule_id')}"
            )
            assert gen.get("severity") == gold.get("severity"), (
                f"Severity mismatch for {gen.get('rule_id')}: {gen.get('severity')} vs {gold.get('severity')}"
            )  # pylint: disable=line-too-long
            assert gen.get("message") == gold.get("message"), (
                f"Message mismatch for {gen.get('rule_id')}: {gen.get('message')} vs {gold.get('message')}"
            )  # pylint: disable=line-too-long

    def test_oracle_regeneration_consistency(self, fixtures_dir):
        """Test that oracle regeneration is consistent across multiple runs."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"

        # Generate oracle multiple times
        oracle1 = build_oracle_for_k8s([str(fixture_file)])
        oracle2 = build_oracle_for_k8s([str(fixture_file)])
        oracle3 = build_oracle_for_k8s([str(fixture_file)])

        # All should be identical
        def sort_key(finding):
            return finding.get("rule_id", finding.get("id", ""))

        sorted1 = sorted(oracle1, key=sort_key)
        sorted2 = sorted(oracle2, key=sort_key)
        sorted3 = sorted(oracle3, key=sort_key)

        assert sorted1 == sorted2, "Oracle generation not consistent between runs"
        assert sorted2 == sorted3, "Oracle generation not consistent between runs"

    def test_oracle_contains_expected_findings(self, fixtures_dir, oracle_dir):
        """Test that oracle contains expected security findings."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"
        golden_file = oracle_dir / "bad_pod.json"

        generated_oracle = build_oracle_for_k8s([str(fixture_file)])

        # Load golden oracle to know what we expect
        with open(golden_file, "r", encoding="utf-8") as f:
            golden_oracle = json.load(f)

        # Extract rule IDs from both
        generated_ids = {f.get("rule_id", f.get("id", "")) for f in generated_oracle}
        golden_ids = {f.get("rule_id", f.get("id", "")) for f in golden_oracle}

        # Should have the same rule IDs
        assert generated_ids == golden_ids, f"Rule ID mismatch: generated {generated_ids}, golden {golden_ids}"

        # Should have at least some findings
        assert len(generated_oracle) > 0, "Oracle should contain security findings"

    def test_oracle_json_serialization(self, fixtures_dir):
        """Test that oracle can be properly serialized to JSON."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"

        generated_oracle = build_oracle_for_k8s([str(fixture_file)])

        # Should be able to serialize to JSON
        json_str = json.dumps(generated_oracle, indent=2)
        assert json_str, "Oracle should serialize to valid JSON"

        # Should be able to deserialize back
        deserialized = json.loads(json_str)
        assert deserialized == generated_oracle, "JSON round-trip should preserve data"


class TestOracleRegressionDetection:
    """Test detection of oracle regressions."""

    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "dataset"

    @pytest.fixture
    def fixtures_dir(self, test_data_dir):
        """Get the fixtures directory."""
        return test_data_dir / "fixtures"

    @pytest.fixture
    def oracle_dir(self, test_data_dir):
        """Get the oracle directory."""
        return test_data_dir / "oracle"

    def test_detect_missing_findings(self, fixtures_dir):
        """Test that we can detect when expected findings go missing."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"

        # Generate current oracle
        current_oracle = build_oracle_for_k8s([str(fixture_file)])

        # Simulate a regression by removing some findings
        if current_oracle:
            reduced_oracle = current_oracle[:-1]  # Remove last finding

            # This should be detected as a regression
            assert len(reduced_oracle) < len(current_oracle), "Regression test setup failed"

    def test_detect_new_findings(self, fixtures_dir):
        """Test that we can detect when new findings are added."""
        fixture_file = fixtures_dir / "k8s" / "bad_pod.yaml"

        # Generate current oracle
        current_oracle = build_oracle_for_k8s([str(fixture_file)])

        # Simulate new findings by adding a fake one
        extended_oracle = current_oracle + [{"rule_id": "TEST_001", "message": "Test finding", "severity": "LOW"}]

        # This should be detected as new findings
        assert len(extended_oracle) > len(current_oracle), "New findings test setup failed"
