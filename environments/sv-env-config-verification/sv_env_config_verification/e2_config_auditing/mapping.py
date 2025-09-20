"""Mapping between tool-specific findings and the common :class:`Violation` schema."""

from __future__ import annotations

from typing import List

from .adapters.types import E2Severity, ToolFinding, Violation

TOOL_SEV_TO_E2: dict[str, dict[str, E2Severity]] = {
    "semgrep": {"INFO": "low", "WARNING": "med", "ERROR": "high"},
    "kube-linter": {"Info": "low", "Warning": "med", "Error": "high"},
    "opa": {"low": "low", "medium": "med", "med": "med", "high": "high"},
}


def normalize_findings(findings: List[ToolFinding]) -> List[Violation]:
    """Map tool-specific findings to the common :class:`Violation` schema."""

    out: List[Violation] = []
    for f in findings:
        sev_map = TOOL_SEV_TO_E2.get(f.tool, {})
        e2_sev = sev_map.get((f.severity or "").strip(), "med")
        out.append(
            Violation(
                id=f"{f.tool}/{f.rule_id}",
                severity=e2_sev,
                message=f.message,
                file=f.file,
                start_line=f.start_line,
                end_line=f.end_line,
                source_tool=f.tool,
                native_rule_id=f.rule_id,
            )
        )
    return out


def to_prd_schema(violations: List[Violation]) -> list[dict]:
    """Reduce :class:`Violation` objects to PRD-mandated dict form."""

    return [{"id": v.id, "severity": v.severity} for v in violations]


__all__ = [
    "TOOL_SEV_TO_E2",
    "normalize_findings",
    "to_prd_schema",
]
