"""Security configuration auditing environment (E2).

This module implements PRD Environment #2. Models examine security
configuration files, optionally call analysis tools, and must return a
structured report of violations along with optional patches and a
confidence estimate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import verifiers as vf
from datasets import Dataset

# Allow importing shared utilities when developing from the repo
sys.path.append(str(Path(__file__).resolve().parents[2]))
from sv_shared.utils import (  # type: ignore  # pylint: disable=wrong-import-position
    get_response_text,
)


class ConfigVerificationParser(vf.Parser):
    """Parser to extract structured findings from model responses."""

    def parse_answer(self, completion: Any) -> Dict[str, Any]:
        """Parse the model completion into the expected schema.

        Args:
            completion: Raw model response.

        Returns:
            Parsed dictionary with ``violations``, ``patch``, and
            ``confidence`` keys. Returns an empty dict if parsing fails.
        """
        text = get_response_text(completion)
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return {}
        except (json.JSONDecodeError, TypeError):  # pragma: no cover - defensive programming
            return {}
        return data

    def get_format_reward_func(self):
        """Return a format reward function checking JSON structure."""

        def format_reward(  # pylint: disable=unused-argument
            completion,
            answer: str = "",
            **kwargs: Dict[str, Any],
        ) -> float:
            text = get_response_text(completion)
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):  # pragma: no cover - defensive programming
                return 0.0

            violations = data.get("violations")
            has_conf = isinstance(data.get("confidence"), (int, float))
            has_patch = isinstance(data.get("patch"), str)

            if (
                isinstance(violations, list)
                and all(
                    isinstance(v, dict)
                    and "id" in v
                    and v.get("severity") in {"low", "med", "high"}
                    for v in violations
                )
                and has_conf
                and has_patch
            ):
                return 1.0

            if isinstance(data, dict):
                return 0.5

            return 0.0

        return format_reward


def analyze_ssh_config(config: str) -> Dict[str, Any]:
    """Analyze SSH configuration for security issues."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    cfg = " ".join(config.lower().split())

    if "permitrootlogin yes" in cfg:
        violations.append({"id": "ssh-permit-root-login", "severity": "high"})
        patches.append("PermitRootLogin no")
    if "passwordauthentication yes" in cfg:
        violations.append({"id": "ssh-password-auth", "severity": "med"})
        patches.append("PasswordAuthentication no")
    if "permitemptypasswords yes" in cfg:
        violations.append({"id": "ssh-empty-passwords", "severity": "high"})
        patches.append("PermitEmptyPasswords no")
    if "protocol 1" in cfg:
        violations.append({"id": "ssh-protocol-v1", "severity": "high"})
        patches.append("Protocol 2")
    if "strictmodes no" in cfg:
        violations.append({"id": "ssh-strictmodes-disabled", "severity": "med"})
        patches.append("StrictModes yes")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_firewall_rules(rules: str) -> Dict[str, Any]:
    """Analyze firewall rules for security issues."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    rules_lower = rules.lower()

    if "0.0.0.0/0" in rules or "any any" in rules_lower:
        violations.append({"id": "fw-open-to-world", "severity": "high"})
        patches.append("Restrict source addresses")
    if "allow all" in rules_lower:
        violations.append({"id": "fw-allow-all", "severity": "high"})
        patches.append("Replace 'allow all' with specific rules")
    if "telnet" in rules_lower or "port 23" in rules_lower:
        violations.append({"id": "fw-telnet-allowed", "severity": "med"})
        patches.append("Remove telnet access")
    if "ftp" in rules_lower or "port 21" in rules_lower:
        violations.append({"id": "fw-ftp-allowed", "severity": "med"})
        patches.append("Remove FTP access")
    if "deny" not in rules_lower and "drop" not in rules_lower:
        violations.append({"id": "fw-missing-deny", "severity": "low"})
        patches.append("Add explicit deny rules")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_iam_policy(policy: str) -> Dict[str, Any]:
    """Analyze IAM policy for wildcard permissions."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    policy_lower = policy.lower()
    policy_norm = policy_lower.replace(" ", "")

    if "\"action\":\"*\"" in policy_norm or "\"action\":[\"*\"]" in policy_norm:
        violations.append({"id": "iam-wildcard-action", "severity": "high"})
        patches.append("Specify allowed actions explicitly")
    if "\"resource\":\"*\"" in policy_norm:
        violations.append({"id": "iam-wildcard-resource", "severity": "high"})
        patches.append("Restrict resource ARNs")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_nginx_config(config: str) -> Dict[str, Any]:
    """Analyze nginx configuration for insecure directives."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    cfg = config.lower()

    if "autoindex on" in cfg:
        violations.append({"id": "nginx-autoindex-on", "severity": "low"})
        patches.append("autoindex off")
    if "server_tokens on" in cfg:
        violations.append({"id": "nginx-server-tokens-on", "severity": "low"})
        patches.append("server_tokens off")
    if "client_max_body_size 0" in cfg:
        violations.append({"id": "nginx-no-body-limit", "severity": "med"})
        patches.append("client_max_body_size 10M")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_rego_policy(policy: str) -> Dict[str, Any]:
    """Analyze OPA/Rego policy for insecure defaults."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    text = policy.replace(" ", "").lower()

    if "defaultallow=true" in text:
        violations.append({"id": "rego-default-allow", "severity": "high"})
        patches.append("default allow = false")
    if "allow=true" in text or "allow{true}" in text:
        violations.append({"id": "rego-allow-all", "severity": "high"})
        patches.append("Specify allow conditions")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_k8s_config(config: str) -> Dict[str, Any]:
    """Analyze Kubernetes configuration for risky settings."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    cfg = config.lower()

    if "privileged: true" in cfg:
        violations.append({"id": "k8s-privileged-container", "severity": "high"})
        patches.append("privileged: false")
    if "runasuser: 0" in cfg or "runasnonroot: false" in cfg:
        violations.append({"id": "k8s-run-as-root", "severity": "high"})
        patches.append("runAsNonRoot: true")
    if ":latest" in cfg:
        violations.append({"id": "k8s-latest-tag", "severity": "med"})
        patches.append("Pin image tag")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def analyze_semgrep_code(code: str) -> Dict[str, Any]:
    """Analyze code snippet for patterns Semgrep would flag."""

    violations: List[Dict[str, str]] = []
    patches: List[str] = []
    lower = code.lower()

    if "eval(" in lower or "exec(" in lower:
        violations.append({"id": "semgrep-eval", "severity": "high"})
        patches.append("Avoid eval/exec")
    if "subprocess" in lower and "shell=true" in lower:
        violations.append({"id": "semgrep-shell", "severity": "med"})
        patches.append("Avoid shell=True")
    if "os.system" in lower:
        violations.append({"id": "semgrep-os-system", "severity": "med"})
        patches.append("Use subprocess without shell")

    return {
        "violations": violations,
        "patch": "\n".join(patches),
        "confidence": 1.0,
    }


def reward_correct_analysis(
    completion,
    answer: Dict[str, Any] | None = None,
    tools_used: List[str] | None = None,
    **kwargs: Dict[str, Any],  # pylint: disable=unused-argument
) -> float:
    """Reward function that checks if the security analysis is correct."""

    text = get_response_text(completion)
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):  # pragma: no cover - defensive
            return 0.0
    except (json.JSONDecodeError, TypeError):  # pragma: no cover - defensive programming
        return 0.0

    expected = answer or {}
    weight_map = {"high": 1.0, "med": 0.6, "low": 0.3}
    expected_ids = {v["id"]: v["severity"] for v in expected.get("violations", [])}
    max_weight = sum(weight_map.get(sev, 0.0) for sev in expected_ids.values())

    tp_weight = 0.0
    fp_weight = 0.0
    for vio in parsed.get("violations", []):
        vio_id = vio.get("id")
        severity = vio.get("severity")
        weight = weight_map.get(severity, 0.0)
        if vio_id in expected_ids and expected_ids[vio_id] == severity:
            tp_weight += weight
        else:
            fp_weight += weight

    if max_weight == 0:
        base = 1.0 if tp_weight == 0 and fp_weight == 0 else 0.0
    else:
        recall = tp_weight / max_weight
        precision = tp_weight / (tp_weight + fp_weight) if (tp_weight + fp_weight) else 0.0
        base = 0.7 * recall + 0.3 * precision

    patch_bonus = 0.1 if parsed.get("patch") else 0.0
    tool_bonus = 0.1 if tools_used else 0.0

    reward = base + patch_bonus + tool_bonus
    return float(min(1.0, max(0.0, reward)))


def load_environment(
    dataset_name: str = "synthetic",  # pylint: disable=unused-argument
    max_examples: int = 100,
) -> vf.ToolEnv:
    """Load the Configuration Verification environment."""

    def _create_synthetic_dataset() -> Dataset:
        """Create a synthetic dataset of configuration files with known issues."""

        configs = [
            {
                "config_type": "ssh",
                "config": (
                    "Port 22\n"
                    "PermitRootLogin yes\n"
                    "PasswordAuthentication yes\n"
                    "PermitEmptyPasswords no\n"
                    "StrictModes yes"
                ),
                "tool": analyze_ssh_config,
            },
            {
                "config_type": "ssh",
                "config": (
                    "Port 2222\n"
                    "PermitRootLogin no\n"
                    "PasswordAuthentication no\n"
                    "PubkeyAuthentication yes\n"
                    "StrictModes yes"
                ),
                "tool": analyze_ssh_config,
            },
            {
                "config_type": "firewall",
                "config": (
                    "allow tcp from any to any port 22\n"
                    "allow tcp from 0.0.0.0/0 to any port 80\n"
                    "allow all from any to any"
                ),
                "tool": analyze_firewall_rules,
            },
            {
                "config_type": "firewall",
                "config": (
                    "allow tcp from 192.168.1.0/24 to any port 22\n"
                    "allow tcp from 10.0.0.0/8 to any port 443\n"
                    "deny all from any to any"
                ),
                "tool": analyze_firewall_rules,
            },
            {
                "config_type": "iam",
                "config": (
                    '{"Version": "2012-10-17", "Statement": '
                    '[{"Effect": "Allow", "Action": "*", "Resource": "*"}]}'
                ),
                "tool": analyze_iam_policy,
            },
            {
                "config_type": "iam",
                "config": (
                    '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", '
                    '"Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::mybucket/*"}]}'
                ),
                "tool": analyze_iam_policy,
            },
            {
                "config_type": "nginx",
                "config": (
                    "server {\n"
                    "  listen 80;\n"
                    "  autoindex on;\n"
                    "  server_tokens on;\n"
                    "  client_max_body_size 0;\n"
                    "}"
                ),
                "tool": analyze_nginx_config,
            },
            {
                "config_type": "nginx",
                "config": (
                    "server {\n"
                    "  listen 443 ssl;\n"
                    "  ssl_protocols TLSv1.2 TLSv1.3;\n"
                    "  server_tokens off;\n"
                    "  client_max_body_size 10M;\n"
                    "}"
                ),
                "tool": analyze_nginx_config,
            },
            {
                "config_type": "rego",
                "config": (
                    "package example\n"
                    "default allow = true\n"
                ),
                "tool": analyze_rego_policy,
            },
            {
                "config_type": "rego",
                "config": (
                    "package example\n"
                    "default allow = false\n"
                    "allow { input.user == \"admin\" }\n"
                ),
                "tool": analyze_rego_policy,
            },
            {
                "config_type": "k8s",
                "config": (
                    "apiVersion: v1\n"
                    "kind: Pod\n"
                    "metadata:\n  name: test\n"
                    "spec:\n  containers:\n  - name: app\n    image: myapp:latest\n    securityContext:\n      runAsUser: 0\n      privileged: true\n"
                ),
                "tool": analyze_k8s_config,
            },
            {
                "config_type": "k8s",
                "config": (
                    "apiVersion: v1\n"
                    "kind: Pod\n"
                    "metadata:\n  name: test\n"
                    "spec:\n  containers:\n  - name: app\n    image: myapp:v1\n    securityContext:\n      runAsUser: 1000\n      privileged: false\n"
                ),
                "tool": analyze_k8s_config,
            },
            {
                "config_type": "code",
                "config": (
                    "import os, subprocess\n"
                    "user = input()\n"
                    "eval(user)\n"
                    "subprocess.Popen(user, shell=True)\n"
                ),
                "tool": analyze_semgrep_code,
            },
            {
                "config_type": "code",
                "config": (
                    "def safe():\n"
                    "    return 'ok'\n"
                    "print(safe())\n"
                ),
                "tool": analyze_semgrep_code,
            },
        ]

        examples = []
        for item in configs[: max_examples if max_examples else None]:
            answer = item["tool"](item["config"])
            question = f"Analyze this {item['config_type']} configuration:\n{item['config']}"
            examples.append(
                {
                    "question": question,
                    "answer": answer,
                    "config_type": item["config_type"],
                }
            )
        return Dataset.from_list(examples)

    dataset = _create_synthetic_dataset()
    parser = ConfigVerificationParser()

    tools = [
        analyze_ssh_config,
        analyze_firewall_rules,
        analyze_iam_policy,
        analyze_nginx_config,
        analyze_rego_policy,
        analyze_k8s_config,
        analyze_semgrep_code,
    ]

    rubric = vf.Rubric(
        funcs=[
            reward_correct_analysis,
            parser.get_format_reward_func(),
        ],
        weights=[1.0, 0.3],
    )

    return vf.ToolEnv(
        name="sv-env-config-verification",
        description=(
            "Audit security configuration files to identify misconfigurations and policy violations."
        ),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        tools=tools,
        system_prompt=(
            "You are a security configuration auditor. Return JSON with keys 'violations', 'patch', and 'confidence'."
        ),
    )
