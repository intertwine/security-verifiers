"""Utility helpers shared across environments."""

from __future__ import annotations

from typing import Any


def get_response_text(completion: Any) -> str:
    """Extract text content from a completion structure.

    The Verifiers library may return either a raw string or a list of
    message dictionaries. This helper normalizes those inputs to a plain
    string for reward functions and parsers.
    """

    if completion is None:
        return ""
    if isinstance(completion, list):
        if not completion:
            return ""
        last = completion[-1]
        if isinstance(last, dict):
            content = last.get("content")
            return "" if content is None else str(content)
        return "" if last is None else str(last)
    return "" if completion is None else str(completion)


__all__ = ["get_response_text"]
