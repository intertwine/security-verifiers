"""Tests for sv_shared reward functions."""

from __future__ import annotations

import pytest

from sv_shared.parsers import JsonClassificationParser
from sv_shared.rewards import (
    reward_accuracy,
    reward_asymmetric_cost,
    reward_calibration,
)


@pytest.fixture
def parser() -> JsonClassificationParser:
    """Create a parser with standard allowed labels."""
    return JsonClassificationParser(allowed_labels=["Benign", "Malicious", "Abstain"])


class TestRewardAccuracy:
    """Tests for reward_accuracy function."""

    @pytest.mark.parametrize(
        "completion,answer,expected",
        [
            ('{"label": "Malicious", "confidence": 0.8}', "Malicious", 1.0),
            ('{"label": "Benign", "confidence": 0.8}', "Malicious", 0.0),
            ('{"label": "Abstain", "confidence": 0.5}', "Abstain", 1.0),
            # Case-insensitive comparison of *parsed* label with answer
            ('{"label": "Malicious", "confidence": 0.9}', "malicious", 1.0),
            ('{"label": "Benign", "confidence": 0.9}', "BENIGN", 1.0),
        ],
    )
    def test_basic_accuracy(
        self,
        completion: str,
        answer: str,
        expected: float,
        parser: JsonClassificationParser,
    ) -> None:
        """Test basic accuracy reward for correct and incorrect predictions."""
        reward = reward_accuracy(completion=completion, answer=answer, parser=parser)
        assert reward == expected

    def test_empty_predicted_label(self, parser: JsonClassificationParser) -> None:
        """Test accuracy returns 0.0 when prediction is empty."""
        completion = '{"confidence": 0.8}'  # Missing label
        assert reward_accuracy(completion=completion, answer="Malicious", parser=parser) == 0.0

    def test_empty_answer(self, parser: JsonClassificationParser) -> None:
        """Test accuracy returns 0.0 when answer is empty."""
        completion = '{"label": "Malicious", "confidence": 0.8}'
        assert reward_accuracy(completion=completion, answer="", parser=parser) == 0.0

    def test_invalid_json(self, parser: JsonClassificationParser) -> None:
        """Test accuracy returns 0.0 for invalid JSON."""
        assert reward_accuracy(completion="not json", answer="Malicious", parser=parser) == 0.0

    def test_message_list_format(self, parser: JsonClassificationParser) -> None:
        """Test accuracy works with message list format."""
        completion = [{"role": "assistant", "content": '{"label": "Malicious", "confidence": 0.9}'}]
        assert reward_accuracy(completion=completion, answer="Malicious", parser=parser) == 1.0


class TestRewardCalibration:
    """Tests for reward_calibration function."""

    @pytest.mark.parametrize(
        "completion,answer,expected",
        [
            # Perfect calibration (correct + high confidence)
            ('{"label": "Malicious", "confidence": 1.0}', "Malicious", 1.0),
            # Perfect calibration (incorrect + zero confidence)
            ('{"label": "Benign", "confidence": 0.0}', "Malicious", 1.0),
            # Good calibration (correct + 0.9 confidence)
            ('{"label": "Malicious", "confidence": 0.9}', "Malicious", 0.9),
            # Poor calibration (incorrect + high confidence)
            ('{"label": "Benign", "confidence": 0.9}', "Malicious", 0.1),
            # Medium calibration (correct + 0.5 confidence)
            ('{"label": "Malicious", "confidence": 0.5}', "Malicious", 0.5),
        ],
    )
    def test_calibration_scenarios(
        self,
        completion: str,
        answer: str,
        expected: float,
        parser: JsonClassificationParser,
    ) -> None:
        """Test calibration reward for various prediction scenarios."""
        reward = reward_calibration(completion=completion, answer=answer, parser=parser)
        assert reward == pytest.approx(expected)

    def test_empty_predicted_label(self, parser: JsonClassificationParser) -> None:
        """Test calibration returns 0.0 when prediction is empty."""
        completion = '{"confidence": 0.8}'
        assert reward_calibration(completion=completion, answer="Malicious", parser=parser) == 0.0

    def test_invalid_json(self, parser: JsonClassificationParser) -> None:
        """Test calibration returns 0.0 for invalid JSON."""
        assert reward_calibration(completion="not json", answer="Malicious", parser=parser) == 0.0

    def test_calibration_formula(self, parser: JsonClassificationParser) -> None:
        """Test calibration formula: 1.0 - abs(confidence - correctness)."""
        # Correct prediction with 0.7 confidence: 1.0 - abs(0.7 - 1.0) = 1.0 - 0.3 = 0.7
        reward = reward_calibration(
            completion='{"label": "Malicious", "confidence": 0.7}',
            answer="Malicious",
            parser=parser,
        )
        assert reward == pytest.approx(0.7)

        # Incorrect prediction with 0.3 confidence: 1.0 - abs(0.3 - 0.0) = 1.0 - 0.3 = 0.7
        reward = reward_calibration(
            completion='{"label": "Benign", "confidence": 0.3}',
            answer="Malicious",
            parser=parser,
        )
        assert reward == pytest.approx(0.7)

    def test_message_list_format(self, parser: JsonClassificationParser) -> None:
        """Test calibration works with message list format."""
        completion = [{"role": "assistant", "content": '{"label": "Malicious", "confidence": 0.9}'}]
        reward = reward_calibration(completion=completion, answer="Malicious", parser=parser)
        assert reward == pytest.approx(0.9)


class TestRewardAsymmetricCost:
    """Tests for reward_asymmetric_cost function."""

    @pytest.mark.parametrize(
        "completion,answer,expected",
        [
            # Correct predictions get +1.0
            ('{"label": "Malicious", "confidence": 0.9}', "Malicious", 1.0),
            ('{"label": "Benign", "confidence": 0.9}', "Benign", 1.0),
            ('{"label": "Abstain", "confidence": 0.5}', "Abstain", 1.0),
            # False negative (predict Benign when Malicious) gets -1.0
            ('{"label": "Benign", "confidence": 0.9}', "Malicious", -1.0),
            # False positive (predict Malicious when Benign) gets 0.0
            ('{"label": "Malicious", "confidence": 0.9}', "Benign", 0.0),
            # Abstain when should be Malicious gets 0.0
            ('{"label": "Abstain", "confidence": 0.5}', "Malicious", 0.0),
            # Abstain when should be Benign gets 0.0
            ('{"label": "Abstain", "confidence": 0.5}', "Benign", 0.0),
        ],
    )
    def test_asymmetric_cost_scenarios(
        self,
        completion: str,
        answer: str,
        expected: float,
        parser: JsonClassificationParser,
    ) -> None:
        """Test asymmetric cost reward for various prediction scenarios."""
        reward = reward_asymmetric_cost(completion=completion, answer=answer, parser=parser)
        assert reward == expected

    def test_case_insensitive(self, parser: JsonClassificationParser) -> None:
        """Test asymmetric cost comparison is case-insensitive for parsed labels."""
        # False negative: Benign (parsed) vs MALICIOUS (answer, case-insensitive match)
        reward = reward_asymmetric_cost(
            completion='{"label": "Benign", "confidence": 0.9}',
            answer="MALICIOUS",
            parser=parser,
        )
        assert reward == -1.0

    def test_empty_predicted_label(self, parser: JsonClassificationParser) -> None:
        """Test asymmetric cost returns 0.0 when prediction is empty."""
        completion = '{"confidence": 0.8}'
        assert reward_asymmetric_cost(completion=completion, answer="Malicious", parser=parser) == 0.0

    def test_empty_answer(self, parser: JsonClassificationParser) -> None:
        """Test asymmetric cost returns 0.0 when answer is empty."""
        completion = '{"label": "Malicious", "confidence": 0.8}'
        assert reward_asymmetric_cost(completion=completion, answer="", parser=parser) == 0.0

    def test_invalid_json(self, parser: JsonClassificationParser) -> None:
        """Test asymmetric cost returns 0.0 for invalid JSON."""
        assert reward_asymmetric_cost(completion="not json", answer="Malicious", parser=parser) == 0.0

    def test_confidence_ignored(self, parser: JsonClassificationParser) -> None:
        """Test that confidence value doesn't affect asymmetric cost reward."""
        # Same false negative with different confidence values
        reward_low_conf = reward_asymmetric_cost(
            completion='{"label": "Benign", "confidence": 0.1}',
            answer="Malicious",
            parser=parser,
        )
        reward_high_conf = reward_asymmetric_cost(
            completion='{"label": "Benign", "confidence": 0.9}',
            answer="Malicious",
            parser=parser,
        )
        assert reward_low_conf == reward_high_conf == -1.0

    def test_message_list_format(self, parser: JsonClassificationParser) -> None:
        """Test asymmetric cost works with message list format."""
        completion = [{"role": "assistant", "content": '{"label": "Benign", "confidence": 0.9}'}]
        assert reward_asymmetric_cost(completion=completion, answer="Malicious", parser=parser) == -1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
