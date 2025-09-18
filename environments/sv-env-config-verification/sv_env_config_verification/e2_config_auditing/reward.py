from __future__ import annotations

from typing import List, Tuple

from .adapters.types import Violation

SEV_WEIGHT = {"low": 0.3, "med": 0.6, "high": 1.0}


def score_detection(pred: List[Violation], oracle: List[Violation]) -> Tuple[float, float, float]:
    """Weighted precision/recall/F1 based on violation IDs."""

    o_ids = {v.id: SEV_WEIGHT[v.severity] for v in oracle}
    p_ids = {v.id: SEV_WEIGHT[v.severity] for v in pred}
    tp = sum(SEV_WEIGHT[v.severity] for v in pred if v.id in o_ids)
    fp = sum(SEV_WEIGHT[v.severity] for v in pred if v.id not in o_ids)
    fn = sum(w for vid, w in o_ids.items() if vid not in p_ids)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def score_patch_delta(oracle: List[Violation], post: List[Violation]) -> float:
    """Weighted count of oracle violations removed after patch application."""

    o = {v.id: SEV_WEIGHT[v.severity] for v in oracle}
    p = {v.id for v in post}
    return sum(w for vid, w in o.items() if vid not in p)


def final_reward(
    pred: List[Violation],
    oracle: List[Violation],
    patch_removed_weight: float = 1.0,
    format_bonus: float = 0.05,
    invalid_penalty: float = -0.25,
    had_valid_json: bool = True,
    post_patch: List[Violation] | None = None,
) -> float:
    """Compute final reward in range [-1, 2]."""

    _prec, _rec, f1 = score_detection(pred, oracle)
    reward = f1
    if post_patch is not None:
        reward += patch_removed_weight * score_patch_delta(oracle, post_patch)
    reward += format_bonus if had_valid_json else invalid_penalty
    return max(-1.0, min(2.0, reward))


__all__ = [
    "score_detection",
    "score_patch_delta",
    "final_reward",
    "SEV_WEIGHT",
]
