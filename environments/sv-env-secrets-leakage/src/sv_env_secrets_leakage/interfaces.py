from __future__ import annotations

from typing import Any, Mapping, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Verifier(Protocol):
    """Minimal verifier interface placeholder for secrets-leakage checks."""

    def score(self, input_text: str, output_text: str) -> float:
        ...

    def details(self) -> Mapping[str, Any]:
        ...


class Environment(Protocol):
    """Wraps verifiers to compute reward and info for leakage prevention."""

    def evaluate(self, input_text: str, output_text: str) -> Tuple[float, Mapping[str, Any]]:
        ...


__all__ = ["Verifier", "Environment"]

