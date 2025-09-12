"""Utility helpers shared across environments."""

from __future__ import annotations

from typing import Any


def get_response_text(completion: Any) -> str:
    """Extract text content from a completion structure.

    The Verifiers library may return either a raw string or a list of
    message dictionaries. This helper normalizes those inputs to a plain
    string for reward functions and parsers.
    """

    if isinstance(completion, list):
        return completion[-1].get("content", "") if completion else ""
    return str(completion)


__all__ = ["get_response_text"]
