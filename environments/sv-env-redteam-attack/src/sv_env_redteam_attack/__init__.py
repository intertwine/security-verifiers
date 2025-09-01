"""sv_env_redteam_attack: Security Verifiers environment for Red Team Attack Simulation.

This package implements PRD Environment #3: A MultiTurnEnv where the agent learns
to probe AI systems for vulnerabilities through creative jailbreak techniques.
"""

from .main import load_environment

__version__ = "0.1.0"
__all__ = ["load_environment"]
