"""Transcript helpers that preserve prior assistant bytes across turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


class Renderer(Protocol):
    def render(self, messages: list[dict[str, Any]]) -> str:
        """Render chat messages to model input text."""


@dataclass(frozen=True)
class PreservedTurn:
    role: str
    content: str
    rendered_bytes: bytes


class JsonLineRenderer:
    """Deterministic test renderer with Qwen-like text-before-JSON tolerance."""

    def render(self, messages: list[dict[str, Any]]) -> str:
        return "\n".join(f"<|{msg.get('role')}|>\n{msg.get('content', '')}" for msg in messages)


def preserve_turn(renderer: Renderer, messages: list[dict[str, Any]], role: str, content: str) -> PreservedTurn:
    rendered = renderer.render([*messages, {"role": role, "content": content}])
    return PreservedTurn(role=role, content=content, rendered_bytes=rendered.encode("utf-8"))


def bridge_to_next_turn(
    prior_rendered_bytes: bytes,
    tool_message: dict[str, Any],
    *,
    turn_separator: str = "\n",
) -> bytes:
    """Append a tool/environment message without re-rendering prior sampled text."""

    rendered_tool = json.dumps(
        {"role": tool_message.get("role", "tool"), "content": tool_message.get("content", "")},
        sort_keys=True,
    )
    return prior_rendered_bytes + turn_separator.encode("utf-8") + rendered_tool.encode("utf-8")


def parse_tool_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON tool call from text that may include assistant prose."""

    start = text.find("{")
    if start < 0:
        return None
    for end in range(len(text), start, -1):
        try:
            value = json.loads(text[start:end])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


__all__ = [
    "JsonLineRenderer",
    "PreservedTurn",
    "bridge_to_next_turn",
    "parse_tool_json",
    "preserve_turn",
]
