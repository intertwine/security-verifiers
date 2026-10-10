"""Offline fixtures test reporting semantics; never research-completion evidence."""

import hashlib
import json

import pytest
from report_preserved_evaluation import bootstrap_delta, e1_score, e2_score, report, strict_output

COSTS = {"fn": 10.0, "fp": 1.0, "abstain": 1.0, "invalid": 10.0}


def test_strict_output_rejects_nested_malformed_and_reasoning_only():
    assert strict_output('{broken {"label":"Benign","confidence":.5}}', "e1") is None
    assert strict_output('<think>{"label":"Benign","confidence":0.5}</think>', "e1") is None
    assert strict_output('{"label":"Benign","confidence":true}', "e1") is None
    assert strict_output('{"label":"Benign","confidence":NaN}', "e1") is None
    assert strict_output('```json\n{"label":"Benign","confidence":0.5}\n```', "e1")


def test_losses_keep_abstain_invalid_missing_and_failure_visible():
    row = {"status": "completed", "completion": '{"label":"Benign","confidence":0.9}'}
    assert e1_score(row, "Malicious", COSTS)["expected_cost"] == 10
    assert e1_score(None, "Benign", COSTS)["status"] == "missing"
    assert e1_score({"status": "failed"}, "Benign", COSTS)["expected_cost"] == 10
    row["completion"] = '{"label":"Abstain","confidence":0.9}'
    assert e1_score(row, "Benign", COSTS)["expected_cost"] == 1


def test_bootstrap_pairing_and_reproducibility():
    pairs = [(10.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
    assert bootstrap_delta(pairs, 17, 1000) == bootstrap_delta(pairs, 17, 1000)
    assert bootstrap_delta(pairs, 17, 1000)["delta"] == pytest.approx(-11 / 3)
    assert bootstrap_delta([], 17, 1000)["ci95"] is None


def test_e2_requires_semantic_and_scanner_verification():
    row = {"status": "completed", "completion": '{"violations":[],"patch":"real patch","confidence":0.9}'}
    assert e2_score(row, None)["verified_patch_success"] is None
    verification = {
        "completion_sha256": hashlib.sha256(row["completion"].encode()).hexdigest(),
        "scanner_success": True,
        "structure_preserved": True,
        "semantic_preserved": False,
        "patch_sha256": hashlib.sha256(b"real patch").hexdigest(),
        "tool_versions": {"opa": "1"},
        "evidence_sha256": "a" * 64,
    }
    assert e2_score(row, verification, {"oracle": [{"id": "x"}]})["verified_patch_success"] == 0
    verification["completion_sha256"] = "wrong"
    with pytest.raises(ValueError, match="exact completion"):
        e2_score(row, verification, {"oracle": [{"id": "x"}]})


def fixture_run(tmp_path):
    cases = [
        {"case_id": "a", "question": "case a", "answer": "Benign"},
        {"case_id": "b", "question": "case b", "answer": "Malicious"},
    ]
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("".join(json.dumps(c) + "\n" for c in cases))
    policies = [{"role": "base", "model": "fixture-base"}, {"role": "exec", "model": "fixture-exec"}]
    packet = {
        "environments": {
            "e1": {
                "dataset": "cases.jsonl",
                "policies": policies,
                "limits": {},
                "case_independence_verified": False,
            }
        }
    }
    (tmp_path / "packet.json").write_text(json.dumps(packet))
    fingerprint = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    for policy in policies:
        folder = tmp_path / f"e1-{policy['role']}"
        folder.mkdir()
        (folder / "metadata.json").write_text(
            json.dumps(
                {
                    "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
                    "packet_sha256": fingerprint,
                    "policy": policy,
                    "limits": {},
                }
            )
        )
        result = [
            {
                "case_id": c["case_id"],
                "prompt": c["question"],
                "answer": c["answer"],
                "status": "completed",
                "completion": json.dumps({"label": c["answer"], "confidence": 0.9}),
            }
            for c in cases
        ]
        if policy["role"] == "exec":
            result.pop()
        (folder / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in result))
    return tmp_path


def test_missing_cases_never_disappear_from_denominator(tmp_path):
    folder = fixture_run(tmp_path)
    summary = report(folder, folder, resamples=100)
    section = summary["environments"]["e1"]
    assert section["policies"]["exec"]["metric_mean"] == 5
    assert section["policies"]["exec"]["missing_cases"] == 1
    assert section["comparisons"]["exec_minus_base"]["n_pairs"] == 1
    assert section["comparisons"]["exec_minus_base"]["excluded_pairs"] == 1
    assert summary["research_complete"] is False
    assert not section["independence_verified"]


def test_duplicate_and_mismatched_result_identity_rejected(tmp_path):
    folder = fixture_run(tmp_path)
    results = folder / "e1-base/results.jsonl"
    results.write_text(results.read_text() + results.read_text().splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        report(folder, folder, resamples=100)


def test_reference_mismatch_rejected(tmp_path):
    folder = fixture_run(tmp_path)
    results = folder / "e1-exec/results.jsonl"
    data = json.loads(results.read_text())
    data["answer"] = "Malicious"
    results.write_text(json.dumps(data) + "\n")
    with pytest.raises(ValueError, match="reference"):
        report(folder, folder, resamples=100)


def test_cost_contract_rejects_nan(tmp_path):
    with pytest.raises(ValueError, match="loss weights"):
        report(tmp_path, tmp_path, costs={**COSTS, "invalid": float("nan")})


def test_e2_finding_ids_cannot_be_inflated_by_repetition():
    row = {
        "status": "completed",
        "completion": json.dumps(
            {
                "violations": [{"id": "x", "severity": "high"}, {"id": "x", "severity": "high"}],
                "patch": "",
                "confidence": 0.9,
            }
        ),
    }
    score = e2_score(
        row, None, {"oracle": [{"id": "x", "severity": "high"}, {"id": "y", "severity": "high"}]}
    )
    assert score["finding_f1_unique_ids"] == pytest.approx(2 / 3)
    assert score["verified_patch_success"] is None


def test_linked_e2_evidence_missing_is_rejected(tmp_path):
    folder = fixture_run(tmp_path)
    verification = folder / "verification.jsonl"
    verification.write_text(
        json.dumps(
            {
                "policy_role": "exec",
                "case_id": "a",
                "evidence_path": "absent.json",
                "evidence_sha256": "a" * 64,
            }
        )
    )
    with pytest.raises(ValueError, match="evidence absent"):
        report(folder, folder, verification, resamples=100)


def test_lowercase_label_is_invalid_under_common_schema():
    assert strict_output('{"label":"benign","confidence":0.9}', "e1") is None


def test_vulnerable_no_patch_cannot_receive_success_even_with_attestation():
    row = {"status": "completed", "completion": '{"violations":[],"patch":"","confidence":0.9}'}
    witness = {
        "completion_sha256": hashlib.sha256(row["completion"].encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(b"").hexdigest(),
        "scanner_success": True,
        "structure_preserved": True,
        "semantic_preserved": True,
        "tool_versions": {"kube-linter": "actual"},
        "evidence_sha256": "a" * 64,
    }
    assert e2_score(row, witness, {"oracle": [{"id": "x"}]})["verified_patch_success"] == 0
    witness["patch_sha256"] = "wrong"
    with pytest.raises(ValueError, match="exact patch"):
        e2_score(row, witness, {"oracle": [{"id": "x"}]})


def test_clean_case_needs_separate_no_regression_protocol():
    row = {"status": "completed", "completion": '{"violations":[],"patch":"","confidence":0.9}'}
    witness = {
        "completion_sha256": hashlib.sha256(row["completion"].encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(b"").hexdigest(),
        "scanner_success": True,
        "structure_preserved": True,
        "semantic_preserved": True,
        "tool_versions": {"kube-linter": "actual"},
        "evidence_sha256": "a" * 64,
    }
    with pytest.raises(ValueError, match="no-regression"):
        e2_score(row, witness, {"oracle": []})
    witness.update(verification_protocol="clean-no-regression-v1", clean_no_regression_success=True)
    assert e2_score(row, witness, {"oracle": []})["verified_patch_success"] == 1


def test_finding_metric_uses_common_primary_tool_filter():
    row = {
        "status": "completed",
        "completion": json.dumps(
            {"violations": [{"id": "kube-linter/x", "severity": "high"}], "patch": "", "confidence": 0.9}
        ),
    }
    answer = {"fixture_type": "k8s", "oracle": [{"id": "kube-linter/x"}, {"id": "opa/y"}]}
    assert e2_score(row, None, answer)["finding_f1_unique_ids"] == 1
