"""Tests for the phishing detection environment."""

from unittest.mock import patch

import pytest
import verifiers as vf
from datasets import Dataset
from sv_env_phishing_detection.main import (
    PhishingEmailParser,
    load_environment,
    reward_correct_classification,
    transform_dataset,
)


@pytest.mark.parametrize(
    "completion, answer, expected_reward",
    [
        ("Phishing", "Phishing", 1.0),
        ("Legitimate", "Legitimate", 1.0),
        ("Phishing", "Legitimate", 0.0),
        ("Legitimate", "Phishing", 0.0),
        ("  phishing  ", "Phishing", 1.0),
        ("legitimate\n", "Legitimate", 1.0),
    ],
)
def test_correct_classification(completion, answer, expected_reward):
    """Test the reward function for exact label matching."""
    parser = PhishingEmailParser()
    reward = reward_correct_classification(completion, answer, parser=parser)
    assert reward == expected_reward


class TestPhishingEmailParser:
    """Test cases for PhishingEmailParser class."""

    def test_parse_answer_phishing(self):
        """Test parsing phishing responses."""
        parser = PhishingEmailParser()
        assert parser.parse_answer("Phishing") == "Phishing"
        assert parser.parse_answer("phishing") == "Phishing"
        assert parser.parse_answer("  PHISHING  ") == "Phishing"
        assert parser.parse_answer("This is a phishing email") == "Phishing"

    def test_parse_answer_legitimate(self):
        """Test parsing legitimate responses."""
        parser = PhishingEmailParser()
        assert parser.parse_answer("Legitimate") == "Legitimate"
        assert parser.parse_answer("legitimate") == "Legitimate"
        assert parser.parse_answer("  LEGITIMATE  ") == "Legitimate"
        assert parser.parse_answer("This looks legitimate to me") == "Legitimate"
        assert parser.parse_answer("It's safe") == "Legitimate"
        assert parser.parse_answer("not phishing") == "Legitimate"

    def test_parse_answer_unknown(self):
        """Test parsing unknown responses."""
        parser = PhishingEmailParser()
        assert parser.parse_answer("Unknown") == "Unknown"
        assert parser.parse_answer("  Unclear  ") == "Unclear"
        assert parser.parse_answer("") == ""

    def test_format_reward_perfect(self):
        """Test format reward for perfect responses."""
        parser = PhishingEmailParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Phishing") == 1.0
        assert format_func("Legitimate") == 1.0
        assert format_func("phishing") == 1.0
        assert format_func("legitimate") == 1.0

    def test_format_reward_partial(self):
        """Test format reward for partial responses."""
        parser = PhishingEmailParser()
        format_func = parser.get_format_reward_func()

        assert format_func("This is phishing") == 0.5
        assert format_func("Looks legitimate to me") == 0.5
        assert format_func("I think it's a phishing attempt") == 0.5

    def test_format_reward_poor(self):
        """Test format reward for poor responses."""
        parser = PhishingEmailParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Unknown") == 0.0
        assert format_func("I don't know") == 0.0
        assert format_func("") == 0.0
        assert format_func("Suspicious") == 0.0

    def test_format_reward_list_completion(self):
        """Test format reward with list-style completion."""
        parser = PhishingEmailParser()
        format_func = parser.get_format_reward_func()

        completion = [{"role": "assistant", "content": "Phishing"}]
        assert format_func(completion) == 1.0

        completion = [{"role": "assistant", "content": "This is phishing"}]
        assert format_func(completion) == 0.5


def test_reward_correct_classification_edge_cases():
    """Test reward function edge cases."""
    parser = PhishingEmailParser()

    # Test with no parser
    assert reward_correct_classification("Phishing", "Phishing") == 1.0
    assert reward_correct_classification("Legitimate", "Phishing") == 0.0

    # Test with empty inputs
    assert reward_correct_classification("", "Phishing", parser=parser) == 0.0
    assert reward_correct_classification("Phishing", "", parser=parser) == 0.0

    # Test with list completion
    completion = [{"role": "assistant", "content": "Phishing"}]
    assert reward_correct_classification(completion, "Phishing", parser=parser) == 1.0

    # Test with empty list
    assert reward_correct_classification([], "Phishing", parser=parser) == 0.0


def test_transform_dataset():
    """Test the dataset transformation logic."""
    # Test with integer labels
    raw_data_int = [
        {
            "text": "Click here to verify your account: http://phishing-site.com",
            "subject": "Account Verification Required",
            "sender": "security@fake-bank.com",
            "label": 1,  # Binary: 1 = phishing
        },
        {
            "text": "Meeting scheduled for tomorrow at 2 PM.",
            "subject": "Meeting Reminder",
            "sender": "boss@company.com",
            "label": 0,  # Binary: 0 = legitimate
        },
    ]
    raw_dataset_int = Dataset.from_list(raw_data_int)
    transformed_int = transform_dataset(raw_dataset_int, max_examples=None)

    # Test with string labels
    raw_data_str = [
        {
            "email": "Your package has been delivered.",
            "label": "legitimate",  # String label
        },
        {
            "body": "Win $1000000 now! Click here!",
            "label": "spam",  # String label mapped to phishing
        },
    ]
    raw_dataset_str = Dataset.from_list(raw_data_str)
    transformed_str = transform_dataset(raw_dataset_str, max_examples=None)

    # Test integer labels
    assert len(transformed_int) == 2
    assert "question" in transformed_int.column_names
    assert "answer" in transformed_int.column_names
    assert transformed_int[0]["answer"] == "Phishing"
    assert transformed_int[1]["answer"] == "Legitimate"
    assert "From: security@fake-bank.com" in transformed_int[0]["question"]
    assert "Subject: Account Verification Required" in transformed_int[0]["question"]

    # Test string labels
    assert len(transformed_str) == 2
    assert transformed_str[0]["answer"] == "Legitimate"
    assert transformed_str[1]["answer"] == "Phishing"


def test_transform_dataset_with_max_examples():
    """Test dataset transformation with max_examples limit."""
    raw_data = [
        {"text": "Email 1", "label": 0},
        {"text": "Email 2", "label": 1},
        {"text": "Email 3", "label": 0},
    ]
    raw_dataset = Dataset.from_list(raw_data)

    transformed = transform_dataset(raw_dataset, max_examples=2)

    assert len(transformed) == 2
    assert transformed[0]["answer"] == "Legitimate"
    assert transformed[1]["answer"] == "Phishing"


@patch("sv_env_phishing_detection.main.load_dataset")
def test_load_environment_successful_download(mock_load_dataset):
    """Test loading the environment with a mocked successful dataset download."""
    # Mock the dataset returned by load_dataset
    mock_data = [
        {
            "text": "Verify your account now!",
            "label": 1,
        }
    ]
    mock_dataset = Dataset.from_list(mock_data)
    mock_load_dataset.return_value = mock_dataset

    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 1
    mock_load_dataset.assert_called_once_with("zefang-liu/phishing-email-dataset", split="train")


@patch("sv_env_phishing_detection.main.load_dataset")
def test_load_environment_download_fails(mock_load_dataset):
    """Test loading the environment when the dataset download fails."""
    # Configure the mock to raise an exception
    mock_load_dataset.side_effect = ConnectionError("Download failed")

    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    # Check that it falls back to the synthetic dataset
    assert len(env.dataset) == 10
    # The synthetic dataset has 5 phishing, then 5 legitimate examples
    assert env.dataset[0]["answer"] == "Phishing"
    assert env.dataset[5]["answer"] == "Legitimate"


@patch("sv_env_phishing_detection.main.load_dataset")
def test_load_environment_various_exceptions(mock_load_dataset):
    """Test loading environment with different exception types."""
    # Test with different exception types that should trigger fallback
    exceptions = [
        FileNotFoundError("File not found"),
        ValueError("Invalid value"),
        ImportError("Import failed"),
        AssertionError("Assertion failed"),
    ]

    for exception in exceptions:
        mock_load_dataset.side_effect = exception
        env = load_environment()
        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None and len(env.dataset) == 10  # Synthetic dataset


def test_load_environment_custom_parameters():
    """Test load_environment with custom parameters."""
    with patch("sv_env_phishing_detection.main.load_dataset") as mock_load_dataset:
        mock_data = [{"text": "test email", "label": 1}] * 5
        mock_dataset = Dataset.from_list(mock_data)
        mock_load_dataset.return_value = mock_dataset

        env = load_environment(dataset_name="custom/dataset", max_examples=3)

        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None and len(env.dataset) == 3  # Limited by max_examples
        mock_load_dataset.assert_called_once_with("custom/dataset", split="train")
