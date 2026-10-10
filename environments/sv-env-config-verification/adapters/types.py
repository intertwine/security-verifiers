"""Adapters for different analysis tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

E2Severity = Literal["low", "med", "high"]


@dataclass
class ToolFinding:
    """Raw finding emitted by a specific analysis tool."""

    tool: Literal["opa", "kube-linter", "semgrep"]
    rule_id: str
    severity: str
    message: str
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    extra: dict[str, Any] | None = None


@dataclass
class Violation:
    """Normalized violation used by the environment and reward."""

    id: str
    severity: E2Severity
    message: str | None = None
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    source_tool: str | None = None
    native_rule_id: str | None = None


@dataclass
class AuditOutput:
    """Model or baseline output after schema parsing."""

    violations: list[Violation]
    patch: str | None
    confidence: float
    tools_used: list[str] | None = None


__all__ = [
    "AuditOutput",
    "E2Severity",
    "ToolFinding",
    "Violation",
]
