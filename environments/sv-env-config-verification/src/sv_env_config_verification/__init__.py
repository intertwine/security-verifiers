"""sv_env_config_verification: Security Verifiers environment for Security Policy Verification.

This package implements PRD Environment #2: A ToolEnv where models audit security
configuration files (system configs, cloud policies, etc.) to identify misconfigurations
or policy violations. The model can invoke analysis tools to parse or test configs.
"""

from .environment import ConfigVerificationEnvironment
from .verifier import ConfigVerificationVerifier

__version__ = "0.1.0"
__all__ = ["ConfigVerificationEnvironment", "ConfigVerificationVerifier"]


def load_environment():
    """Load the Config Verification environment for use with Verifiers framework.

    Returns:
        ConfigVerificationEnvironment: Configured environment ready for RL training
    """
    return ConfigVerificationEnvironment()
