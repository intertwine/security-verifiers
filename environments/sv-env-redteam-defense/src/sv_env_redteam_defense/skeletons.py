from __future__ import annotations

from typing import Any, Mapping, Tuple

from .interfaces import Environment as EnvironmentProtocol
from .interfaces import Verifier as VerifierProtocol


class ToolUseSafetyVerifier(VerifierProtocol):
    """Placeholder verifier for safe external tool/action usage."""

    def score(self, action: str, observation: str) -> float:  # noqa: D401
        """Compute a scalar score for (action, observation)."""
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:  # noqa: D401
        """Return auxiliary information from the last verification."""
        raise NotImplementedError


class ToolUseSafetyEnvironment(EnvironmentProtocol):
    """Placeholder environment that aggregates verifiers to produce RL signal."""

    def evaluate(self, action: str, observation: str) -> Tuple[float, Mapping[str, Any]]:  # noqa: D401
        """Compute a (reward, info) tuple for the (action, observation)."""
        raise NotImplementedError
