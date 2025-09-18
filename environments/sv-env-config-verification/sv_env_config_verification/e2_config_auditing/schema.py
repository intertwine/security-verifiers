from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

from .adapters.types import Violation


class ViolationModel(BaseModel):
    id: str
    severity: str = Field(pattern="^(low|med|high)$")


class AuditOutputModel(BaseModel):
    violations: List[ViolationModel]
    patch: str | None = ""
    confidence: float


def parse_model_output(model_json: Dict[str, Any]) -> Tuple[List[Violation], str | None, float]:
    """Validate model output against the PRD schema."""

    parsed = AuditOutputModel.model_validate(model_json)
    violations = [Violation(id=v.id, severity=v.severity) for v in parsed.violations]
    return violations, parsed.patch, parsed.confidence


__all__ = ["parse_model_output", "AuditOutputModel", "ViolationModel"]
