from __future__ import annotations

from typing import Any, Mapping, Tuple

from .interfaces import Environment as EnvironmentProtocol
from .interfaces import Verifier as VerifierProtocol


class PromptInjectionVerifier(VerifierProtocol):
    """Placeholder verifier for prompt-injection and jailbreak resilience."""

    def score(self, input_text: str, output_text: str) -> float:  # noqa: D401
        """Compute a scalar score for the (input, output) pair."""
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:  # noqa: D401
        """Return auxiliary information from the last verification."""
        raise NotImplementedError


class PromptInjectionEnvironment(EnvironmentProtocol):
    """Placeholder environment that aggregates verifiers to produce RL signal."""

    def evaluate(self, input_text: str, output_text: str) -> Tuple[float, Mapping[str, Any]]:  # noqa: D401
        """Compute a (reward, info) tuple for the (input, output)."""
        raise NotImplementedError

