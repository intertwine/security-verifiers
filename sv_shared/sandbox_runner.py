"""Small adapter layer for sandbox-backed tool execution."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .tool_runner import ToolResult, ToolRunner


def dry_run_sandbox(command: Sequence[str], *, image: str, mode: str = "prime-sandbox") -> ToolResult:
    """Return the command that would run in a sandbox without requiring credentials."""

    return ToolRunner(mode=mode, image=image).run(command, cwd=Path.cwd(), dry_run=True)


def run_local_tool(command: Sequence[str], *, cwd: Path | None = None) -> ToolResult:
    """Run a lightweight local command with normalized output."""

    return ToolRunner(mode="local").run(command, cwd=cwd)
