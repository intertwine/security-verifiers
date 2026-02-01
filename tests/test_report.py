"""Tests for bench/report.py - SV-Bench Report Generator."""

import json
import tempfile
from pathlib import Path

import pytest

# Import from bench module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bench.report import (
    compute_e1_metrics,
    compute_e2_metrics,
    generate_summary,
    generate_report_md,
    load_results,
    _compute_ece,
    _compute_brier,
    _compute_aurc,
)
import numpy as np


# ============================================================================
# E1 Tests: Network Logs Metrics
# ============================================================================


class TestE1Metrics:
    """Tests for E1 network logs metrics."""

    def test_perfect_predictions(self):
        """Test metrics with perfect predictions."""
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 1.0},
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.95},
            {"predicted_label": "Benign", "answer": "Benign", "confidence": 0.9},
            {"predicted_label": "Benign", "answer": "Benign", "confidence": 0.85},
        ]
        metrics = compute_e1_metrics(results)
        
        assert metrics["detection"]["accuracy"] == 1.0
        assert metrics["detection"]["tpr"] == 1.0
        assert metrics["detection"]["fpr"] == 0.0
        assert metrics["detection"]["f1"] == 1.0
        assert metrics["confusion_matrix"]["tp"] == 2
        assert metrics["confusion_matrix"]["tn"] == 2
        assert metrics["confusion_matrix"]["fp"] == 0
        assert metrics["confusion_matrix"]["fn"] == 0

    def test_all_wrong_predictions(self):
        """Test metrics with all wrong predictions."""
        results = [
            {"predicted_label": "Malicious", "answer": "Benign", "confidence": 0.9},
            {"predicted_label": "Benign", "answer": "Malicious", "confidence": 0.9},
        ]
        metrics = compute_e1_metrics(results)
        
        assert metrics["detection"]["accuracy"] == 0.0
        assert metrics["detection"]["tpr"] == 0.0
        assert metrics["confusion_matrix"]["fp"] == 1
        assert metrics["confusion_matrix"]["fn"] == 1

    def test_abstention_handling(self):
        """Test that abstain predictions are handled correctly."""
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9},
            {"predicted_label": "Benign", "answer": "Benign", "confidence": 0.8},
            {"predicted_label": "Abstain", "answer": "Malicious", "confidence": 0.5},
            {"predicted_label": "Abstain", "answer": "Benign", "confidence": 0.4},
        ]
        metrics = compute_e1_metrics(results)
        
        assert metrics["abstention"]["abstain_rate"] == 0.5
        assert metrics["detection"]["accuracy"] == 1.0  # Among non-abstained
        assert metrics["confusion_matrix"]["abstain"] == 2

    def test_asymmetric_cost(self):
        """Test asymmetric cost calculation."""
        # One FN (malicious predicted as benign) - high cost
        results = [
            {"predicted_label": "Benign", "answer": "Malicious", "confidence": 0.9},
        ]
        metrics = compute_e1_metrics(results)
        
        assert metrics["cost"]["total_cost"] == 10.0  # FN cost weight
        
        # One FP (benign predicted as malicious) - low cost
        results = [
            {"predicted_label": "Malicious", "answer": "Benign", "confidence": 0.9},
        ]
        metrics = compute_e1_metrics(results)
        
        assert metrics["cost"]["total_cost"] == 1.0  # FP cost weight

    def test_empty_results(self):
        """Test handling of empty results."""
        metrics = compute_e1_metrics([])
        
        assert metrics["detection"]["accuracy"] == 0.0
        assert metrics["abstention"]["abstain_rate"] == 0.0


class TestCalibrationMetrics:
    """Tests for calibration metric functions."""

    def test_ece_perfect_calibration(self):
        """Test ECE with perfectly calibrated predictions."""
        correct = np.array([1, 1, 0, 0], dtype=bool)
        confidences = np.array([0.9, 0.8, 0.2, 0.1])
        
        ece = _compute_ece(correct, confidences, num_bins=10)
        # Not exactly 0 due to binning, but should be low
        assert ece < 0.2

    def test_ece_poor_calibration(self):
        """Test ECE with poorly calibrated predictions."""
        correct = np.array([0, 0, 0, 0], dtype=bool)  # All wrong
        confidences = np.array([0.9, 0.9, 0.9, 0.9])  # But very confident
        
        ece = _compute_ece(correct, confidences, num_bins=10)
        assert ece > 0.8

    def test_brier_perfect(self):
        """Test Brier score with perfect predictions."""
        correct = np.array([1, 1, 0, 0], dtype=bool)
        confidences = np.array([1.0, 1.0, 0.0, 0.0])
        
        brier = _compute_brier(correct, confidences)
        assert brier == 0.0

    def test_brier_worst(self):
        """Test Brier score with worst predictions."""
        correct = np.array([0, 0, 1, 1], dtype=bool)
        confidences = np.array([1.0, 1.0, 0.0, 0.0])
        
        brier = _compute_brier(correct, confidences)
        assert brier == 1.0


# ============================================================================
# E2 Tests: Config Verification Metrics
# ============================================================================


class TestE2Metrics:
    """Tests for E2 config verification metrics."""

    def test_perfect_detection(self):
        """Test metrics with perfect violation detection."""
        results = [
            {
                "predicted_violations": [
                    {"id": "v1", "severity": "high"},
                    {"id": "v2", "severity": "med"},
                ],
                "oracle_violations": [
                    {"id": "v1", "severity": "high"},
                    {"id": "v2", "severity": "med"},
                ],
                "valid_json": True,
            }
        ]
        metrics = compute_e2_metrics(results)
        
        assert metrics["finding_quality"]["precision_weighted"] == 1.0
        assert metrics["finding_quality"]["recall_weighted"] == 1.0
        assert metrics["finding_quality"]["f1_weighted"] == 1.0

    def test_partial_detection(self):
        """Test metrics with partial detection."""
        results = [
            {
                "predicted_violations": [
                    {"id": "v1", "severity": "high"},
                ],
                "oracle_violations": [
                    {"id": "v1", "severity": "high"},
                    {"id": "v2", "severity": "low"},
                ],
                "valid_json": True,
            }
        ]
        metrics = compute_e2_metrics(results)
        
        assert metrics["finding_quality"]["precision_weighted"] == 1.0  # No false positives
        assert metrics["finding_quality"]["recall_weighted"] < 1.0  # Missed v2

    def test_false_positives(self):
        """Test metrics with false positives."""
        results = [
            {
                "predicted_violations": [
                    {"id": "v1", "severity": "high"},
                    {"id": "v3", "severity": "low"},  # False positive
                ],
                "oracle_violations": [
                    {"id": "v1", "severity": "high"},
                ],
                "valid_json": True,
            }
        ]
        metrics = compute_e2_metrics(results)
        
        assert metrics["finding_quality"]["precision_weighted"] < 1.0
        assert metrics["finding_quality"]["recall_weighted"] == 1.0

    def test_patch_metrics(self):
        """Test patch-related metrics."""
        results = [
            {
                "predicted_violations": [{"id": "v1", "severity": "high"}],
                "oracle_violations": [{"id": "v1", "severity": "high"}],
                "patch": "diff content",
                "patch_applied": True,
                "post_patch_violations": [],  # Patch fixed the issue
                "valid_json": True,
            }
        ]
        metrics = compute_e2_metrics(results)
        
        assert metrics["patch"]["patch_provided_rate"] == 1.0
        assert metrics["patch"]["patch_success_rate"] == 1.0
        assert metrics["patch"]["mean_violations_fixed"] == 1.0

    def test_tool_economy(self):
        """Test tool economy metrics."""
        results = [
            {
                "predicted_violations": [{"id": "v1", "severity": "high"}],
                "oracle_violations": [{"id": "v1", "severity": "high"}],
                "tool_calls": 5,
                "tool_time_ms": 250,
                "opa_calls": 2,
                "opa_time_ms": 100,
                "kube-linter_calls": 2,
                "kube-linter_time_ms": 80,
                "semgrep_calls": 1,
                "semgrep_time_ms": 70,
                "valid_json": True,
            }
        ]
        metrics = compute_e2_metrics(results)
        
        assert metrics["tool_economy"]["mean_tool_calls"] == 5.0
        assert metrics["tool_economy"]["mean_tool_time_ms"] == 250.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestReportGeneration:
    """Tests for report generation functions."""

    def test_generate_e1_summary(self):
        """Test generating E1 summary JSON."""
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9},
            {"predicted_label": "Benign", "answer": "Benign", "confidence": 0.8},
        ]
        metadata = {"model": "test-model", "dataset": "test-dataset"}
        
        summary = generate_summary("e1", results, metadata, run_id="test-run")
        
        assert summary["environment"] == "sv-env-network-logs"
        assert summary["model"] == "test-model"
        assert summary["n_examples"] == 2
        assert "detection" in summary["metrics"]
        assert "calibration" in summary["metrics"]

    def test_generate_e2_summary(self):
        """Test generating E2 summary JSON."""
        results = [
            {
                "predicted_violations": [{"id": "v1", "severity": "high"}],
                "oracle_violations": [{"id": "v1", "severity": "high"}],
                "valid_json": True,
            }
        ]
        metadata = {"model": "test-model", "dataset": "test-dataset"}
        
        summary = generate_summary("e2", results, metadata, run_id="test-run")
        
        assert summary["environment"] == "sv-env-config-verification"
        assert "finding_quality" in summary["metrics"]
        assert "patch" in summary["metrics"]

    def test_generate_report_md(self):
        """Test generating markdown report."""
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9},
        ]
        summary = generate_summary("e1", results, {}, run_id="test")
        
        report_md = generate_report_md(summary)
        
        assert "# SV-Bench Report" in report_md
        assert "Detection Performance" in report_md
        assert "Calibration" in report_md

    def test_load_results_from_files(self):
        """Test loading results from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write test results
            results_data = [
                {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9}
            ]
            with open(tmppath / "results.jsonl", "w") as f:
                for r in results_data:
                    f.write(json.dumps(r) + "\n")
            
            # Write test metadata
            metadata_data = {"model": "test-model", "run_id": "test-123"}
            with open(tmppath / "metadata.json", "w") as f:
                json.dump(metadata_data, f)
            
            results, metadata = load_results(tmppath)
            
            assert len(results) == 1
            assert metadata["model"] == "test-model"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
