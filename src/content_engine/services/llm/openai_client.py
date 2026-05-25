"""OpenAI API client wrapper with structured output support."""

import json
import logging
from typing import Any

from openai import OpenAI

from content_engine.config.settings import get_settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Wrapper around OpenAI API for structured content generation."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Get a JSON-structured response from OpenAI.

        Args:
            system_prompt: System message setting context/role
            user_prompt: User message with the actual request
            temperature: Creativity level (0.0-2.0)
            max_tokens: Maximum response length

        Returns:
            Parsed JSON dict from the model response

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        logger.debug(f"OpenAI request: model={self._model}, temp={temperature}")

        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {content[:200]}")
            raise ValueError(f"Invalid JSON response: {e}") from e

        logger.debug(f"OpenAI response: {len(content)} chars, keys={list(result.keys())}")
        return result

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Get a plain text response from OpenAI.

        Args:
            system_prompt: System message setting context/role
            user_prompt: User message with the actual request
            temperature: Creativity level (0.0-2.0)
            max_tokens: Maximum response length

        Returns:
            Text response from the model
        """
        response = self.client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        return content
