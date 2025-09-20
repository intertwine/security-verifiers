"""Test suite for the config auditing environment."""

import verifiers as vf
from sv_env_config_verification import (
    ConfigVerificationParser,
    load_environment,
    reward_config_auditing,
)


class TestConfigVerification:
    """Test suite for the config auditing environment."""

    def test_parser_and_format_reward(self) -> None:
        """Test parser and format reward."""

        parser = ConfigVerificationParser()
        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":0.9}'  # pylint: disable=line-too-long
        parsed = parser.parse_answer(completion)
        assert parsed["violations"][0]["id"].startswith("kube-linter/")
        assert parser.get_format_reward_func()(completion) == 1.0

    def test_reward_no_patch(self) -> None:
        """Test reward with no patch."""

        completion = '{"violations":[{"id":"kube-linter/run-as-root","severity":"high"}],"patch":"","confidence":1.0}'  # pylint: disable=line-too-long
        answer = {
            "oracle": [{"id": "kube-linter/run-as-root", "severity": "high"}],
            "fixture_path": "",
            "fixture_type": "k8s",
        }
        reward = reward_config_auditing(completion, answer)
        assert reward > 0.9

    def test_load_environment(self) -> None:
        """Test loading the environment."""
        # Load environment without tools to avoid schema validation issues with agents SDK
        # The core functionality (dataset, parser, rubric) can still be tested
        env = load_environment(max_examples=1, include_tools=False)
        assert isinstance(env, vf.ToolEnv)
        assert env.dataset is not None, "Dataset should not be None"
        assert len(env.dataset) > 0, "Dataset should not be empty"
        sample = env.dataset[0]
        assert "answer" in sample, f"Sample should have 'answer' key, got keys: {list(sample.keys())}"  # pylint: disable=line-too-long
        assert sample["answer"] is not None, "Answer should not be None"
        assert "oracle" in sample["answer"], (
            f"Answer should have 'oracle' key, got keys: {list(sample['answer'].keys())}"
        )  # pylint: disable=line-too-long
