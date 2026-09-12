"""Application configuration.

Single entry point for environment variables. Resolves which AI
provider is active and, for OpenAI-compatible providers, which base
URL to point the client at. Fails fast at import time if the
configuration is invalid, instead of failing later mid-run.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


def get_required_env(name: str) -> str:
    """Return a required environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Environment variable value.

    Raises:
        RuntimeError: If the variable is missing or empty.
    """
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not configured."
        )

    return value


# --------------------------------------------------------------------------
# AI provider configuration
# --------------------------------------------------------------------------

AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").strip().lower()
AI_MODEL = get_required_env("AI_MODEL")
AI_API_KEY = get_required_env("AI_API_KEY")
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))

# An explicit AI_BASE_URL always wins. This lets someone plug in a
# brand-new OpenAI-compatible provider that isn't in the registry
# below, without touching any code.
_AI_BASE_URL_OVERRIDE = os.getenv("AI_BASE_URL", "").strip() or None

# Providers whose API is genuinely different from OpenAI's Chat
# Completions format and therefore need their own SDK/implementation.
NATIVE_SDK_PROVIDERS = {"anthropic"}

# Known base URLs for common OpenAI-compatible providers. "openai" maps
# to None so the OpenAI SDK falls back to its own default endpoint.
KNOWN_OPENAI_COMPATIBLE_BASE_URLS: dict[str, str | None] = {
    "openai": None,
    "zai": "https://api.z.ai/api/paas/v4/",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

if AI_PROVIDER not in NATIVE_SDK_PROVIDERS:

    _is_known_provider = AI_PROVIDER in KNOWN_OPENAI_COMPATIBLE_BASE_URLS

    if not _is_known_provider and not _AI_BASE_URL_OVERRIDE:
        known = ", ".join(sorted(KNOWN_OPENAI_COMPATIBLE_BASE_URLS))
        raise ValueError(
            f"Unknown AI_PROVIDER '{AI_PROVIDER}'. Use one of: "
            f"{known}, anthropic — or set AI_BASE_URL explicitly if "
            "it's an OpenAI-compatible provider not in this list."
        )

    AI_BASE_URL = (
        _AI_BASE_URL_OVERRIDE
        or KNOWN_OPENAI_COMPATIBLE_BASE_URLS.get(AI_PROVIDER)
    )

else:
    AI_BASE_URL = None

# --------------------------------------------------------------------------
# File paths
# --------------------------------------------------------------------------

INPUT_FILE = PROJECT_ROOT / os.getenv(
    "INPUT_FILE",
    "data/input_data.csv",
)

OUTPUT_FILE = PROJECT_ROOT / os.getenv(
    "OUTPUT_FILE",
    "data/output_data.csv",
)