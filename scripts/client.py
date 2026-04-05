"""Fetches book data from Goodreads."""

from urllib.parse import urlencode

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from .parser import GoodreadsParser


class GoodreadsClient:
    """Fetches book data from Goodreads."""

    BASE_URL = "https://www.goodreads.com"
    _USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    _HEADERS = {
        "User-Agent": _USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> list | dict:
        """Search Goodreads for books matching the query (static HTML via requests)."""
        url = f"{self.BASE_URL}/search?" + urlencode({"q": query})
        try:
            response = requests.get(url, headers=self._HEADERS, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            return {"error": str(exc), "results": []}

        return GoodreadsParser.parse_search_results(response.text)[:limit]

    def get_book_details(self, url: str) -> dict:
        """Fetch details and JS-rendered reviews for a book page (via Playwright)."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    user_agent=self._USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                )
                # Mask navigator.webdriver to avoid bot detection
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for reviews to render; proceed with whatever loaded if they don't appear
                try:
                    page.wait_for_selector(
                        "section.ReviewText, div[data-testid='review'], div.reviewText",
                        timeout=8000,
                    )
                except PlaywrightTimeout:
                    pass
                html = page.content()
                browser.close()
        except Exception as exc:
            return {"error": str(exc)}

        return GoodreadsParser.parse_book_details(html, url=url)
