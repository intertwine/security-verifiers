from __future__ import annotations

from typing import Any, Mapping, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Verifier(Protocol):
    """Minimal verifier interface placeholder for network safety."""

    def score(self, request: str, response: str) -> float: ...

    def details(self) -> Mapping[str, Any]: ...


class Environment(Protocol):
    """Wraps verifiers to compute reward and info for network egress safety."""

    def evaluate(self, request: str, response: str) -> Tuple[float, Mapping[str, Any]]: ...


__all__ = ["Verifier", "Environment"]
