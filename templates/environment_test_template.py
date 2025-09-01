"""Tests for the environment.

Copy this file to environments/<env-name>/<env_name_with_underscores>_test.py
and implement the test cases.
"""

# disable pylint checking for this template file
# pylint: disable=all
from unittest.mock import patch

import pytest
import verifiers as vf
from datasets import Dataset

# TODO: Update import to match your environment module name
from my_environment import MyParser, load_environment, reward_correct_answer


class TestMyParser:
    """Test cases for the parser class."""

    def test_parse_answer_valid(self):
        """Test parsing valid responses."""
        parser = MyParser()
        # TODO: Add test cases for valid inputs
        assert parser.parse_answer("Valid response") == "Valid response"

    def test_parse_answer_edge_cases(self):
        """Test parsing edge cases."""
        parser = MyParser()
        # TODO: Add edge case tests
        assert parser.parse_answer("") == ""
        assert parser.parse_answer("  \n  ") == ""

    def test_format_reward(self):
        """Test format reward function."""
        parser = MyParser()
        format_func = parser.get_format_reward_func()

        # TODO: Add format reward test cases
        assert format_func("Well formatted") == 1.0
        assert format_func("Partially formatted") >= 0.0
        assert format_func("") == 0.0


@pytest.mark.parametrize(
    "completion, answer, expected_reward",
    [
        # TODO: Add test cases for the reward function
        ("Correct answer", "Correct answer", 1.0),
        ("Wrong answer", "Correct answer", 0.0),
        ("", "Correct answer", 0.0),
    ],
)
def test_reward_correct_answer(completion, answer, expected_reward):
    """Test the correctness reward function."""
    parser = MyParser()
    reward = reward_correct_answer(completion, answer, parser=parser)
    assert reward == expected_reward


def test_load_environment():
    """Test loading the environment."""
    env = load_environment(max_examples=5)

    assert isinstance(env, vf.SingleTurnEnv)  # or vf.MultiTurnEnv
    assert env.dataset is not None
    assert len(env.dataset) <= 5


@patch("my_environment.load_dataset")  # TODO: Update module name
def test_load_environment_with_real_dataset(mock_load_dataset):
    """Test loading environment with mocked dataset."""
    # Mock the dataset
    mock_data = [
        {"question": "Test input", "answer": "Test output"},
    ]
    mock_dataset = Dataset.from_list(mock_data)
    mock_load_dataset.return_value = mock_dataset

    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 1


def test_load_environment_fallback_to_synthetic():
    """Test that environment falls back to synthetic dataset on error."""
    with patch("my_environment.load_dataset") as mock_load_dataset:
        mock_load_dataset.side_effect = ConnectionError("Failed to connect")

        env = load_environment()

        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None
        # Should have synthetic data
        assert len(env.dataset) > 0
