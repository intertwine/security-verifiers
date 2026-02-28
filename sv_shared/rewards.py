"""Shared reward functions for classification environments."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sv_shared.rewards")

# Counter to limit debug spam (log first N per function)
_debug_counter: dict[str, int] = {}
_DEBUG_LOG_LIMIT = 10


def _should_debug_log(func_name: str) -> bool:
    """Rate-limit debug logging to first N calls per function."""
    debug = os.environ.get("SV_DEBUG", "")
    if not debug:
        return False
    count = _debug_counter.get(func_name, 0)
    _debug_counter[func_name] = count + 1
    return count < _DEBUG_LOG_LIMIT


def _coerce_answer(answer: Any) -> str:
    """Coerce answer to string, handling ClassLabel ints from Hub datasets."""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, int):
        # ClassLabel: 0 = Benign, 1 = Malicious (E1 convention)
        logger.warning(
            "[SV_DEBUG] _coerce_answer: got int answer=%d, coercing to string", answer
        )
        return "Malicious" if answer == 1 else "Benign"
    if isinstance(answer, bool):
        return "Malicious" if answer else "Benign"
    return str(answer)


def _extract(parser, completion: Any) -> tuple[str, float]:  # noqa: ANN001
    """Helper to extract parsed label and confidence."""

    label = parser.parse_answer(completion)
    confidence = parser.parse_confidence(completion)
    return label, confidence


def reward_accuracy(
    *,
    completion: Any,
    answer: Any,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Binary accuracy reward for classification."""

    answer = _coerce_answer(answer)
    predicted, _ = _extract(parser, completion)
    result = 0.0
    if predicted and answer:
        result = 1.0 if predicted.lower() == answer.lower() else 0.0

    if _should_debug_log("reward_accuracy"):
        logger.warning(
            "[SV_DEBUG] reward_accuracy: predicted=%r, answer=%r (type=%s), "
            "completion_type=%s, result=%.1f",
            predicted, answer, type(answer).__name__,
            type(completion).__name__, result,
        )
    return result


def reward_calibration(
    *,
    completion: Any,
    answer: Any,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Calibration reward based on absolute error."""

    answer = _coerce_answer(answer)
    predicted, conf = _extract(parser, completion)
    if not predicted:
        result = 0.0
    else:
        correct = 1.0 if predicted.lower() == answer.lower() else 0.0
        result = 1.0 - abs(conf - correct)

    if _should_debug_log("reward_calibration"):
        logger.warning(
            "[SV_DEBUG] reward_calibration: predicted=%r, conf=%.2f, "
            "answer=%r, result=%.2f",
            predicted, conf if predicted else 0.0, answer, result,
        )
    return result


def reward_asymmetric_cost(
    *,
    completion: Any,
    answer: Any,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Penalize false negatives more than false positives."""

    answer = _coerce_answer(answer)
    predicted, _ = _extract(parser, completion)
    if not predicted or not answer:
        result = 0.0
    elif predicted.lower() == answer.lower():
        result = 1.0
    elif predicted.lower() == "benign" and answer.lower() == "malicious":
        result = -1.0
    else:
        result = 0.0

    if _should_debug_log("reward_asymmetric_cost"):
        logger.warning(
            "[SV_DEBUG] reward_asymmetric_cost: predicted=%r, answer=%r, result=%.1f",
            predicted, answer, result,
        )
    return result


__all__ = [
    "reward_accuracy",
    "reward_calibration",
    "reward_asymmetric_cost",
]
