"""CSV input and output utilities.

Handles reading, validation, and writing of CSV files used by the
data enrichment pipeline. This module has no knowledge of AI providers
or prompts — it only deals with tabular data.
"""

import logging
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


REQUIRED_COLUMNS = {
    "title",
    "price",
    "condition",
    "shipping",
}


def read_csv(path: Path) -> pd.DataFrame:
    """Read and validate the input CSV file.

    Args:
        path: Path to the input CSV file.

    Returns:
        DataFrame containing the input data.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be accessed.
        ValueError: If required columns are missing.
        pd.errors.EmptyDataError: If the file is empty.
        pd.errors.ParserError: If the CSV cannot be parsed.
    """
    logger.info("Reading CSV file: %s", path)

    if not path.exists():
        raise FileNotFoundError(f"Input CSV file not found: {path}")

    try:
        df = pd.read_csv(path)

    except PermissionError:
        logger.exception("Permission denied while reading CSV: %s", path)
        raise

    except pd.errors.EmptyDataError:
        logger.exception("CSV file is empty: %s", path)
        raise

    except pd.errors.ParserError:
        logger.exception("Unable to parse CSV file: %s", path)
        raise

    validate_required_columns(df)

    logger.info("Loaded %d records from CSV.", len(df))

    return df


def validate_required_columns(df: pd.DataFrame) -> None:
    """Validate that required input columns exist.

    Args:
        df: Input DataFrame.

    Raises:
        ValueError: If one or more required columns are missing.
    """
    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            "Missing required CSV columns: " + ", ".join(sorted(missing_columns))
        )


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to a CSV file.

    Args:
        df: DataFrame to save.
        path: Destination path.

    Raises:
        PermissionError: If the destination cannot be written.
        OSError: If another filesystem error occurs.
    """
    logger.info("Writing CSV file: %s", path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8")

    except PermissionError:
        logger.exception("Permission denied while writing CSV: %s", path)
        raise

    except OSError:
        logger.exception("Filesystem error while writing CSV: %s", path)
        raise

    logger.info("CSV successfully written: %s", path)