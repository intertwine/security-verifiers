"""sv_env_config_verification: Security Verifiers environment
for Security Configuration Verification.

This package implements PRD Environment #2: A ToolEnv where models audit security
configuration files to identify misconfigurations or policy violations. The model can
invoke analysis tools to parse or test the config and produce compliance verdicts.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict

import verifiers as vf
from datasets import Dataset

sys.path.append(str(Path(__file__).resolve().parents[2]))
from sv_shared.utils import get_response_text  # type: ignore  # pylint: disable=wrong-import-position


class ConfigVerificationParser(vf.Parser):
    """Parser to extract security findings from model responses."""

    def parse_answer(self, completion: str) -> str:
        """Extract security findings or compliance verdict from the response.

        Args:
            completion: The raw model completion/response.

        Returns:
            The extracted findings or verdict in standard format.
        """
        # Clean and normalize the response
        cleaned = completion.strip().lower()

        # Look for compliance verdicts
        # Check non-compliant before compliant
        if "non-compliant" in cleaned or "non compliant" in cleaned or "violation" in cleaned:
            return "Non-compliant"
        if "compliant" in cleaned:
            return "Compliant"
        if "insecure" in cleaned or "vulnerable" in cleaned:
            return "Insecure"
        if "secure" in cleaned and "insecure" not in cleaned:
            return "Secure"

        # Return original if no clear verdict found
        return completion.strip()

    def get_format_reward_func(self):
        """Return a format reward function that checks for proper analysis format."""

        def format_reward(
            completion,
            answer="",  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
        ):
            """Reward proper security analysis format."""
            response = get_response_text(completion)
            cleaned = response.strip().lower()

            # Perfect format: includes clear verdict and reasoning
            if any(
                verdict in cleaned
                for verdict in [
                    "secure",
                    "insecure",
                    "compliant",
                    "non-compliant",
                    "vulnerable",
                ]
            ) and ("because" in cleaned or "issue" in cleaned or "found" in cleaned or "detected" in cleaned):  # pylint: disable=line-too-long
                return 1.0

            # Good format: has verdict but minimal reasoning
            if any(
                verdict in cleaned
                for verdict in [
                    "secure",
                    "insecure",
                    "compliant",
                    "non-compliant",
                    "vulnerable",
                ]
            ):
                return 0.5

            # Poor format: no clear verdict
            return 0.0

        return format_reward


def analyze_ssh_config(config: str) -> Dict[str, Any]:
    """Tool function to analyze SSH configuration for security issues.

    Args:
        config: SSH configuration text to analyze.

    Returns:
        Dictionary containing analysis results and detected issues.
    """
    issues = []
    recommendations = []

    config_lower = config.lower()
    # Normalize whitespace for better matching
    config_normalized = " ".join(config_lower.split())

    # Check for insecure settings
    if "permitrootlogin yes" in config_normalized:
        issues.append("Root login is enabled - high security risk")
        recommendations.append("Set 'PermitRootLogin no' or 'PermitRootLogin prohibit-password'")

    if "passwordauthentication yes" in config_normalized:
        issues.append("Password authentication enabled - vulnerable to brute force")
        recommendations.append("Use key-based authentication: 'PasswordAuthentication no'")

    if "permitemptypasswords yes" in config_normalized:
        issues.append("Empty passwords allowed - critical security vulnerability")
        recommendations.append("Set 'PermitEmptyPasswords no'")

    if "protocol 1" in config_normalized:
        issues.append("SSH Protocol 1 enabled - outdated and insecure")
        recommendations.append("Use only Protocol 2")

    if "strictmodes no" in config_normalized:
        issues.append("StrictModes disabled - weakens file permission checks")
        recommendations.append("Set 'StrictModes yes'")

    return {
        "config_type": "SSH",
        "issues_found": len(issues),
        "issues": issues,
        "recommendations": recommendations,
        "verdict": "Insecure" if issues else "Secure",
    }


def analyze_firewall_rules(rules: str) -> Dict[str, Any]:
    """Tool function to analyze firewall rules for security issues.

    Args:
        rules: Firewall rules text to analyze.

    Returns:
        Dictionary containing analysis results and detected issues.
    """
    issues = []
    recommendations = []

    rules_lower = rules.lower()

    # Check for overly permissive rules
    if "0.0.0.0/0" in rules or "any any" in rules_lower:
        issues.append("Overly permissive rule allowing all traffic")
        recommendations.append("Restrict rules to specific IP ranges and ports")

    if "allow all" in rules_lower:
        issues.append("Rule allows all traffic - security risk")
        recommendations.append("Use specific protocol and port restrictions")

    if "telnet" in rules_lower or "port 23" in rules_lower:
        issues.append("Telnet (port 23) allowed - unencrypted protocol")
        recommendations.append("Use SSH instead of Telnet")

    if "ftp" in rules_lower or "port 21" in rules_lower:
        issues.append("FTP (port 21) allowed - unencrypted protocol")
        recommendations.append("Use SFTP or FTPS instead")

    # Check for missing deny rules
    if "deny" not in rules_lower and "drop" not in rules_lower:
        issues.append("No explicit deny rules found")
        recommendations.append("Add explicit deny rules for unauthorized traffic")

    return {
        "config_type": "Firewall",
        "issues_found": len(issues),
        "issues": issues,
        "recommendations": recommendations,
        "verdict": "Insecure" if issues else "Secure",
    }


def reward_correct_analysis(
    completion,
    answer: str = "",
    tools_used: list | None = None,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Reward function that checks if the security analysis is correct.

    Args:
        completion: The model's response with security findings.
        answer: The ground truth issues from the dataset.
        tools_used: List of tools the model used for analysis.
        **kwargs: Additional arguments.

    Returns:
        Reward based on accuracy of issue detection.
    """
    response = get_response_text(completion)
    response_lower = response.lower()

    # Check if model used appropriate analysis tools
    tool_bonus = 0.2 if tools_used else 0.0

    # Simple heuristic: check if key issues are mentioned
    if not answer:
        return 0.0 + tool_bonus

    answer_lower = answer.lower()

    # Count how many expected issues were found
    issues_found = 0
    expected_issues = answer_lower.split(",")

    for issue in expected_issues:
        issue = issue.strip()
        if issue and issue in response_lower:
            issues_found += 1

    if expected_issues:
        accuracy = issues_found / len(expected_issues)
    else:
        accuracy = 1.0 if "secure" in response_lower else 0.0

    return min(1.0, accuracy + tool_bonus)


def load_environment(
    dataset_name: str = "synthetic",  # pylint: disable=unused-argument
    max_examples: int = 100,
) -> vf.ToolEnv:
    """Load the Configuration Verification environment.

    This environment is a tool-enabled task where the model audits security
    configuration files and identifies misconfigurations or policy violations.

    Args:
        dataset_name: Dataset name (currently only synthetic supported).
        max_examples: Maximum number of examples to use.

    Returns:
        A Verifiers ToolEnv configured for the task.
    """

    def _create_synthetic_dataset():
        """Create a synthetic dataset of configuration files with known issues."""
        examples = []

        # pylint: disable=line-too-long
        config_examples = [
            # SSH configurations
            {
                "question": (
                    "Analyze this SSH configuration:\n"
                    "Port 22\n"
                    "PermitRootLogin yes\n"
                    "PasswordAuthentication yes\n"
                    "PermitEmptyPasswords no\n"
                    "StrictModes yes"
                ),
                "answer": "Root login enabled, Password authentication vulnerable to brute force",
                "config_type": "ssh",
            },
            {
                "question": (
                    "Analyze this SSH configuration:\n"
                    "Port 2222\n"
                    "PermitRootLogin no\n"
                    "PasswordAuthentication no\n"
                    "PubkeyAuthentication yes\n"
                    "StrictModes yes"
                ),
                "answer": "Secure",
                "config_type": "ssh",
            },
            {
                "question": (
                    "Review this SSH config:\nProtocol 1\nPermitRootLogin yes\nPermitEmptyPasswords yes\nStrictModes no"
                ),
                "answer": ("Protocol 1 insecure, Root login enabled, Empty passwords allowed, StrictModes disabled"),
                "config_type": "ssh",
            },
            # Firewall rules
            {
                "question": (
                    "Analyze these firewall rules:\n"
                    "allow tcp from any to any port 22\n"
                    "allow tcp from 0.0.0.0/0 to any port 80\n"
                    "allow all from any to any"
                ),
                "answer": "Overly permissive rules, Allow all traffic risk, Unrestricted access",
                "config_type": "firewall",
            },
            {
                "question": (
                    "Review these firewall rules:\n"
                    "allow tcp from 192.168.1.0/24 to any port 22\n"
                    "allow tcp from 10.0.0.0/8 to any port 443\n"
                    "deny all from any to any"
                ),
                "answer": "Secure",
                "config_type": "firewall",
            },
            {
                "question": (
                    "Check these firewall rules:\n"
                    "allow tcp from any to any port 23\n"
                    "allow tcp from any to any port 21\n"
                    "allow udp from 0.0.0.0/0 to any"
                ),
                "answer": "Telnet allowed, FTP unencrypted, Overly permissive UDP",
                "config_type": "firewall",
            },
            # Cloud IAM policies
            {
                "question": (
                    "Review this IAM policy:\n"
                    '{"Version": "2012-10-17", "Statement": '
                    '[{"Effect": "Allow", "Action": "*", "Resource": "*"}]}'
                ),
                "answer": "Wildcard permissions, Full admin access, No resource restrictions",
                "config_type": "iam",
            },
            {
                "question": (
                    "Analyze this IAM policy:\n"
                    '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], '
                    '"Resource": "arn:aws:s3:::mybucket/*"}]}'
                ),
                "answer": "Secure",
                "config_type": "iam",
            },
            # Nginx configurations
            {
                "question": (
                    "Review this nginx config:\n"
                    "server {\n"
                    "  listen 80;\n"
                    "  autoindex on;\n"
                    "  server_tokens on;\n"
                    "  client_max_body_size 0;\n"
                    "}"
                ),
                "answer": "Directory listing enabled, Server version exposed, No upload size limit",
                "config_type": "nginx",
            },
            {
                "question": (
                    "Check this nginx config:\n"
                    "server {\n"
                    "  listen 443 ssl;\n"
                    "  ssl_protocols TLSv1.2 TLSv1.3;\n"
                    "  server_tokens off;\n"
                    "  client_max_body_size 10M;\n"
                    "}"
                ),
                "answer": "Secure",
                "config_type": "nginx",
            },
        ]
        # pylint: enable=line-too-long

        examples.extend(config_examples[:max_examples] if max_examples else config_examples)
        return Dataset.from_list(examples)

    dataset = _create_synthetic_dataset()

    parser = ConfigVerificationParser()

    # Define tools available to the model
    tools = [
        analyze_ssh_config,
        analyze_firewall_rules,
    ]

    rubric = vf.Rubric(
        funcs=[
            reward_correct_analysis,
            parser.get_format_reward_func(),
        ],
        weights=[1.0, 0.3],  # Analysis accuracy is primary, format is secondary
    )

    return vf.ToolEnv(
        name="sv-env-config-verification",
        description=(
            "Audit security configuration files to identify misconfigurations and policy violations."  # pylint: disable=line-too-long
        ),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        tools=tools,
        system_prompt=(
            "You are a security configuration auditor. Analyze the provided configuration files "
            "for security vulnerabilities and policy violations. Use the available analysis tools "
            "when appropriate. Report your findings clearly, including specific issues and recommendations."  # pylint: disable=line-too-long
        ),
    )
