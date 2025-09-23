"""Generate oracle violations for Kubernetes and Terraform manifests."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from adapters.kubelinter_adapter import kubelinter_lint
from adapters.opa_adapter import opa_eval
from adapters.semgrep_adapter import semgrep_scan
from mapping import normalize_findings, to_prd_schema


def build_oracle_for_k8s(paths: Sequence[str]) -> list[dict]:
    """Generate oracle violations for Kubernetes manifests."""

    findings = kubelinter_lint(paths)
    return to_prd_schema(normalize_findings(findings))


def build_oracle_for_tf(paths: Sequence[str], semgrep_rules: Sequence[str] | str = ("p/ci",)) -> list[dict]:
    """Generate oracle violations for Terraform files using semgrep."""

    findings = semgrep_scan(paths, rules=semgrep_rules)
    return to_prd_schema(normalize_findings(findings))


def build_oracle_with_opa(input_data: str | Dict[str, Any], policy_paths: Sequence[str]) -> list[dict]:
    """Example helper for org-specific OPA policies."""

    findings = opa_eval(input_data, policy_paths)
    return to_prd_schema(normalize_findings(findings))


def load_golden_oracle(path: str) -> list:
    """Load golden oracle violations from a JSON file."""
    import json
    from adapters.types import Violation

    with open(path, "r") as f:
        data = json.load(f)

    return [Violation(id=v["id"], severity=v["severity"]) for v in data]


__all__ = [
    "build_oracle_for_k8s",
    "build_oracle_for_tf",
    "build_oracle_with_opa",
    "load_golden_oracle",
]
