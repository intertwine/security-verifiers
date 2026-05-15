#!/usr/bin/env python3
"""Prepare a Prime hosted-training matrix for the SV-Bench research claim."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REWARD_CONFIGS = {
    ("e1", "executable"): "configs/rl/e1_executable_reward.toml",
    ("e1", "llm_judge"): "configs/rl/e1_llm_judge_reward.toml",
    ("e1", "hybrid"): "configs/rl/e1_hybrid_reward.toml",
    ("e2", "executable"): "configs/rl/e2_executable_reward.toml",
    ("e2", "llm_judge"): "configs/rl/e2_llm_judge_reward.toml",
    ("e2", "hybrid"): "configs/rl/e2_hybrid_reward.toml",
}
ENV_DEFAULTS = {
    "e1": {"max_steps": 200, "eval_examples": 50},
    "e2": {"max_steps": 250, "eval_examples": 30},
}
PILOT_DEFAULTS = {
    "e1": {"max_steps": 50, "eval_examples": 25},
    "e2": {"max_steps": 60, "eval_examples": 20},
}
PRIME_TOP_LEVEL_FIELDS = {
    "name",
    "model",
    "max_steps",
    "batch_size",
    "rollouts_per_example",
    "learning_rate",
    "lora_alpha",
    "oversampling_factor",
    "max_async_level",
    "checkpoint_id",
    "cluster_name",
    "run_config",
    "env_files",
    "env",
    "sampling",
    "eval",
    "val",
    "buffer",
    "wandb",
    "checkpoints",
    "adapters",
    "infrastructure",
    "tailscale",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{key} = {_format_scalar(item)}" for key, item in value.items()) + " }"
    raise TypeError(f"Unsupported TOML value: {value!r}")


def _dump_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    deferred: list[tuple[str, Any]] = []
    for key, value in data.items():
        if isinstance(value, dict) or (isinstance(value, list) and value and isinstance(value[0], dict)):
            deferred.append((key, value))
        else:
            lines.append(f"{key} = {_format_scalar(value)}")
    for key, value in deferred:
        lines.append("")
        if isinstance(value, dict):
            lines.append(f"[{key}]")
            for child_key, child_value in value.items():
                lines.append(f"{child_key} = {_format_scalar(child_value)}")
        elif isinstance(value, list):
            for item in value:
                lines.append(f"[[{key}]]")
                for child_key, child_value in item.items():
                    lines.append(f"{child_key} = {_format_scalar(child_value)}")
                lines.append("")
            if lines and lines[-1] == "":
                lines.pop()
    return "\n".join(lines) + "\n"


def _parse_size_b(model_name: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*[Bb](?![A-Za-z])", model_name)
    if not match:
        return None
    return float(match.group(1))


def _price(model: dict[str, Any]) -> float:
    keys = (
        "effective_training_price_per_mtok",
        "training_price_per_mtok",
        "effective_inference_input_price_per_mtok",
        "inference_input_price_per_mtok",
    )
    for key in keys:
        value = model.get(key)
        if isinstance(value, int | float):
            return float(value)
    return 999999.0


def _model_score(model: dict[str, Any], min_size_b: float, max_size_b: float) -> tuple[float, float, str]:
    name = str(model.get("name", ""))
    size = _parse_size_b(name)
    if model.get("at_capacity") is True:
        capacity_penalty = 1000.0
    else:
        capacity_penalty = 0.0
    if size is None:
        size_score = max_size_b + 100.0
    elif size < min_size_b:
        size_score = min_size_b + 50.0 + (min_size_b - size)
    elif size > max_size_b:
        size_score = size + 100.0
    else:
        size_score = size
    recency_bonus = 0.0
    if re.search(r"qwen3|llama-?3|gemma-?3|phi-?4|2026|2507|2510|260", name, re.I):
        recency_bonus = -0.5
    return (capacity_penalty + size_score + recency_bonus, _price(model), name)


def select_model(models: list[dict[str, Any]], min_size_b: float, max_size_b: float) -> dict[str, Any]:
    candidates = [model for model in models if model.get("name")]
    if not candidates:
        raise ValueError("Prime model catalog did not contain any named models")
    return sorted(candidates, key=lambda model: _model_score(model, min_size_b, max_size_b))[0]


def _load_models(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.models_json:
        payload = json.loads(Path(args.models_json).read_text(encoding="utf-8"))
    else:
        result = subprocess.run(
            ["prime", "train", "models", "--output", "json", "--plain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stdout or result.stderr).strip())
        payload = json.loads(result.stdout)
    models = payload.get("models") if isinstance(payload, dict) else payload
    if not isinstance(models, list):
        raise ValueError("Expected Prime model JSON to contain .models[]")
    return [model for model in models if isinstance(model, dict)]


def _apply_profile(
    data: dict[str, Any],
    env_id: str,
    reward_source: str,
    profile: str,
    model: str,
    run_set_id: str,
) -> dict[str, Any]:
    updated = {key: value for key, value in data.items() if key in PRIME_TOP_LEVEL_FIELDS}
    updated["name"] = f"svbench-{env_id}-{reward_source}-{profile}-{run_set_id}"
    updated["model"] = model
    defaults = PILOT_DEFAULTS if profile == "pilot" else ENV_DEFAULTS
    env_defaults = defaults[env_id]
    updated["max_steps"] = env_defaults["max_steps"]
    if isinstance(updated.get("eval"), dict):
        updated["eval"] = dict(updated["eval"])
        updated["eval"]["num_examples"] = env_defaults["eval_examples"]
        if isinstance(updated["eval"].get("env"), list):
            updated["eval"]["env"] = [dict(item) for item in updated["eval"]["env"]]
            for item in updated["eval"]["env"]:
                args = dict(item.get("args", {}))
                args["max_examples"] = env_defaults["eval_examples"]
                args["reward_source"] = reward_source
                item["args"] = args
    if isinstance(updated.get("env"), list):
        updated["env"] = [dict(item) for item in updated["env"]]
        for item in updated["env"]:
            args = dict(item.get("args", {}))
            args["max_examples"] = env_defaults["max_steps"]
            item["args"] = args
    return updated


def _secret_flags(reward_source: str, secret_env_file: str | None) -> list[str]:
    if reward_source not in {"llm_judge", "hybrid"} or not secret_env_file:
        return []
    return ["--env-file", secret_env_file]


def _write_matrix(args: argparse.Namespace, model_name: str, selected_model: dict[str, Any]) -> Path:
    run_set_id = args.run_set_id or f"svbench-research-claim-{_utc_stamp()}"
    out_dir = Path(args.out_dir or REPO_ROOT / "outputs" / "prime_research_claim" / run_set_id)
    config_dir = out_dir / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    matrix: list[dict[str, Any]] = []
    commands: list[str] = []
    for env_id in args.env:
        for reward_source in args.reward_source:
            source_path = REPO_ROOT / REWARD_CONFIGS[(env_id, reward_source)]
            source_config = _load_toml(source_path)
            config = _apply_profile(
                source_config,
                env_id,
                reward_source,
                args.profile,
                model_name,
                run_set_id,
            )
            config_path = config_dir / f"{env_id}_{reward_source}_{args.profile}.toml"
            config_path.write_text(_dump_toml(config), encoding="utf-8")
            command = _shell_join(
                [
                    "uv",
                    "run",
                    "prime",
                    "train",
                    _display_path(config_path),
                    "--plain",
                    "--yes",
                    *_secret_flags(reward_source, args.secret_env_file),
                ]
            )
            commands.append(command)
            matrix.append(
                {
                    "environment": env_id,
                    "reward_source": reward_source,
                    "source_config": str(source_path.relative_to(REPO_ROOT)),
                    "generated_config": _display_path(config_path),
                    "command": command,
                    "profile": args.profile,
                    "model": model_name,
                    "reward_config_id": source_config.get("reward_config_id"),
                    "budget_group": source_config.get("budget_group"),
                    "trainer": source_config.get("trainer"),
                    "requires_openai_api_key": reward_source in {"llm_judge", "hybrid"},
                }
            )

    payload = {
        "run_set_id": run_set_id,
        "profile": args.profile,
        "selected_model": selected_model,
        "matrix": matrix,
    }
    (out_dir / "run_matrix.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    launch_lines = [
        f"# Prime Hosted Training Launch Plan: {run_set_id}",
        "",
        f"- profile: `{args.profile}`",
        f"- model: `{model_name}`",
        "",
        "Run these commands after `make lab-check` reports `hosted-ready`:",
        "",
        "Judge and hybrid runs require `OPENAI_API_KEY` in the hosted container. "
        "Pass `--secret-env-file .env` to include `--env-file .env` in generated commands.",
        "",
        "```bash",
        *commands,
        "```",
        "",
        "After each launch, record the returned Prime run ID in `run_matrix.json` "
        "before collecting artifacts.",
        "",
    ]
    (out_dir / "launch_commands.md").write_text("\n".join(launch_lines), encoding="utf-8")
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare SV-Bench Prime hosted-training launch configs.")
    parser.add_argument("--models-json", help="Path to `prime train models --output json --plain` output")
    parser.add_argument("--model", help="Explicit hosted-training model ID; skips automatic model selection")
    parser.add_argument(
        "--min-size-b",
        type=float,
        default=1.0,
        help="Preferred minimum model size in billions for non-trivial progress runs",
    )
    parser.add_argument(
        "--max-size-b",
        type=float,
        default=4.0,
        help="Preferred maximum model size in billions",
    )
    parser.add_argument("--profile", choices=["pilot", "claim"], default="pilot")
    parser.add_argument("--env", choices=["e1", "e2"], nargs="+", default=["e1", "e2"])
    parser.add_argument(
        "--reward-source",
        choices=["executable", "llm_judge", "hybrid"],
        nargs="+",
        default=["executable", "llm_judge", "hybrid"],
    )
    parser.add_argument("--run-set-id", help="Stable run set ID")
    parser.add_argument("--out-dir", help="Output directory for generated configs and launch plan")
    parser.add_argument(
        "--secret-env-file",
        help="Optional .env file to pass to judge/hybrid Prime launches, for example `.env`.",
    )
    args = parser.parse_args()

    if args.model:
        model_name = args.model
        selected_model = {"name": model_name, "selection": "explicit"}
    else:
        models = _load_models(args)
        selected_model = select_model(models, args.min_size_b, args.max_size_b)
        model_name = str(selected_model["name"])

    out_dir = _write_matrix(args, model_name, selected_model)
    print(f"selected_model={model_name}")
    print(f"output_dir={_display_path(out_dir)}")
    print(f"launch_plan={_display_path(out_dir / 'launch_commands.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
