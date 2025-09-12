"""Tests for the configuration verification environment."""

import json

import verifiers as vf
from sv_env_config_verification import (
    ConfigVerificationParser,
    analyze_firewall_rules,
    analyze_iam_policy,
    analyze_k8s_config,
    analyze_nginx_config,
    analyze_rego_policy,
    analyze_semgrep_code,
    analyze_ssh_config,
    load_environment,
    reward_correct_analysis,
)


class TestConfigVerificationParser:
    """Tests for the parser and format reward."""

    def test_parse_answer_structured(self):
        parser = ConfigVerificationParser()
        completion = (
            '{"violations":[{"id":"x","severity":"low"}],"patch":"","confidence":0.9}'
        )
        parsed = parser.parse_answer(completion)
        assert parsed["violations"][0]["id"] == "x"

    def test_parse_answer_invalid(self):
        parser = ConfigVerificationParser()
        assert parser.parse_answer("not json") == {}

    def test_format_reward(self):
        parser = ConfigVerificationParser()
        format_func = parser.get_format_reward_func()

        good = (
            '{"violations":[{"id":"a","severity":"high"}],"patch":"fix","confidence":1.0}'
        )
        partial = '{"violations":[],"confidence":1}'

        assert format_func(good) == 1.0
        assert format_func(partial) == 0.5
        assert format_func("plain text") == 0.0


def test_analyze_ssh_config():
    config = """
    Port 22
    PermitRootLogin yes
    PasswordAuthentication yes
    """
    result = analyze_ssh_config(config)
    assert any(v["id"] == "ssh-permit-root-login" for v in result["violations"])
    assert result["patch"]

    secure = """
    Port 2222
    PermitRootLogin no
    PasswordAuthentication no
    """
    result_secure = analyze_ssh_config(secure)
    assert result_secure["violations"] == []


def test_analyze_firewall_rules():
    rules = """
    allow tcp from 0.0.0.0/0 to any port 22
    allow all from any to any
    """
    result = analyze_firewall_rules(rules)
    ids = {v["id"] for v in result["violations"]}
    assert "fw-open-to-world" in ids and "fw-allow-all" in ids

    secure = """
    allow tcp from 192.168.1.0/24 to any port 22
    deny all from any to any
    """
    assert analyze_firewall_rules(secure)["violations"] == []


def test_additional_tools():
    iam = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"*","Resource":"*"}]}'
    nginx = "server {\n autoindex on;\n server_tokens on;\n}"
    rego = "package p\ndefault allow = true"
    k8s = (
        "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - image: a:latest\n    securityContext:\n      runAsUser: 0\n      privileged: true\n"
    )
    code = "eval('1')"
    secure_rego = "package p\ndefault allow = false\nallow { input.user == \"admin\" }"
    secure_k8s = (
        "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - image: a:v1\n    securityContext:\n      runAsUser: 1000\n      privileged: false\n"
    )
    secure_code = "print('ok')"
    assert analyze_iam_policy(iam)["violations"]
    assert analyze_nginx_config(nginx)["violations"]
    assert analyze_rego_policy(rego)["violations"]
    assert analyze_k8s_config(k8s)["violations"]
    assert analyze_semgrep_code(code)["violations"]
    assert analyze_rego_policy(secure_rego)["violations"] == []
    assert analyze_k8s_config(secure_k8s)["violations"] == []
    assert analyze_semgrep_code(secure_code)["violations"] == []


def test_reward_correct_analysis():
    config = "Port 22\nPermitRootLogin yes\nPasswordAuthentication yes"
    answer = analyze_ssh_config(config)
    completion = json.dumps(answer)

    reward = reward_correct_analysis(completion, answer, ["analyze_ssh_config"])
    assert reward > 0.9

    partial = json.dumps(
        {
            "violations": [answer["violations"][0]],
            "patch": "",
            "confidence": 0.5,
        }
    )
    partial_reward = reward_correct_analysis(partial, answer, None)
    assert 0.0 < partial_reward < reward


def test_load_environment():
    env = load_environment(max_examples=4)
    assert isinstance(env, vf.ToolEnv)
    assert env.tools and len(env.tools) == 7
    sample = env.dataset[0]
    assert "violations" in sample["answer"]
    assert "patch" in sample["answer"]
    assert "config_type" in sample
