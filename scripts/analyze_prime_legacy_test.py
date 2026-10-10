"""Tests for evidence boundaries in offline legacy analysis."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_prime_legacy import completion_text, e1_metrics, e1_record, summarize_run  # noqa: E402


def sample(label="Benign", confidence=0.9, answer="Benign", **extra):
    return {
        "completion": [
            {"role": "assistant", "content": json.dumps({"label": label, "confidence": confidence})}
        ],
        "answer": answer,
        **extra,
    }


def test_reasoning_channel_is_explicitly_separate():
    record = sample()
    record["completion"][0]["reasoning_content"] = record["completion"][0].pop("content")
    assert e1_record(record, False) is None
    assert e1_record(record, True)["prediction"] == "benign"
    assert e1_metrics([record])["n_unparseable_or_unlabeled"] == 1


def test_never_scrape_tool_observation_as_prediction():
    record = sample()
    record["completion"][0]["role"] = "tool"
    assert completion_text(record, True) == ""


@pytest.mark.parametrize("confidence", [True, -1, 1.1, float("nan"), "0.9"])
def test_invalid_confidence_is_not_repaired(confidence):
    assert e1_record(sample(confidence=confidence), False) is None


def test_malformed_json_is_not_regex_salvaged():
    record = sample()
    record["completion"][0]["content"] = '{"label":"Benign", "confidence":0.9, "rationale":"broken}'
    assert e1_record(record, False) is None


def test_malformed_outer_json_is_not_salvaged_from_nested_object():
    record = sample()
    record["completion"][0]["content"] = '{"broken":, "nested":{"label":"Benign","confidence":0.9}}'
    assert e1_record(record, False) is None


def test_denominators_and_undefined_metrics_are_explicit():
    data = e1_metrics([sample(), sample("Abstain"), {"answer": "Benign"}])
    assert data["n_samples"] == 3
    assert data["n_parseable_labeled"] == 2
    assert data["n_non_abstained"] == 1
    assert data["accuracy_non_abstained"] == 1
    assert data["correct_fraction_all_samples"] == pytest.approx(1 / 3)
    assert data["tpr_non_abstained"] is None
    assert data["brier_correctness_non_abstained"] == pytest.approx(0.01)


def test_fn_cost_and_calibration_use_correctness():
    data = e1_metrics([sample(answer="Malicious"), sample("Malicious", answer="Benign")])
    assert data["confusion"]["fn"] == data["confusion"]["fp"] == 1
    assert data["cost_total_non_abstained"] == 11
    assert data["brier_correctness_non_abstained"] == pytest.approx(0.81)


def test_retains_colliding_sample_ids_and_records_training_boundary(tmp_path):
    path = tmp_path / "team" / "training_runs" / "run"
    path.mkdir(parents=True)
    (path / "metadata.json").write_text(
        json.dumps(
            {"id": "run", "status": "COMPLETED", "environments": [{"id": "intertwine/sv-env-network-logs"}]}
        )
    )
    records = [
        sample(step=0, problem_id=5, sample_id=0, reward=1),
        sample("Malicious", step=0, problem_id=5, sample_id=0, reward=0),
    ]
    (path / "results.jsonl").write_text("\n".join(json.dumps(r) for r in records))
    data = summarize_run(path)
    assert data["n_samples"] == 2
    assert data["unique_problem_ids"] == 1
    assert data["heldout_evidence"] is False
    assert data["sample_curve"][0]["mean_archived_reward"] == 0.5
