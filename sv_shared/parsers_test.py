"""Tests for sv_shared parsers."""

from __future__ import annotations

import pytest

from sv_shared.parsers import JsonClassificationParser, extract_json_from_markdown


class TestJsonClassificationParser:
    """Tests for JsonClassificationParser."""

    @pytest.fixture
    def parser(self) -> JsonClassificationParser:
        """Create a parser with standard allowed labels."""
        return JsonClassificationParser(allowed_labels=["Benign", "Malicious", "Abstain"])

    def test_parse_answer_valid_json(self, parser: JsonClassificationParser) -> None:
        """Test parsing valid JSON with correct label."""
        completion = '{"label": "Malicious", "confidence": 0.9, "rationale": "scan detected"}'
        assert parser.parse_answer(completion) == "Malicious"

    def test_parse_answer_invalid_label(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON with invalid label returns empty string."""
        completion = '{"label": "Unknown", "confidence": 0.5}'
        assert parser.parse_answer(completion) == ""

    def test_parse_answer_missing_label(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON without label field returns empty string."""
        completion = '{"confidence": 0.5, "rationale": "test"}'
        assert parser.parse_answer(completion) == ""

    def test_parse_answer_invalid_json(self, parser: JsonClassificationParser) -> None:
        """Test parsing malformed JSON returns empty string."""
        completion = "not valid json"
        assert parser.parse_answer(completion) == ""

    def test_parse_answer_non_dict_json(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON array returns empty string."""
        completion = '["Benign", "Malicious"]'
        assert parser.parse_answer(completion) == ""

    def test_parse_confidence_valid(self, parser: JsonClassificationParser) -> None:
        """Test parsing valid confidence value."""
        completion = '{"label": "Benign", "confidence": 0.75}'
        assert parser.parse_confidence(completion) == pytest.approx(0.75)

    def test_parse_confidence_missing(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON without confidence returns 0.0."""
        completion = '{"label": "Benign"}'
        assert parser.parse_confidence(completion) == pytest.approx(0.0)

    def test_parse_confidence_invalid_type(self, parser: JsonClassificationParser) -> None:
        """Test parsing non-numeric confidence returns 0.0."""
        completion = '{"label": "Benign", "confidence": "high"}'
        assert parser.parse_confidence(completion) == pytest.approx(0.0)

    def test_parse_confidence_out_of_range_high(self, parser: JsonClassificationParser) -> None:
        """Test parsing confidence > 1.0 returns 0.0."""
        completion = '{"label": "Benign", "confidence": 1.5}'
        assert parser.parse_confidence(completion) == pytest.approx(0.0)

    def test_parse_confidence_out_of_range_low(self, parser: JsonClassificationParser) -> None:
        """Test parsing confidence < 0.0 returns 0.0."""
        completion = '{"label": "Benign", "confidence": -0.5}'
        assert parser.parse_confidence(completion) == pytest.approx(0.0)

    def test_parse_confidence_boundary_values(self, parser: JsonClassificationParser) -> None:
        """Test parsing confidence at boundaries (0.0 and 1.0)."""
        assert parser.parse_confidence('{"label": "Benign", "confidence": 0.0}') == pytest.approx(0.0)
        assert parser.parse_confidence('{"label": "Benign", "confidence": 1.0}') == pytest.approx(1.0)

    def test_format_reward_valid(self, parser: JsonClassificationParser) -> None:
        """Test format reward function returns 1.0 for valid output."""
        fmt = parser.get_format_reward_func()
        completion = '{"label": "Benign", "confidence": 0.5, "rationale": "looks safe"}'
        assert fmt(completion) == 1.0

    def test_format_reward_invalid_json(self, parser: JsonClassificationParser) -> None:
        """Test format reward returns 0.0 for malformed JSON."""
        fmt = parser.get_format_reward_func()
        assert fmt("not json") == 0.0

    def test_format_reward_invalid_label(self, parser: JsonClassificationParser) -> None:
        """Test format reward returns 0.0 for invalid label."""
        fmt = parser.get_format_reward_func()
        completion = '{"label": "Invalid", "confidence": 0.5}'
        assert fmt(completion) == 0.0

    def test_format_reward_invalid_confidence(self, parser: JsonClassificationParser) -> None:
        """Test format reward returns 0.0 for out-of-range confidence."""
        fmt = parser.get_format_reward_func()
        assert fmt('{"label": "Benign", "confidence": 2.0}') == 0.0
        assert fmt('{"label": "Benign", "confidence": -0.5}') == 0.0

    def test_format_reward_missing_fields(self, parser: JsonClassificationParser) -> None:
        """Test format reward returns 0.0 for missing required fields."""
        fmt = parser.get_format_reward_func()
        assert fmt('{"label": "Benign"}') == 0.0  # Missing confidence
        assert fmt('{"confidence": 0.5}') == 0.0  # Missing label

    def test_format_reward_accepts_int_confidence(self, parser: JsonClassificationParser) -> None:
        """Test format reward accepts integer confidence values."""
        fmt = parser.get_format_reward_func()
        completion = '{"label": "Benign", "confidence": 1}'
        assert fmt(completion) == 1.0

    def test_custom_allowed_labels(self) -> None:
        """Test parser works with custom allowed labels."""
        custom_parser = JsonClassificationParser(allowed_labels=["Safe", "Unsafe"])
        assert custom_parser.parse_answer('{"label": "Safe"}') == "Safe"
        assert custom_parser.parse_answer('{"label": "Benign"}') == ""  # Not in allowed

    def test_handles_message_list_format(self, parser: JsonClassificationParser) -> None:
        """Test parser handles Verifiers message list format."""
        # Verifiers may return list of message dicts
        completion = [
            {"role": "user", "content": "prompt"},
            {"role": "assistant", "content": '{"label": "Malicious", "confidence": 0.8}'},
        ]
        assert parser.parse_answer(completion) == "Malicious"
        assert parser.parse_confidence(completion) == pytest.approx(0.8)

    def test_handles_empty_message_list(self, parser: JsonClassificationParser) -> None:
        """Test parser handles empty message list."""
        completion = []
        assert parser.parse_answer(completion) == ""
        assert parser.parse_confidence(completion) == pytest.approx(0.0)

    def test_parse_answer_markdown_code_block_with_json_tag(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON wrapped in ```json code block."""
        completion = '```json\n{"label": "Malicious", "confidence": 0.85}\n```'
        assert parser.parse_answer(completion) == "Malicious"
        assert parser.parse_confidence(completion) == pytest.approx(0.85)

    def test_parse_answer_markdown_code_block_without_tag(self, parser: JsonClassificationParser) -> None:
        """Test parsing JSON wrapped in ``` code block (no language tag)."""
        completion = '```\n{"label": "Benign", "confidence": 0.9}\n```'
        assert parser.parse_answer(completion) == "Benign"
        assert parser.parse_confidence(completion) == pytest.approx(0.9)

    def test_parse_answer_markdown_with_rationale(self, parser: JsonClassificationParser) -> None:
        """Test parsing markdown-wrapped JSON with rationale (like gpt-4o-mini output)."""
        completion = """```json
{
  "label": "Abstain",
  "confidence": 0.5,
  "rationale": "The log entry indicates a TCP SYN packet which is typically used to initiate a connection."
}
```"""
        assert parser.parse_answer(completion) == "Abstain"
        assert parser.parse_confidence(completion) == pytest.approx(0.5)

    def test_format_reward_markdown_code_block(self, parser: JsonClassificationParser) -> None:
        """Test format reward accepts markdown-wrapped JSON."""
        fmt = parser.get_format_reward_func()
        completion = '```json\n{"label": "Malicious", "confidence": 0.9}\n```'
        assert fmt(completion) == 1.0

    def test_raw_json_still_works(self, parser: JsonClassificationParser) -> None:
        """Test that raw JSON (without markdown) still parses correctly."""
        completion = '{"label": "Benign", "confidence": 0.75}'
        assert parser.parse_answer(completion) == "Benign"
        assert parser.parse_confidence(completion) == pytest.approx(0.75)
        fmt = parser.get_format_reward_func()
        assert fmt(completion) == 1.0


class TestExtractJsonFromMarkdown:
    """Tests for extract_json_from_markdown helper."""

    def test_extracts_json_with_language_tag(self) -> None:
        """Test extraction from ```json block."""
        text = '```json\n{"key": "value"}\n```'
        assert extract_json_from_markdown(text) == '{"key": "value"}'

    def test_extracts_json_without_language_tag(self) -> None:
        """Test extraction from ``` block (no language)."""
        text = '```\n{"key": "value"}\n```'
        assert extract_json_from_markdown(text) == '{"key": "value"}'

    def test_returns_original_if_no_code_block(self) -> None:
        """Test that text without code block is returned unchanged."""
        text = '{"key": "value"}'
        assert extract_json_from_markdown(text) == '{"key": "value"}'

    def test_handles_multiline_json(self) -> None:
        """Test extraction of multiline JSON."""
        text = """```json
{
  "label": "Malicious",
  "confidence": 0.9,
  "rationale": "Test"
}
```"""
        result = extract_json_from_markdown(text)
        assert '"label": "Malicious"' in result
        assert '"confidence": 0.9' in result

    def test_handles_text_before_code_block(self) -> None:
        """Test extraction when there's text before the code block."""
        text = 'Here is my analysis:\n```json\n{"label": "Benign"}\n```'
        assert extract_json_from_markdown(text) == '{"label": "Benign"}'

    def test_handles_text_after_code_block(self) -> None:
        """Test extraction when there's text after the code block."""
        text = '```json\n{"label": "Benign"}\n```\nThis is my reasoning.'
        assert extract_json_from_markdown(text) == '{"label": "Benign"}'

    def test_case_insensitive_json_tag(self) -> None:
        """Test that JSON tag is case-insensitive."""
        text = '```JSON\n{"label": "Benign"}\n```'
        assert extract_json_from_markdown(text) == '{"label": "Benign"}'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
