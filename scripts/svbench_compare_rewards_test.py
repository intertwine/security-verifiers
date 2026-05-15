from __future__ import annotations

import json
from pathlib import Path

import pytest
from bench.compare_rewards import _build_summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def _manifest(path: str, reward_source: str) -> dict:
    data = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    data["reward_source"] = reward_source
    data["reward_config_id"] = f"fixture_{reward_source}"
    data["_manifest_path"] = str(REPO_ROOT / path)
    return data


def test_compare_rewards_accepts_matched_budget() -> None:
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    summary = _build_summary("e1", manifests, allow_unmatched=False)
    assert summary["budget_mismatches"] == {}
    assert summary["metric_rows"]


def test_compare_rewards_refuses_unmatched_budget() -> None:
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    manifests["judge"]["max_steps"] = 999
    with pytest.raises(ValueError, match="Budget parity failed"):
        _build_summary("e1", manifests, allow_unmatched=False)


def test_compare_rewards_allows_unmatched_with_flag() -> None:
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    manifests["hybrid"]["tool_budget"] = 3
    summary = _build_summary("e1", manifests, allow_unmatched=True)
    assert "tool_budget" in summary["budget_mismatches"]
