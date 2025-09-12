"""Common parser implementations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

import verifiers as vf

from .utils import get_response_text


@dataclass
class JsonClassificationParser(vf.Parser):
    """Parse JSON classification outputs with confidence and rationale.

    The expected output schema is::

        {
            "label": "Benign|Malicious|Abstain",
            "confidence": 0.0..1.0,
            "rationale": "string (optional)"
        }
    """

    allowed_labels: Iterable[str]

    def _parse_json(self, completion: Any) -> dict[str, Any]:
        text = get_response_text(completion)
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return {}

    def parse_answer(self, completion: Any) -> str:
        data = self._parse_json(completion)
        label = data.get("label")
        if isinstance(label, str) and label in self.allowed_labels:
            return label
        return ""

    def parse_confidence(self, completion: Any) -> float:
        data = self._parse_json(completion)
        conf = data.get("confidence")
        if conf is None:
            return 0.0
        try:
            conf_f = float(conf)
        except (TypeError, ValueError):
            return 0.0
        return conf_f if 0.0 <= conf_f <= 1.0 else 0.0

    def get_format_reward_func(self):  # type: ignore[override]
        parser = self

        def format_reward(completion: Any, **kwargs: Any) -> float:  # noqa: ANN401
            data = parser._parse_json(completion)
            label = data.get("label")
            conf = data.get("confidence")
            if (
                isinstance(label, str)
                and label in parser.allowed_labels
                and isinstance(conf, (int, float))
                and 0.0 <= float(conf) <= 1.0
            ):
                return 1.0
            return 0.0

        return format_reward


__all__ = ["JsonClassificationParser"]
