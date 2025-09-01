"""sv_env_config_verification: Security Verifiers environment for Security Configuration Verification.

This package implements PRD Environment #2: A ToolEnv where models audit security
configuration files to identify misconfigurations or policy violations.
"""

from .main import load_environment

__version__ = "0.1.0"
__all__ = ["load_environment"]
