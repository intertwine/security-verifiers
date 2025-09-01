"""Tests for the network logs environment."""

from unittest.mock import patch

import pytest
import verifiers as vf
from datasets import Dataset
from sv_env_network_logs.main import (
    NetworkLogParser,
    load_environment,
    reward_correct_classification,
    transform_dataset,
)


@pytest.mark.parametrize(
    "completion, answer, expected_reward",
    [
        ("Malicious", "Malicious", 1.0),
        ("Benign", "Benign", 1.0),
        ("Malicious", "Benign", 0.0),
        ("Benign", "Malicious", 0.0),
        ("  malicious  ", "Malicious", 1.0),
        ("benign\n", "Benign", 1.0),
    ],
)
def test_correct_classification(completion, answer, expected_reward):
    """Test the reward function for exact label matching."""
    parser = NetworkLogParser()
    reward = reward_correct_classification(completion, answer, parser=parser)
    assert reward == expected_reward


class TestNetworkLogParser:
    """Test cases for NetworkLogParser class."""

    def test_parse_answer_malicious(self):
        """Test parsing malicious responses."""
        parser = NetworkLogParser()
        assert parser.parse_answer("Malicious") == "Malicious"
        assert parser.parse_answer("malicious") == "Malicious"
        assert parser.parse_answer("  MALICIOUS  ") == "Malicious"
        assert parser.parse_answer("This is malicious behavior") == "Malicious"

    def test_parse_answer_benign(self):
        """Test parsing benign responses."""
        parser = NetworkLogParser()
        assert parser.parse_answer("Benign") == "Benign"
        assert parser.parse_answer("benign") == "Benign"
        assert parser.parse_answer("  BENIGN  ") == "Benign"
        assert parser.parse_answer("This looks benign to me") == "Benign"

    def test_parse_answer_unknown(self):
        """Test parsing unknown responses."""
        parser = NetworkLogParser()
        assert parser.parse_answer("Unknown") == "Unknown"
        assert parser.parse_answer("  Unclear  ") == "Unclear"
        assert parser.parse_answer("") == ""

    def test_format_reward_perfect(self):
        """Test format reward for perfect responses."""
        parser = NetworkLogParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Malicious") == 1.0
        assert format_func("Benign") == 1.0
        assert format_func("malicious") == 1.0
        assert format_func("benign") == 1.0

    def test_format_reward_partial(self):
        """Test format reward for partial responses."""
        parser = NetworkLogParser()
        format_func = parser.get_format_reward_func()

        assert format_func("This is malicious") == 0.5
        assert format_func("Looks benign to me") == 0.5
        assert format_func("I think it's malicious behavior") == 0.5

    def test_format_reward_poor(self):
        """Test format reward for poor responses."""
        parser = NetworkLogParser()
        format_func = parser.get_format_reward_func()

        assert format_func("Unknown") == 0.0
        assert format_func("I don't know") == 0.0
        assert format_func("") == 0.0
        assert format_func("Safe") == 0.0

    def test_format_reward_list_completion(self):
        """Test format reward with list-style completion."""
        parser = NetworkLogParser()
        format_func = parser.get_format_reward_func()

        completion = [{"role": "assistant", "content": "Malicious"}]
        assert format_func(completion) == 1.0

        completion = [{"role": "assistant", "content": "This is malicious"}]
        assert format_func(completion) == 0.5


def test_reward_correct_classification_edge_cases():
    """Test reward function edge cases."""
    parser = NetworkLogParser()

    # Test with no parser
    assert reward_correct_classification("Malicious", "Malicious") == 1.0
    assert reward_correct_classification("Benign", "Malicious") == 0.0

    # Test with empty inputs
    assert reward_correct_classification("", "Malicious", parser=parser) == 0.0
    assert reward_correct_classification("Malicious", "", parser=parser) == 0.0

    # Test with list completion
    completion = [{"role": "assistant", "content": "Malicious"}]
    assert reward_correct_classification(completion, "Malicious", parser=parser) == 1.0

    # Test with empty list
    assert reward_correct_classification([], "Malicious", parser=parser) == 0.0


def test_transform_dataset():
    """Test the dataset transformation logic."""
    raw_data = [
        {
            "id.orig_h": "192.168.1.1",
            "id.orig_p": 12345,
            "id.resp_h": "8.8.8.8",
            "id.resp_p": 53,
            "proto": "udp",
            "service": "dns",
            "detailed-label": "Benign",
            "label": "Benign",
        },
        {
            "id.orig_h": "10.0.0.2",
            "id.orig_p": 666,
            "id.resp_h": "10.0.0.1",
            "id.resp_p": 666,
            "proto": "tcp",
            "service": "-NA-",
            "detailed-label": "Attack",
            "label": "Malicious",
        },
    ]
    raw_dataset = Dataset.from_list(raw_data)

    transformed = transform_dataset(raw_dataset, max_examples=None)

    assert len(transformed) == 2
    assert "question" in transformed.column_names
    assert "answer" in transformed.column_names
    assert transformed[0]["answer"] == "Benign"
    assert transformed[1]["answer"] == "Malicious"
    assert "id.orig_h=192.168.1.1" in transformed[0]["question"]


def test_transform_dataset_with_max_examples():
    """Test dataset transformation with max_examples limit."""
    raw_data = [
        {"id.orig_h": "192.168.1.1", "label": "Benign"},
        {"id.orig_h": "192.168.1.2", "label": "Malicious"},
        {"id.orig_h": "192.168.1.3", "label": "Benign"},
    ]
    raw_dataset = Dataset.from_list(raw_data)

    transformed = transform_dataset(raw_dataset, max_examples=2)

    assert len(transformed) == 2
    assert transformed[0]["answer"] == "Benign"
    assert transformed[1]["answer"] == "Malicious"


@patch("sv_env_network_logs.main.load_dataset")
def test_load_environment_successful_download(mock_load_dataset):
    """Test loading the environment with a mocked successful dataset download."""
    # Mock the dataset returned by load_dataset
    mock_data = [
        {
            "id.orig_h": "192.168.1.100",
            "label": "Benign",
        }
    ]
    mock_dataset = Dataset.from_list(mock_data)
    mock_load_dataset.return_value = mock_dataset

    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 1
    mock_load_dataset.assert_called_once_with("19kmunz/iot-23-preprocessed-minimumcolumns", split="train")


@patch("sv_env_network_logs.main.load_dataset")
def test_load_environment_download_fails(mock_load_dataset):
    """Test loading the environment when the dataset download fails."""
    # Configure the mock to raise an exception
    mock_load_dataset.side_effect = ConnectionError("Download failed")

    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    # Check that it falls back to the synthetic dataset
    assert len(env.dataset) == 10
    # The synthetic dataset has 3 benign, then 3 malicious examples
    assert env.dataset[3]["answer"] == "Malicious"


@patch("sv_env_network_logs.main.load_dataset")
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
    with patch("sv_env_network_logs.main.load_dataset") as mock_load_dataset:
        mock_data = [{"id.orig_h": "test", "label": "Benign"}] * 5
        mock_dataset = Dataset.from_list(mock_data)
        mock_load_dataset.return_value = mock_dataset

        env = load_environment(dataset_name="custom/dataset", max_examples=3)

        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None and len(env.dataset) == 3  # Limited by max_examples
        mock_load_dataset.assert_called_once_with("custom/dataset", split="train")
