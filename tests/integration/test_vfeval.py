"""Integration tests for vf-eval compatibility and Hub deployment.

These tests validate that Security Verifiers environments work correctly with:
- vf-eval command line interface
- Synthetic datasets (no data dependencies)
- Multi-tiered dataset loading (local → hub → synthetic)
- Prime Intellect Environments Hub

Run with: pytest tests/integration/ -v -m integration
Or: make test-integration (if implemented in Makefile)
"""

import os
import subprocess
import sys

import pytest


def run_command(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"


@pytest.mark.integration
class TestSyntheticDatasetLoading:
    """Test environments can load synthetic datasets without data dependencies."""

    def test_e1_synthetic_loading(self):
        """Test E1 can load synthetic dataset."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-network-logs')
from sv_env_network_logs import load_environment

env = load_environment(dataset_source='synthetic', max_examples=10)
assert len(env.dataset) > 0, "Synthetic dataset is empty"
print(f"✓ E1: Loaded {len(env.dataset)} synthetic examples")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E1 synthetic loading failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
        assert "Loaded" in stdout, "Expected success message not found"

    def test_e2_synthetic_loading(self):
        """Test E2 can load builtin fixtures."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-config-verification')
from sv_env_config_verification import load_environment

env = load_environment(dataset_source='synthetic', max_examples=10)
assert len(env.dataset) > 0, "Builtin fixtures are empty"
print(f"✓ E2: Loaded {len(env.dataset)} builtin fixtures")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E2 synthetic loading failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
        assert "Loaded" in stdout, "Expected success message not found"


@pytest.mark.integration
class TestDatasetSourceParameter:
    """Test dataset_source parameter works correctly."""

    def test_e1_dataset_source_auto(self):
        """Test E1 auto mode (should fall back to synthetic)."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-network-logs')
from sv_env_network_logs import load_environment

# Without local datasets or HF_TOKEN, should fall back to synthetic
env = load_environment(dataset_source='auto', max_examples=10)
assert len(env.dataset) > 0
print(f"✓ E1 auto mode: {len(env.dataset)} examples")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E1 auto mode failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"

    def test_e2_dataset_source_auto(self):
        """Test E2 auto mode (should fall back to builtin)."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-config-verification')
from sv_env_config_verification import load_environment

# Without local datasets or HF_TOKEN, should fall back to builtin
env = load_environment(dataset_source='auto', max_examples=10)
assert len(env.dataset) > 0
print(f"✓ E2 auto mode: {len(env.dataset)} examples")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E2 auto mode failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("TEST_VFEVAL"),
    reason="vf-eval tests require TEST_VFEVAL=1 and verifiers installed",
)
class TestVfEvalCompatibility:
    """Test vf-eval command line interface compatibility.

    These tests require:
    - verifiers package installed
    - Environments installed in editable mode
    - TEST_VFEVAL=1 environment variable

    Skip by default to avoid dependency on vf-eval installation.
    """

    def test_vfeval_e1_synthetic(self):
        """Test vf-eval with E1 using synthetic dataset."""
        # Note: This would require environments to be installed via pip/uv
        # and vf-eval to be available on PATH
        cmd = [
            "vf-eval",
            "sv-env-network-logs",
            "--model",
            "gpt-5-mini",
            "--num-examples",
            "3",
        ]

        # Set environment to use synthetic data
        env = os.environ.copy()
        env["DATASET_SOURCE"] = "synthetic"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )

            # Check if vf-eval is available
            if "command not found" in result.stderr or "not found" in result.stderr:
                pytest.skip("vf-eval not installed")

            assert result.returncode == 0, (
                f"vf-eval E1 failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )
        except FileNotFoundError:
            pytest.skip("vf-eval not found in PATH")

    def test_vfeval_e2_fixtures(self):
        """Test vf-eval with E2 using builtin fixtures."""
        cmd = [
            "vf-eval",
            "sv-env-config-verification",
            "--model",
            "gpt-5-mini",
            "--num-examples",
            "2",
        ]

        env = os.environ.copy()
        env["DATASET_SOURCE"] = "synthetic"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )

            if "command not found" in result.stderr or "not found" in result.stderr:
                pytest.skip("vf-eval not installed")

            assert result.returncode == 0, (
                f"vf-eval E2 failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )
        except FileNotFoundError:
            pytest.skip("vf-eval not found in PATH")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("HF_TOKEN") or not os.environ.get("TEST_HUB_LOADING"),
    reason="Hub loading tests require HF_TOKEN and TEST_HUB_LOADING=1",
)
class TestHubDatasetLoading:
    """Test loading datasets from HuggingFace Hub.

    These tests require:
    - HF_TOKEN environment variable set
    - TEST_HUB_LOADING=1 environment variable
    - Access to datasets (either intertwine's or user's repos)
    - E1_HF_REPO and E2_HF_REPO configured (optional, defaults to intertwine's)

    Skip by default to avoid requiring Hub access.
    """

    def test_e1_hub_loading(self):
        """Test E1 can load from HuggingFace Hub."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-network-logs')
from sv_env_network_logs import load_environment

env = load_environment(dataset_source='hub', max_examples=10)
assert len(env.dataset) > 0, "Hub dataset is empty"
print(f"✓ E1 Hub: Loaded {len(env.dataset)} examples")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E1 Hub loading failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
        assert "Loaded" in stdout

    def test_e2_hub_loading(self):
        """Test E2 can load from HuggingFace Hub."""
        code = """
import sys
sys.path.insert(0, 'environments/sv-env-config-verification')
from sv_env_config_verification import load_environment

env = load_environment(dataset_source='hub', max_examples=10)
assert len(env.dataset) > 0, "Hub dataset is empty"
print(f"✓ E2 Hub: Loaded {len(env.dataset)} examples")
"""
        returncode, stdout, stderr = run_command([sys.executable, "-c", code])
        assert returncode == 0, f"E2 Hub loading failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
        assert "Loaded" in stdout


if __name__ == "__main__":
    # Allow running tests directly for quick validation
    pytest.main([__file__, "-v", "-m", "integration"])
