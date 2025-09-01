"""sv_env_redteam_defense: Security Verifiers environment for Red Team Defense.

This package implements PRD Environment #6: A MultiTurnEnv where the model learns
to defend against adversarial prompts while maintaining helpfulness.
"""

from .main import load_environment

__version__ = "0.1.0"
__all__ = ["load_environment"]
