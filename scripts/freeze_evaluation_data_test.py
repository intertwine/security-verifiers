"""Scientific provenance and identity regressions for frozen evaluation cases."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from freeze_evaluation_data import freeze


def data(tmp_path, name, rows):
    path = tmp_path / name
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def test_deduplicates_inputs_and_preserves_unknown_provenance(tmp_path):
    source = data(tmp_path, "source.jsonl", [{"question": "one", "answer": "a"}] * 2)
    manifest = freeze(source, tmp_path / "frozen", 1)
    assert manifest["duplicate_input_rows"] == 1
    assert manifest["heldout_verified"] is False
    assert manifest["independence_status"] == "case-independence-unverified"


def test_same_prompt_with_other_label_is_overlap(tmp_path):
    source = data(tmp_path, "source.jsonl", [{"question": "one", "answer": "a"}])
    train = data(tmp_path, "train.jsonl", [{"question": "one", "answer": "b"}])
    with pytest.raises(ValueError, match="only 0 eligible"):
        freeze(source, tmp_path / "frozen", 1, train)


def test_conflicting_candidate_labels_rejected(tmp_path):
    source = data(
        tmp_path, "source.jsonl", [{"question": "one", "answer": "a"}, {"question": "one", "answer": "b"}]
    )
    with pytest.raises(ValueError, match="contradictory"):
        freeze(source, tmp_path / "frozen", 1)


def test_retained_samples_never_establish_full_exclusion(tmp_path):
    source = data(tmp_path, "source.jsonl", [{"question": "heldout"}])
    train = data(tmp_path, "train.jsonl", [{"question": "train"}])
    provenance = tmp_path / "provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "dataset_sha256": hashlib.sha256(train.read_bytes()).hexdigest(),
                "coverage": "retained-training-samples",
            }
        )
    )
    assert freeze(source, tmp_path / "frozen", 1, train, provenance)["heldout_verified"] is False


def test_full_membership_checks_evidence_and_source_digest(tmp_path):
    source = data(tmp_path, "source.jsonl", [{"question": "heldout"}])
    train = data(tmp_path, "train.jsonl", [{"question": "train"}])
    evidence = tmp_path / "membership.txt"
    evidence.write_text("Example test attestation, not research evidence")
    provenance = tmp_path / "provenance.json"
    descriptor = {
        "dataset_sha256": hashlib.sha256(train.read_bytes()).hexdigest(),
        "coverage": "full-training-membership",
        "training_run_ids": ["test-run"],
        "source_revision": "a" * 40,
        "membership_evidence": {
            "path": evidence.name,
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        },
    }
    provenance.write_text(json.dumps(descriptor))
    result = freeze(source, tmp_path / "frozen", 1, train, provenance)
    assert result["heldout_verified"] is False
    assert result["claimed_full_membership"] is True
    evidence.write_text("tampered")
    with pytest.raises(ValueError, match="evidence checksum"):
        freeze(source, tmp_path / "other", 1, train, provenance)
    descriptor["dataset_sha256"] = "0" * 64
    provenance.write_text(json.dumps(descriptor))
    with pytest.raises(ValueError, match="dataset checksum"):
        freeze(source, tmp_path / "third", 1, train, provenance)


def test_output_is_immutable_and_deterministic(tmp_path):
    a = data(tmp_path, "a.jsonl", [{"question": "two"}, {"question": "one"}])
    b = data(tmp_path, "b.jsonl", [{"question": "one"}, {"question": "two"}])
    out = tmp_path / "frozen"
    assert freeze(a, out, 2)["dataset_sha256"] == freeze(b, tmp_path / "other", 2)["dataset_sha256"]
    with pytest.raises(ValueError, match="already exists"):
        freeze(a, out, 2)


@pytest.mark.parametrize("row", [{"question": ""}, {"question": None}, {"prompt": []}])
def test_empty_or_nontext_inputs_rejected(tmp_path, row):
    source = data(tmp_path, "source.jsonl", [row])
    with pytest.raises(ValueError, match="nonempty string"):
        freeze(source, tmp_path / "frozen", 1)
