#!/usr/bin/env python3
"""Collect Prime hosted-training artifacts into SV-Bench run manifests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from bench.run_manifest import current_git_sha, hash_file, utc_now, write_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGICAL_ENV = {
    "e1": "sv-env-network-logs",
    "e2": "sv-env-config-verification",
}
DATASET = {
    "e1": "datasets/public_mini/e1.jsonl",
    "e2": "datasets/public_mini/e2.jsonl",
}
TERMINAL_SUCCESS = {"COMPLETED"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_prime(args: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    result = subprocess.run(
        ["prime", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        if allow_failure:
            return {"error": output, "returncode": result.returncode}
        raise RuntimeError(output)
    if not output:
        return {}
    return json.loads(output)


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _latest_metric(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    metrics = metrics_payload.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return {}
    return sorted(
        (metric for metric in metrics if isinstance(metric, dict)),
        key=lambda metric: int(metric.get("step") or -1),
    )[-1]


def _first_environment(run: dict[str, Any]) -> dict[str, Any]:
    environments = run.get("environments")
    if isinstance(environments, list) and environments and isinstance(environments[0], dict):
        return environments[0]
    return {}


def _config_environment(config: dict[str, Any]) -> dict[str, Any]:
    environments = config.get("env")
    if isinstance(environments, list) and environments and isinstance(environments[0], dict):
        return environments[0]
    return {}


def validate_run_matches_matrix(
    *,
    matrix_item: dict[str, Any],
    run_payload: dict[str, Any],
    config: dict[str, Any],
) -> None:
    run = run_payload["run"]
    run_env = _first_environment(run)
    config_env = _config_environment(config)
    run_args = run_env.get("args", {}) if isinstance(run_env.get("args"), dict) else {}
    config_args = config_env.get("args", {}) if isinstance(config_env.get("args"), dict) else {}
    checks = {
        "model": (matrix_item.get("model") or config.get("model"), run.get("base_model")),
        "max_steps": (config.get("max_steps"), run.get("max_steps")),
        "reward_source": (matrix_item.get("reward_source"), run_args.get("reward_source")),
        "prime_environment_id": (config_env.get("id"), run_env.get("id")),
    }
    mismatches = {
        key: {"expected": expected, "actual": actual}
        for key, (expected, actual) in checks.items()
        if expected is not None and actual is not None and expected != actual
    }
    if mismatches:
        raise ValueError(
            f"Prime run {run.get('id')} does not match matrix row: " + json.dumps(mismatches, sort_keys=True)
        )
    if config_args.get("reward_source") and run_args.get("reward_source") != config_args.get("reward_source"):
        raise ValueError(
            f"Prime run {run.get('id')} reward_source does not match generated config: "
            f"{run_args.get('reward_source')} != {config_args.get('reward_source')}"
        )


def _write_rollouts(out_path: Path, rollouts_payload: dict[str, Any]) -> None:
    samples = rollouts_payload.get("samples") if isinstance(rollouts_payload, dict) else None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        if isinstance(samples, list):
            for sample in samples:
                handle.write(json.dumps(sample, sort_keys=True) + "\n")


def _artifact_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_manifest(
    *,
    matrix_item: dict[str, Any],
    run_payload: dict[str, Any],
    config: dict[str, Any],
    metrics_summary_path: Path,
    results_jsonl_path: Path,
    metadata_json_path: Path,
) -> dict[str, Any]:
    run = run_payload["run"]
    env_id = str(matrix_item["environment"])
    source_config = REPO_ROOT / str(matrix_item["source_config"])
    generated_config = REPO_ROOT / str(matrix_item["generated_config"])
    source_data = _load_toml(source_config)
    tooling = source_data.get("tooling", {}) if isinstance(source_data.get("tooling"), dict) else {}
    sampling = config.get("sampling", {}) if isinstance(config.get("sampling"), dict) else {}
    environment = _first_environment(run)
    eval_config = run.get("eval_config") or {}
    buffer_config = run.get("buffer_config") or {}
    return {
        "run_id": str(run["id"]),
        "git_sha": current_git_sha(),
        "timestamp_utc": utc_now(),
        "environment_id": LOGICAL_ENV[env_id],
        "prime_environment_id": environment.get("id"),
        "environment_version": str(environment.get("version") or "unknown"),
        "dataset_id": DATASET[env_id],
        "dataset_revision": "public-mini-v1",
        "split": "train",
        "model_id": str(run.get("base_model") or config.get("model")),
        "model_revision_or_digest": "prime-hosted",
        "sampling_params": sampling,
        "reward_config_id": str(matrix_item["reward_config_id"]),
        "reward_config_hash": hash_file(source_config),
        "reward_source": str(matrix_item["reward_source"]),
        "budget_group": str(matrix_item["budget_group"]),
        "seed": int(buffer_config.get("seed") or 0),
        "platform_mode": "hosted",
        "trainer": str(matrix_item.get("trainer") or "grpo"),
        "max_steps": int(run.get("max_steps") or config.get("max_steps") or 0),
        "rollouts_per_example": int(
            run.get("rollouts_per_example") or config.get("rollouts_per_example") or 1
        ),
        "max_tokens": int(run.get("max_tokens") or sampling.get("max_tokens") or 1),
        "max_turns": int(tooling.get("max_turns") or (1 if env_id == "e1" else 5)),
        "tool_budget": int(tooling.get("tool_budget") or (0 if env_id == "e1" else 3)),
        "input_artifacts": [_artifact_path(source_config), _artifact_path(generated_config)],
        "output_artifacts": [_artifact_path(metrics_summary_path), _artifact_path(results_jsonl_path)],
        "metrics_summary_path": _artifact_path(metrics_summary_path),
        "results_jsonl_path": _artifact_path(results_jsonl_path),
        "metadata_json_path": _artifact_path(metadata_json_path),
        "notes": (
            f"Prime hosted pilot run status={run.get('status')}; "
            f"eval_examples={eval_config.get('num_examples')}; profile={matrix_item.get('profile')}; "
            "claim_ready is recorded in metrics_summary_path and requires COMPLETED plus non-empty metrics."
        ),
        "prime_run_id": str(run["id"]),
        "team": str(run.get("team_id") or "unknown"),
        "compute_profile": str(run.get("cluster_id") or "unknown"),
        "platform_image": "prime-hosted-training",
        "adapter_id": str(run.get("adapter_id") or "pending"),
    }


def collect_one(
    matrix_item: dict[str, Any],
    base_dir: Path,
    *,
    require_completed: bool = False,
) -> dict[str, Any]:
    run_id = str(matrix_item["prime_run_id"])
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    run_payload = _run_prime(["train", "get", run_id, "--output", "json", "--plain"])
    generated_config = REPO_ROOT / str(matrix_item["generated_config"])
    config = _load_toml(generated_config)
    validate_run_matches_matrix(matrix_item=matrix_item, run_payload=run_payload, config=config)
    progress = _run_prime(["train", "progress", run_id, "--plain"], allow_failure=True)
    metrics = _run_prime(["train", "metrics", run_id, "--plain"], allow_failure=True)
    usage = _run_prime(["train", "usage", run_id, "--output", "json", "--plain"], allow_failure=True)

    _write_json(run_dir / "metadata.json", run_payload)
    _write_json(run_dir / "progress.json", progress)
    _write_json(run_dir / "metrics_raw.json", metrics)
    _write_json(run_dir / "usage.json", usage)

    latest_metric = _latest_metric(metrics)
    run_status = run_payload["run"].get("status")
    claim_ready = run_status in TERMINAL_SUCCESS and bool(latest_metric)
    if require_completed and not claim_ready:
        raise ValueError(
            f"Prime run {run_id} is not claim-ready: status={run_status}, metrics={bool(latest_metric)}"
        )
    metrics_summary = {
        "metrics": latest_metric,
        "run_status": run_status,
        "claim_ready": claim_ready,
    }
    metrics_summary_path = run_dir / "metrics_summary.json"
    _write_json(metrics_summary_path, metrics_summary)

    rollouts_payload: dict[str, Any] = {}
    steps = progress.get("steps_with_samples") if isinstance(progress, dict) else None
    if isinstance(steps, list) and steps:
        rollouts_payload = _run_prime(
            ["train", "rollouts", run_id, "--step", str(max(steps)), "--num", "25", "--plain"],
            allow_failure=True,
        )
    _write_json(run_dir / "rollouts_raw.json", rollouts_payload)
    results_jsonl_path = run_dir / "results.jsonl"
    _write_rollouts(results_jsonl_path, rollouts_payload)

    manifest = build_manifest(
        matrix_item=matrix_item,
        run_payload=run_payload,
        config=config,
        metrics_summary_path=metrics_summary_path,
        results_jsonl_path=results_jsonl_path,
        metadata_json_path=run_dir / "metadata.json",
    )
    write_manifest(run_dir / "run_manifest.json", manifest)
    return {
        "run_id": run_id,
        "status": run_payload["run"].get("status"),
        "claim_ready": claim_ready,
        "manifest": _artifact_path(run_dir / "run_manifest.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect SV-Bench Prime hosted-training artifacts.")
    parser.add_argument("--matrix", required=True, help="Path to run_matrix.json")
    parser.add_argument("--out-dir", help="Artifact output directory")
    parser.add_argument(
        "--only-run-id",
        action="append",
        default=[],
        help="Collect only a specific Prime run ID",
    )
    parser.add_argument(
        "--require-completed",
        action="store_true",
        help="Fail unless selected runs are completed and have non-empty metrics.",
    )
    args = parser.parse_args()
    if not args.require_completed:
        print(
            "WARNING: writing diagnostic artifacts without --require-completed; "
            "do not use these manifests as claim evidence.",
            file=sys.stderr,
        )

    matrix_path = Path(args.matrix)
    matrix = _load_json(matrix_path)
    out_dir = Path(args.out_dir or matrix_path.parent / "artifacts")
    selected = set(args.only_run_id)
    summaries = []
    for item in matrix["matrix"]:
        if "prime_run_id" not in item:
            continue
        if selected and item["prime_run_id"] not in selected:
            continue
        summaries.append(collect_one(item, out_dir, require_completed=args.require_completed))
    _write_json(out_dir / "collection_summary.json", {"runs": summaries})
    print(json.dumps({"artifact_dir": _artifact_path(out_dir), "runs": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
