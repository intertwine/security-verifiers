"""Tests for the fully featured network log anomaly environment."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import verifiers as vf
from datasets import Dataset

from sv_env_network_logs import NetworkLogParser, load_environment, transform_dataset
from sv_shared.rewards import (
    reward_accuracy,
    reward_calibration,
    reward_asymmetric_cost,
)


class TestNetworkLogParser:
    """Tests for parsing and format validation."""

    def test_extracts_label_and_confidence(self) -> None:
        parser = NetworkLogParser()
        completion = '{"label": "Malicious", "confidence": 0.9, "rationale": "scan"}'
        assert parser.parse_answer(completion) == "Malicious"
        assert parser.parse_confidence(completion) == pytest.approx(0.9)
        # Missing fields default gracefully
        assert parser.parse_answer("{}") == ""
        assert parser.parse_confidence("{}") == pytest.approx(0.0)

    def test_format_reward(self) -> None:
        parser = NetworkLogParser()
        fmt = parser.get_format_reward_func()
        good = '{"label": "Benign", "confidence": 0.5}'
        bad_json = "not json"
        bad_label = '{"label": "Unknown", "confidence": 0.5}'
        bad_conf = '{"label": "Benign", "confidence": 2}'
        assert fmt(good) == 1.0
        assert fmt(bad_json) == 0.0
        assert fmt(bad_label) == 0.0
        assert fmt(bad_conf) == 0.0


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        ('{"label": "Malicious", "confidence": 0.8}', "Malicious", 1.0),
        ('{"label": "Benign", "confidence": 0.8}', "Malicious", 0.0),
    ],
)
def test_reward_accuracy(completion: str, answer: str, expected: float) -> None:
    parser = NetworkLogParser()
    reward = reward_accuracy(completion=completion, answer=answer, parser=parser)
    assert reward == expected


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        (
            '{"label": "Malicious", "confidence": 0.9}',
            "Malicious",
            pytest.approx(1.0 - abs(0.9 - 1.0)),
        ),
        (
            '{"label": "Malicious", "confidence": 0.1}',
            "Benign",
            pytest.approx(1.0 - abs(0.1 - 0.0)),
        ),
    ],
)
def test_reward_calibration(completion: str, answer: str, expected: float) -> None:
    parser = NetworkLogParser()
    reward = reward_calibration(completion=completion, answer=answer, parser=parser)
    assert reward == expected


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        ('{"label": "Benign", "confidence": 0.9}', "Malicious", -1.0),
        ('{"label": "Malicious", "confidence": 0.2}', "Benign", 0.0),
        ('{"label": "Abstain", "confidence": 0.4}', "Malicious", 0.0),
    ],
)
def test_reward_asymmetric_cost(completion: str, answer: str, expected: float) -> None:
    parser = NetworkLogParser()
    reward = reward_asymmetric_cost(completion=completion, answer=answer, parser=parser)
    assert reward == expected


def test_transform_dataset() -> None:
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


@patch("sv_env_network_logs.load_dataset")
def test_load_environment_builds_rubric(mock_load_dataset) -> None:
    mock_load_dataset.return_value = Dataset.from_list([{"id.orig_h": "1", "label": "Benign"}])
    logger = Mock()
    logger.enabled = True

    env = load_environment(max_examples=1, logger=logger)
    assert isinstance(env, vf.SingleTurnEnv)
    assert len(env.rubric.reward_funcs) == 4
    mock_load_dataset.assert_called_once()
    logger.log_environment_init.assert_called_once()
    call_kwargs = logger.log_environment_init.call_args.kwargs
    assert call_kwargs["environment_name"] == "sv-env-network-logs"
    assert call_kwargs["total_examples"] == 1
