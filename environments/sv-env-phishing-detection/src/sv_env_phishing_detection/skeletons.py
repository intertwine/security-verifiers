from __future__ import annotations

from typing import Any, Mapping, Tuple

from .interfaces import Environment as EnvironmentProtocol
from .interfaces import Verifier as VerifierProtocol


class SecretsLeakageVerifier(VerifierProtocol):
    """Placeholder verifier for secrets leakage prevention and redaction."""

    def score(self, input_text: str, output_text: str) -> float:  # noqa: D401
        """Compute a scalar score for leakage risk in (input, output)."""
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:  # noqa: D401
        """Return auxiliary information from the last verification."""
        raise NotImplementedError


class SecretsLeakageEnvironment(EnvironmentProtocol):
    """Placeholder environment that aggregates verifiers to produce RL signal."""

    def evaluate(self, input_text: str, output_text: str) -> Tuple[float, Mapping[str, Any]]:  # noqa: D401
        """Compute a (reward, info) tuple for the (input, output)."""
        raise NotImplementedError
