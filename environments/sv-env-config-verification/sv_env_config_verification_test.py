import verifiers as vf

from sv_env_config_verification import (
    ConfigVerificationParser,
    load_environment,
    reward_config_auditing,
)


class TestConfigVerification:
    def test_parser_and_format_reward(self) -> None:
        parser = ConfigVerificationParser()
        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":0.9}'
        parsed = parser.parse_answer(completion)
        assert parsed["violations"][0]["id"].startswith("kube-linter/")
        assert parser.get_format_reward_func()(completion) == 1.0

    def test_reward_no_patch(self) -> None:
        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":1.0}'
        answer = {
            "oracle": [{"id": "kube-linter/run-as-root", "severity": "high"}],
            "fixture_path": "",
            "fixture_type": "k8s",
        }
        reward = reward_config_auditing(completion, answer)
        assert reward > 0.9

    def test_load_environment(self) -> None:
        env = load_environment(max_examples=1)
        assert isinstance(env, vf.ToolEnv)
        sample = env.dataset[0]
        assert "oracle" in sample["answer"]
