#!/usr/bin/env python3
"""SV-Bench v0.1 release package checker."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH) PRIVATE KEY)")
REQUIRED_FILES = [
    "SVBENCH_STATUS.md",
    "SVBENCH.md",
    "plans/ROADMAP-2026-SUITE.md",
    "bench/schemas/run_manifest.schema.json",
    "bench/fixtures/e1_run_manifest.json",
    "bench/fixtures/e2_run_manifest.json",
    "bench/leaderboard/v0.1.schema.json",
    "bench/leaderboard/v0.1.json",
    "datasets/HELDOUT_POLICY.md",
    "results/v0.1_baselines.md",
    "results/v0.1_training.md",
    "reports/SVBENCH_v0.1_technical_report.md",
]
EVAL_PARITY_FIELDS = (
    "git_sha",
    "environment_id",
    "environment_version",
    "dataset_id",
    "dataset_revision",
    "split",
    "reward_config_hash",
    "sampling_params",
    "seed",
    "max_tokens",
    "max_turns",
    "tool_budget",
)
TRAINING_PARITY_FIELDS = (
    "git_sha",
    "training_settings",
    "environment_id",
    "environment_version",
    "prime_environment_id",
    "dataset_id",
    "dataset_revision",
    "split",
    "model_id",
    "model_revision_or_digest",
    "max_steps",
    "rollouts_per_example",
    "max_tokens",
    "max_turns",
    "tool_budget",
    "trainer",
    "sampling_params",
    "seed",
)
UNRESOLVED = {"fixture", "pending", "unknown", "prime-hosted", "latest", "main"}
OPERATIONAL_METRICS = {
    "e1": {
        "detection.accuracy": "higher",
        "detection.f1": "higher",
        "detection.tpr": "higher",
        "detection.fpr": "lower",
        "detection.fnr": "lower",
        "calibration.ece": "lower",
        "calibration.brier": "lower",
        "cost.cost_weighted_accuracy": "higher",
        "abstention.aurc": "lower",
    },
    "e2": {
        "finding_quality.f1_weighted": "higher",
        "finding_quality.f1_unweighted": "higher",
        "finding_quality.f1_weighted_positive_only": "higher",
        "finding_quality.f1_unweighted_positive_only": "higher",
        "patch.patch_success_rate": "higher",
        "patch.patch_fix_rate": "higher",
        "patch.new_violations_introduced": "lower",
        "episode.clean_pass_rate": "higher",
        "episode.false_positive_rate_on_clean": "lower",
    },
}


def _artifact(path: str, base: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return base / candidate if (base / candidate).exists() else REPO_ROOT / candidate


def _research_manifest(path: str, env: str, *, evaluation: bool) -> dict:
    """Load real evidence; schema-valid smoke manifests alone cannot prove completion."""
    manifest_path = _artifact(path, REPO_ROOT)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(_read("bench/schemas/run_manifest.schema.json"))
    jsonschema.validate(manifest, schema)
    expected_env = {"e1": "sv-env-network-logs", "e2": "sv-env-config-verification"}[env]
    if manifest["environment_id"] != expected_env:
        raise ValueError(f"{env}: incorrect environment in {path}")
    for field in ("model_revision_or_digest", "dataset_revision", "environment_version"):
        value = manifest[field].strip().lower()
        if value in UNRESOLVED or "fixture" in value or value.startswith("public-mini"):
            raise ValueError(f"{env}: unresolved or smoke-only {field} in {path}")
    if not re.fullmatch(
        r"(?:sha256:)?(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", manifest["model_revision_or_digest"]
    ):
        raise ValueError(f"{env}: immutable model revision or digest required in {path}")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", manifest["git_sha"]):
        raise ValueError(f"{env}: immutable git_sha required in {path}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", manifest["reward_config_hash"]):
        raise ValueError(f"{env}: reward_config_hash digest required in {path}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", manifest.get("dataset_sha256", "")):
        raise ValueError(f"{env}: dataset_sha256 required in {path}")
    if evaluation and manifest["split"] not in {"heldout", "test"}:
        raise ValueError(f"{env}: heldout/test evaluation required in {path}")
    if not evaluation and (manifest["max_steps"] <= 0 or manifest["trainer"] == "none"):
        raise ValueError(f"{env}: actual training evidence required in {path}")
    if not evaluation:
        settings = manifest.get("training_settings", {})
        batch_size = settings.get("batch_size") if isinstance(settings, dict) else None
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError(f"{env}: training_settings requires positive batch_size")
        for field in ("lora", "optimizer"):
            if not isinstance(settings.get(field), dict) or not settings[field]:
                raise ValueError(f"{env}: training_settings requires explicit {field} configuration")
        curve = json.loads(_artifact(manifest["learning_curve_path"], manifest_path.parent).read_text())
        if curve.get("run_id") != manifest["run_id"]:
            raise ValueError(f"{env}: learning curve must reference the training run")
        if manifest["max_steps"] <= 1 or any(
            curve.get(field) != manifest["max_steps"] for field in ("planned_steps", "completed_steps")
        ):
            raise ValueError(f"{env}: learning curve must show a completed non-smoke planned budget")
        points = curve.get("points", [])
        steps = set()
        for point in points:
            step, value = point.get("step"), point.get("value")
            if (
                isinstance(step, bool)
                or not isinstance(step, int)
                or not 0 <= step <= manifest["max_steps"]
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{env}: learning curve requires finite observed values and valid steps")
            steps.add(step)
        if len(steps) < 2 or max(steps) != manifest["max_steps"]:
            raise ValueError(f"{env}: learning curve requires two distinct steps including completion")
    if env == "e2":
        backends = manifest.get("tool_backends")
        if (
            not isinstance(backends, list)
            or not backends
            or any(
                not isinstance(backend, str) or not backend.strip() or backend.lower() in UNRESOLVED
                for backend in backends
            )
        ):
            raise ValueError(f"e2: explicit tool_backends provenance required in {path}")
    for field in ("results_jsonl_path", "metadata_json_path", "metrics_summary_path"):
        artifact = _artifact(manifest[field], manifest_path.parent)
        if not artifact.is_file() or not artifact.stat().st_size:
            raise ValueError(f"{env}: missing or empty {field} in {path}")
        if field == "results_jsonl_path":
            rows = [json.loads(line) for line in artifact.read_text().splitlines() if line.strip()]
            if not rows or any(not isinstance(row, dict) for row in rows):
                raise ValueError(f"{env}: nonempty result objects required in {path}")
        else:
            json.loads(artifact.read_text(encoding="utf-8"))
    summary = json.loads(_artifact(manifest["metrics_summary_path"], manifest_path.parent).read_text())
    if manifest["platform_mode"] == "hosted" and summary.get("run_status") != "COMPLETED":
        raise ValueError(f"{env}: hosted run must be COMPLETED in {path}")
    manifest["_summary"] = summary
    return manifest


def _parity(left: dict, right: dict, fields: tuple[str, ...], label: str) -> None:
    mismatches = [field for field in fields if left.get(field) != right.get(field)]
    if mismatches:
        raise ValueError(f"{label}: unmatched fields: {', '.join(mismatches)}")


def _metric(manifest: dict, name: str) -> float:
    value = manifest["_summary"].get("metrics", {})
    for part in name.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"missing finite heldout metric: {name}")
    return float(value)


def _check_split_provenance(path: str, training: dict, heldout: dict) -> None:
    provenance_path = _artifact(path, REPO_ROOT)
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    for field, manifest in (("train", training), ("heldout", heldout)):
        if provenance[f"{field}_dataset_sha256"] != manifest["dataset_sha256"]:
            raise ValueError(f"split provenance: {field} dataset digest mismatch")
    ids = []
    for field in ("train", "heldout"):
        data = json.loads(_artifact(provenance[f"{field}_ids_path"], provenance_path.parent).read_text())
        if (
            not isinstance(data, list)
            or not data
            or any(not isinstance(item, str) or not item for item in data)
        ):
            raise ValueError("split provenance requires nonempty string ID lists")
        if len(data) != len(set(data)):
            raise ValueError("split provenance contains duplicate IDs")
        ids.append(set(data))
    if ids[0] & ids[1]:
        raise ValueError("split provenance: training and heldout IDs overlap")


def _check_research_completion(errors: list[str], evidence_path: Path) -> None:
    """Check the empirical evidence contract, not statistical significance or its authenticity."""
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        for env in ("e1", "e2"):
            experiment = evidence[env]
            baseline = _research_manifest(experiment["baseline_manifest"], env, evaluation=True)
            trained = _research_manifest(experiment["trained_manifest"], env, evaluation=True)
            training = _research_manifest(experiment["training_manifest"], env, evaluation=False)
            _parity(baseline, trained, EVAL_PARITY_FIELDS + ("dataset_sha256",), f"{env} heldout")
            if env == "e2":
                _parity(baseline, trained, ("tool_backends",), "e2 scanner backend/version")
            _parity(baseline, training, ("model_id", "model_revision_or_digest"), f"{env} base model")
            _parity(baseline, trained, ("model_id",), f"{env} trained model")
            if baseline["model_revision_or_digest"] == trained["model_revision_or_digest"]:
                raise ValueError(f"{env}: base and trained checkpoint digests must differ")
            checkpoint = training.get("trained_model_revision_or_digest")
            if checkpoint != trained["model_revision_or_digest"]:
                raise ValueError(f"{env}: trained evaluation must reference the training checkpoint")
            if training["dataset_sha256"] == trained["dataset_sha256"]:
                raise ValueError(f"{env}: training and heldout datasets must differ")
            if training.get("heldout_overlap_count") != 0 or isinstance(
                training.get("heldout_overlap_count"), bool
            ):
                raise ValueError(f"{env}: heldout_overlap_count=0 required")
            _check_split_provenance(experiment["split_provenance"], training, trained)
            metric = experiment["metric"]
            if metric not in OPERATIONAL_METRICS[env]:
                raise ValueError(f"{env}: use a supported independent task metric, not training reward")
            direction = experiment["direction"]
            if direction != OPERATIONAL_METRICS[env][metric]:
                raise ValueError(f"{env}: incorrect improvement direction for {metric}")
            delta = _metric(trained, metric) - _metric(baseline, metric)
            if delta * (1 if direction == "higher" else -1) <= 0:
                raise ValueError(f"{env}: no positive heldout improvement for {metric}")
            if training.get("reward_source") != "executable":
                raise ValueError(f"{env}: executable-reward training required")
            if env == "e1":
                judge_training = _research_manifest(
                    experiment["judge_training_manifest"], env, evaluation=False
                )
                judge = _research_manifest(experiment["judge_manifest"], env, evaluation=True)
                if judge_training.get("reward_source") != "llm_judge":
                    raise ValueError("e1: llm_judge training required for reward comparison")
                _parity(
                    training,
                    judge_training,
                    TRAINING_PARITY_FIELDS + ("dataset_sha256",),
                    "e1 reward comparison",
                )
                _parity(trained, judge, EVAL_PARITY_FIELDS + ("dataset_sha256",), "e1 common scorer")
                if (
                    judge_training.get("trained_model_revision_or_digest")
                    != judge["model_revision_or_digest"]
                ):
                    raise ValueError("e1: judge evaluation must reference the judge training checkpoint")
                _metric(judge, metric)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, jsonschema.ValidationError) as exc:
        errors.append(f"research completion evidence: {exc}")


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _check_required_files(errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")


def _check_scope_docs(errors: list[str]) -> None:
    docs = "\n".join(_read(rel) for rel in ("README.md", "SVBENCH_STATUS.md", "SVBENCH.md"))
    lowered = docs.lower()
    if "v0.1" not in lowered or "e1" not in lowered or "e2" not in lowered:
        errors.append("docs do not clearly describe v0.1 E1/E2 scope")
    if "e5/e6" not in lowered and "e5" not in lowered:
        errors.append("docs do not mention E5/E6 publication guardrails")
    if "only e1/e2" not in lowered and "e1/e2 only" not in lowered and "e1 and e2 only" not in lowered:
        errors.append("docs do not explicitly state v0.1 includes only E1/E2")


def _check_leaderboard(errors: list[str]) -> None:
    schema_path = REPO_ROOT / "bench/leaderboard/v0.1.schema.json"
    data_path = REPO_ROOT / "bench/leaderboard/v0.1.json"
    if not schema_path.exists() or not data_path.exists():
        return
    try:
        jsonschema.validate(
            json.loads(data_path.read_text(encoding="utf-8")),
            json.loads(schema_path.read_text(encoding="utf-8")),
        )
    except jsonschema.ValidationError as exc:
        errors.append(f"leaderboard schema validation failed: {exc.message}")


def _check_public_data(errors: list[str]) -> None:
    for rel in (
        "datasets/public_mini/e5_sanitized.jsonl",
        "datasets/public_mini/e6_sanitized.jsonl",
        "docs/redteam-data-publication-policy.md",
    ):
        path = REPO_ROOT / rel
        if not path.exists():
            errors.append(f"missing safety/publication file: {rel}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "sanitized" not in text:
            errors.append(f"{rel} does not state sanitized handling")
    unsafe_public = [
        "raw harmful corpus",
        "weaponized payload",
        "real exploit instructions",
        "malware payload",
        "ransomware",
        "backdoor",
        "botnet",
        "explosive",
        "credential theft",
        "phishing kit",
        "ddos",
    ]
    for path in (REPO_ROOT / "datasets/public_mini").glob("e[56]*.jsonl"):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in unsafe_public:
            if phrase in text:
                errors.append(f"public mini data contains forbidden phrase `{phrase}` in {path}")


def _check_secrets(errors: list[str]) -> None:
    scan_roots = [
        "README.md",
        "SVBENCH_STATUS.md",
        "SVBENCH.md",
        "configs",
        "bench",
        "datasets",
        "docs",
        "results",
        "reports",
    ]
    for rel in scan_roots:
        path = REPO_ROOT / rel
        paths = [path] if path.is_file() else list(path.glob("**/*"))
        for item in paths:
            if not item.is_file() or item.suffix in {".pyc", ".png", ".jpg", ".jpeg"}:
                continue
            text = item.read_text(encoding="utf-8", errors="ignore")
            if SECRET_RE.search(text):
                errors.append(f"possible secret in {item.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SV-Bench v0.1 release package.")
    parser.add_argument("--strict", action="store_true", help="Run the offline package checks used by CI.")
    parser.add_argument(
        "--research-complete",
        action="store_true",
        help="Also require real E1/E2 heldout improvement and a matched E1 reward comparison.",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=REPO_ROOT / "results/research_completion.json",
        help="Research evidence index (required only with --research-complete).",
    )
    args = parser.parse_args()

    errors: list[str] = []
    _check_required_files(errors)
    if not errors:
        _check_scope_docs(errors)
        _check_leaderboard(errors)
        _check_public_data(errors)
        _check_secrets(errors)
    if args.research_complete:
        _check_research_completion(errors, args.evidence)

    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1
    print("✓ SV-Bench v0.1 offline release package checks passed")
    if args.research_complete:
        print("✓ E1/E2 research completion evidence checks passed; scientific review is still required")
    else:
        print("  Empirical research completion was not checked; use --research-complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
