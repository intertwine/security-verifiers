from __future__ import annotations

# ruff: noqa: E402,I001

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
loaded_sv_shared = sys.modules.get("sv_shared")
if loaded_sv_shared:
    paths = list(getattr(loaded_sv_shared, "__path__", []))
    shared_path = str(REPO_ROOT / "sv_shared")
    if shared_path not in paths:
        getattr(loaded_sv_shared, "__path__").insert(0, shared_path)

from sv_shared.rendering import JsonLineRenderer, bridge_to_next_turn, parse_tool_json, preserve_turn  # noqa: E402
from sv_shared.sandbox_runner import dry_run_sandbox  # noqa: E402
from sv_shared.tool_runner import ToolRunner  # noqa: E402


def test_tool_runner_local_lightweight_command() -> None:
    result = ToolRunner(mode="local").run(["python", "-c", "print('ok')"])
    assert result.exit_code == 0
    assert result.stdout_snippet.strip() == "ok"
    assert result.duration_ms >= 0


def test_sandbox_dry_run_does_not_need_credentials() -> None:
    result = dry_run_sandbox(["semgrep", "--version"], image="svbench/e2-policy:local")
    assert result.mode == "prime-sandbox"
    assert result.dry_run is True
    assert result.exit_code == 0


def test_renderer_preserves_prior_bytes_when_appending_tool_result() -> None:
    renderer = JsonLineRenderer()
    messages = [{"role": "user", "content": "Check this config."}]
    sampled = 'I will call a tool first.\n{"tool": "opa", "args": {"strict": true}}'
    preserved = preserve_turn(renderer, messages, "assistant", sampled)
    bridged = bridge_to_next_turn(
        preserved.rendered_bytes,
        {"role": "tool", "content": json.dumps({"ok": True})},
    )
    assert bridged.startswith(preserved.rendered_bytes)
    assert sampled.encode("utf-8") in bridged


def test_qwen_like_text_before_json_tool_call_parses() -> None:
    parsed = parse_tool_json('Let me inspect it.\n{"tool": "semgrep", "args": {"json": true}}')
    assert parsed == {"tool": "semgrep", "args": {"json": True}}
