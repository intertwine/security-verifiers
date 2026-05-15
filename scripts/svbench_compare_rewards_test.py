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
    summary = _build_summary("e1", manifests, allow_unmatched=True)
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


def test_compare_rewards_refuses_incomplete_hosted_run(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text('{"metrics": {"reward": 1.0}, "run_status": "RUNNING"}\n', encoding="utf-8")
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    for manifest in manifests.values():
        manifest["platform_mode"] = "hosted"
        manifest["metrics_summary_path"] = str(summary_path)
    with pytest.raises(ValueError, match="not complete enough"):
        _build_summary("e1", manifests, allow_unmatched=False)


def test_compare_rewards_refuses_hosted_run_without_status(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text('{"metrics": {"reward": 1.0}}\n', encoding="utf-8")
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    for manifest in manifests.values():
        manifest["platform_mode"] = "hosted"
        manifest["metrics_summary_path"] = str(summary_path)
    with pytest.raises(ValueError, match="not complete enough"):
        _build_summary("e1", manifests, allow_unmatched=False)


def test_compare_rewards_refuses_hosted_identity_mismatches() -> None:
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    manifests["executable"]["prime_environment_id"] = "intertwine/sv-env-network-logs"
    manifests["judge"]["prime_environment_id"] = "intertwine/sv-netlogs-judge"
    with pytest.raises(ValueError, match="Hosted identity parity failed"):
        _build_summary("e1", manifests, allow_unmatched=False)


def test_compare_rewards_allows_hosted_identity_mismatches_with_flag() -> None:
    manifests = {
        "executable": _manifest("bench/fixtures/e1_run_manifest.json", "executable"),
        "judge": _manifest("bench/fixtures/e1_run_manifest.json", "llm_judge"),
        "hybrid": _manifest("bench/fixtures/e1_run_manifest.json", "hybrid"),
    }
    manifests["executable"]["prime_environment_id"] = "intertwine/sv-env-network-logs"
    manifests["judge"]["prime_environment_id"] = "intertwine/sv-netlogs-judge"
    summary = _build_summary("e1", manifests, allow_unmatched=True)
    assert summary["budget_mismatches"] == {}
    assert (
        summary["hosted_identity_mismatches"]["prime_environment_id"]["judge"]
        == "intertwine/sv-netlogs-judge"
    )
