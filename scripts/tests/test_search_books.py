"""Tests for search_books.py using mocked HTTP responses."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow importing from parent scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from search_books import get_book_details, search_books

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

BOOK_DETAIL_HTML = """
<html><body>
<h1 data-testid="bookTitle">The Hobbit</h1>
<div data-testid="description">
  <span>Short description.</span>
  <span>In a hole in the ground there lived a hobbit. A longer and more detailed description of the classic Tolkien novel.</span>
</div>
<div class="reviewText">Absolutely wonderful classic fantasy that holds up perfectly.</div>
<div class="reviewText">A charming adventure story perfect for all ages.</div>
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


# ---------------------------------------------------------------------------
# search_books tests
# ---------------------------------------------------------------------------

class TestSearchBooks:
    def test_parse_search_results(self):
        with patch("search_books.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = search_books("hobbit")

        assert isinstance(results, list)
        assert len(results) == 2

        first = results[0]
        assert first["title"] == "The Hobbit"
        assert first["author"] == "J.R.R. Tolkien"
        assert first["avg_rating"] == 4.28
        assert "goodreads.com" in first["url"]

    def test_limit_respected(self):
        with patch("search_books.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = search_books("hobbit", limit=1)

        assert len(results) == 1

    def test_empty_results_when_no_table(self):
        with patch("search_books.requests.get", return_value=_mock_response(EMPTY_SEARCH_HTML)):
            results = search_books("xyzzy_no_such_book")

        assert results == []

    def test_network_error_returns_error_dict(self):
        import requests as req
        with patch("search_books.requests.get", side_effect=req.RequestException("timeout")):
            result = search_books("hobbit")

        assert isinstance(result, dict)
        assert "error" in result
        assert "timeout" in result["error"]


# ---------------------------------------------------------------------------
# get_book_details tests
# ---------------------------------------------------------------------------

class TestGetBookDetails:
    def test_parse_book_details(self):
        url = "https://www.goodreads.com/book/show/375802"
        with patch("search_books.requests.get", return_value=_mock_response(BOOK_DETAIL_HTML)):
            result = get_book_details(url)

        assert result["title"] == "The Hobbit"
        assert "hobbit" in result["description"].lower()
        assert len(result["reviews"]) == 2
        assert result["url"] == url

    def test_reviews_truncated_at_500_chars(self):
        long_review = "x" * 600
        html = f"""
        <html><body>
        <h1 data-testid="bookTitle">Test Book</h1>
        <div class="reviewText">{long_review}</div>
        </body></html>
        """
        with patch("search_books.requests.get", return_value=_mock_response(html)):
            result = get_book_details("https://www.goodreads.com/book/show/1")

        assert len(result["reviews"][0]) <= 504  # 500 chars + "..."
        assert result["reviews"][0].endswith("...")

    def test_network_error_returns_error_dict(self):
        import requests as req
        with patch("search_books.requests.get", side_effect=req.RequestException("connection refused")):
            result = get_book_details("https://www.goodreads.com/book/show/1")

        assert "error" in result
        assert "connection refused" in result["error"]

    def test_missing_fields_handled_gracefully(self):
        minimal_html = "<html><body><p>Nothing here</p></body></html>"
        with patch("search_books.requests.get", return_value=_mock_response(minimal_html)):
            result = get_book_details("https://www.goodreads.com/book/show/1")

        assert result["title"] is None
        assert result["description"] is None
        assert result["reviews"] == []
