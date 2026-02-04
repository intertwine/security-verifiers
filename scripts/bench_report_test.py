"""Tests for bench/report.py - SV-Bench Report Generator."""

import json
from pathlib import Path

import pytest
from bench.report import (
    TOOL_NAME_MAP,
    TOOL_NAMES,
    _compute_aurc,
    _compute_brier,
    _compute_ece,
    compute_e1_metrics,
    compute_e2_metrics,
    generate_report_md,
    generate_summary,
    load_results,
)


class TestE1Metrics:
    """Tests for E1 network logs metrics."""

    def test_perfect_predictions(self) -> None:
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

    def test_abstention_handling(self) -> None:
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9},
            {"predicted_label": "Benign", "answer": "Benign", "confidence": 0.8},
            {"predicted_label": "Abstain", "answer": "Malicious", "confidence": 0.5},
            {"predicted_label": "Abstain", "answer": "Benign", "confidence": 0.4},
        ]
        metrics = compute_e1_metrics(results)

        assert metrics["abstention"]["abstain_rate"] == 0.5
        assert metrics["detection"]["accuracy"] == 1.0
        assert metrics["confusion_matrix"]["abstain"] == 2

    def test_empty_results(self) -> None:
        metrics = compute_e1_metrics([])

        assert metrics["detection"]["accuracy"] == 0.0
        assert metrics["abstention"]["abstain_rate"] == 0.0


class TestCalibrationMetrics:
    """Tests for calibration metric functions."""

    def test_ece_poor_calibration(self) -> None:
        correct = [False, False, False, False]
        confidences = [0.9, 0.9, 0.9, 0.9]

        ece = _compute_ece(correct, confidences, num_bins=10)
        assert ece > 0.8

    def test_ece_includes_confidence_one(self) -> None:
        correct = [False]
        confidences = [1.0]

        ece = _compute_ece(correct, confidences, num_bins=10)
        assert ece >= 0.99

    def test_brier_perfect(self) -> None:
        correct = [True, True, False, False]
        confidences = [1.0, 1.0, 0.0, 0.0]

        brier = _compute_brier(correct, confidences)
        assert brier == 0.0

    def test_aurc_non_negative(self) -> None:
        # Coverage decreases as threshold increases; AURC should still be non-negative.
        predictions = ["malicious", "benign", "malicious", "benign"]
        actuals = ["malicious", "benign", "benign", "benign"]
        confidences = [0.9, 0.8, 0.2, 0.1]

        aurc = _compute_aurc(predictions, actuals, confidences)
        assert aurc >= 0.0


class TestE2Metrics:
    """Tests for E2 config verification metrics."""

    def test_perfect_detection(self) -> None:
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

    def test_tool_economy(self) -> None:
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

    def test_patch_fix_rate_global(self) -> None:
        results = [
            {
                "predicted_violations": [],
                "oracle_violations": [
                    {"id": "v1", "severity": "high"},
                    {"id": "v2", "severity": "high"},
                ],
                "patch": "diff",
                "patch_applied": True,
                "post_patch_violations": [{"id": "v2", "severity": "high"}],
                "valid_json": True,
            },
            {
                "predicted_violations": [],
                "oracle_violations": [{"id": "v3", "severity": "low"}],
                "patch": "diff",
                "patch_applied": True,
                "post_patch_violations": [],
                "valid_json": True,
            },
        ]
        metrics = compute_e2_metrics(results)

        assert metrics["patch"]["patch_fix_rate"] == pytest.approx(1.3 / 2.3, rel=1e-3)


class TestReportGeneration:
    """Tests for report generation functions."""

    def test_generate_e1_summary_from_completion(self) -> None:
        results = [
            {"completion": '{"label": "Malicious", "confidence": 0.9}', "answer": "Malicious"},
            {"completion": '{"label": "Benign", "confidence": 0.8}', "answer": "Benign"},
        ]
        metadata = {"model": "test-model", "dataset": "test-dataset"}

        summary = generate_summary("e1", results, metadata, run_id="test-run")

        assert summary["environment"] == "sv-env-network-logs"
        assert summary["model"] == "test-model"
        assert summary["n_examples"] == 2
        assert "detection" in summary["metrics"]

    def test_generate_e1_strict_recovers_from_malformed_json(self) -> None:
        # Malformed JSON (broken string) but with recoverable label/confidence.
        completion = '{"label":"Malicious","confidence":0.9,"rationale":"broken}'
        results = [{"completion": completion, "answer": "Malicious"}]
        summary = generate_summary("e1", results, {"model": "test-model"}, run_id="bad-json", strict=True)
        assert summary["n_examples"] == 1

    def test_generate_e2_summary_from_completion(self, tmp_path: Path) -> None:
        answer = {
            "oracle": [{"id": "v1", "severity": "high"}],
            "fixture_path": str(tmp_path / "fixture.yaml"),
            "fixture_type": "k8s",
        }
        completion = '{"violations": [{"id": "v1", "severity": "high"}], "patch": "", "confidence": 0.8}'
        results = [
            {
                "completion": completion,
                "answer": json.dumps(answer),
                "tool_interactions": [],
                "turns_used": 1,
            }
        ]
        metadata = {"model": "test-model", "dataset": "test-dataset"}

        summary = generate_summary("e2", results, metadata, run_id="test-run")

        assert summary["environment"] == "sv-env-config-verification"
        assert "finding_quality" in summary["metrics"]
        assert "f1_weighted_positive_only" in summary["metrics"]["finding_quality"]
        assert "f1_unweighted_positive_only" in summary["metrics"]["finding_quality"]
        assert "clean_pass_rate" in summary["metrics"]["episode"]
        assert "false_positive_rate_on_clean" in summary["metrics"]["episode"]
        assert "severity_breakdown" in summary

    def test_generate_e2_summary_from_answer_violations_schema(self) -> None:
        # Hub datasets may store the oracle under "violations" with tool + rule_id.
        answer = {
            "violations": [
                {"tool": "kube-linter", "rule_id": "latest-tag", "severity": "medium"},
                {"tool": "kube-linter", "rule_id": "run-as-non-root", "severity": "high"},
            ],
            "patch": "",
        }
        completion = (
            "{"
            '"violations": ['
            '{"id": "kube-linter/latest-tag", "severity": "med"},'
            '{"id": "kube-linter/run-as-non-root", "severity": "high"}'
            "],"
            '"patch": "",'
            '"confidence": 0.8'
            "}"
        )
        summary = generate_summary(
            "e2",
            [{"completion": completion, "answer": json.dumps(answer)}],
            {},
            run_id="t",
        )
        assert summary["metrics"]["finding_quality"]["f1_weighted"] == 1.0

    def test_generate_report_md(self) -> None:
        results = [
            {"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9},
        ]
        summary = generate_summary("e1", results, {}, run_id="test")

        report_md = generate_report_md(summary)

        assert "# SV-Bench Report" in report_md
        assert "Detection Performance" in report_md
        assert "Calibration" in report_md

    def test_strict_mode_missing_fields(self) -> None:
        with pytest.raises(ValueError):
            generate_summary("e1", [{"answer": "Malicious"}], {}, strict=True)

        with pytest.raises(ValueError):
            generate_summary("e2", [{"completion": "{}"}], {}, strict=True)

    def test_malformed_completion_non_strict(self) -> None:
        summary = generate_summary(
            "e1",
            [{"completion": "not json", "answer": "Malicious"}],
            {},
            run_id="bad",
            strict=False,
        )
        assert summary["environment"] == "sv-env-network-logs"

    def test_load_results_from_files(self, tmp_path: Path) -> None:
        results_data = [{"predicted_label": "Malicious", "answer": "Malicious", "confidence": 0.9}]
        (tmp_path / "results.jsonl").write_text(
            "\n".join(json.dumps(r) for r in results_data) + "\n",
            encoding="utf-8",
        )
        metadata_data = {"model": "test-model", "run_id": "test-123"}
        (tmp_path / "metadata.json").write_text(json.dumps(metadata_data), encoding="utf-8")

        results, metadata = load_results(tmp_path)

        assert len(results) == 1
        assert metadata["model"] == "test-model"


class TestToolNameMap:
    def test_all_tool_names_mapped(self) -> None:
        assert set(TOOL_NAMES).issubset(set(TOOL_NAME_MAP.values()))
