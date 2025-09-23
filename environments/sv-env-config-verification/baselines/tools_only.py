"""Baseline that emits the oracle as the prediction."""

from __future__ import annotations

from typing import Literal

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from oracle import build_oracle_for_k8s, build_oracle_for_tf


def emit_oracle_as_prediction(fixture_path: str, type_: Literal["k8s", "tf"]) -> dict:
    """Return the oracle as the prediction, simulating a perfect tool-only model."""

    oracle = build_oracle_for_k8s([fixture_path]) if type_ == "k8s" else build_oracle_for_tf([fixture_path])
    return {"violations": oracle, "patch": "", "confidence": 0.99}


__all__ = ["emit_oracle_as_prediction"]
