"""Tests for search_books.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from search_books import GoodreadsClient, GoodreadsParser

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

SEARCH_HTML = """
<html><body>
<table class="tableList">
  <tr>
    <td><a class="bookTitle" href="/book/show/375802.The_Hobbit">
      <span itemprop="name">The Hobbit</span></a></td>
    <td><a class="authorName" href="/author/show/656983">
      <span itemprop="name">J.R.R. Tolkien</span></a></td>
    <td><span class="minirating">4.28 avg rating — 3,845,876 ratings</span></td>
  </tr>
  <tr>
    <td><a class="bookTitle" href="/book/show/5907.The_Hobbit_or_There_and_Back_Again">
      <span itemprop="name">The Hobbit, or There and Back Again</span></a></td>
    <td><a class="authorName" href="/author/show/656983">
      <span itemprop="name">J.R.R. Tolkien</span></a></td>
    <td><span class="minirating">4.30 avg rating — 100,000 ratings</span></td>
  </tr>
</table>
</body></html>
"""

EMPTY_SEARCH_HTML = """
<html><body>
<p>No results found.</p>
</body></html>
"""

# Uses modern Goodreads selectors (section.ReviewText) as returned by Playwright
BOOK_DETAIL_HTML = """
<html><body>
<h1 data-testid="bookTitle">The Hobbit</h1>
<div data-testid="description">
  <span>Short description.</span>
  <span>In a hole in the ground there lived a hobbit. A longer and more detailed description of the classic Tolkien novel.</span>
</div>
<section class="ReviewText">Absolutely wonderful classic fantasy that holds up perfectly.</section>
<section class="ReviewText">A charming adventure story perfect for all ages.</section>
</body></html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(html: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.text = html
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def _mock_playwright(html: str) -> MagicMock:
    """Build a mock sync_playwright context manager that returns the given HTML."""
    mock_page = MagicMock()
    mock_page.content.return_value = html
    mock_page.wait_for_selector.return_value = None

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    return mock_ctx


# ---------------------------------------------------------------------------
# GoodreadsParser tests (pure functions, no mocking needed)
# ---------------------------------------------------------------------------

class TestGoodreadsParser:
    def test_parse_search_results(self):
        results = GoodreadsParser.parse_search_results(SEARCH_HTML)
        assert len(results) == 2
        first = results[0]
        assert first["title"] == "The Hobbit"
        assert first["author"] == "J.R.R. Tolkien"
        assert first["avg_rating"] == 4.28
        assert "goodreads.com/book/show/375802" in first["url"]

    def test_parse_search_results_empty(self):
        assert GoodreadsParser.parse_search_results(EMPTY_SEARCH_HTML) == []

    def test_parse_search_results_missing_rating(self):
        html = """
        <html><body><table class="tableList">
          <tr>
            <td><a class="bookTitle" href="/book/show/1"><span>No Rating Book</span></a></td>
            <td><a class="authorName"><span>Someone</span></a></td>
          </tr>
        </table></body></html>
        """
        results = GoodreadsParser.parse_search_results(html)
        assert results[0]["avg_rating"] is None

    def test_parse_book_details(self):
        result = GoodreadsParser.parse_book_details(BOOK_DETAIL_HTML, url="https://example.com")
        assert result["title"] == "The Hobbit"
        assert "hobbit" in result["description"].lower()
        assert len(result["reviews"]) == 2
        assert result["url"] == "https://example.com"

    def test_parse_book_details_truncates_reviews(self):
        html = f"""
        <html><body>
        <section class="ReviewText">{"x" * 600}</section>
        </body></html>
        """
        result = GoodreadsParser.parse_book_details(html)
        assert len(result["reviews"][0]) <= 504
        assert result["reviews"][0].endswith("...")

    def test_parse_book_details_missing_fields(self):
        result = GoodreadsParser.parse_book_details("<html><body><p>Nothing</p></body></html>")
        assert result["title"] is None
        assert result["description"] is None
        assert result["reviews"] == []

    def test_parse_book_details_legacy_review_selector(self):
        html = """
        <html><body>
        <div class="reviewText">A legacy review.</div>
        </body></html>
        """
        result = GoodreadsParser.parse_book_details(html)
        assert len(result["reviews"]) == 1


# ---------------------------------------------------------------------------
# GoodreadsClient tests (mocks requests / Playwright)
# ---------------------------------------------------------------------------

class TestGoodreadsClient:
    def setup_method(self):
        self.client = GoodreadsClient()

    def test_search_returns_results(self):
        with patch("search_books.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = self.client.search("hobbit")
        assert len(results) == 2
        assert results[0]["title"] == "The Hobbit"

    def test_search_respects_limit(self):
        with patch("search_books.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = self.client.search("hobbit", limit=1)
        assert len(results) == 1

    def test_search_empty_results(self):
        with patch("search_books.requests.get", return_value=_mock_response(EMPTY_SEARCH_HTML)):
            assert self.client.search("xyzzy_no_such_book") == []

    def test_search_network_error(self):
        import requests as req
        with patch("search_books.requests.get", side_effect=req.RequestException("timeout")):
            result = self.client.search("hobbit")
        assert "error" in result
        assert "timeout" in result["error"]

    def test_get_book_details_returns_parsed_result(self):
        url = "https://www.goodreads.com/book/show/375802"
        with patch("search_books.sync_playwright", return_value=_mock_playwright(BOOK_DETAIL_HTML)):
            result = self.client.get_book_details(url)
        assert result["title"] == "The Hobbit"
        assert len(result["reviews"]) == 2
        assert result["url"] == url

    def test_get_book_details_playwright_error(self):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Exception("browser crashed"))
        mock_ctx.__exit__ = MagicMock(return_value=False)
        with patch("search_books.sync_playwright", return_value=mock_ctx):
            result = self.client.get_book_details("https://www.goodreads.com/book/show/1")
        assert "error" in result
        assert "browser crashed" in result["error"]
