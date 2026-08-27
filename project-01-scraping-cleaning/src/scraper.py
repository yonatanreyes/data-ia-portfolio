"""Scraper for eBay laptop listings.

Uses Playwright to render the search results page (eBay relies on
JavaScript for part of its listing markup) and BeautifulSoup to parse
the resulting HTML and extract raw product data. The raw output is
saved as JSON for the cleaning pipeline (see cleaning.py) to consume.
"""

import asyncio
import json
import logging
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag
from playwright.async_api import Page, async_playwright

# --- Configuration ---------------------------------------------------------

BASE_URL = "https://www.ebay.com/sch/i.html?_nkw=laptop&_pgn={page}"
MAX_PAGES = 2
PAGE_LOAD_TIMEOUT_MS = 5000
# Keep True for normal runs. If scraping suddenly returns no results
# (possible anti-bot detection or a layout change), switch to False
# temporarily to watch the browser and debug visually.
HEADLESS = True

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "raw_data.json"

PRODUCT_CARD_SELECTOR = "div.su-card-container__content"
TITLE_SELECTOR = "div.s-card__title span.su-styled-text.primary.default"
PRICE_SELECTOR = "span.s-card__price span.su-styled-text.primary.bold"
PRICE_FALLBACK_SELECTOR = "span.s-card__price"
SHIPPING_SELECTOR = (
    "div.s-card__attribute-row:nth-of-type(3) "
    "span.su-styled-text.secondary.large"
)
CONDITION_SELECTOR = "div.s-card__subtitle span.su-styled-text.secondary.default"
CONDITION_SEPARATOR_CHARS = " ·"
SPONSORED_LISTING_TEXT = "Shop on eBay"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# --- Parsing helpers ---------------------------------------------------

def _extract_text(card: Tag, selector: str) -> str | None:
    """Return the stripped text of the first element matching a selector.

    Args:
        card: A BeautifulSoup Tag representing a single product card.
        selector: CSS selector to look for within the card.

    Returns:
        The stripped text if the element is found, otherwise None.
    """
    element = card.select_one(selector)
    return element.get_text(strip=True) if element else None


def _clean_condition_text(raw_condition: str | None) -> str | None:
    """Strip the trailing separator eBay adds after the condition text.

    eBay renders the condition as the first item in a subtitle line
    shared with other attributes (e.g. "Refurbished · Dell"), so the
    raw extracted text includes a trailing " · " that needs to be
    removed to keep only the condition value itself.

    Args:
        raw_condition: The raw text extracted from the condition span,
            or None if the element wasn't found.

    Returns:
        The cleaned condition text, or None if there was nothing to clean.
    """
    if not raw_condition:
        return None
    return raw_condition.rstrip(CONDITION_SEPARATOR_CHARS) or None


def parse_product_card(card: Tag) -> dict | None:
    """Extract raw product fields from a single product card.

    Args:
        card: A BeautifulSoup Tag representing one listing card.

    Returns:
        A dict with the raw scraped fields, or None if the card is a
        sponsored placeholder ("Shop on eBay") rather than a real listing.
    """
    title = _extract_text(card, TITLE_SELECTOR)

    if not title or SPONSORED_LISTING_TEXT in title:
        return None

    price = _extract_text(card, PRICE_SELECTOR) or _extract_text(
        card, PRICE_FALLBACK_SELECTOR
    )
    shipping = _extract_text(card, SHIPPING_SELECTOR)
    condition = _clean_condition_text(_extract_text(card, CONDITION_SELECTOR))

    return {
        "title": title,
        "price": price,
        "shipping": shipping,
        "condition": condition,
    }


def extract_products_from_html(html: str) -> list[dict]:
    """Parse a search results page and return the raw product list.

    Args:
        html: Full HTML content of an eBay search results page.

    Returns:
        A list of dicts, one per valid product card found on the page.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(PRODUCT_CARD_SELECTOR)
    logger.info("Found %d product cards on the page", len(cards))

    products = [parse_product_card(card) for card in cards]
    return [product for product in products if product is not None]


# --- Scraping ------------------------------------------------------------

async def fetch_page_html(page: Page, url: str) -> str:
    """Navigate to a URL and return the rendered page HTML.

    eBay occasionally aborts the initial navigation with a redirect,
    which Playwright surfaces as an exception even though the page
    still loads correctly. That case is logged as a warning and
    execution continues; any other issue would surface later when the
    HTML fails to contain the expected product cards.

    Args:
        page: An active Playwright Page instance.
        url: The URL to navigate to.

    Returns:
        The full HTML content of the page after the fixed wait.
    """
    try:
        await page.goto(url, wait_until="domcontentloaded")
    except Exception as error:  # noqa: BLE001 - eBay redirect quirk
        logger.warning("Navigation warning for %s: %s", url, error)

    # Fixed wait to allow eBay's client-side rendering to finish.
    # TODO: replace with page.wait_for_selector(PRODUCT_CARD_SELECTOR)
    # for a more reliable, less arbitrary wait once the selector has
    # been confirmed stable across page loads.
    await page.wait_for_timeout(PAGE_LOAD_TIMEOUT_MS)

    return await page.content()


async def scrape_listings(max_pages: int = MAX_PAGES) -> list[dict]:
    """Scrape eBay laptop listings across a fixed number of pages.

    Args:
        max_pages: Number of search result pages to scrape.

    Returns:
        A list of raw product dicts collected across all pages.
    """
    all_products: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=HEADLESS)
        try:
            context = await browser.new_context()
            page = await context.new_page()

            for page_number in range(1, max_pages + 1):
                url = BASE_URL.format(page=page_number)
                logger.info("Scraping page %d: %s", page_number, url)

                html = await fetch_page_html(page, url)
                page_products = extract_products_from_html(html)
                all_products.extend(page_products)
        finally:
            # Ensures the browser is closed even if scraping fails,
            # and does so while Playwright's driver is still running.
            await browser.close()

    return all_products


# --- Persistence -----------------------------------------------------------

def save_raw_data(products: list[dict], output_file: Path = OUTPUT_FILE) -> None:
    """Save the raw scraped products to a JSON file.

    Args:
        products: List of raw product dicts to persist.
        output_file: Destination path for the JSON file.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(products, json_file, indent=4, ensure_ascii=False)
    logger.info("Saved %d products to %s", len(products), output_file)


# --- Entry point -----------------------------------------------------------

async def main() -> None:
    """Run the full scraping process and persist the raw results."""
    products = await scrape_listings()
    save_raw_data(products)
    logger.info("Scraping finished. Total products extracted: %d", len(products))


if __name__ == "__main__":
    asyncio.run(main())