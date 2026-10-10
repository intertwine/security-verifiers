"""LLM explainer baseline."""

from __future__ import annotations


def naive_llm_explainer(_: str) -> dict[str, object]:
    """A placeholder baseline that returns no violations but claims low confidence."""

    return {"violations": [], "patch": "", "confidence": 0.1}


__all__ = ["naive_llm_explainer"]
