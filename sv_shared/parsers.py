"""Common parser implementations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import verifiers as vf

from .utils import get_response_text


def extract_json_from_markdown(text: str) -> str:
    """Extract JSON content from markdown code blocks.

    Handles formats like:
        ```json
        {"key": "value"}
        ```

        ```
        {"key": "value"}
        ```

    Returns the extracted JSON string, or the original text if no code block found.
    """
    # Pattern matches ```json or ``` followed by content and closing ```
    pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


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

        # Try raw text first (for models that output clean JSON)
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Try extracting from markdown code blocks (for models like gpt-4o-mini)
        extracted = extract_json_from_markdown(text)
        if extracted != text:  # Only retry if extraction changed something
            try:
                data = json.loads(extracted)
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


__all__ = ["JsonClassificationParser", "extract_json_from_markdown"]
