"""Prompt construction for the laptop enrichment pipeline.

This is the single place that turns a listing (plus the expected output
schema) into the exact messages sent to any AI provider. Both provider
implementations call `build_messages` instead of formatting prompts
themselves, which keeps the prompt consistent regardless of which
model answers it.
"""

import json
from typing import Any, TypeVar, get_args

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


SYSTEM_PROMPT = """
You are a data enrichment assistant specialized in laptop listings.

Follow these rules:
- Only use information supported by the provided listing data.
- Do not invent specifications or missing information.
- If a specification is not available, use null.
- Evaluate value based only on the price, condition, and shipping given.
- Respond with a single, FLAT JSON object containing ONLY the requested
  top-level keys and their values — no markdown, no nested wrapper
  objects, no JSON Schema metadata (no "properties", "required",
  "type", or "description" keys), no explanations outside the JSON.
"""

USER_PROMPT_TEMPLATE = """
Analyze the following laptop listing:

Title: {title}
Price: {price}
Condition: {condition}
Shipping: {shipping}

Respond with a JSON object with exactly these top-level keys: {field_names}.

Here is an example of the exact shape expected (values are placeholders,
replace them with your real analysis of the listing above):
{example_json}
"""


def _placeholder_for_field(annotation: Any) -> Any:
    """Return a representative placeholder value for a field's type.

    Args:
        annotation: The type annotation of a Pydantic model field.

    Returns:
        A placeholder value matching the field's underlying type.
    """
    # Unwrap "X | None" (Optional) to get the underlying type.
    args = get_args(annotation)
    if type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        annotation = non_none[0] if non_none else str

    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    return "string"


def build_example_json(schema: type[T]) -> str:
    """Build a concrete example JSON object for the given schema.

    Showing a flat example (instead of a raw JSON Schema with meta
    keys like "properties" or "description") is far more reliable
    across different AI providers, which otherwise sometimes echo the
    schema's own structure instead of producing an instance of it.

    Args:
        schema: Pydantic model describing the expected output shape.

    Returns:
        A JSON string with placeholder values for every field.
    """
    example = {
        name: _placeholder_for_field(field.annotation)
        for name, field in schema.model_fields.items()
    }
    return json.dumps(example, indent=2)


def build_user_prompt(listing: dict[str, Any], schema: type[T]) -> str:
    """Build the user prompt for a single listing.

    Args:
        listing: Cleaned laptop listing data.
        schema: Pydantic model describing the expected output shape.

    Returns:
        Formatted user prompt string, including an example of the
        target output shape.
    """
    field_names = ", ".join(schema.model_fields.keys())
    example_json = build_example_json(schema)

    return USER_PROMPT_TEMPLATE.format(
        title=listing.get("title", ""),
        price=listing.get("price", ""),
        condition=listing.get("condition", ""),
        shipping=listing.get("shipping", ""),
        field_names=field_names,
        example_json=example_json,
    )


def build_messages(
    listing: dict[str, Any],
    schema: type[T],
) -> list[dict[str, str]]:
    """Build the system/user message pair sent to the AI provider.

    Args:
        listing: Cleaned laptop listing data.
        schema: Pydantic model describing the expected output shape.

    Returns:
        A list with exactly two messages: system, then user.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(listing, schema)},
    ]