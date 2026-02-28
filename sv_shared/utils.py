"""Utility helpers shared across environments."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sv_shared.utils")


def get_response_text(completion: Any) -> str:
    """Extract text content from a completion structure.

    The Verifiers library may return either a raw string or a list of
    message dictionaries. This helper normalizes those inputs to a plain
    string for reward functions and parsers.
    """
    debug = os.environ.get("SV_DEBUG", "")

    if completion is None:
        if debug:
            logger.warning("[SV_DEBUG] get_response_text: completion is None")
        return ""
    if isinstance(completion, list):
        if not completion:
            if debug:
                logger.warning("[SV_DEBUG] get_response_text: completion is empty list")
            return ""
        last = completion[-1]
        if isinstance(last, dict):
            content = last.get("content")
            result = "" if content is None else str(content)
            if debug:
                logger.warning(
                    "[SV_DEBUG] get_response_text: list[dict] path | "
                    "len=%d, last_role=%s, content_type=%s, text=%.200s",
                    len(completion), last.get("role"), type(content).__name__, result,
                )
            return result
        result = "" if last is None else str(last)
        if debug:
            logger.warning(
                "[SV_DEBUG] get_response_text: list[other] path | "
                "len=%d, last_type=%s, text=%.200s",
                len(completion), type(last).__name__, result,
            )
        return result
    result = str(completion)
    if debug:
        logger.warning(
            "[SV_DEBUG] get_response_text: raw string path | "
            "type=%s, text=%.200s",
            type(completion).__name__, result,
        )
    return result


__all__ = ["get_response_text"]
