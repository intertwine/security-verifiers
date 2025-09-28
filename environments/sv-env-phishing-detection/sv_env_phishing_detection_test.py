"""Tests for the phishing detection environment."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import verifiers as vf
from datasets import Dataset

from sv_env_phishing_detection import (
    PhishingEmailParser,
    load_environment,
    reward_evidence_alignment,
    reward_phishing_asymmetric_cost,
    transform_dataset,
)
from sv_shared.rewards import reward_accuracy, reward_calibration


class TestPhishingEmailParser:
    """Test cases for the JSON phishing parser."""

    def test_parse_answer_and_confidence(self) -> None:
        """Parser should normalize labels and extract confidence."""
        parser = PhishingEmailParser()
        completion = '{"label": "phishing", "confidence": 0.87}'
        assert parser.parse_answer(completion) == "Phishing"
        assert parser.parse_confidence(completion) == pytest.approx(0.87)

    def test_parse_evidence(self) -> None:
        """Evidence should be extracted as a list of strings."""
        parser = PhishingEmailParser()
        completion = '{"label": "Legitimate", "confidence": 0.55, "evidence": ["trusted-sender.com", "dkim-pass"]}'
        assert parser.parse_evidence(completion) == ["trusted-sender.com", "dkim-pass"]

    def test_parse_invalid_payload(self) -> None:
        """Invalid payloads should return empty values."""
        parser = PhishingEmailParser()
        assert parser.parse_answer("not json") == ""
        assert parser.parse_confidence("not json") == 0.0
        assert parser.parse_evidence("not json") == []

    def test_format_reward(self) -> None:
        """Well-formed JSON outputs receive format credit."""
        parser = PhishingEmailParser()
        format_func = parser.get_format_reward_func()

        assert format_func('{"label": "Phishing", "confidence": 1.0}') == 1.0
        assert (
            format_func(
                [
                    {
                        "role": "assistant",
                        "content": '{"label": "Abstain", "confidence": 0.4, "evidence": ["needs-manual-review"]}',
                    }
                ]
            )
            == 1.0
        )

        # Missing or malformed fields earn no reward
        assert format_func('{"label": "Unknown"}') == 0.0
        assert format_func('{"label": "Phishing", "confidence": 2}') == 0.0
        assert format_func('{"label": "Legitimate", "confidence": 0.3, "evidence": "string"}') == 0.0


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        ('{"label": "Phishing", "confidence": 0.9}', "Phishing", 1.0),
        ('{"label": "Legitimate", "confidence": 0.7}', "Phishing", 0.0),
        ('{"label": "Abstain", "confidence": 0.2}', "Legitimate", 0.0),
    ],
)
def test_reward_accuracy(completion: str, answer: str, expected: float) -> None:
    """Classification reward uses parsed labels."""
    parser = PhishingEmailParser()
    assert reward_accuracy(completion=completion, answer=answer, parser=parser) == expected


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        ('{"label": "Phishing", "confidence": 0.95}', "Phishing", pytest.approx(0.95)),
        ('{"label": "Phishing", "confidence": 0.1}', "Phishing", pytest.approx(0.1)),
        ('{"label": "Legitimate", "confidence": 0.8}', "Phishing", pytest.approx(0.2)),
        ('{"label": "Abstain", "confidence": 0.3}', "Legitimate", pytest.approx(0.7)),
    ],
)
def test_reward_calibration(completion: str, answer: str, expected: float) -> None:
    """Calibration reward reflects probability error."""
    parser = PhishingEmailParser()
    assert reward_calibration(completion=completion, answer=answer, parser=parser) == expected


@pytest.mark.parametrize(
    "completion, answer, expected",
    [
        ('{"label": "Legitimate", "confidence": 0.4}', "Phishing", -1.0),
        ('{"label": "Phishing", "confidence": 0.6}', "Phishing", 1.0),
        ('{"label": "Abstain", "confidence": 0.4}', "Phishing", 0.3),
        ('{"label": "Phishing", "confidence": 0.9}', "Legitimate", -0.2),
        ('{"label": "Abstain", "confidence": 0.5}', "Legitimate", 0.5),
    ],
)
def test_reward_asymmetric_cost(completion: str, answer: str, expected: float) -> None:
    """False negatives are heavily penalized."""
    parser = PhishingEmailParser()
    assert reward_phishing_asymmetric_cost(completion=completion, answer=answer, parser=parser) == expected


def test_reward_evidence_alignment() -> None:
    """Evidence reward matches indicators in state metadata or prompt text."""
    parser = PhishingEmailParser()
    completion = '{"label": "Phishing", "confidence": 0.8, "evidence": ["http://bad.example", "credential-request"]}'
    state = {
        "metadata": {"phishing_indicators": ["http://bad.example", "credential-request", "spoofed-domain"]},
        "question": "From: attacker@example.com\n\nVisit http://bad.example and provide credentials.",
    }

    score = reward_evidence_alignment(
        completion=completion,
        answer="Phishing",
        parser=parser,
        state=state,
        prompt=state["question"],
    )

    assert score == pytest.approx(1.0)

    # When evidence does not match the indicators, the reward collapses
    bad_completion = '{"label": "Phishing", "confidence": 0.8, "evidence": ["generic"]}'
    assert (
        reward_evidence_alignment(
            completion=bad_completion,
            answer="Phishing",
            parser=parser,
            state=state,
            prompt=state["question"],
        )
        == 0.0
    )


def test_transform_dataset_builds_metadata() -> None:
    """Dataset transformation constructs prompts and phishing indicators."""
    raw_dataset = Dataset.from_list(
        [
            {
                "text": "Click here to reset your password: http://evil.example/reset",
                "subject": "Reset Required",
                "sender": "it-support@example.com",
                "label": 1,
            },
            {
                "body": "Lunch menu attached.",
                "subject": "Lunch",
                "sender": "cafeteria@corp.com",
                "label": 0,
            },
        ]
    )

    transformed = transform_dataset(raw_dataset, max_examples=None)

    assert transformed.column_names == ["question", "answer", "metadata"]
    phishing_entry = transformed[0]
    assert phishing_entry["answer"] == "Phishing"
    assert "From: it-support@example.com" in phishing_entry["question"]
    assert "Subject: Reset Required" in phishing_entry["question"]
    assert "http://evil.example/reset" in phishing_entry["question"]
    assert "phishing_indicators" in phishing_entry["metadata"]
    assert "http://evil.example/reset" in phishing_entry["metadata"]["phishing_indicators"]

    legitimate_entry = transformed[1]
    assert legitimate_entry["answer"] == "Legitimate"
    assert legitimate_entry["metadata"]["phishing_indicators"] == []


def test_transform_dataset_respects_max_examples() -> None:
    """The transformation honors the provided max_examples limit."""
    raw_dataset = Dataset.from_list([{"text": f"Email {idx}", "label": idx % 2} for idx in range(5)])

    transformed = transform_dataset(raw_dataset, max_examples=3)

    assert len(transformed) == 3


@patch("sv_env_phishing_detection.load_dataset")
def test_load_environment_successful_download(mock_load_dataset) -> None:
    """When the dataset loads, the environment keeps the first N examples."""

    mock_dataset = Dataset.from_list(
        [
            {"text": "Suspicious link http://phish.local", "label": 1},
            {"text": "Quarterly update", "label": 0},
        ]
    )
    mock_load_dataset.return_value = mock_dataset

    env = load_environment(max_examples=1)

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 1
    mock_load_dataset.assert_called_once_with("zefang-liu/phishing-email-dataset", split="train")
    assert env.dataset[0]["answer"] in {"Phishing", "Legitimate"}


@patch("sv_env_phishing_detection.load_dataset")
def test_load_environment_fallback(mock_load_dataset) -> None:
    """Dataset failures produce the deterministic synthetic corpus."""

    mock_load_dataset.side_effect = ConnectionError("boom")
    env = load_environment()

    assert isinstance(env, vf.SingleTurnEnv)
    assert env.dataset is not None
    assert len(env.dataset) == 12
    assert env.dataset[0]["metadata"]["phishing_indicators"]
    assert env.dataset[-1]["answer"] == "Legitimate"


@patch("sv_env_phishing_detection.load_dataset")
def test_load_environment_various_exceptions(mock_load_dataset) -> None:
    """Different failure modes also use the synthetic dataset."""

    for exc in (
        FileNotFoundError("missing"),
        ValueError("bad"),
        ImportError("import"),
        AssertionError("assert"),
    ):
        mock_load_dataset.side_effect = exc
        env = load_environment()
        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None
        assert len(env.dataset) == 12


def test_load_environment_custom_dataset() -> None:
    """Custom parameters are forwarded to the dataset loader."""

    with patch("sv_env_phishing_detection.load_dataset") as mock_load_dataset:
        mock_dataset = Dataset.from_list(
            [
                {"text": "Please review the invoice", "label": 0},
                {"text": "Suspicious login", "label": 1},
            ]
        )
        mock_load_dataset.return_value = mock_dataset

        env = load_environment(dataset_name="custom/dataset", max_examples=2)

        assert isinstance(env, vf.SingleTurnEnv)
        assert env.dataset is not None
        assert len(env.dataset) == 2
        mock_load_dataset.assert_called_once_with("custom/dataset", split="train")


def test_environment_rubric_configuration() -> None:
    """The rubric combines accuracy, format, calibration, cost, and evidence rewards."""
    with patch("sv_env_phishing_detection.load_dataset") as mock_load_dataset:
        mock_dataset = Dataset.from_list([{"text": "hi", "label": 0}])
        mock_load_dataset.return_value = mock_dataset

        env = load_environment(max_examples=1)

    assert env.rubric is not None
    assert len(env.rubric.reward_funcs) == 5
    assert env.rubric.reward_weights == [1.0, 0.2, 0.2, 0.4, 0.2]
