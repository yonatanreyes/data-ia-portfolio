
# Project 02 — AI-Powered Laptop Data Enrichment Pipeline

![Python](https://img.shields.io/badge/python-3.12-blue)
![Status](https://img.shields.io/badge/status-completed-brightgreen)
![Built with](<https://img.shields.io/badge/built%20with-OpenAI%20%7C%20Anthropic%20%7C%20Pydantic-orange>)

## What this does

Enriches raw laptop listing data (title, price, condition, shipping) using an LLM to extract structured specifications — brand, RAM, storage, CPU, category, and a value rating with reasoning. The pipeline works with OpenAI, any OpenAI-compatible provider (Z.ai, Mistral, DeepSeek, Groq, Gemini), or Anthropic, swappable through configuration alone.

## Why it's useful

Listing titles are unstructured and inconsistent — the same laptop might be described as "16GB RAM" in one listing and "16 GB" or "16gb ram" in another. This pipeline turns that free text into a validated, structured dataset (via Pydantic schemas) ready for filtering, comparison, or price benchmarking, while handling the realities of calling an LLM in production: transient network failures, malformed responses, and rate limits — without a single bad row stopping the whole batch.

## Tech stack

- Python 3.12
- OpenAI SDK — used both for OpenAI itself and for any OpenAI-compatible endpoint (Z.ai, Mistral, DeepSeek, Groq, Gemini)
- Anthropic SDK — native support for Claude models
- Pydantic — validates every AI response against a strict output schema
- python-dotenv — loads provider configuration from `.env`
- Pandas — reads the input CSV and assembles the enriched output

## Data schema

**Input** (required columns):

| Field         | Type   | Description                   |
| ------------- | ------ | ----------------------------- |
| `title`     | string | Listing title                 |
| `price`     | string | Listed price                  |
| `condition` | string | Item condition as listed      |
| `shipping`  | string | Shipping cost/terms as listed |

**Output** (added columns, one set per row):

| Field            | Type           | Description                                               |
| ---------------- | -------------- | --------------------------------------------------------- |
| `brand`        | string         | Manufacturer extracted from the title                     |
| `ram_gb`       | int or null    | RAM in GB, if stated                                      |
| `storage_gb`   | int or null    | Storage in GB, if stated                                  |
| `cpu`          | string or null | CPU model, if stated                                      |
| `category`     | string         | Laptop category (e.g. "Business", "Gaming")               |
| `value_rating` | string         | Qualitative value assessment based on price and condition |
| `reasoning`    | string         | Short explanation behind the value rating                 |

## Project structure

```
project-02-ai-enrichment/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                       # Pipeline orchestrator
│   ├── config.py                     # Environment configuration and provider resolution
│   ├── schemas.py                    # Pydantic output contract
│   ├── prompts.py                    # Prompt construction
│   ├── retry.py                      # Exponential backoff for transient errors
│   ├── csv_handler.py                # CSV read/write and validation
│   └── providers/
│       ├── base.py                   # AIProvider interface
│       ├── openai_compatible.py      # OpenAI + OpenAI-compatible providers
│       └── anthropic_provider.py     # Anthropic (Claude)
├── data/
│   └── input_data_sample.csv         # Sample input dataset for testing
└── output/                           # Gitignored — generated on each run
    └── .gitkeep
```

## How to run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy the environment template and fill in your provider and API key:
   ```bash
   cp .env.example .env
   ```
3. Run the pipeline:
   ```bash
   python -m app.main
   ```

The enriched dataset is written to the path set in `OUTPUT_FILE` (default: `output/output_data.csv`).

## Switching AI providers

Changing models is a configuration change only — no code edits required:

```env
AI_PROVIDER=zai
AI_MODEL=glm-4.5-flash
AI_API_KEY=your_zai_key_here
```

Supported out of the box: `openai`, `zai`, `mistral`, `deepseek`, `groq`, `gemini`, `anthropic`. Any other OpenAI-compatible provider works by setting `AI_BASE_URL` explicitly.

## Example output

Running the pipeline against `data/input_data_sample.csv` (the file set in `INPUT_FILE` by default) is a quick way to validate the setup end to end without exhausting free-tier quotas.

## Notes

- One failed row (network error, empty response, or schema mismatch) is logged and filled with empty fields — it never stops the rest of the batch.
- Free-tier rate limits vary significantly by provider and model; `input_data_sample.csv` is provided specifically to test the pipeline without hitting daily quotas.
- Batch-mode (asynchronous, high-volume) processing is out of scope for this version — the pipeline runs synchronously, one listing at a time, which is sufficient for the dataset sizes this project targets.
- No real client data is included in this repository — the sample data reflects publicly available laptop listings only.
- Structured output is enforced via Pydantic on every provider, regardless of whether the underlying model natively supports structured outputs.
