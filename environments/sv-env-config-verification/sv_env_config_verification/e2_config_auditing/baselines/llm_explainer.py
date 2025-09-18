from __future__ import annotations

from typing import Dict


def naive_llm_explainer(fixture: str) -> Dict[str, object]:
    """A placeholder baseline that returns no violations but claims low confidence."""

    return {"violations": [], "patch": "", "confidence": 0.1}


__all__ = ["naive_llm_explainer"]
