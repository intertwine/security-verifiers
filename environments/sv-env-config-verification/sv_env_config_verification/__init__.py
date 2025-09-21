"""Tool-grounded configuration auditing environment (E2).

This package wraps the :mod:`e2_config_auditing` module and exposes it as a
`verifiers` environment. Models receive raw Kubernetes or Terraform
configuration files, optionally call analysis tools, and must return a JSON
object with violations, an optional patch, and a confidence score.
"""

from __future__ import annotations

import json

# Allow importing shared utilities when developing from the repo
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import verifiers as vf
import yaml  # noqa: F401 - used in run_opa function
from datasets import Dataset
from pydantic import BaseModel, ConfigDict

# Ensure repository root is on sys.path so `sv_shared` is importable when running from source
# __file__ .../environments/sv-env-config-verification/sv_env_config_verification/__init__.py
# parents[3] points to the repository root
sys.path.append(str(Path(__file__).resolve().parents[3]))

from sv_shared import (  # type: ignore  # pylint: disable=wrong-import-position
    RolloutLogger,
    get_response_text,
)

# pylint: disable=wrong-import-position
from .e2_config_auditing.adapters.kubelinter_adapter import kubelinter_lint
from .e2_config_auditing.adapters.opa_adapter import opa_eval
from .e2_config_auditing.adapters.semgrep_adapter import semgrep_scan
from .e2_config_auditing.adapters.types import Violation
from .e2_config_auditing.mapping import normalize_findings
from .e2_config_auditing.patching import try_apply_patch
from .e2_config_auditing.reward import final_reward
from .e2_config_auditing.schema import parse_model_output


# Pydantic model for tool finding dictionaries
class ToolFindingModel(BaseModel):
    """Pydantic model for tool finding dictionaries."""

    tool: Literal["opa", "kube-linter", "semgrep"]
    rule_id: str
    severity: str
    message: str
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


DATASET_ROOT = Path(__file__).resolve().parent / "e2_config_auditing" / "dataset"


def run_kubelinter(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``kubelinter_lint`` as a simple tool."""

    findings = []
    for f in kubelinter_lint(paths):
        # Create dict without extra field to avoid schema issues
        finding_dict = {
            "tool": f.tool,
            "rule_id": f.rule_id,
            "severity": f.severity,
            "message": f.message,
            "file": f.file,
            "start_line": f.start_line,
            "end_line": f.end_line,
        }
        findings.append(finding_dict)
    return findings


def run_semgrep(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``semgrep_scan`` as a simple tool."""

    findings = []
    for f in semgrep_scan(paths):
        # Create dict without extra field to avoid schema issues
        finding_dict = {
            "tool": f.tool,
            "rule_id": f.rule_id,
            "severity": f.severity,
            "message": f.message,
            "file": f.file,
            "start_line": f.start_line,
            "end_line": f.end_line,
        }
        findings.append(finding_dict)
    return findings


def run_opa(paths: List[str]) -> List[Dict[str, Any]]:
    """Expose ``opa_eval`` as a simple tool for configuration files."""

    findings = []
    policy_dir = Path(__file__).resolve().parent / "e2_config_auditing" / "policies"

    for file_path in paths:
        # Read the configuration file
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Determine file type and select appropriate policies
            if file_path.endswith((".yaml", ".yml")):
                # Kubernetes YAML - parse to JSON for OPA
                import yaml

                data = yaml.safe_load(content)
                policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]
            elif file_path.endswith(".tf"):
                # Terraform - would need HCL parser, skip for now
                continue
            else:
                # Try as JSON
                data = json.loads(content)
                policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

            # Run OPA evaluation
            file_findings = opa_eval(data, policy_paths)
            for f in file_findings:
                # Create dict without extra field to avoid schema issues
                finding_dict = {
                    "tool": f.tool,
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "message": f.message,
                    "file": f.file or file_path,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                }
                findings.append(finding_dict)
        except Exception:
            # Skip files that can't be parsed
            continue

    return findings


class ConfigVerificationParser(vf.Parser):
    """Parser validating the PRD JSON schema."""

    def parse_answer(self, completion: Any) -> Dict[str, Any]:
        text = get_response_text(completion)
        try:
            data = json.loads(text)
            violations, patch, confidence = parse_model_output(data)
        except (json.JSONDecodeError, ValueError):  # pragma: no cover - defensive
            return {}
        return {
            "violations": [v.__dict__ for v in violations],
            "patch": patch or "",
            "confidence": confidence,
        }

    def get_format_reward_func(self):  # pragma: no cover - simple
        def format_reward(completion, answer="", **kwargs):  # pylint: disable=unused-argument
            text = get_response_text(completion)
            try:
                data = json.loads(text)
                parse_model_output(data)
            except (json.JSONDecodeError, ValueError):
                return 0.0
            return 1.0

        return format_reward


# pylint: disable=unused-argument
def reward_config_auditing(
    completion,
    answer: Dict[str, Any] | str | None = None,
    **kwargs: Dict[str, Any],
) -> float:
    """Reward combining detection accuracy and patch verification.

    In recent verifiers releases, datasets often store `answer` as a string.
    Accept both dict and JSON string forms for compatibility.
    """

    text = get_response_text(completion)
    try:
        data = json.loads(text)
        violations_pred, patch, _ = parse_model_output(data)
    except (json.JSONDecodeError, ValueError, KeyError):
        return 0.0

    # Normalize answer to a dict
    answer_obj: Dict[str, Any] = {}
    if isinstance(answer, str):
        try:
            answer_obj = json.loads(answer)
        except json.JSONDecodeError:
            answer_obj = {}
    elif isinstance(answer, dict):
        answer_obj = answer

    oracle_dicts = (answer_obj or {}).get("oracle", [])
    oracle = [Violation(id=v["id"], severity=v["severity"]) for v in oracle_dicts]

    post: List[Violation] | None = None
    if patch:
        fixture_path = (answer_obj or {}).get("fixture_path", "")
        fixture_type = (answer_obj or {}).get("fixture_type", "k8s")
        applied, new_text = try_apply_patch(fixture_path, patch)
        if applied:
            with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
                tmp.write(new_text)
                tmp_path = tmp.name
            if fixture_type == "k8s":
                post_findings = kubelinter_lint([tmp_path])
            else:
                post_findings = semgrep_scan([tmp_path])
            post = normalize_findings(post_findings)
            Path(tmp_path).unlink(missing_ok=True)

    return final_reward(violations_pred, oracle, post_patch=post)


def _load_examples(max_examples: int | None = None) -> List[Dict[str, Any]]:
    fixtures = [
        {
            "type": "k8s",
            "path": DATASET_ROOT / "fixtures" / "k8s" / "bad_pod.yaml",
            "oracle": DATASET_ROOT / "oracle" / "bad_pod.json",
        },
        {
            "type": "tf",
            "path": DATASET_ROOT / "fixtures" / "tf" / "bad.tf",
            "oracle": DATASET_ROOT / "oracle" / "bad_tf.json",
        },
    ]
    items: List[Dict[str, Any]] = []
    for item in fixtures[: max_examples if max_examples else None]:
        question = Path(item["path"]).read_text(encoding="utf-8")
        oracle = json.loads(Path(item["oracle"]).read_text(encoding="utf-8"))
        answer_obj = {
            "oracle": oracle,
            "fixture_path": str(item["path"]),
            "fixture_type": item["type"],
        }
        # Store answer as JSON string for compatibility with recent verifiers schemas
        items.append({"question": question, "answer": json.dumps(answer_obj)})
    return items


def load_environment(
    dataset_name: str = "builtin",  # pylint: disable=unused-argument
    max_examples: int = 100,
    logger: RolloutLogger | None = None,
    include_tools: bool = True,
) -> vf.ToolEnv:
    """Load the configuration auditing environment.

    Args:
        dataset_name: Placeholder dataset name for compatibility.
        max_examples: Maximum number of fixtures to surface in the dataset.
        logger: Optional rollout logger to capture dataset metadata.
        include_tools: Whether to include security tools (can be disabled for testing).
    """

    dataset = Dataset.from_list(_load_examples(max_examples))
    parser = ConfigVerificationParser()
    rubric = vf.Rubric(
        funcs=[reward_config_auditing, parser.get_format_reward_func()],
        weights=[1.0, 0.05],
    )
    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name="sv-env-config-verification",
            dataset_name=dataset_name,
            total_examples=len(dataset),
            metadata={"max_examples": max_examples, "fixture_root": str(DATASET_ROOT)},
        )

    return vf.ToolEnv(
        name="sv-env-config-verification",
        description=("Audit Kubernetes and Terraform configurations using pinned tool outputs."),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        # Expose only tools whose schemas convert cleanly to strict JSON schema for tool calling
        tools=[run_kubelinter, run_semgrep, run_opa] if include_tools else [],
        system_prompt=(
            "You are a security auditor for Kubernetes and Terraform configurations.\n\n"
            "If tools are available, you may use:\n"
            "- run_kubelinter: Analyze Kubernetes YAML files for security issues\n"
            "- run_semgrep: Scan Terraform and other files for security patterns\n"
            "- run_opa: Evaluate configurations against Open Policy Agent security policies\n\n"
            "For Kubernetes, check for violations like:\n"
            "- kube-linter/run-as-non-root (containers running as root)\n"
            "- kube-linter/latest-tag (using :latest image tags)\n"
            "- kube-linter/no-read-only-root-fs (writable root filesystem)\n"
            "- kube-linter/unset-cpu-requirements (missing CPU limits/requests)\n"
            "- kube-linter/unset-memory-requirements (missing memory limits/requests)\n"
            "- kube-linter/privilege-escalation-container (allowPrivilegeEscalation)\n"
            "- kube-linter/non-existent-service-account (invalid service account)\n"
            "- opa/GEN_001, opa/GEN_002 (OPA policy violations)\n\n"
            "For Terraform, be conservative - only flag clear security issues.\n\n"
            "Return a JSON object with exactly these fields:\n"
            "- violations: array of objects, each with 'id' (string like 'tool/rule-id'), "
            "'severity' ('low', 'med', or 'high')\n"
            "- patch: string containing a unified diff (optional, can be empty string)\n"
            "- confidence: float between 0 and 1\n\n"
            "Example:\n"
            "{\n"
            '  "violations": [\n'
            '    {"id": "kube-linter/run-as-non-root", "severity": "med"},\n'
            '    {"id": "kube-linter/latest-tag", "severity": "med"},\n'
            '    {"id": "opa/GEN_001", "severity": "med"}\n'
            "  ],\n"
            '  "patch": "",\n'
            '  "confidence": 0.9\n'
            "}"
        ),
    )


__all__ = [
    "ConfigVerificationParser",
    "reward_config_auditing",
    "load_environment",
]
