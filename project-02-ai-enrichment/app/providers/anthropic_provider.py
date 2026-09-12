"""AI provider for Anthropic's Claude models.

Anthropic's API is not OpenAI-compatible: the system prompt is a
top-level parameter (not a message with role="system"), and the SDK
and exception types are different. This class exists specifically to
adapt that difference, while still exposing the same
`generate_structured` method as `OpenAICompatibleProvider` — so
`main.py` never has to know which one it's talking to.
"""

import logging
from typing import TypeVar

from anthropic import (
    Anthropic,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import BaseModel

from app.prompts import build_messages
from app.providers.base import AIProvider
from app.retry import with_retry


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, APITimeoutError)


class AnthropicProvider(AIProvider):
    """Provider for Anthropic's native Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
        max_output_tokens: int = 1024,
    ) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.max_output_tokens = max_output_tokens

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

        # Anthropic takes the system prompt as its own parameter, not
        # as a message in the list — this is the one structural
        # difference this class has to translate.
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"]

        response = with_retry(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ),
            max_retries=self.max_retries,
            retry_on=RETRYABLE_ERRORS,
        )

        content = response.content[0].text if response.content else None

        if not content:
            raise ValueError("Provider returned an empty response.")

        try:
            return schema.model_validate_json(content)

        except Exception as error:
            raise ValueError(
                f"Provider response did not match the expected schema: {error}"
            ) from error