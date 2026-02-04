"""Test suite for the config auditing environment."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import verifiers as vf

from sv_env_config_verification import (
    ConfigVerificationParser,
    load_environment,
    reward_config_auditing,
)
from adapters import kubelinter_adapter, opa_adapter, semgrep_adapter
from adapters.types import ToolFinding, Violation
from mapping import normalize_findings
from oracle import load_golden_oracle
from patching import try_apply_patch
from reward import final_reward
from schema import parse_model_output


class TestConfigVerification:
    """Test suite for the config auditing environment."""

    def test_parser_and_format_reward(self) -> None:
        """Test parser and format reward."""
        parser = ConfigVerificationParser()
        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":0.9}'
        parsed = parser.parse_answer(completion)
        assert parsed["violations"][0]["id"].startswith("kube-linter/")
        assert parser.get_format_reward_func()(completion) == 1.0

    def test_parser_invalid_json(self) -> None:
        """Test parser with invalid JSON."""
        parser = ConfigVerificationParser()
        completion = "not valid json"
        parsed = parser.parse_answer(completion)
        assert parsed == {}
        assert parser.get_format_reward_func()(completion) == 0.0

    def test_parser_missing_fields(self) -> None:
        """Test parser with missing required fields."""
        parser = ConfigVerificationParser()
        completion = '{"violations":[]}'  # Missing patch and confidence
        parsed = parser.parse_answer(completion)
        assert parsed == {}
        assert parser.get_format_reward_func()(completion) == 0.0

    def test_reward_no_patch(self) -> None:
        """Test reward with no patch."""
        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":1.0}'
        answer = {
            "oracle": [{"id": "kube-linter/run-as-root", "severity": "high"}],
            "fixture_path": "",
            "fixture_type": "k8s",
        }
        reward = reward_config_auditing(completion, answer)
        assert reward > 0.9

    def test_reward_with_string_answer(self) -> None:
        """Test reward when answer is provided as JSON string."""
        completion = '{"violations":[{"id":"kube-linter/test","severity":"med"}],"patch":"","confidence":0.8}'
        answer_str = json.dumps(
            {
                "oracle": [{"id": "kube-linter/test", "severity": "med"}],
                "fixture_path": "",
                "fixture_type": "k8s",
            }
        )
        reward = reward_config_auditing(completion, answer_str)
        assert reward > 0.5

    def test_reward_with_hub_style_answer(self) -> None:
        """Test reward when oracle is stored under 'violations' with tool/rule_id."""
        completion = '{"violations":[{"id":"kube-linter/latest-tag","severity":"med"}],"patch":"","confidence":0.8}'
        answer = {
            "violations": [{"tool": "kube-linter", "rule_id": "latest-tag", "severity": "medium", "msg": "x"}],
            "patch": "",
        }
        reward = reward_config_auditing(completion, answer)
        assert reward > 0.5

    def test_reward_invalid_json(self) -> None:
        """Test reward with invalid JSON returns 0."""
        completion = "invalid json"
        answer = {"oracle": [], "fixture_path": "", "fixture_type": "k8s"}
        reward = reward_config_auditing(completion, answer)
        assert reward == 0.0

    def test_reward_empty_violations(self) -> None:
        """Test reward with empty violations list."""
        completion = '{"violations":[],"patch":"","confidence":1.0}'
        answer = {
            "oracle": [{"id": "kube-linter/test", "severity": "high"}],
            "fixture_path": "",
            "fixture_type": "k8s",
        }
        reward = reward_config_auditing(completion, answer)
        assert reward < 0.5  # Should be penalized for missing violations

    def test_load_environment(self) -> None:
        """Test loading the environment."""
        env = load_environment(max_examples=1, include_tools=False)
        assert isinstance(env, vf.ToolEnv)
        assert env.dataset is not None, "Dataset should not be None"
        assert len(env.dataset) > 0, "Dataset should not be empty"
        sample = env.dataset[0]
        assert "answer" in sample
        assert "question" in sample

    def test_load_environment_with_tools(self) -> None:
        """Test loading environment with tools enabled."""
        env = load_environment(max_examples=1, include_tools=True)
        assert isinstance(env, vf.ToolEnv)
        assert len(env.tools) == 3  # run_kubelinter, run_semgrep, run_opa
        assert env.tools[0].__name__ == "run_kubelinter"
        assert env.tools[1].__name__ == "run_semgrep"
        assert env.tools[2].__name__ == "run_opa"


class TestKubeLinterAdapter:
    """Tests for kubelinter adapter."""

    def test_kubelinter_end_line(self, monkeypatch: Any) -> None:
        """Test kubelinter adapter end line."""
        dummy_output = json.dumps(
            {
                "Reports": [
                    {
                        "Check": "run-as-non-root",
                        "Diagnostic": {"Message": "msg"},
                        "Object": {"Metadata": {"FilePath": "f.yaml"}},
                    }
                ]
            }
        )

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 0, dummy_output, "")

        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = kubelinter_adapter.kubelinter_lint(["f.yaml"])
        assert len(findings) == 1
        assert findings[0].end_line is None

    def test_kubelinter_finding_complete(self, monkeypatch: Any) -> None:
        """Test kubelinter finding parsing with all fields."""
        dummy_output = json.dumps(
            {
                "Reports": [
                    {
                        "Check": "latest-tag",
                        "Diagnostic": {
                            "Message": 'container "app" uses image without tag',
                        },
                        "Object": {
                            "Metadata": {
                                "FilePath": "deploy.yaml",
                                "LineInfo": {"Line": 15},
                            }
                        },
                    }
                ]
            }
        )

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 0, dummy_output, "")

        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = kubelinter_adapter.kubelinter_lint(["deploy.yaml"])
        assert len(findings) == 1
        finding = findings[0]
        assert finding.tool == "kube-linter"
        assert finding.rule_id == "latest-tag"
        assert finding.severity == ""  # kubelinter doesn't provide severity directly
        assert finding.file == "deploy.yaml"
        assert finding.start_line == 15

    def test_kubelinter_invalid_json(self, monkeypatch: Any) -> None:
        """Test kubelinter with invalid JSON output."""

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 1, "not json", "error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        with pytest.raises(kubelinter_adapter.KubeLinterError):
            kubelinter_adapter.kubelinter_lint(["test.yaml"])

    def test_kubelinter_empty_reports(self, monkeypatch: Any) -> None:
        """Test kubelinter with no violations."""
        dummy_output = json.dumps({"Reports": []})

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 0, dummy_output, "")

        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = kubelinter_adapter.kubelinter_lint(["clean.yaml"])
        assert findings == []


class TestOpaAdapter:
    """Tests for OPA adapter."""

    def test_opa_eval_violations(self, monkeypatch: Any) -> None:
        """Test OPA evaluation with violations."""
        dummy_output = json.dumps(
            {
                "result": [
                    {
                        "expressions": [
                            {
                                "value": {
                                    "violations": [
                                        {
                                            "rule_id": "GEN_001",
                                            "severity": "med",
                                            "message": "Container runs as root",
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        )

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 0, dummy_output, "")

        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = opa_adapter.opa_eval({"test": "data"}, ["policy.rego"])
        assert len(findings) == 1
        assert findings[0].tool == "opa"
        assert findings[0].rule_id == "GEN_001"

    def test_opa_eval_error(self, monkeypatch: Any) -> None:
        """Test OPA evaluation with error."""

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            raise subprocess.CalledProcessError(1, "opa", stderr="policy error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        with pytest.raises(opa_adapter.OPAError) as exc_info:
            opa_adapter.opa_eval({"test": "data"}, ["policy.rego"])
        assert "policy error" in str(exc_info.value)

    def test_opa_eval_binary_not_found(self, monkeypatch: Any) -> None:
        """Test OPA when binary is not found."""

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        with pytest.raises(opa_adapter.OPAError) as exc_info:
            opa_adapter.opa_eval({"test": "data"}, ["policy.rego"])
        assert "not found" in str(exc_info.value)


class TestSemgrepAdapter:
    """Tests for Semgrep adapter."""

    def test_semgrep_scan(self, monkeypatch: Any) -> None:
        """Test semgrep scanning."""
        dummy_output = json.dumps(
            {
                "results": [
                    {
                        "check_id": "terraform.aws.security.aws-ec2-has-public-ip",
                        "path": "main.tf",
                        "start": {"line": 10},
                        "end": {"line": 15},
                        "extra": {
                            "message": "EC2 instance has public IP",
                            "severity": "WARNING",
                        },
                    }
                ]
            }
        )

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            return subprocess.CompletedProcess(args, 0, dummy_output, "")

        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = semgrep_adapter.semgrep_scan(["main.tf"])
        assert len(findings) == 1
        finding = findings[0]
        assert finding.tool == "semgrep"
        assert finding.severity == "WARNING"  # semgrep returns raw severity, normalized later by mapping
        assert finding.start_line == 10
        assert finding.end_line == 15

    def test_semgrep_scan_error(self, monkeypatch: Any) -> None:
        """Test semgrep scan with error."""

        def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
            raise subprocess.CalledProcessError(1, "semgrep", stderr="scan failed")

        monkeypatch.setattr(subprocess, "run", mock_run)
        with pytest.raises(semgrep_adapter.SemgrepError) as exc_info:
            semgrep_adapter.semgrep_scan(["test.tf"])
        assert "scan failed" in str(exc_info.value)


class TestMapping:
    """Tests for finding normalization."""

    def test_normalize_findings(self) -> None:
        """Test normalizing findings to violations."""
        findings = [
            ToolFinding(
                tool="kube-linter",
                rule_id="run-as-non-root",
                severity="Error",  # Use the actual severity format from kubelinter
                message="Container runs as root",
            ),
            ToolFinding(
                tool="opa",
                rule_id="GEN_001",
                severity="med",
                message="Missing security context",
            ),
        ]
        violations = normalize_findings(findings)
        assert len(violations) == 2
        assert violations[0].id == "kube-linter/run-as-non-root"
        assert violations[0].severity == "high"  # mapped from "Error"
        assert violations[1].id == "opa/GEN_001"
        assert violations[1].severity == "med"

    def test_normalize_findings_unknown_severity(self) -> None:
        """Test normalizing with unknown severity defaults to med."""
        findings = [
            ToolFinding(
                tool="kube-linter",
                rule_id="test",
                severity="UNKNOWN",
                message="test",
            )
        ]
        violations = normalize_findings(findings)
        assert violations[0].severity == "med"  # Should default to med

    def test_normalize_findings_empty_severity(self) -> None:
        """Test normalizing with empty severity."""
        findings = [
            ToolFinding(
                tool="kube-linter",
                rule_id="test",
                severity="",
                message="test",
            )
        ]
        violations = normalize_findings(findings)
        assert violations[0].severity == "med"  # Should default to med


class TestPatching:
    """Tests for patch application."""

    def test_apply_valid_patch(self, tmp_path: Path) -> None:
        """Test applying a valid unified diff."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("line1\nline2\nline3\n")

        test_patch = """--- test.yaml
+++ test.yaml
@@ -1,3 +1,3 @@
 line1
-line2
+modified_line2
 line3
"""
        applied, new_text = try_apply_patch(str(test_file), test_patch)
        assert applied
        assert "modified_line2" in new_text

    def test_apply_invalid_patch(self, tmp_path: Path) -> None:
        """Test applying an invalid patch."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("original content")

        invalid_patch = "not a valid patch"
        applied, new_text = try_apply_patch(str(test_file), invalid_patch)
        # Invalid patch returns False with original content
        assert not applied
        assert new_text == "original content"

    def test_apply_patch_nonexistent_file(self) -> None:
        """Test applying patch to non-existent file - should raise FileNotFoundError."""
        test_patch = """--- test.yaml
+++ test.yaml
@@ -1 +1 @@
-old
+new
"""
        # The patching module doesn't handle non-existent files gracefully, it raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            try_apply_patch("/nonexistent/file.yaml", test_patch)

    def test_apply_empty_patch(self, tmp_path: Path) -> None:
        """Test applying empty patch."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("content")

        applied, new_text = try_apply_patch(str(test_file), "")
        # Empty patch might be considered "valid" but no-op
        if applied:
            assert new_text == "content" or new_text == ""
        else:
            assert new_text == ""


class TestSchema:
    """Tests for model output parsing."""

    def test_parse_valid_output(self) -> None:
        """Test parsing valid model output."""
        data = {
            "violations": [{"id": "kube-linter/test", "severity": "high"}],
            "patch": "",
            "confidence": 0.95,
        }
        violations, patch, confidence = parse_model_output(data)
        assert len(violations) == 1
        assert violations[0].id == "kube-linter/test"
        assert patch == ""
        assert confidence == 0.95

    def test_parse_invalid_severity(self) -> None:
        """Test parsing with invalid severity."""
        data = {
            "violations": [{"id": "test", "severity": "invalid"}],
            "patch": "",
            "confidence": 1.0,
        }
        with pytest.raises(ValueError):
            parse_model_output(data)

    def test_parse_missing_confidence(self) -> None:
        """Test parsing with missing confidence."""
        data = {
            "violations": [],
            "patch": "",
            # Missing confidence
        }
        with pytest.raises(ValueError):
            parse_model_output(data)

    def test_parse_with_patch(self) -> None:
        """Test parsing with a patch."""
        data = {
            "violations": [{"id": "test/rule", "severity": "low"}],
            "patch": "--- a.yaml\n+++ b.yaml\n@@ -1 +1 @@\n-old\n+new",
            "confidence": 0.8,
        }
        violations, patch, confidence = parse_model_output(data)
        assert len(violations) == 1
        assert patch is not None
        assert "old" in patch
        assert confidence == 0.8


class TestReward:
    """Tests for reward calculation."""

    def test_perfect_detection(self) -> None:
        """Test reward for perfect detection."""
        predicted = [
            Violation(id="kube-linter/test1", severity="high"),
            Violation(id="opa/test2", severity="med"),
        ]
        oracle = predicted.copy()
        reward = final_reward(predicted, oracle)
        assert reward == 1.05  # 1.0 for perfect detection + 0.05 format bonus

    def test_partial_detection(self) -> None:
        """Test reward for partial detection."""
        predicted = [Violation(id="kube-linter/test1", severity="high")]
        oracle = [
            Violation(id="kube-linter/test1", severity="high"),
            Violation(id="opa/test2", severity="med"),
        ]
        reward = final_reward(predicted, oracle)
        assert 0.5 < reward < 1.0

    def test_false_positives(self) -> None:
        """Test reward with false positives."""
        predicted = [
            Violation(id="kube-linter/false1", severity="high"),
            Violation(id="kube-linter/false2", severity="high"),
        ]
        oracle = []
        reward = final_reward(predicted, oracle)
        assert reward < 0.5  # Should be penalized for false positives

    def test_reward_with_patch_improvement(self) -> None:
        """Test reward when patch reduces violations."""
        predicted = [
            Violation(id="kube-linter/test1", severity="high"),
            Violation(id="kube-linter/test2", severity="med"),
        ]
        oracle = predicted.copy()
        post_patch = [Violation(id="kube-linter/test2", severity="med")]  # test1 fixed
        reward = final_reward(predicted, oracle, post_patch=post_patch)
        assert reward > 1.0  # Should get bonus for fixing violations


class TestOracle:
    """Tests for oracle loading."""

    def test_load_golden_oracle(self) -> None:
        """Test loading golden oracle data."""
        oracle_path = Path(__file__).parent / "dataset" / "oracle" / "bad_pod.json"
        if oracle_path.exists():
            violations = load_golden_oracle(str(oracle_path))
            assert len(violations) > 0
            assert all(hasattr(v, "id") for v in violations)
            assert all(hasattr(v, "severity") for v in violations)

    def test_load_golden_oracle_nonexistent(self) -> None:
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_golden_oracle("/nonexistent/oracle.json")


class TestIntegration:
    """Integration tests."""

    def test_environment_with_dataset(self) -> None:
        """Test environment loads with real dataset."""
        env = load_environment(max_examples=2, include_tools=False)
        assert env.dataset is not None, "Dataset should not be None"
        assert len(env.dataset) <= 2

        for idx in range(len(env.dataset)):
            sample = env.dataset[idx]
            assert "question" in sample
            assert "answer" in sample

            # Parse answer to ensure it's valid JSON
            answer_str = sample["answer"]
            assert isinstance(answer_str, str), "Answer should be a JSON string"
            answer = json.loads(answer_str)
            assert "oracle" in answer
            assert "fixture_path" in answer
            assert "fixture_type" in answer

    def test_environment_system_prompt(self) -> None:
        """Test that environment has proper system prompt."""
        env = load_environment(max_examples=1, include_tools=False)
        assert env.system_prompt is not None
        assert "security auditor" in env.system_prompt
        assert "JSON" in env.system_prompt
        assert "violations" in env.system_prompt
