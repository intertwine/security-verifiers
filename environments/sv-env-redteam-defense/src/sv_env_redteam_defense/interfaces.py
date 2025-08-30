from __future__ import annotations

from typing import Any, Mapping, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Verifier(Protocol):
    """Minimal verifier interface placeholder for tool-use safety."""

    def score(self, action: str, observation: str) -> float: ...

    def details(self) -> Mapping[str, Any]: ...


class Environment(Protocol):
    """Wraps verifiers to compute reward and info for tool-use constraints."""

    def evaluate(self, action: str, observation: str) -> Tuple[float, Mapping[str, Any]]: ...


__all__ = ["Verifier", "Environment"]
