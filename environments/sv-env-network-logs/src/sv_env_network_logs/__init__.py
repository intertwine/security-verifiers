"""sv_env_network_logs: Security Verifiers environment for Anomaly Detection in Network Logs.

This package implements PRD Environment #1: A SingleTurnEnv where models classify
network log entries as malicious or benign. It provides a controlled setup to evaluate
an LLM's ability to interpret semi-structured log text and detect threats.
"""

from .environment import NetworkLogsEnvironment
from .verifier import NetworkLogsVerifier

__version__ = "0.1.0"
__all__ = ["NetworkLogsEnvironment", "NetworkLogsVerifier"]

def load_environment():
    """Load the Network Logs Anomaly Detection environment for use with Verifiers framework.

    Returns:
        NetworkLogsEnvironment: Configured environment ready for RL training
    """
    return NetworkLogsEnvironment()
