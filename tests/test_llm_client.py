from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from core.llm.client import LLMClient, LLMError


def test_rule_based_mode_no_keys():
    """With no API keys configured, ask() should raise LLMError."""
    with patch("core.llm.client.settings") as mock_settings:
        mock_settings.CHAT_PROVIDER = "auto"
        mock_settings.has_anthropic_key = False
        mock_settings.has_openai_key = False
        mock_settings.has_google_key = False
        client = LLMClient()
        with pytest.raises(LLMError):
            client.ask("system", "user")


def test_ask_json_strips_markdown_fence():
    """ask_json should strip ```json ... ``` fences before parsing."""
    client = LLMClient()
    with patch.object(client, "ask", return_value='```json\n{"key": "value"}\n```'):
        result = client.ask_json("system", "user")
    assert result == {"key": "value"}


def test_ask_json_no_fence():
    client = LLMClient()
    with patch.object(client, "ask", return_value='{"items": [1, 2, 3]}'):
        result = client.ask_json("system", "user")
    assert result == {"items": [1, 2, 3]}


def test_gemini_mode_google_key_only():
    """When only Google key is set and embed_provider=gemini, embed() uses Gemini."""
    with patch("core.llm.client.settings") as mock_settings:
        mock_settings.EMBED_PROVIDER = "gemini"
        mock_settings.has_google_key = True
        mock_settings.has_openai_key = False
        mock_settings.GOOGLE_API_KEY = "fake_key"

        client = LLMClient()
        mock_google = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        mock_google.models.embed_content.return_value = mock_response
        client._google = mock_google

        result = client._embed_gemini("test text")
    assert result == [0.1, 0.2, 0.3]
