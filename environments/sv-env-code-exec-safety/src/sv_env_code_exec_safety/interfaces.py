from __future__ import annotations

from typing import Any, Mapping, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Verifier(Protocol):
    """Minimal verifier interface placeholder for code-exec safety."""

    def score(self, code: str, execution_log: str) -> float:
        ...

    def details(self) -> Mapping[str, Any]:
        ...


class Environment(Protocol):
    """Wraps verifiers to compute reward and info for safe code execution."""

    def evaluate(self, code: str, execution_log: str) -> Tuple[float, Mapping[str, Any]]:
        ...


__all__ = ["Verifier", "Environment"]

