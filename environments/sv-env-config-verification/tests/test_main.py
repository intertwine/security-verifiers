"""Tests for the configuration verification environment."""

import pytest
import verifiers as vf
from sv_env_config_verification.main import (
    ConfigVerificationParser,
    analyze_firewall_rules,
    analyze_ssh_config,
    load_environment,
    reward_correct_analysis,
)


class TestConfigVerificationParser:
    """Test cases for ConfigVerificationParser class."""

    def test_parse_answer_secure(self):
        """Test parsing secure/compliant responses."""
        parser = ConfigVerificationParser()
        assert parser.parse_answer("Secure") == "Secure"
        assert parser.parse_answer("Configuration is secure") == "Secure"
        assert parser.parse_answer("Compliant") == "Compliant"
        assert parser.parse_answer("Fully compliant with policies") == "Compliant"

    def test_parse_answer_insecure(self):
        """Test parsing insecure/non-compliant responses."""
        parser = ConfigVerificationParser()
        assert parser.parse_answer("Insecure") == "Insecure"
        assert parser.parse_answer("Configuration is insecure") == "Insecure"
        assert parser.parse_answer("Vulnerable") == "Insecure"
        assert parser.parse_answer("Non-compliant") == "Non-compliant"
        assert parser.parse_answer("Policy violation detected") == "Non-compliant"

    def test_parse_answer_unknown(self):
        """Test parsing unknown responses."""
        parser = ConfigVerificationParser()
        assert parser.parse_answer("Unknown") == "Unknown"
        assert parser.parse_answer("Need more information") == "Need more information"
        assert parser.parse_answer("") == ""

    def test_format_reward_perfect(self):
        """Test format reward for perfect responses."""
        parser = ConfigVerificationParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Insecure because root login is enabled") == 1.0
        assert format_func("Secure - no issues found") == 1.0
        assert format_func("Vulnerable: detected open ports") == 1.0

    def test_format_reward_partial(self):
        """Test format reward for partial responses."""
        parser = ConfigVerificationParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Insecure") == 0.5
        assert format_func("Compliant") == 0.5
        assert format_func("This is vulnerable") == 0.5

    def test_format_reward_poor(self):
        """Test format reward for poor responses."""
        parser = ConfigVerificationParser()
        format_func = parser.get_format_reward_func()

        assert format_func("I don't know") == 0.0
        assert format_func("Maybe") == 0.0
        assert format_func("") == 0.0


def test_analyze_ssh_config_insecure():
    """Test SSH config analysis with insecure settings."""
    config = """
    Port 22
    PermitRootLogin yes
    PasswordAuthentication yes
    PermitEmptyPasswords yes
    Protocol 1
    StrictModes no
    """

    result = analyze_ssh_config(config)

    assert result["config_type"] == "SSH"
    assert result["verdict"] == "Insecure"
    assert result["issues_found"] == 5
    assert len(result["issues"]) == 5
    assert len(result["recommendations"]) == 5
    assert "Root login is enabled" in result["issues"][0]


def test_analyze_ssh_config_secure():
    """Test SSH config analysis with secure settings."""
    config = """
    Port 2222
    PermitRootLogin no
    PasswordAuthentication no
    PubkeyAuthentication yes
    Protocol 2
    StrictModes yes
    """

    result = analyze_ssh_config(config)

    assert result["config_type"] == "SSH"
    assert result["verdict"] == "Secure"
    assert result["issues_found"] == 0
    assert len(result["issues"]) == 0


def test_analyze_firewall_rules_insecure():
    """Test firewall rules analysis with insecure rules."""
    rules = """
    allow tcp from 0.0.0.0/0 to any port 22
    allow all from any to any
    allow tcp from any to any port 23
    allow tcp from any to any port 21
    """

    result = analyze_firewall_rules(rules)

    assert result["config_type"] == "Firewall"
    assert result["verdict"] == "Insecure"
    assert result["issues_found"] >= 3
    assert any("Overly permissive" in issue for issue in result["issues"])
    assert any("Telnet" in issue for issue in result["issues"])


def test_analyze_firewall_rules_secure():
    """Test firewall rules analysis with secure rules."""
    rules = """
    allow tcp from 192.168.1.0/24 to 192.168.1.10 port 22
    allow tcp from 10.0.0.0/8 to any port 443
    deny all from any to any
    """

    result = analyze_firewall_rules(rules)

    assert result["config_type"] == "Firewall"
    assert result["verdict"] == "Secure"
    assert result["issues_found"] == 0


def test_reward_correct_analysis_with_tools():
    """Test reward function with tool usage."""
    completion = "Insecure: Root login enabled, Password authentication vulnerable"
    answer = "Root login enabled, Password authentication vulnerable"
    tools_used = ["analyze_ssh_config"]

    reward = reward_correct_analysis(completion, answer, tools_used)
    assert reward > 0.5  # Should get accuracy + tool bonus


def test_reward_correct_analysis_without_tools():
    """Test reward function without tool usage."""
    completion = "Configuration is secure"
    answer = "Secure"

    reward = reward_correct_analysis(completion, answer, None)
    assert reward > 0.0  # Should get some reward for correct verdict


def test_reward_correct_analysis_partial_match():
    """Test reward with partial issue detection."""
    completion = "Found issue: Root login enabled"
    answer = "Root login enabled, Password authentication vulnerable, Empty passwords"

    reward = reward_correct_analysis(completion, answer)
    assert 0.0 < reward < 1.0  # Partial credit for finding some issues


def test_load_environment():
    """Test loading the configuration verification environment."""
    env = load_environment(max_examples=5)

    assert isinstance(env, vf.ToolEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 5
    assert env.tools is not None
    assert len(env.tools) == 2  # SSH and firewall analyzers
    assert env.name == "sv-env-config-verification"


def test_load_environment_dataset_structure():
    """Test that the synthetic dataset has the expected structure."""
    env = load_environment(max_examples=3)

    assert "question" in env.dataset.column_names
    assert "answer" in env.dataset.column_names
    assert "config_type" in env.dataset.column_names

    # Check that different config types are present
    config_types = [example["config_type"] for example in env.dataset]
    assert any(ct in ["ssh", "firewall", "iam", "nginx"] for ct in config_types)
