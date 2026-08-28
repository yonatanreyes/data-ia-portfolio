"""
Data cleaning pipeline for raw eBay scraping data.

This module reads raw JSON data, cleans numeric fields, removes duplicates,
normalizes text formats, and exports the structured dataset to CSV and JSON.
"""

import json
import logging
from pathlib import Path

import pandas as pd

# --- Configuration ---------------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RAW_DATA_FILE = OUTPUT_DIR / "raw_data.json"
CLEAN_DATA_CSV = OUTPUT_DIR / "clean_data.csv"
CLEAN_DATA_JSON = OUTPUT_DIR / "clean_data.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# --- Data Loading ----------------------------------------------------------

def load_raw_data(file_path: Path) -> pd.DataFrame | None:
    """
    Loads raw data from a JSON or CSV file into a Pandas DataFrame.

    Args:
        file_path: Path object pointing to the data file.

    Returns:
        A Pandas DataFrame if successful, otherwise None.
    """
    try:
        if file_path.suffix == ".json":
            return pd.read_json(file_path)
        elif file_path.suffix == ".csv":
            return pd.read_csv(file_path)
        else:
            logger.error("Unsupported file type: %s", file_path.suffix)
            return None
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to load data: %s", e)
        return None


# --- Data Cleaning ---------------------------------------------------------

def clean_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Extracts numeric values from messy string columns, converts them to float,
    and rounds to 2 decimal places. Handles currency symbols and thousand separators.

    Args:
        df: The Pandas DataFrame containing the raw data.
        columns: A list of column names to be cleaned.

    Returns:
        The DataFrame with the specified columns cleaned and rounded.
    """
    # Captures numbers with multiple thousand separators (e.g., "4,389,381.30")
    pattern = r'(\d[\d.,]*\d|\d)'
    
    for col in columns:
        if col not in df.columns:
            logger.warning("Column '%s' not found. Skipping.", col)
            continue
            
        extracted = df[col].str.extract(pattern, expand=False)
        # Remove commas so Pandas can parse the string into a float
        cleaned_strings = extracted.str.replace(',', '', regex=False)
        
        # Coerce invalid data to NaN and round to fix floating-point precision issues
        df[col] = pd.to_numeric(cleaned_strings, errors='coerce').round(2)
            
    return df


def remove_duplicate_records(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """
    Removes duplicate rows based on a subset of columns.

    Args:
        df: The Pandas DataFrame to process.
        subset: List of column names to consider for identifying duplicates.

    Returns:
        DataFrame with duplicates removed.
    """
    initial_count = len(df)
    df_clean = df.drop_duplicates(subset=subset)
    removed_count = initial_count - len(df_clean)
    logger.info("Removed %d duplicate records.", removed_count)
    return df_clean


def normalize_condition(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fills missing condition values and normalizes text to Title Case.

    Args:
        df: The Pandas DataFrame to process.

    Returns:
        DataFrame with the 'condition' column normalized.
    """
    if 'condition' in df.columns:
        # Fill NaNs first, then convert to string and apply Title Case
        df['condition'] = df['condition'].fillna('Not specified')
        df['condition'] = df['condition'].astype(str).str.title()
    return df


# --- Data Export -----------------------------------------------------------

def export_clean_data(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """
    Exports the cleaned DataFrame to CSV and JSON formats.
    
    Uses the standard json library for JSON export to avoid unwanted 
    escaping of forward slashes (e.g., "\/").

    Args:
        df: The cleaned Pandas DataFrame.
        csv_path: Destination path for the CSV file.
        json_path: Destination path for the JSON file.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to CSV
    df.to_csv(csv_path, index=False, encoding='utf-8')
    logger.info("Data exported to CSV: %s", csv_path)
    
    # Export to JSON (using standard json library to avoid escaping forward slashes)
    records = df.to_dict(orient='records')
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=4, ensure_ascii=False)
    logger.info("Data exported to JSON: %s", json_path)


# --- Orchestration ---------------------------------------------------------

def main() -> None:
    """Runs the full data cleaning pipeline and persists the results."""
    logger.info("Starting data cleaning pipeline...")
    
    # 1. Load data
    df = load_raw_data(RAW_DATA_FILE)
    if df is None:
        return
        
    initial_rows = len(df)
    logger.info("Loaded %d raw records.", initial_rows)
    
    # 2. Drop critical nulls (title and price)
    df = df.dropna(subset=['title', 'price'])
    logger.info("Dropped rows with missing title or price. %d records remaining.", len(df))
    
    # 3. Clean numeric columns
    df = clean_numeric_columns(df, ['price', 'shipping'])
    
    # 4. Remove duplicates
    df = remove_duplicate_records(df, subset=['title', 'item_url'])
    
    # 5. Fill remaining nulls and normalize text
    df['shipping'] = df['shipping'].fillna(0.0)
    df = normalize_condition(df)
    
    # 6. Export data
    export_clean_data(df, CLEAN_DATA_CSV, CLEAN_DATA_JSON)
    
    logger.info("Cleaning pipeline finished successfully. Final records: %d", len(df))


if __name__ == "__main__":
    main()




