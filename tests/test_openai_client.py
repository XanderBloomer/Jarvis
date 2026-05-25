"""Tests for the OpenAI client wrapper."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_engine.services.llm.openai_client import OpenAIClient


def make_mock_response(content: str) -> MagicMock:
    """Create a mock OpenAI API response."""
    mock_message = MagicMock()
    mock_message.content = content

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestOpenAIClient:
    """Tests for the OpenAI client wrapper."""

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_complete_json_parses_response(self, mock_openai_class: MagicMock) -> None:
        """complete_json returns parsed JSON dict."""
        response_data = {"hook_type": "fear_curiosity", "score": 8}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response(
            json.dumps(response_data)
        )
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        result = client.complete_json(
            system_prompt="You are a test.",
            user_prompt="Analyze this.",
        )

        assert result == response_data
        mock_client.chat.completions.create.assert_called_once()

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_complete_json_raises_on_invalid_json(
        self, mock_openai_class: MagicMock
    ) -> None:
        """complete_json raises ValueError on non-JSON response."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response(
            "This is not JSON at all"
        )
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(ValueError, match="Invalid JSON"):
            client.complete_json(
                system_prompt="You are a test.",
                user_prompt="Analyze this.",
            )

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_complete_json_raises_on_empty_response(
        self, mock_openai_class: MagicMock
    ) -> None:
        """complete_json raises ValueError on empty response."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response(None)
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(ValueError, match="Empty response"):
            client.complete_json(
                system_prompt="You are a test.",
                user_prompt="Analyze this.",
            )

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_complete_text_returns_string(self, mock_openai_class: MagicMock) -> None:
        """complete_text returns the raw text content."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response(
            "Once upon a time in a dark forest..."
        )
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        result = client.complete_text(
            system_prompt="You are a storyteller.",
            user_prompt="Write a story.",
        )

        assert result == "Once upon a time in a dark forest..."

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_complete_json_uses_json_response_format(
        self, mock_openai_class: MagicMock
    ) -> None:
        """complete_json sets response_format to json_object."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response('{"ok": true}')
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        client.complete_json(system_prompt="test", user_prompt="test")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_client_uses_specified_model(self, mock_openai_class: MagicMock) -> None:
        """Client uses the model specified at init."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response('{"ok": true}')
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        client.complete_json(system_prompt="test", user_prompt="test")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    @patch("content_engine.services.llm.openai_client.OpenAI")
    def test_client_passes_temperature(self, mock_openai_class: MagicMock) -> None:
        """Client passes temperature parameter."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_mock_response('{"ok": true}')
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        client.complete_json(system_prompt="test", user_prompt="test", temperature=0.2)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.2
