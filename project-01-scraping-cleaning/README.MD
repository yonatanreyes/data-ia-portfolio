
# Project 01 — eBay Laptop Scraper & Data Cleaning Pipeline

![Python](https://img.shields.io/badge/python-3.12-blue)
![Status](https://img.shields.io/badge/status-completed-brightgreen)
![Built with](<https://img.shields.io/badge/built%20with-Playwright%20%7C%20Pandas-orange>)

## What this does

Extracts laptop listings from eBay (US market) using Playwright and BeautifulSoup, then cleans and normalizes the raw data with Pandas. The output is an analysis-ready dataset suited for competitive price monitoring.

## Why it's useful

Raw scraped data is messy: prices come as strings with currency symbols, shipping costs are inconsistently formatted, and duplicate listings are common. This pipeline turns that raw HTML into a clean, structured dataset in one repeatable process — ready to load straight into a spreadsheet or downstream analysis, without manual cleanup.

## Tech stack

- Python 3.12
- Playwright — renders the dynamic search results page
- BeautifulSoup — parses the HTML and extracts raw fields
- Pandas — cleans, normalizes, and exports the final dataset

## Data schema

| Field         | Type   | Description                                                 |
| ------------- | ------ | ----------------------------------------------------------- |
| `title`     | string | Listing title                                               |
| `price`     | float  | Current price, cleaned from currency symbols                |
| `shipping`  | float  | Shipping cost —`0.0` if free, `NaN` if not specified   |
| `condition` | string | Item condition (e.g., "Brand New", "Pre-Owned"), Title case |
| `item_url`  | string | Absolute URL to the listing                                 |

## Project structure

```
project-01-scraping-cleaning/
├── README.md
├── requirements.txt
├── src/
│   ├── scraper.py       # Playwright + BeautifulSoup extraction
│   └── cleaning.py      # Pandas transformation
├── sample_output.csv    # Curated sample of the clean dataset
└── output/              # Gitignored — generated on each run
    └── .gitkeep
```

## How to run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Run the scraper (produces `output/raw_data.json`):
   ```bash
   python src/scraper.py
   ```
3. Run the cleaning pipeline (produces `output/clean_data.csv` and `output/clean_data.json`):
   ```bash
   python src/cleaning.py
   ```

## Example output

See [`sample_output.csv`](./sample_output.csv) for a sample of the cleaned dataset.

## Notes

- Scoped to page 1 of search results only — pagination is out of scope for this milestone.
- Respects reasonable request timing; not intended for aggressive or large-scale scraping.
- No real client data is included in this repository — the sample data reflects publicly available eBay listings only.
- Scheduling, historical price tracking, notifications, and AI-based enrichment are handled as separate features, not part of this project's scope.
- The scraper does not force a fixed locale, so eBay renders language and currency based on where it's executed. Prices in `sample_output.csv` appear in COP because the sample was generated from Colombia; running the scraper from a different location will reflect that region's language and currency instead.
