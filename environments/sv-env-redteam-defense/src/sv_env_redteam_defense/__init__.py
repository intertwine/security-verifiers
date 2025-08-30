"""sv_env_redteam_defense: Security Verifiers environment for Interactive Red-Teaming.

This package implements PRD Environment #6: A MultiTurnEnv that simulates an ongoing
interaction between a user with potentially malicious requests and an AI assistant.
The goal is to train the assistant (agent) to respond safely under attack while
maintaining helpfulness and refusing harmful requests.
"""

from .environment import RedTeamDefenseEnvironment
from .verifier import RedTeamDefenseVerifier

__version__ = "0.1.0"
__all__ = ["RedTeamDefenseEnvironment", "RedTeamDefenseVerifier"]

def load_environment():
    """Load the Red-Team Defense environment for use with Verifiers framework.

    Returns:
        RedTeamDefenseEnvironment: Configured environment ready for RL training
    """
    return RedTeamDefenseEnvironment()
