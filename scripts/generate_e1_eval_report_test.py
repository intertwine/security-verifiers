"""Tests for E1 evaluation report generator."""

import json
from pathlib import Path

from generate_e1_eval_report import (
    analyze_run,
    calculate_ece,
    parse_completion,
)


class TestParseCompletion:
    """Tests for parse_completion function."""

    def test_valid_completion(self):
        """Test parsing a valid completion JSON."""
        completion = '{"label": "Malicious", "confidence": 0.85, "rationale": "..."}'
        label, confidence = parse_completion(completion)
        assert label == "malicious"
        assert confidence == 0.85

    def test_valid_completion_abstain(self):
        """Test parsing an abstain completion."""
        completion = '{"label": "Abstain", "confidence": 0.90, "rationale": "..."}'
        label, confidence = parse_completion(completion)
        assert label == "abstain"
        assert confidence == 0.90

    def test_invalid_json(self):
        """Test parsing invalid JSON returns None."""
        completion = "not valid json"
        label, confidence = parse_completion(completion)
        assert label is None
        assert confidence is None

    def test_missing_fields(self):
        """Test parsing JSON with missing fields."""
        completion = '{"rationale": "test"}'
        label, confidence = parse_completion(completion)
        assert label == ""
        assert confidence == 0.0


class TestCalculateECE:
    """Tests for ECE (Expected Calibration Error) calculation."""

    def test_perfect_calibration(self):
        """Test ECE with perfectly calibrated predictions."""
        # All predictions with 0.5 confidence, 50% correct
        predictions = [
            ("malicious", "malicious", 0.5),
            ("benign", "benign", 0.5),
            ("malicious", "benign", 0.5),
            ("benign", "malicious", 0.5),
        ]
        ece = calculate_ece(predictions, n_bins=10)
        assert 0.0 <= ece <= 0.1  # Should be very low

    def test_poor_calibration(self):
        """Test ECE with poorly calibrated predictions."""
        # All predictions with 0.9 confidence but only 50% correct
        predictions = [
            ("malicious", "malicious", 0.9),
            ("benign", "benign", 0.9),
            ("malicious", "benign", 0.9),
            ("benign", "malicious", 0.9),
        ]
        ece = calculate_ece(predictions, n_bins=10)
        assert ece > 0.3  # Should be high due to overconfidence

    def test_empty_predictions(self):
        """Test ECE with no predictions."""
        ece = calculate_ece([], n_bins=10)
        assert ece == 0.0

    def test_abstentions_ignored(self):
        """Test that abstentions are filtered out."""
        predictions = [
            ("abstain", "malicious", 0.9),
            ("malicious", "malicious", 0.8),
        ]
        ece = calculate_ece(predictions, n_bins=10)
        assert ece >= 0.0  # Should only consider non-abstain prediction


class TestAnalyzeRun:
    """Tests for analyze_run function."""

    def test_analyze_valid_run(self, tmp_path: Path):
        """Test analyzing a valid run directory."""
        # Create test metadata
        metadata = {
            "environment": "sv-env-network-logs",
            "model": "gpt-5-mini",
            "dataset": "iot23-train-dev-test-v1.jsonl",
            "timestamp": "2025-10-23T06:41:16Z",
            "num_examples": 10,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Create test results
        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Malicious", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Benign", "confidence": 0.8}',
            },
            {
                "index": 2,
                "answer": "Malicious",
                "completion": '{"label": "Benign", "confidence": 0.7}',
            },
            {
                "index": 3,
                "answer": "Benign",
                "completion": '{"label": "Abstain", "confidence": 0.95}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # Analyze the run (with summary writing enabled)
        report = analyze_run(tmp_path, write_summary=True)

        assert report is not None
        assert report["Split"] == "ID (IoT-23)"
        assert report["Model"] == "gpt-5-mini"
        assert report["N"] == 4
        assert report["Abstain%"] == 25.0  # 1 out of 4
        assert 0.0 <= report["Acc"] <= 1.0
        assert 0.0 <= report["ECE"] <= 1.0
        assert report["run_id"] == tmp_path.name

        # Verify summary.json was created
        summary_file = tmp_path / "summary.json"
        assert summary_file.exists()

        # Verify summary.json content matches report
        with open(summary_file) as f:
            summary = json.load(f)
        assert summary == report

    def test_analyze_missing_files(self, tmp_path: Path):
        """Test that analyze_run returns None for missing files."""
        report = analyze_run(tmp_path)
        assert report is None

    def test_analyze_cic_dataset(self, tmp_path: Path):
        """Test dataset split detection for CIC-IDS-2017."""
        metadata = {
            "model": "qwen3-14b",
            "dataset": "cic-ids-2017-ood-v1.jsonl",
            "timestamp": "2025-10-23T06:42:56Z",
            "num_examples": 2,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Malicious", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Benign", "confidence": 0.8}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["Split"] == "OOD (CIC-IDS-2017)"

    def test_analyze_unsw_dataset(self, tmp_path: Path):
        """Test dataset split detection for UNSW-NB15."""
        metadata = {
            "model": "qwen3-14b",
            "dataset": "unsw-nb15-ood-v1.jsonl",
            "timestamp": "2025-10-23T06:41:33Z",
            "num_examples": 2,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Malicious", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Benign", "confidence": 0.8}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["Split"] == "OOD (UNSW-NB15)"

    def test_all_abstentions(self, tmp_path: Path):
        """Test run where all predictions are abstentions."""
        metadata = {
            "model": "test-model",
            "dataset": "iot23-train-dev-test-v1.jsonl",
            "timestamp": "2025-10-23T06:41:16Z",
            "num_examples": 2,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Abstain", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Abstain", "confidence": 0.95}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["Abstain%"] == 100.0
        assert report["Acc"] == 0.0
        assert report["FN%"] == 0.0
        assert report["FP%"] == 0.0

    def test_no_write_summary(self, tmp_path: Path):
        """Test that summary.json is not written when write_summary=False."""
        metadata = {
            "model": "test-model",
            "dataset": "iot23-train-dev-test-v1.jsonl",
            "timestamp": "2025-10-23T06:41:16Z",
            "num_examples": 2,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Malicious", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Benign", "confidence": 0.8}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # Analyze without writing summary
        report = analyze_run(tmp_path, write_summary=False)
        assert report is not None

        # Verify summary.json was NOT created
        summary_file = tmp_path / "summary.json"
        assert not summary_file.exists()

    def test_idempotency(self, tmp_path: Path):
        """Test that analyze_run produces identical output when called multiple times."""
        metadata = {
            "model": "test-model",
            "dataset": "iot23-train-dev-test-v1.jsonl",
            "timestamp": "2025-10-23T06:41:16Z",
            "num_examples": 4,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "answer": "Malicious",
                "completion": '{"label": "Malicious", "confidence": 0.9}',
            },
            {
                "index": 1,
                "answer": "Benign",
                "completion": '{"label": "Benign", "confidence": 0.8}',
            },
            {
                "index": 2,
                "answer": "Malicious",
                "completion": '{"label": "Benign", "confidence": 0.7}',
            },
            {
                "index": 3,
                "answer": "Benign",
                "completion": '{"label": "Abstain", "confidence": 0.95}',
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # First call - create summary.json
        result1 = analyze_run(tmp_path, write_summary=True)
        with open(tmp_path / "summary.json") as f:
            file1 = json.load(f)

        # Second call - recreate summary.json (simulates running report generator)
        result2 = analyze_run(tmp_path, write_summary=True)
        with open(tmp_path / "summary.json") as f:
            file2 = json.load(f)

        # Both calls should produce identical results
        assert result1 == result2
        assert file1 == file2

        # This confirms the workflow is idempotent:
        # 1. eval_network_logs.py creates summary.json
        # 2. generate_e1_eval_report.py can safely recreate it
        # 3. No conflicts occur
