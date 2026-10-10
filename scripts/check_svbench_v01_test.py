from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_svbench_v01 as checker  # noqa: E402


def _write(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[Path, dict]:
    """Synthetic valid evidence for testing the contract, never reportable research."""
    index = {}
    for env in ("e1", "e2"):
        fixture = json.loads((checker.REPO_ROOT / f"bench/fixtures/{env}_run_manifest.json").read_text())
        metric = "detection.accuracy" if env == "e1" else "finding_quality.f1_weighted"
        group, name = metric.split(".")
        experiment = {"metric": metric, "direction": "higher"}
        variants = ["baseline", "trained", "training"]
        if env == "e1":
            variants += ["judge", "judge_training"]
        for variant in variants:
            manifest = copy.deepcopy(fixture)
            training = variant.endswith("training")
            manifest.update(
                run_id=f"{env}-{variant}",
                git_sha="a" * 40,
                dataset_revision="b" * 40,
                dataset_sha256=("c" if training else "d") * 64,
                split="train" if training else "heldout",
                reward_config_hash="e" * 64,
                model_revision_or_digest="a" * 64
                if training or variant == "baseline"
                else ("c" if variant == "judge" else "b") * 64,
                model_id="test-model",
                reward_source="llm_judge" if variant == "judge_training" else "executable",
                max_steps=10 if training else 0,
                trainer="grpo" if training else "none",
                tool_backends=["semgrep:1.2.3"],
                heldout_overlap_count=0,
                trained_model_revision_or_digest=("c" if variant == "judge_training" else "b") * 64,
            )
            manifest["metadata_json_path"] = _write(tmp_path / f"{env}-{variant}-metadata.json", {})
            manifest["metrics_summary_path"] = _write(
                tmp_path / f"{env}-{variant}-metrics.json",
                {"metrics": {group: {name: 0.5 if variant == "baseline" else 0.7}}},
            )
            manifest["results_jsonl_path"] = _write(tmp_path / f"{env}-{variant}-results.jsonl", {"id": 1})
            if training:
                manifest["training_settings"] = {
                    "batch_size": 16,
                    "lora": {"rank": 16, "alpha": 32},
                    "optimizer": {"name": "adamw", "learning_rate": 1e-5},
                }
                manifest["learning_curve_path"] = _write(
                    tmp_path / f"{env}-{variant}-curve.json",
                    {
                        "run_id": manifest["run_id"],
                        "planned_steps": 10,
                        "completed_steps": 10,
                        "points": [{"step": 0, "value": 0.5}, {"step": 10, "value": 0.7}],
                    },
                )
            experiment[f"{variant}_manifest"] = _write(tmp_path / f"{env}-{variant}.json", manifest)
        train_ids = _write(tmp_path / f"{env}-train-ids.json", ["train-1"])
        heldout_ids = _write(tmp_path / f"{env}-heldout-ids.json", ["heldout-1"])
        experiment["split_provenance"] = _write(
            tmp_path / f"{env}-split-provenance.json",
            {
                "train_dataset_sha256": "c" * 64,
                "heldout_dataset_sha256": "d" * 64,
                "train_ids_path": train_ids,
                "heldout_ids_path": heldout_ids,
            },
        )
        index[env] = experiment
    path = tmp_path / "research_completion.json"
    _write(path, index)
    return path, index


def _mutate(index: dict, env: str, variant: str, **changes: object) -> None:
    path = Path(index[env][f"{variant}_manifest"])
    data = json.loads(path.read_text())
    data.update(changes)
    _write(path, data)


def test_valid_completion_contract(evidence: tuple[Path, dict]) -> None:
    errors: list[str] = []
    checker._check_research_completion(errors, evidence[0])
    assert errors == []


def test_absent_empirical_evidence_is_actionable(tmp_path: Path) -> None:
    errors: list[str] = []
    checker._check_research_completion(errors, tmp_path / "research_completion.json")
    assert "research_completion.json" in errors[0]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"dataset_revision": "public-mini-v1"}, "smoke-only"),
        ({"model_revision_or_digest": "prime-hosted"}, "unresolved"),
        ({"split": "train"}, "heldout/test"),
        ({"reward_config_hash": "pending"}, "digest required"),
        ({"dataset_sha256": ""}, "dataset_sha256 required"),
        ({"results_jsonl_path": "missing.jsonl"}, "missing or empty"),
    ],
)
def test_rejects_smoke_and_missing_provenance(
    evidence: tuple[Path, dict], changes: dict, message: str
) -> None:
    path, index = evidence
    _mutate(index, "e1", "baseline", **changes)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert message in errors[0]


def test_rejects_mismatched_reward_training_budget(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "judge_training", max_tokens=8192)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "reward comparison: unmatched fields: max_tokens" in errors[0]


def test_rejects_different_judge_evaluator(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "judge", reward_config_hash="f" * 64)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "common scorer: unmatched fields: reward_config_hash" in errors[0]


def test_rejects_missing_backend_provenance(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e2", "trained", tool_backends=[])
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "tool_backends provenance required" in errors[0]


def test_rejects_no_heldout_gain(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    manifest = json.loads(Path(index["e2"]["trained_manifest"]).read_text())
    _write(Path(manifest["metrics_summary_path"]), {"metrics": {"finding_quality": {"f1_weighted": 0.5}}})
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "no positive heldout improvement" in errors[0]


def test_rejects_training_reward_as_task_metric(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    index["e1"]["metric"] = "avg@1"
    _write(path, index)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "independent task metric" in errors[0]


def test_rejects_unlinked_checkpoint(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "training", trained_model_revision_or_digest="pending")
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "reference the training checkpoint" in errors[0]


def test_rejects_train_heldout_overlap(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e2", "training", heldout_overlap_count=1)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "heldout_overlap_count=0" in errors[0]


def test_rejects_nonfinite_metric(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    manifest = json.loads(Path(index["e1"]["trained_manifest"]).read_text())
    _write(Path(manifest["metrics_summary_path"]), {"metrics": {"detection": {"accuracy": float("nan")}}})
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "missing finite heldout metric" in errors[0]


def test_rejects_same_base_and_trained_checkpoint(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "trained", model_revision_or_digest="a" * 64)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "checkpoint digests must differ" in errors[0]


def test_rejects_incomplete_hosted_training(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "training", platform_mode="hosted")
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "hosted run must be COMPLETED" in errors[0]


def test_checks_actual_split_ids_despite_zero_overlap_declaration(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    provenance = json.loads(Path(index["e1"]["split_provenance"]).read_text())
    _write(Path(provenance["heldout_ids_path"]), ["train-1"])
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "training and heldout IDs overlap" in errors[0]


def test_rejects_reward_alias_as_operational_metric(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    index["e1"]["metric"] = "my_custom_reward"
    _write(path, index)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "supported independent task metric" in errors[0]


def test_rejects_wrong_metric_direction(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    index["e1"]["direction"] = "lower"
    _write(path, index)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "incorrect improvement direction" in errors[0]


@pytest.mark.parametrize(
    ("env", "changes", "message"),
    [
        ("e1", {"git_sha": "f" * 40}, "heldout: unmatched fields: git_sha"),
        ("e2", {"tool_backends": ["fallback:1.2.3"]}, "scanner backend/version"),
    ],
)
def test_rejects_changed_evaluator(
    evidence: tuple[Path, dict], env: str, changes: dict, message: str
) -> None:
    path, index = evidence
    _mutate(index, env, "trained", **changes)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert message in errors[0]


@pytest.mark.parametrize("field", ["batch_size", "lora", "optimizer"])
def test_rejects_mismatched_training_settings(evidence: tuple[Path, dict], field: str) -> None:
    path, index = evidence
    manifest = json.loads(Path(index["e1"]["judge_training_manifest"]).read_text())
    settings = manifest["training_settings"]
    settings[field] = 32 if field == "batch_size" else {"changed": True}
    _mutate(index, "e1", "judge_training", training_settings=settings)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "reward comparison: unmatched fields: training_settings" in errors[0]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"points": [{"step": 10, "value": 0.7}]}, "two distinct steps"),
        ({"completed_steps": 9}, "completed non-smoke planned budget"),
        ({"run_id": "another-run"}, "reference the training run"),
    ],
)
def test_rejects_inadequate_learning_curve(evidence: tuple[Path, dict], changes: dict, message: str) -> None:
    path, index = evidence
    manifest = json.loads(Path(index["e1"]["training_manifest"]).read_text())
    curve_path = Path(manifest["learning_curve_path"])
    curve = json.loads(curve_path.read_text())
    curve.update(changes)
    _write(curve_path, curve)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert message in errors[0]


def test_rejects_one_step_training_pilot(evidence: tuple[Path, dict]) -> None:
    path, index = evidence
    _mutate(index, "e1", "training", max_steps=1)
    errors: list[str] = []
    checker._check_research_completion(errors, path)
    assert "completed non-smoke planned budget" in errors[0]
