"""Main entry point for the AI data enrichment pipeline."""

import logging

import pandas as pd

from app.config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_MAX_RETRIES,
    AI_MODEL,
    AI_PROVIDER,
    INPUT_FILE,
    NATIVE_SDK_PROVIDERS,
    OUTPUT_FILE,
)
from app.csv_handler import read_csv, write_csv
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import AIProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import EnrichedListing


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def build_ai_provider() -> AIProvider:
    """Build the AI provider selected in configuration.

    This is the ONLY place in the project that chooses which concrete
    provider class to instantiate. Everything downstream works against
    the `AIProvider` interface, so switching providers is a matter of
    editing `.env`, not code.

    Returns:
        A ready-to-use AIProvider instance.
    """
    if AI_PROVIDER in NATIVE_SDK_PROVIDERS:
        return AnthropicProvider(
            api_key=AI_API_KEY,
            model=AI_MODEL,
            max_retries=AI_MAX_RETRIES,
        )

    return OpenAICompatibleProvider(
        api_key=AI_API_KEY,
        model=AI_MODEL,
        base_url=AI_BASE_URL,
        max_retries=AI_MAX_RETRIES,
    )


def enrich_dataframe(df: pd.DataFrame, provider: AIProvider) -> pd.DataFrame:
    """Enrich every row of a DataFrame using the given AI provider.

    A failure on a single listing (after retries are exhausted, or a
    schema mismatch) is logged and filled with empty enrichment
    fields, instead of crashing the whole run. One bad row should
    never cost you the other 999 results.

    Args:
        df: Original input DataFrame.
        provider: AI provider used to enrich each listing.

    Returns:
        DataFrame combining original columns and enrichment columns.
    """
    empty_result = {field: None for field in EnrichedListing.model_fields}
    enriched_rows = []

    for _, row in df.iterrows():
        listing = row.to_dict()

        try:
            result = provider.generate_structured(listing, EnrichedListing)
            enriched_rows.append(result.model_dump())

        # Broad on purpose: this loop must survive ANY failure on a
        # single listing (network errors past retries, malformed JSON,
        # schema mismatches) without aborting the rest of the batch.
        except Exception as error:
            logger.error(
                "Failed to enrich listing '%s': %s",
                listing.get("title", "Unknown"),
                error,
            )
            enriched_rows.append(empty_result)

    enriched_df = pd.DataFrame(enriched_rows)

    return pd.concat(
        [df.reset_index(drop=True), enriched_df.reset_index(drop=True)],
        axis=1,
    )


def main() -> None:
    """Run the laptop data enrichment pipeline."""
    logger.info(
        "Starting data enrichment pipeline with provider '%s'.",
        AI_PROVIDER,
    )

    df = read_csv(INPUT_FILE)
    logger.info("Processing %d listings.", len(df))

    provider = build_ai_provider()
    result_df = enrich_dataframe(df, provider)

    write_csv(result_df, OUTPUT_FILE)

    logger.info("Enrichment pipeline completed successfully.")


if __name__ == "__main__":
    main()