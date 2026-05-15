from __future__ import annotations

# ruff: noqa: E402,I001

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.collect_prime_research_claim import build_manifest, validate_run_matches_matrix


def test_build_manifest_uses_logical_env_for_reward_comparison(tmp_path: Path) -> None:
    metrics_summary = tmp_path / "metrics_summary.json"
    results = tmp_path / "results.jsonl"
    metadata = tmp_path / "metadata.json"
    metrics_summary.write_text('{"metrics": {"reward/all/mean": 0.5}}\n', encoding="utf-8")
    results.write_text("{}\n", encoding="utf-8")
    metadata.write_text("{}\n", encoding="utf-8")

    manifest = build_manifest(
        matrix_item={
            "environment": "e1",
            "source_config": "configs/rl/e1_llm_judge_reward.toml",
            "generated_config": "configs/rl/e1_llm_judge_reward.toml",
            "reward_config_id": "e1_llm_judge_reward",
            "reward_source": "llm_judge",
            "budget_group": "e1-v0.1-matched-budget",
            "trainer": "grpo",
            "profile": "pilot",
        },
        run_payload={
            "run": {
                "id": "run123",
                "base_model": "Qwen/Qwen3.5-2B",
                "status": "COMPLETED",
                "max_steps": 50,
                "max_tokens": 2048,
                "rollouts_per_example": 8,
                "team_id": "team",
                "cluster_id": "cluster",
                "environments": [
                    {
                        "id": "intertwine/sv-netlogs-judge",
                        "version": "0.2.18",
                    }
                ],
                "eval_config": {"num_examples": 25},
                "buffer_config": {"seed": 42},
            }
        },
        config={"model": "Qwen/Qwen3.5-2B", "sampling": {"max_tokens": 2048, "temperature": 0.7}},
        metrics_summary_path=metrics_summary,
        results_jsonl_path=results,
        metadata_json_path=metadata,
    )

    assert manifest["environment_id"] == "sv-env-network-logs"
    assert manifest["prime_environment_id"] == "intertwine/sv-netlogs-judge"
    assert manifest["platform_mode"] == "hosted"
    assert manifest["prime_run_id"] == "run123"
    json.dumps(manifest)


def test_validate_run_matches_matrix_rejects_mislabeled_reward_source() -> None:
    with pytest.raises(ValueError, match="does not match matrix row"):
        validate_run_matches_matrix(
            matrix_item={
                "model": "Qwen/Qwen3.5-2B",
                "reward_source": "llm_judge",
            },
            run_payload={
                "run": {
                    "id": "run123",
                    "base_model": "Qwen/Qwen3.5-2B",
                    "max_steps": 50,
                    "environments": [
                        {
                            "id": "intertwine/sv-env-network-logs",
                            "args": {"reward_source": "executable"},
                        }
                    ],
                }
            },
            config={
                "model": "Qwen/Qwen3.5-2B",
                "max_steps": 50,
                "env": [
                    {
                        "id": "intertwine/sv-env-network-logs",
                        "args": {"reward_source": "executable"},
                    }
                ],
            },
        )
