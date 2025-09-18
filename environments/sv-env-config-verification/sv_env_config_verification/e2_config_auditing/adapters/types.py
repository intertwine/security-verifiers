from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

E2Severity = Literal["low", "med", "high"]


@dataclass
class ToolFinding:
    """Raw finding emitted by a specific analysis tool."""

    tool: Literal["opa", "kube-linter", "semgrep"]
    rule_id: str
    severity: str
    message: str
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class Violation:
    """Normalized violation used by the environment and reward."""

    id: str
    severity: E2Severity
    message: Optional[str] = None
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    source_tool: Optional[str] = None
    native_rule_id: Optional[str] = None


@dataclass
class AuditOutput:
    """Model or baseline output after schema parsing."""

    violations: List[Violation]
    patch: Optional[str]
    confidence: float
    tools_used: Optional[List[str]] = None


__all__ = [
    "E2Severity",
    "ToolFinding",
    "Violation",
    "AuditOutput",
]
