"""Offline regressions for patch deletion and duplicate-detection gaming."""

import pytest
import yaml

import env as auditing_env
from adapters.types import ToolFinding, Violation
from patching import preserves_config_structure
from reward import final_reward

POD = """apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: server
      image: nginx:latest
"""


def test_valid_image_fix_preserves_resource_and_container() -> None:
    assert preserves_config_structure(POD, POD.replace("nginx:latest", "nginx:1.27"), "k8s")


def test_deleting_resource_or_container_does_not_qualify_as_fix() -> None:
    assert not preserves_config_structure(POD, "", "k8s")
    assert not preserves_config_structure(POD, POD[: POD.index("spec:")], "k8s")
    assert not preserves_config_structure(POD, POD.replace("name: app", "name: other"), "k8s")


def test_relocated_container_in_unrelated_field_cannot_preserve_workload() -> None:
    patched = yaml.safe_load(POD)
    patched["not_a_workload"] = {"containers": patched["spec"]["containers"]}
    patched["spec"] = {}
    assert not preserves_config_structure(POD, yaml.safe_dump(patched), "k8s")


def test_list_resources_cannot_disappear() -> None:
    listing = yaml.safe_dump({"apiVersion": "v1", "kind": "List", "items": [yaml.safe_load(POD)]})
    assert preserves_config_structure(listing, POD, "k8s")
    assert not preserves_config_structure(POD, "apiVersion: v1\nkind: List\nitems: []\n", "k8s")


def test_malformed_yaml_has_no_patch_credit() -> None:
    assert not preserves_config_structure(POD, "spec: [", "k8s")


def test_terraform_resource_deletion_is_rejected_but_acl_fix_is_allowed() -> None:
    original = 'resource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n'
    assert preserves_config_structure(original, original.replace("public-read", "private"), "tf")
    assert not preserves_config_structure(original, "# removed\n", "tf")
    assert not preserves_config_structure(original, original.replace('"data"', '"other"'), "tf")


@pytest.mark.parametrize("prefix,suffix", [("/*\n", "\n*/"), ("// ", ""), ("# ", "")])
def test_commented_terraform_declaration_does_not_preserve_resource(prefix, suffix) -> None:
    original = 'resource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n'
    assert not preserves_config_structure(original, prefix + original + suffix, "tf")


def test_terraform_comment_markers_in_quoted_strings_are_not_comments() -> None:
    original = 'resource "aws_s3_bucket" "data" {\n  note = "// # /* \\" quoted */"\n}\n'
    patched = "// header\n" + original + "\n/* footer */\n"
    assert preserves_config_structure(original, patched, "tf")


@pytest.mark.parametrize("heredoc", ["<<EOT", "<<-EOT"])
def test_terraform_heredoc_cannot_spoof_preserved_resource(heredoc) -> None:
    original = 'resource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n'
    patched = f"locals {{ bait = {heredoc}\n{original}EOT\n}}\n"
    assert not preserves_config_structure(original, patched, "tf")


def test_terraform_multiline_or_unterminated_quoted_string_cannot_spoof_resource() -> None:
    original = 'resource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n'
    assert not preserves_config_structure(original, f'locals {{ bait = "\n{original}"\n}}', "tf")
    assert not preserves_config_structure(original, original + 'locals { bait = "unterminated', "tf")


def test_repeated_correct_finding_cannot_hide_missing_rule() -> None:
    correct = Violation(id="kube-linter/test1", severity="high")
    oracle = [correct, Violation(id="kube-linter/test2", severity="high")]
    assert final_reward([correct] * 100, oracle) == final_reward([correct], oracle)


def test_repeated_false_finding_uses_max_severity_independent_of_order() -> None:
    correct = Violation(id="kube-linter/test1", severity="high")
    low = Violation(id="kube-linter/false1", severity="low")
    high = Violation(id="kube-linter/false1", severity="high")
    expected = final_reward([correct, high], [correct])
    assert final_reward([correct, high, low], [correct]) == expected
    assert final_reward([correct, low, high], [correct]) == expected


@pytest.mark.parametrize("replacement", ["", "apiVersion: v1\nkind: Pod\nmetadata:\n  name: app\n"])
def test_environment_does_not_scan_or_reward_deleted_workload(tmp_path, monkeypatch, replacement) -> None:
    path = tmp_path / "pod.yaml"
    path.write_text(POD)
    instance = object.__new__(auditing_env.ConfigAuditingEnv)
    instance.fixture_path = str(path)
    instance.fixture_type = "k8s"
    instance.oracle = [{"id": "kube-linter/latest-tag", "severity": "med"}]
    monkeypatch.setattr(auditing_env, "try_apply_patch", lambda *_: (True, replacement))

    def unexpected_scan(*_):
        pytest.fail("deleted workload must not be scanned for removal credit")

    monkeypatch.setattr(auditing_env, "kubelinter_lint", unexpected_scan)
    output = instance.step(
        {
            "violations": [{"id": "kube-linter/latest-tag", "severity": "med"}],
            "patch": "nonempty patch",
            "confidence": 1.0,
        }
    )
    assert output["reward"] == 1.05  # detection only; no patch-removal bonus


def test_environment_noop_patch_has_no_removal_credit_and_keeps_yaml_suffix(tmp_path, monkeypatch) -> None:
    path = tmp_path / "pod.yaml"
    path.write_text(POD)
    instance = object.__new__(auditing_env.ConfigAuditingEnv)
    instance.fixture_path = str(path)
    instance.fixture_type = "k8s"
    instance.oracle = [{"id": "kube-linter/latest-tag", "severity": "med"}]
    monkeypatch.setattr(auditing_env, "try_apply_patch", lambda *_: (True, POD))

    def scan(paths):
        assert paths[0].endswith(".yaml")
        return [ToolFinding(tool="kube-linter", rule_id="latest-tag", severity="med", message="latest")]

    monkeypatch.setattr(auditing_env, "kubelinter_lint", scan)
    output = instance.step(
        {
            "violations": [{"id": "kube-linter/latest-tag", "severity": "med"}],
            "patch": "nonempty patch",
            "confidence": 1.0,
        }
    )
    assert output["reward"] == 1.05
