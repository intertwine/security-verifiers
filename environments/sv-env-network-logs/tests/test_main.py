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
