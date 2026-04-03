from __future__ import annotations
from typing import Any, Optional
import json
import re
from config import settings

# Model constants
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GPT4O_MODEL = "gpt-4o"
GEMINI_MODEL = "gemini-2.5-flash"
OPENAI_EMBED_MODEL = "text-embedding-3-small"
GEMINI_EMBED_MODEL = "models/text-embedding-004"


class LLMError(Exception):
    pass


class EmbeddingError(Exception):
    pass


class LLMClient:
    def __init__(self) -> None:
        self._anthropic = None
        self._openai = None
        self._google = None

    def _get_anthropic(self):
        if self._anthropic is None:
            import anthropic
            self._anthropic = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic

    def _get_openai(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _get_google(self):
        if self._google is None:
            import google.genai as genai
            self._google = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._google

    def _resolve_provider(self) -> str:
        if settings.CHAT_PROVIDER != "auto":
            return settings.CHAT_PROVIDER
        if settings.has_anthropic_key:
            return "anthropic"
        if settings.has_openai_key:
            return "openai"
        if settings.has_google_key:
            return "google"
        return "rules"

    def ask(self, system: str, user: str, **kwargs: Any) -> str:
        provider = self._resolve_provider()
        if provider == "anthropic":
            return self._ask_anthropic(system, user, **kwargs)
        if provider == "openai":
            return self._ask_openai(system, user, **kwargs)
        if provider == "google":
            return self._ask_google(system, user, **kwargs)
        raise LLMError("No LLM provider available. Configure an API key or use the rule-based engine.")

    def _ask_anthropic(self, system: str, user: str, **kwargs: Any) -> str:
        client = self._get_anthropic()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=kwargs.get("max_tokens", 2048),
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def _ask_openai(self, system: str, user: str, **kwargs: Any) -> str:
        client = self._get_openai()
        response = client.chat.completions.create(
            model=GPT4O_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=kwargs.get("max_tokens", 2048),
        )
        return response.choices[0].message.content

    def _ask_google(self, system: str, user: str, **kwargs: Any) -> str:
        client = self._get_google()
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=kwargs.get("max_tokens", 2048),
            ),
        )
        return response.text

    def ask_json(self, system: str, user: str, **kwargs: Any) -> Any:
        raw = self.ask(system, user, **kwargs)
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    def embed(self, text: str) -> list[float]:
        provider = settings.EMBED_PROVIDER
        if provider == "gemini" and settings.has_google_key:
            return self._embed_gemini(text)
        if settings.has_openai_key:
            return self._embed_openai(text)
        raise EmbeddingError("No embedding provider available.")

    def _embed_gemini(self, text: str) -> list[float]:
        client = self._get_google()
        response = client.models.embed_content(
            model=GEMINI_EMBED_MODEL,
            contents=text,
        )
        return response.embeddings[0].values

    def _embed_openai(self, text: str) -> list[float]:
        client = self._get_openai()
        response = client.embeddings.create(
            model=OPENAI_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding


# Global singleton
llm = LLMClient()
