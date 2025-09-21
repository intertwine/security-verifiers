"""Shared reward functions for classification environments."""

from __future__ import annotations

from typing import Any

from .utils import get_response_text


def _extract(parser, completion: Any) -> tuple[str, float]:  # noqa: ANN001
    """Helper to extract parsed label and confidence."""

    text = get_response_text(completion)
    label = parser.parse_answer(text)
    confidence = parser.parse_confidence(text)
    return label, confidence


def reward_accuracy(
    *,
    completion: Any,
    answer: str,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Binary accuracy reward for classification."""

    predicted, _ = _extract(parser, completion)
    if not predicted or not answer:
        return 0.0
    return 1.0 if predicted.lower() == answer.lower() else 0.0


def reward_calibration(
    *,
    completion: Any,
    answer: str,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Calibration reward based on absolute error."""

    predicted, conf = _extract(parser, completion)
    if not predicted:
        return 0.0
    correct = 1.0 if predicted.lower() == answer.lower() else 0.0
    return 1.0 - abs(conf - correct)


def reward_asymmetric_cost(
    *,
    completion: Any,
    answer: str,
    parser,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Penalize false negatives more than false positives."""

    predicted, _ = _extract(parser, completion)
    if not predicted or not answer:
        return 0.0
    if predicted.lower() == answer.lower():
        return 1.0
    if predicted.lower() == "benign" and answer.lower() == "malicious":
        return -1.0
    return 0.0


__all__ = [
    "reward_accuracy",
    "reward_calibration",
    "reward_asymmetric_cost",
]
