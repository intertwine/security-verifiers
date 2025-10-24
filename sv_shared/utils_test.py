"""Tests for sv_shared utility functions."""

from __future__ import annotations

import pytest

from sv_shared.utils import get_response_text


class TestGetResponseText:
    """Tests for get_response_text function."""

    def test_string_input(self) -> None:
        """Test extracting text from plain string."""
        assert get_response_text("Hello, world!") == "Hello, world!"

    def test_empty_string(self) -> None:
        """Test extracting text from empty string."""
        assert get_response_text("") == ""

    def test_message_list_single_message(self) -> None:
        """Test extracting text from single message in list."""
        messages = [{"role": "assistant", "content": "Response text"}]
        assert get_response_text(messages) == "Response text"

    def test_message_list_multiple_messages(self) -> None:
        """Test extracting text from last message in list."""
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Second message"},
            {"role": "user", "content": "Third message"},
            {"role": "assistant", "content": "Last message"},
        ]
        assert get_response_text(messages) == "Last message"

    def test_message_list_empty(self) -> None:
        """Test extracting text from empty message list."""
        assert get_response_text([]) == ""

    def test_message_without_content(self) -> None:
        """Test extracting text from message without content field."""
        messages = [{"role": "assistant"}]
        assert get_response_text(messages) == ""

    def test_message_with_empty_content(self) -> None:
        """Test extracting text from message with empty content."""
        messages = [{"role": "assistant", "content": ""}]
        assert get_response_text(messages) == ""

    def test_number_input(self) -> None:
        """Test converting number to string."""
        assert get_response_text(42) == "42"
        assert get_response_text(3.14) == "3.14"

    def test_none_input(self) -> None:
        """Test converting None to string."""
        assert get_response_text(None) == "None"

    def test_dict_input_not_in_list(self) -> None:
        """Test converting dict (not in list) to string."""
        result = get_response_text({"role": "assistant", "content": "text"})
        assert isinstance(result, str)
        assert "role" in result or "assistant" in result

    def test_json_content(self) -> None:
        """Test extracting JSON content from message."""
        messages = [
            {
                "role": "assistant",
                "content": '{"label": "Malicious", "confidence": 0.9}',
            }
        ]
        assert get_response_text(messages) == '{"label": "Malicious", "confidence": 0.9}'

    def test_multiline_content(self) -> None:
        """Test extracting multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        messages = [{"role": "assistant", "content": content}]
        assert get_response_text(messages) == content

    def test_unicode_content(self) -> None:
        """Test extracting unicode content."""
        messages = [{"role": "assistant", "content": "Hello 世界 🌍"}]
        assert get_response_text(messages) == "Hello 世界 🌍"

    def test_list_with_mixed_types(self) -> None:
        """Test list with non-dict items (edge case)."""
        # Should still try to get last item's content
        messages = [
            "string item",
            {"role": "assistant", "content": "Dict content"},
        ]
        assert get_response_text(messages) == "Dict content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
