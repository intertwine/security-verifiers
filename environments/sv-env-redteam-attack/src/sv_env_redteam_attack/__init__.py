"""sv_env_redteam_attack: Security Verifiers environment for Red-Teaming Simulator.

This package implements PRD Environment #3: A MultiTurnEnv where the agent plays the role
of an adversary probing an AI system for weaknesses. The goal is to elicit unsafe or
disallowed outputs from the simulated target model through creative jailbreak techniques.
"""

from .environment import RedTeamAttackEnvironment
from .verifier import RedTeamAttackVerifier

__version__ = "0.1.0"
__all__ = ["RedTeamAttackEnvironment", "RedTeamAttackVerifier"]

def load_environment():
    """Load the Red-Team Attack environment for use with Verifiers framework.

    Returns:
        RedTeamAttackEnvironment: Configured environment ready for RL training
    """
    return RedTeamAttackEnvironment()
