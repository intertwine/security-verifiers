"""Tests for E2 evaluation report generator."""

import json
from pathlib import Path

from generate_e2_eval_report import analyze_run


class TestAnalyzeRun:
    """Tests for analyze_run function."""

    def test_analyze_valid_run_with_tools(self, tmp_path: Path):
        """Test analyzing a valid run directory with tool usage."""
        # Create test metadata
        metadata = {
            "environment": "sv-env-config-verification",
            "model": "gpt-5-mini",
            "dataset": "k8s-labeled-v1.jsonl",
            "timestamp": "2025-10-25T16:39:51Z",
            "num_examples": 4,
            "include_tools": True,
            "max_turns": 5,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Create test results with tool interactions
        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "tool_interactions": [
                    {"turn": 0, "tool": "run_kubelinter", "arguments": {"paths": ["/tmp/test.yaml"]}},
                ],
                "turns_used": 2,
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "tool_interactions": [
                    {"turn": 0, "tool": "run_semgrep", "arguments": {"paths": ["/tmp/test.tf"]}},
                    {"turn": 1, "tool": "run_opa", "arguments": {"paths": ["/tmp/test.tf"]}},
                ],
                "turns_used": 3,
                "rewards": {"reward_config_auditing": 0.9, "format_reward": 1.0},
            },
            {
                "index": 2,
                "completion": '{"violations": [], "confidence": 0.75}',
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.7, "format_reward": 1.0},
            },
            {
                "index": 3,
                "completion": "invalid json",
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        # Analyze the run (with summary writing enabled)
        report = analyze_run(tmp_path, write_summary=True)

        assert report is not None
        assert report["Split"] == "K8s"
        assert report["Model"] == "gpt-5-mini"
        assert report["N"] == 4
        assert report["MeanReward"] == 0.6  # (0.8 + 0.9 + 0.7 + 0.0) / 4
        assert report["FormatSuccess%"] == 75.0  # 3 out of 4 succeeded
        assert report["Error%"] == 0.0  # No completion errors
        assert report["AvgTools"] == 1.5  # (1 + 2 + 0 + 0) / 2 samples with tools
        assert report["AvgTurns"] == 1.75  # (2 + 3 + 1 + 1) / 4
        assert report["run_id"] == tmp_path.name
        assert report["include_tools"] is True

        # Verify summary.json was created
        summary_file = tmp_path / "summary.json"
        assert summary_file.exists()

        # Verify summary.json content matches report
        with open(summary_file) as f:
            summary = json.load(f)
        assert summary == report

    def test_analyze_valid_run_without_tools(self, tmp_path: Path):
        """Test analyzing a run where tools were disabled."""
        metadata = {
            "environment": "sv-env-config-verification",
            "model": "gpt-5-mini",
            "dataset": "terraform-labeled-v1.jsonl",
            "timestamp": "2025-10-25T16:40:00Z",
            "num_examples": 2,
            "include_tools": False,
            "max_turns": 1,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.9, "format_reward": 1.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path, write_summary=True)

        assert report is not None
        assert report["Split"] == "Terraform"
        assert report["MeanReward"] == 0.85  # (0.8 + 0.9) / 2
        assert report["FormatSuccess%"] == 100.0
        assert report["AvgTools"] == 0.0  # No tools used
        assert report["AvgTurns"] == 1.0
        assert report["include_tools"] is False

    def test_analyze_run_with_completion_errors(self, tmp_path: Path):
        """Test analyzing a run with completion errors."""
        metadata = {
            "model": "test-model",
            "dataset": "builtin",
            "timestamp": "2025-10-25T16:40:10Z",
            "num_examples": 3,
            "include_tools": True,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": "",
                "completion_error": "API rate limit exceeded",
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
            },
            {
                "index": 2,
                "completion": "",
                "completion_error": "Connection timeout",
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)

        assert report is not None
        assert report["Error%"] == 66.67  # 2 out of 3 had errors (rounded)
        assert report["MeanReward"] == 0.2667  # (0.8 + 0.0 + 0.0) / 3 (rounded)
        assert report["FormatSuccess%"] == 33.33  # 1 out of 3 succeeded

    def test_analyze_missing_files(self, tmp_path: Path):
        """Test that analyze_run returns None for missing files."""
        report = analyze_run(tmp_path)
        assert report is None

    def test_analyze_combined_dataset(self, tmp_path: Path):
        """Test dataset split detection for combined dataset."""
        metadata = {
            "model": "qwen3-14b",
            "dataset": "combined",
            "timestamp": "2025-10-25T16:40:20Z",
            "num_examples": 2,
            "include_tools": True,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "rewards": {"reward_config_auditing": 0.9, "format_reward": 1.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["Split"] == "Combined"

    def test_analyze_builtin_fixtures(self, tmp_path: Path):
        """Test dataset split detection for builtin test fixtures."""
        metadata = {
            "model": "test-model",
            "dataset": "builtin",
            "timestamp": "2025-10-25T16:40:30Z",
            "num_examples": 1,
            "include_tools": False,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "rewards": {"reward_config_auditing": 1.0, "format_reward": 1.0},
            }
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["Split"] == "Fixtures"

    def test_no_write_summary(self, tmp_path: Path):
        """Test that summary.json is not written when write_summary=False."""
        metadata = {
            "model": "test-model",
            "dataset": "k8s-labeled-v1.jsonl",
            "timestamp": "2025-10-25T16:40:40Z",
            "num_examples": 2,
            "include_tools": True,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "rewards": {"reward_config_auditing": 0.9, "format_reward": 1.0},
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
            "dataset": "k8s-labeled-v1.jsonl",
            "timestamp": "2025-10-25T16:40:50Z",
            "num_examples": 3,
            "include_tools": True,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "tool_interactions": [{"turn": 0, "tool": "run_kubelinter", "arguments": {}}],
                "turns_used": 2,
                "rewards": {"reward_config_auditing": 0.8, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.9, "format_reward": 1.0},
            },
            {
                "index": 2,
                "completion": "invalid",
                "tool_interactions": [],
                "turns_used": 1,
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
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
        # 1. eval_config_verification.py creates summary.json
        # 2. generate_e2_eval_report.py can safely recreate it
        # 3. No conflicts occur

    def test_all_format_failures(self, tmp_path: Path):
        """Test run where all format validations failed."""
        metadata = {
            "model": "test-model",
            "dataset": "k8s-labeled-v1.jsonl",
            "timestamp": "2025-10-25T16:41:00Z",
            "num_examples": 2,
            "include_tools": False,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": "not json",
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
            },
            {
                "index": 1,
                "completion": "also not json",
                "rewards": {"reward_config_auditing": 0.0, "format_reward": 0.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["FormatSuccess%"] == 0.0
        assert report["MeanReward"] == 0.0

    def test_high_tool_usage(self, tmp_path: Path):
        """Test run with extensive tool usage."""
        metadata = {
            "model": "test-model",
            "dataset": "combined",
            "timestamp": "2025-10-25T16:41:10Z",
            "num_examples": 2,
            "include_tools": True,
            "max_turns": 10,
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        results = [
            {
                "index": 0,
                "completion": '{"violations": [], "confidence": 0.9}',
                "tool_interactions": [
                    {"turn": 0, "tool": "run_kubelinter", "arguments": {}},
                    {"turn": 1, "tool": "run_semgrep", "arguments": {}},
                    {"turn": 2, "tool": "run_opa", "arguments": {}},
                    {"turn": 3, "tool": "run_kubelinter", "arguments": {}},
                    {"turn": 4, "tool": "run_semgrep", "arguments": {}},
                ],
                "turns_used": 8,
                "rewards": {"reward_config_auditing": 0.95, "format_reward": 1.0},
            },
            {
                "index": 1,
                "completion": '{"violations": [], "confidence": 0.85}',
                "tool_interactions": [
                    {"turn": 0, "tool": "run_opa", "arguments": {}},
                ],
                "turns_used": 3,
                "rewards": {"reward_config_auditing": 0.85, "format_reward": 1.0},
            },
        ]
        results_file = tmp_path / "results.jsonl"
        with open(results_file, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")

        report = analyze_run(tmp_path)
        assert report["AvgTools"] == 3.0  # (5 + 1) / 2
        assert report["AvgTurns"] == 5.5  # (8 + 3) / 2
