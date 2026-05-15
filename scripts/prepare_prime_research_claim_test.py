from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_prepare_prime_research_claim_selects_available_small_model(tmp_path: Path) -> None:
    models_path = tmp_path / "models.json"
    models_path.write_text(
        json.dumps(
            {
                "models": [
                    {"name": "Example/Old-8B", "at_capacity": False, "training_price_per_mtok": 3.0},
                    {
                        "name": "Qwen/Qwen3-1.7B-Instruct-2601",
                        "at_capacity": False,
                        "training_price_per_mtok": 1.0,
                    },
                    {
                        "name": "Qwen/Qwen3-0.8B-Instruct-2601",
                        "at_capacity": False,
                        "training_price_per_mtok": 0.5,
                    },
                    {
                        "name": "Qwen/Qwen3-0.6B-Instruct-2601",
                        "at_capacity": True,
                        "training_price_per_mtok": 0.5,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "claim"
    result = subprocess.run(
        [
            "python",
            "scripts/prepare_prime_research_claim.py",
            "--models-json",
            str(models_path),
            "--profile",
            "pilot",
            "--env",
            "e1",
            "--reward-source",
            "executable",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "selected_model=Qwen/Qwen3-1.7B-Instruct-2601" in result.stdout
    matrix = json.loads((out_dir / "run_matrix.json").read_text(encoding="utf-8"))
    assert matrix["matrix"][0]["model"] == "Qwen/Qwen3-1.7B-Instruct-2601"
    config = (out_dir / "configs" / "e1_executable_pilot.toml").read_text(encoding="utf-8")
    assert 'model = "Qwen/Qwen3-1.7B-Instruct-2601"' in config
    assert "max_steps = 50" in config
    assert 'reward_source = "executable"' in config
    assert "reward_config_id" not in config
    assert "budget_group" not in config
    assert "[dataset]" not in config


def test_prepare_prime_research_claim_respects_explicit_model(tmp_path: Path) -> None:
    out_dir = tmp_path / "claim"
    result = subprocess.run(
        [
            "python",
            "scripts/prepare_prime_research_claim.py",
            "--model",
            "Qwen/Qwen3-4B-Instruct-2601",
            "--env",
            "e2",
            "--reward-source",
            "hybrid",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    config = (out_dir / "configs" / "e2_hybrid_pilot.toml").read_text(encoding="utf-8")
    assert 'model = "Qwen/Qwen3-4B-Instruct-2601"' in config
    assert "max_steps = 60" in config
    assert 'reward_source = "hybrid"' in config
    assert "[tooling]" not in config


def test_prepare_prime_research_claim_adds_secret_env_file_for_judge_variants(tmp_path: Path) -> None:
    out_dir = tmp_path / "claim"
    result = subprocess.run(
        [
            "python",
            "scripts/prepare_prime_research_claim.py",
            "--model",
            "Qwen/Qwen3-4B-Instruct-2601",
            "--env",
            "e1",
            "--reward-source",
            "llm_judge",
            "hybrid",
            "--secret-env-file",
            ".env",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    matrix = json.loads((out_dir / "run_matrix.json").read_text(encoding="utf-8"))
    commands = [item["command"] for item in matrix["matrix"]]
    assert commands
    assert all("--env-file .env" in command for command in commands)
    assert all(item["requires_openai_api_key"] for item in matrix["matrix"])
