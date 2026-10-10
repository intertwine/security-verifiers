"""Schema for model output."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field

from adapters.types import E2Severity, Violation


class ViolationModel(BaseModel):
    """Violation model."""

    id: str
    severity: str = Field(pattern="^(low|med|high)$")


class AuditOutputModel(BaseModel):
    """Audit output model."""

    violations: list[ViolationModel]
    patch: str | None = ""
    confidence: float


def parse_model_output(
    model_json: dict[str, Any],
) -> tuple[list[Violation], str | None, float]:
    """Validate model output against the PRD schema."""

    parsed = AuditOutputModel.model_validate(model_json)
    violations = [Violation(id=v.id, severity=cast(E2Severity, v.severity)) for v in parsed.violations]
    return violations, parsed.patch, parsed.confidence


__all__ = ["AuditOutputModel", "ViolationModel", "parse_model_output"]
