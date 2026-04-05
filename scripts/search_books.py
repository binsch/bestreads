#!/usr/bin/env python3
"""Search Goodreads for books and reviews."""

import argparse
import json
import sys
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.goodreads.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 15


def _parse_search_html(html: str) -> list:
    """Parse Goodreads search results page HTML into a list of book dicts."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    table = soup.find("table", class_="tableList")
    if not table:
        return results

    for row in table.find_all("tr"):
        title_tag = row.find("a", class_="bookTitle")
        author_tag = row.find("a", class_="authorName")
        rating_tag = row.find("span", class_="minirating")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        book_url = urljoin(BASE_URL, title_tag.get("href", ""))
        author = author_tag.get_text(strip=True) if author_tag else "Unknown"

        avg_rating = None
        if rating_tag:
            parts = rating_tag.get_text(strip=True).split()
            if parts:
                try:
                    avg_rating = float(parts[0])
                except ValueError:
                    pass

        results.append({
            "title": title,
            "author": author,
            "avg_rating": avg_rating,
            "url": book_url,
        })

    return results


def _parse_book_html(html: str, url: str = "") -> dict:
    """Parse a Goodreads book page HTML (after JS render) into a details dict."""
    soup = BeautifulSoup(html, "lxml")

    # Title — try modern data-testid first, fall back to legacy id
    title_tag = soup.find("h1", {"data-testid": "bookTitle"}) or soup.find(
        "h1", id="bookTitle"
    )
    title = title_tag.get_text(strip=True) if title_tag else None

    # Description — try modern selector, then legacy
    desc_container = soup.find("div", {"data-testid": "description"}) or soup.find(
        "div", id="description"
    )
    description = None
    if desc_container:
        spans = desc_container.find_all("span")
        candidates = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
        if candidates:
            description = max(candidates, key=len)

    # Reviews — modern Goodreads uses <section class="ReviewText">;
    # fall back to legacy selectors for older page versions
    review_nodes = (
        soup.find_all("section", class_="ReviewText")
        or soup.find_all("div", {"data-testid": "review"})
        or soup.find_all("div", class_="reviewText")
    )
    reviews = []
    for node in review_nodes[:5]:
        text = node.get_text(separator=" ", strip=True)
        if text:
            reviews.append(text[:500] + ("..." if len(text) > 500 else ""))

    return {
        "url": url,
        "title": title,
        "description": description,
        "reviews": reviews,
    }


def search_books(query: str, limit: int = 10) -> list:
    """Search Goodreads for books matching the query (uses requests; page is static HTML)."""
    url = f"{BASE_URL}/search?" + urlencode({"q": query})
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"error": str(exc), "results": []}

    return _parse_search_html(response.text)[:limit]


def get_book_details(url: str) -> dict:
    """Fetch details and JS-rendered reviews for a specific book page (uses Playwright)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
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

    return _parse_book_html(html, url=url)


def main():
    parser = argparse.ArgumentParser(description="Search Goodreads for books")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--book-url", metavar="URL", help="Fetch details for a book URL")
    parser.add_argument("--limit", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    if args.book_url:
        result = get_book_details(args.book_url)
    elif args.query:
        result = search_books(args.query, limit=args.limit)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
