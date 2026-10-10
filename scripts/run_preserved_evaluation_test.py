"""Offline safety contracts for the preserved-adapter experiment runner."""

import copy
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run_preserved_evaluation as runner  # noqa: E402


@pytest.fixture
def packet():
    return json.loads((runner.ROOT / "configs/eval/preserved-primary-20261010.json").read_text())


def test_default_packet_is_800_episodes_and_explicitly_blocked(packet, tmp_path):
    checked = runner.validate(packet, tmp_path)
    assert checked["episodes"] == 800
    assert checked["output_token_bound"] == 2048000
    assert "launch_ready" in checked["launch_blockers"]
    with pytest.raises(runner.Blocked, match="Launch blocked"):
        runner.validate(packet, tmp_path, launch=True)


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity"])
def test_invalid_money_rejected(value):
    with pytest.raises(runner.Blocked):
        runner.number(value, "rate")


def billing():
    return {
        "hard_cap_usd": "0.01",
        "input_usd_per_million": "1",
        "output_usd_per_million": "1",
        "fixed_charges_usd": "0.001",
    }


def test_durable_reservation_before_call_and_no_refunds(tmp_path):
    ledger = runner.Ledger(tmp_path / "budget.jsonl", billing())
    ledger.request("failed-request", 4000, 3000)
    restored = runner.Ledger(tmp_path / "budget.jsonl", billing())
    assert restored.spent == Decimal("0.008")
    with pytest.raises(runner.Blocked, match="envelope exhausted"):
        restored.request("next", 2000, 1000)
    assert len(runner.read_rows(restored.path)) == 2


def test_matrix_and_limits_cannot_silently_expand(packet, tmp_path):
    packet["environments"]["e1"]["case_count"] = 201
    with pytest.raises(runner.Blocked, match="primary matrix"):
        runner.validate(packet, tmp_path)
    packet["environments"]["e1"]["case_count"] = 200
    packet["environments"]["e2"]["limits"]["tool_calls_per_episode"] = 4
    with pytest.raises(runner.Blocked, match="tool cap"):
        runner.validate(packet, tmp_path)


def test_dataset_checksum_and_duplicate_case_protection(packet, tmp_path):
    rows = [
        {"case_id": hashlib.sha256(str(i).encode()).hexdigest(), "question": str(i), "answer": "Benign"}
        for i in range(200)
    ]
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("\n".join(map(json.dumps, rows)))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"dataset_sha256": "wrong", "heldout_verified": True}))
    packet["environments"]["e1"].update(dataset=str(dataset), manifest=str(manifest))
    with pytest.raises(runner.Blocked, match="checksum"):
        runner.validate(packet, tmp_path)
    rows[-1]["case_id"] = rows[0]["case_id"]
    dataset.write_text("\n".join(map(json.dumps, rows)))
    with pytest.raises(runner.Blocked, match="identities invalid"):
        runner.validate(packet, tmp_path)


def make_client(responses):
    calls = []

    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        raw = responses.pop(0)
        return SimpleNamespace(model_dump=lambda **_: raw)

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


def setup_episode(tmp_path, packet, env="e1"):
    (tmp_path / "system_prompt.txt").write_text("Return strict JSON.")
    block = packet["environments"][env]
    block["limits"]["input_tokens_per_request"] = 8000
    ledger = runner.Ledger(tmp_path / "budget.jsonl", {**billing(), "hard_cap_usd": "1"})
    row = {"case_id": "a" * 64, "question": "Flow", "answer": "Benign", "info": {}}
    return block, ledger, row


def response(content="{}", used=3, tools=None):
    message = {"role": "assistant", "content": content}
    if tools:
        message["tool_calls"] = tools
    return {"choices": [{"message": message}], "usage": {"completion_tokens": used, "prompt_tokens": 100}}


def test_episode_retains_raw_response_and_reserves_before_network(packet, tmp_path):
    block, ledger, row = setup_episode(tmp_path, packet)
    client, calls = make_client([response()])
    result = runner.episode(client, {"model": "private-adapter"}, row, block, ledger, tmp_path, "test")
    assert result["status"] == "completed"
    assert calls[0]["max_tokens"] == 2048
    assert len(runner.read_rows(tmp_path / "requests.jsonl")) == 1
    assert runner.read_rows(ledger.path)[-1]["identity"] == "test:0"


def test_missing_usage_stops_instead_of_resetting_token_cap(packet, tmp_path):
    block, ledger, row = setup_episode(tmp_path, packet)
    raw = response()
    raw["usage"] = None
    client, calls = make_client([raw])
    with pytest.raises(runner.Blocked, match="usage absent"):
        runner.episode(client, {"model": "test"}, row, block, ledger, tmp_path, "id")
    assert len(calls) == 1
    assert len(runner.read_rows(tmp_path / "requests.jsonl")) == 1


def test_oversize_input_has_no_network_call_or_request_reservation(packet, tmp_path):
    block, ledger, row = setup_episode(tmp_path, packet)
    row["question"] = "x" * 9000
    client, calls = make_client([])
    result = runner.episode(client, {"model": "test"}, row, block, ledger, tmp_path, "id")
    assert result["status"] == "input_cap"
    assert calls == []
    assert len(runner.read_rows(ledger.path)) == 1  # Fixed costs only.


def test_e2_aggregate_output_cap_and_fixture_path_confinement(packet, tmp_path, monkeypatch):
    block, ledger, row = setup_episode(tmp_path, packet, "e2")
    tool_calls = [
        {
            "id": "one",
            "type": "function",
            "function": {"name": "run_kubelinter", "arguments": '{"paths":["/etc/passwd"]}'},
        }
    ]
    client, calls = make_client([response(used=1000, tools=tool_calls), response(used=20)])
    observed = []
    row["question"] = "apiVersion: v1\nkind: Pod\n"
    monkeypatch.setattr(runner, "tool_schema", lambda: [{"function": {"name": "run_kubelinter"}}])
    monkeypatch.setattr(runner, "run_tool", lambda name, path, timeout, rules: observed.append(path) or [])
    result = runner.episode(client, {"model": "test"}, row, block, ledger, tmp_path, "id")
    assert [c["max_tokens"] for c in calls] == [4096, 3096]
    assert str(observed[0]).startswith(str(tmp_path.parent / "fixtures"))
    assert result["tool_interactions"][0]["observation"] == []


def test_resume_changed_packet_rejected_before_credentials(packet, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    (output / "packet.json").write_text('{"different":true}')
    with pytest.raises(runner.Blocked, match="Resume packet differs"):
        runner.execute(packet, tmp_path, output, {"datasets": {}})


def test_exact_case_hash_prevents_fixture_path_traversal(packet, tmp_path):
    rows = [
        {"case_id": hashlib.sha256(str(i).encode()).hexdigest(), "question": str(i), "answer": "Benign"}
        for i in range(200)
    ]
    rows[0]["case_id"] = "../outside"
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("\n".join(map(json.dumps, rows)))
    packet["environments"]["e1"]["dataset"] = str(dataset)
    with pytest.raises(runner.Blocked, match="hash exact prompts"):
        runner.validate(packet, tmp_path)


def test_environment_identity_and_extra_arm_rejected(packet, tmp_path):
    packet["environments"]["e2"]["environment"] = "e1"
    with pytest.raises(runner.Blocked, match="block identity"):
        runner.validate(packet, tmp_path)
    packet["environments"]["e2"]["environment"] = "e2"
    packet["environments"]["extra"] = packet["environments"]["e2"]
    with pytest.raises(runner.Blocked, match="Only primary"):
        runner.validate(packet, tmp_path)


def test_team_scope_and_partial_scanner_inventory_are_launch_blockers(packet, tmp_path):
    packet["billing"]["workspace_scope_verified"] = True
    packet["billing"]["request_headers"] = {}
    packet["environments"]["e2"]["tool_versions"] = {"semgrep": "1.0"}
    checked = runner.validate(packet, tmp_path)
    assert "billing.team_header" in checked["launch_blockers"]
    assert "e2.tool_versions" in checked["launch_blockers"]


def test_fixture_wrapper_extracts_raw_config_and_rejects_ambiguous_text():
    content = 'resource "aws_s3_bucket" "x" {}'
    row = {"question": f"File path: /old/file.tf\n\nConfiguration:\n```text\n{content}\n```"}
    assert runner.fixture_content(row) == (content, "tf")
    with pytest.raises(runner.Blocked, match="ambiguous"):
        runner.fixture_content({"question": "Please inspect this."})


def test_hashed_identity_receipt_detects_mutation(tmp_path):
    receipt = tmp_path / "identity.json"
    receipt.write_text('{"base_revision":"abc"}')
    evidence = {"path": str(receipt), "sha256": runner.digest(receipt)}
    assert runner.verify_evidence(evidence, tmp_path, "identity")["base_revision"] == "abc"
    receipt.write_text('{"base_revision":"changed"}')
    with pytest.raises(runner.Blocked, match="checksum differs"):
        runner.verify_evidence(evidence, tmp_path, "identity")


def test_frozen_source_fingerprints_include_prompt_and_review_receipt(packet, tmp_path):
    for env, block in packet["environments"].items():
        for key in ("dataset", "manifest", "system_prompt_file"):
            path = tmp_path / f"{env}-{key}"
            path.write_text("{}")
            block[key] = str(path)
    review = tmp_path / "review.json"
    review.write_text("{}")
    packet["environments"]["e1"]["scientific_review_evidence"] = {
        "path": str(review),
        "sha256": runner.digest(review),
    }
    before = runner.source_fingerprints(packet, tmp_path)
    review.write_text('{"changed":true}')
    assert runner.source_fingerprints(packet, tmp_path) != before


def test_prime_key_cannot_be_sent_to_other_destination_or_overridden(packet, tmp_path):
    packet["billing"]["endpoint"] = "https://untrusted.example/api/v1"
    with pytest.raises(runner.Blocked, match="official Prime"):
        runner.validate(packet, tmp_path)
    packet["billing"]["endpoint"] = "https://api.pinference.ai/api/v1"
    packet["billing"]["request_headers"]["Authorization"] = "override"
    with pytest.raises(runner.Blocked, match="Only explicit team"):
        runner.validate(packet, tmp_path)


def test_yaml_reordered_keys_and_terraform_copyright_comments_supported():
    yaml = "kind: Pod\napiVersion: v1\nmetadata:\n  name: example\n"
    assert runner.fixture_content({"question": yaml}) == (yaml, "k8s")
    tf = '# Copyright\n\nprovider "aws" {}'
    assert runner.fixture_content({"question": tf}) == (tf, "tf")
    assert not runner.recognizable_fixture({"question": '{{- include "chart" . }}\napiVersion: v1\n'})


def test_identity_receipt_bound_to_selected_policy(packet, tmp_path):
    receipt = tmp_path / "identity.json"
    receipt.write_text(
        json.dumps({"model": "different-model", "base_revision": None, "adapter_sha256": None})
    )
    packet["environments"]["e1"]["policies"][0]["identity_evidence"] = {
        "path": str(receipt),
        "sha256": runner.digest(receipt),
    }
    with pytest.raises(runner.Blocked, match="differs from selected policy"):
        runner.validate(packet, tmp_path)


def test_scientific_attestation_cannot_allow_training_overlap(packet, tmp_path):
    rows = [
        {"case_id": hashlib.sha256(str(i).encode()).hexdigest(), "question": str(i), "answer": "Benign"}
        for i in range(200)
    ]
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text("\n".join(map(json.dumps, rows)))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"dataset_sha256": runner.digest(dataset), "heldout_verified": True}))
    block = packet["environments"]["e1"]
    block.update(dataset=str(dataset), manifest=str(manifest), case_independence_verified=True)
    membership = tmp_path / "membership.json"
    membership.write_text(
        json.dumps(
            {
                "training_run_ids": [p["training_run_id"] for p in block["policies"] if p["role"] != "base"],
                "case_ids": [rows[0]["case_id"]],
            }
        )
    )
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "status": "approved",
                "reviewer": "independent-reviewer",
                "dataset_sha256": runner.digest(dataset),
                "heldout_verified": True,
                "case_independence_verified": True,
                "training_membership_evidence": {
                    "path": str(membership),
                    "sha256": runner.digest(membership),
                },
            }
        )
    )
    block["scientific_review_evidence"] = {"path": str(review), "sha256": runner.digest(review)}
    with pytest.raises(runner.Blocked, match="prompts overlap"):
        runner.validate(packet, tmp_path)
