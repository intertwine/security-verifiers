from __future__ import annotations

from typing import Any, Mapping, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Verifier(Protocol):
    """Minimal verifier interface placeholder.

    A concrete verifier should compute a scalar score (e.g., reward) and may
    expose auxiliary details used for diagnostics or shaping.
    """

    def score(self, input_text: str, output_text: str) -> float:
        """Return a scalar score for the given (input, output) pair."""
        ...

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information about the last verification."""
        ...


class Environment(Protocol):
    """Minimal environment interface placeholder.

    Intended to wrap one or more verifiers to evaluate model behavior and
    produce an RL signal.
    """

    def evaluate(self, input_text: str, output_text: str) -> Tuple[float, Mapping[str, Any]]:
        """Compute a (reward, info) tuple for the (input, output)."""
        ...


__all__ = ["Verifier", "Environment"]
