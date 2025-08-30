from __future__ import annotations

from typing import Any, Mapping, Tuple

from .interfaces import Environment as EnvironmentProtocol
from .interfaces import Verifier as VerifierProtocol


class CodeExecSafetyVerifier(VerifierProtocol):
    """Placeholder verifier for generated-code execution safety."""

    def score(self, code: str, execution_log: str) -> float:  # noqa: D401
        """Compute a scalar safety score for (code, execution_log)."""
        raise NotImplementedError

    def details(self) -> Mapping[str, Any]:  # noqa: D401
        """Return auxiliary information from the last verification."""
        raise NotImplementedError


class CodeExecSafetyEnvironment(EnvironmentProtocol):
    """Placeholder environment that aggregates verifiers to produce RL signal."""

    def evaluate(self, code: str, execution_log: str) -> Tuple[float, Mapping[str, Any]]:  # noqa: D401
        """Compute a (reward, info) tuple for the (code, execution_log)."""
        raise NotImplementedError

