"""Tests for the OPA adapter."""

import json
from pathlib import Path

import pytest

from ..adapters.opa_adapter import OPAError, opa_eval


class TestOPAAdapter:
    """Test the OPA adapter."""

    def test_opa_eval_with_kubernetes_policy(self):
        """Test OPA evaluation with a Kubernetes policy."""
        # Create a simple Kubernetes Pod with security issues
        k8s_pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test-pod", "namespace": "default"},
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "nginx:latest",
                        "securityContext": {
                            "privileged": True,  # Security issue
                            "capabilities": {
                                "add": ["SYS_ADMIN"]  # Security issue
                            },
                        },
                    }
                ]
            },
        }

        policy_dir = Path(__file__).resolve().parents[1] / "policies"
        policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

        findings = opa_eval(k8s_pod, policy_paths)

        # Should find at least the privileged container violation
        assert len(findings) > 0
        assert any(f.rule_id == "K8S_002" for f in findings), "Should detect privileged container"
        assert any(f.severity in ["HIGH", "CRITICAL"] for f in findings)

    def test_opa_eval_with_clean_config(self):
        """Test OPA evaluation with a clean configuration."""
        clean_pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "clean-pod", "namespace": "production"},
            "spec": {
                "containers": [
                    {
                        "name": "app",
                        "image": "myapp:v1.0.0",
                        "resources": {"limits": {"memory": "256Mi", "cpu": "500m"}},
                    }
                ]
            },
        }

        policy_dir = Path(__file__).resolve().parents[1] / "policies"
        policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

        findings = opa_eval(clean_pod, policy_paths)

        # Should have fewer or no findings
        assert len(findings) == 0 or all(f.severity != "CRITICAL" for f in findings)

    def test_opa_eval_with_invalid_binary(self):
        """Test OPA evaluation with an invalid binary path."""
        with pytest.raises(OPAError):
            opa_eval({"test": "data"}, ["some_policy.rego"], opa_bin="/nonexistent/opa")

    def test_opa_eval_with_json_input_string(self):
        """Test OPA evaluation with JSON string input."""
        k8s_service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "test-service"},
            "spec": {
                "ports": [{"port": 22, "targetPort": 22}]  # SSH port
            },
        }

        policy_dir = Path(__file__).resolve().parents[1] / "policies"
        policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

        # Test with JSON string input
        findings = opa_eval(json.dumps(k8s_service), policy_paths)

        # Should detect exposed SSH port
        assert any(f.rule_id == "K8S_004" for f in findings), "Should detect exposed sensitive port"

    def test_opa_eval_finding_structure(self):
        """Test that OPA findings have the expected structure."""
        k8s_pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test-pod"},
            "spec": {"containers": [{"name": "test", "image": "nginx", "securityContext": {"privileged": True}}]},
        }

        policy_dir = Path(__file__).resolve().parents[1] / "policies"
        policy_paths = [str(policy_dir / "lib.rego"), str(policy_dir / "kubernetes_security.rego")]

        findings = opa_eval(k8s_pod, policy_paths)
        assert len(findings) > 0

        # Check finding structure
        finding = findings[0]
        assert finding.tool == "opa"
        assert finding.rule_id
        assert finding.severity
        assert finding.message
        assert finding.extra is not None
