"""Test that normalize_findings and to_prd_schema work as expected."""

from sv_env_config_verification.e2_config_auditing.adapters.types import ToolFinding
from sv_env_config_verification.e2_config_auditing.mapping import (
    normalize_findings,
    to_prd_schema,
)


def test_normalize_and_prd_schema() -> None:
    """Test that normalize_findings and to_prd_schema work as expected."""
    findings = [
        ToolFinding(
            tool="kube-linter",
            rule_id="run-as-non-root",
            severity="Error",
            message="msg",
        )
    ]
    violations = normalize_findings(findings)
    assert violations[0].id == "kube-linter/run-as-non-root"
    assert violations[0].severity == "high"
    prd = to_prd_schema(violations)
    assert prd == [{"id": "kube-linter/run-as-non-root", "severity": "high"}]
