from __future__ import annotations

from typing import Any, Mapping, Tuple

from .interfaces import Environment as EnvironmentProtocol
from .interfaces import Verifier as VerifierProtocol


class NetworkSafetyVerifier(VerifierProtocol):
    """Placeholder verifier for outbound network request safety."""

    def score(self, request: str, response: str) -> float:  # noqa: D401
        """Compute a scalar safety score for (request, response)."""
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:  # noqa: D401
        """Return auxiliary information from the last verification."""
        raise NotImplementedError


class NetworkSafetyEnvironment(EnvironmentProtocol):
    """Placeholder environment that aggregates verifiers to produce RL signal."""

    def evaluate(self, request: str, response: str) -> Tuple[float, Mapping[str, Any]]:  # noqa: D401
        """Compute a (reward, info) tuple for the (request, response)."""
        raise NotImplementedError

