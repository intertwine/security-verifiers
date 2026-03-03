"""Tests for the LLM-judge variant of the network log environment."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest
import verifiers as vf

from sv_env_network_logs_judge import (
    JUDGE_PROMPT,
    NetworkLogParser,
    judge_reward,
    load_environment,
)


class TestJudgeVariantParser:
    """Parser should be identical to the executable verifier variant."""

    def test_extracts_label_and_confidence(self) -> None:
        parser = NetworkLogParser()
        completion = '{"label": "Malicious", "confidence": 0.9, "rationale": "scan"}'
        assert parser.parse_answer(completion) == "Malicious"
        assert parser.parse_confidence(completion) == pytest.approx(0.9)

    def test_rejects_invalid_labels(self) -> None:
        parser = NetworkLogParser()
        assert parser.parse_answer('{"label": "Unknown"}') == ""


class TestJudgePrompt:
    """Verify the judge prompt has the required template variables."""

    def test_has_required_placeholders(self) -> None:
        assert "{question}" in JUDGE_PROMPT
        assert "{answer}" in JUDGE_PROMPT
        assert "{response}" in JUDGE_PROMPT

    def test_mentions_evaluation_criteria(self) -> None:
        prompt_lower = JUDGE_PROMPT.lower()
        assert "label" in prompt_lower
        assert "confidence" in prompt_lower
        assert "json" in prompt_lower


class TestJudgeReward:
    """Test the judge_reward function's response parsing."""

    def _run(self, coro):
        """Helper to run async functions in sync tests."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_yes_response(self) -> None:
        """Judge responding 'yes' should yield reward 1.0."""

        async def mock_judge(prompt, completion, answer, state):
            return "yes"

        result = self._run(judge_reward(prompt="test", completion="test", answer="test", state={}, judge=mock_judge))
        assert result == 1.0

    def test_no_response(self) -> None:
        """Judge responding 'no' should yield reward 0.0."""

        async def mock_judge(prompt, completion, answer, state):
            return "no"

        result = self._run(judge_reward(prompt="test", completion="test", answer="test", state={}, judge=mock_judge))
        assert result == 0.0

    def test_yes_with_trailing_text(self) -> None:
        """Judge responding 'Yes, the response...' should yield 1.0."""

        async def mock_judge(prompt, completion, answer, state):
            return "Yes, the response is correct."

        result = self._run(judge_reward(prompt="test", completion="test", answer="test", state={}, judge=mock_judge))
        assert result == 1.0

    def test_unexpected_response(self) -> None:
        """Unexpected judge response defaults to 0.0."""

        async def mock_judge(prompt, completion, answer, state):
            return "maybe"

        result = self._run(judge_reward(prompt="test", completion="test", answer="test", state={}, judge=mock_judge))
        assert result == 0.0


class TestLoadEnvironment:
    """Test environment loading with synthetic dataset.

    These tests require OPENAI_API_KEY because JudgeRubric creates an
    AsyncOpenAI client at init time. We set a dummy key for unit tests
    (the judge is never actually called).
    """

    @pytest.fixture(autouse=True)
    def _set_dummy_openai_key(self, monkeypatch):
        """Set a dummy OpenAI key so JudgeRubric can initialize."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")

    def _get_judge_rubric(self, env):
        """Extract the JudgeRubric from the env's RubricGroup wrapper."""
        rubric = env.rubric
        # SingleTurnEnv wraps rubrics in a RubricGroup
        if hasattr(rubric, "rubrics"):
            for r in rubric.rubrics:
                if isinstance(r, vf.JudgeRubric):
                    return r
        # Direct JudgeRubric (if verifiers changes wrapping behavior)
        if isinstance(rubric, vf.JudgeRubric):
            return rubric
        pytest.fail(f"No JudgeRubric found in env.rubric (type={type(rubric).__name__})")

    def test_load_with_synthetic_dataset(self) -> None:
        logger = Mock()
        logger.enabled = True

        env = load_environment(dataset_name="synthetic", max_examples=5, logger=logger)
        assert isinstance(env, vf.SingleTurnEnv)
        assert env.rubric is not None
        judge_rubric = self._get_judge_rubric(env)
        assert isinstance(judge_rubric, vf.JudgeRubric)
        assert env.dataset is not None
        assert len(env.dataset) > 0

        logger.log_environment_init.assert_called_once()
        call_kwargs = logger.log_environment_init.call_args.kwargs
        assert call_kwargs["environment_name"] == "sv-env-network-logs-judge"
        assert "synthetic" in call_kwargs["dataset_name"]
        assert call_kwargs["metadata"]["reward_type"] == "llm-judge"

    def test_rubric_has_judge_reward_func(self) -> None:
        env = load_environment(dataset_name="synthetic", max_examples=5)
        judge_rubric = self._get_judge_rubric(env)
        func_names = judge_rubric._get_reward_func_names()
        assert "judge_reward" in func_names

    def test_rubric_uses_correct_judge_model(self) -> None:
        env = load_environment(dataset_name="synthetic", max_examples=5)
        judge_rubric = self._get_judge_rubric(env)
        assert judge_rubric.judge_model == "gpt-4.1-nano"

    def test_custom_judge_model(self) -> None:
        env = load_environment(dataset_name="synthetic", max_examples=5, judge_model="gpt-4.1-mini")
        judge_rubric = self._get_judge_rubric(env)
        assert judge_rubric.judge_model == "gpt-4.1-mini"
