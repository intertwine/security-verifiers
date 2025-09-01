"""sv_env_phishing_detection: Security Verifiers environment for Phishing Email Detection.

This package implements PRD Environment #4: A SingleTurnEnv where models classify
emails as phishing attempts or legitimate emails. The environment provides email text
as prompts and expects classification labels as outputs.
"""

from .main import load_environment

__version__ = "0.1.0"
__all__ = ["load_environment"]
