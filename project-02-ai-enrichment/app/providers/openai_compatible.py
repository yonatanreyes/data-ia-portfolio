"""AI provider for OpenAI and any OpenAI-compatible endpoint.

Many providers (OpenAI itself, Z.ai/GLM, Mistral, DeepSeek, Groq, and
others) expose the exact same request/response shape as OpenAI's Chat
Completions API. Because of that, ONE class handles all of them — the
only thing that changes between providers is the API key, the base
URL, and the model name, all of which come from configuration.
"""

import logging
from typing import TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel

from app.prompts import build_messages
from app.providers.base import AIProvider
from app.retry import with_retry


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Transient errors worth retrying: rate limits, timeouts, dropped
# connections. Anything else (bad API key, invalid request) fails fast.
RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)


class OpenAICompatibleProvider(AIProvider):
    """Provider for OpenAI and OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        # base_url=None makes the SDK default to OpenAI's own endpoint.
        # Any other value points the same client at a different,
        # OpenAI-compatible provider — no other code changes needed.
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries

    def generate_structured(self, listing: dict, schema: type[T]) -> T:
        """Generate and validate a structured response for one listing.

        Args:
            listing: Cleaned laptop listing data.
            schema: Pydantic model describing the expected output shape.

        Returns:
            A validated instance of `schema`.

        Raises:
            ValueError: If the response is empty or does not match
                the expected schema.
        """
        messages = build_messages(listing, schema)

        try:
            response = with_retry(
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=4096,
                ),
                max_retries=self.max_retries,
                retry_on=RETRYABLE_ERRORS,
            )

        except APIStatusError as error:
            # Surface the provider's actual error body (e.g. Z.ai,
            # Mistral) instead of a bare "400 Bad Request", to make
            # debugging configuration issues fast.
            logger.error(
                "Provider rejected the request (status %s): %s",
                error.status_code,
                error.response.text,
            )
            raise

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Provider returned an empty response.")

        try:
            return schema.model_validate_json(content)

        except Exception as error:
            raise ValueError(
                f"Provider response did not match the expected schema: {error}"
            ) from error