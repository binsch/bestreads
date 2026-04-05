"""Tests for GoodreadsClient."""

from unittest.mock import MagicMock, patch

from scripts.client import GoodreadsClient

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
# Tests
# ---------------------------------------------------------------------------

class TestGoodreadsClient:
    def setup_method(self):
        self.client = GoodreadsClient()

    def test_search_uses_custom_timeout(self):
        client = GoodreadsClient(timeout=5)
        with patch("scripts.client.requests.get", return_value=_mock_response(SEARCH_HTML)) as mock_get:
            client.search("hobbit")
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 5

    def test_search_returns_results(self):
        with patch("scripts.client.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = self.client.search("hobbit")
        assert len(results) == 2
        assert results[0]["title"] == "The Hobbit"

    def test_search_respects_limit(self):
        with patch("scripts.client.requests.get", return_value=_mock_response(SEARCH_HTML)):
            results = self.client.search("hobbit", limit=1)
        assert len(results) == 1

    def test_search_empty_results(self):
        with patch("scripts.client.requests.get", return_value=_mock_response("<html><body></body></html>")):
            assert self.client.search("xyzzy_no_such_book") == []

    def test_search_network_error(self):
        import requests as req
        with patch("scripts.client.requests.get", side_effect=req.RequestException("timeout")):
            result = self.client.search("hobbit")
        assert "error" in result
        assert "timeout" in result["error"]

    def test_search_http_error(self):
        import requests as req
        mock = _mock_response(SEARCH_HTML, status_code=403)
        mock.raise_for_status.side_effect = req.HTTPError("403 Forbidden")
        with patch("scripts.client.requests.get", return_value=mock):
            result = self.client.search("hobbit")
        assert "error" in result
        assert "403" in result["error"]

    def test_get_book_details_returns_parsed_result(self):
        url = "https://www.goodreads.com/book/show/375802"
        with patch("scripts.client.sync_playwright", return_value=_mock_playwright(BOOK_DETAIL_HTML)):
            result = self.client.get_book_details(url)
        assert result["title"] == "The Hobbit"
        assert len(result["reviews"]) == 2
        assert result["url"] == url

    def test_get_book_details_review_timeout(self):
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        mock_ctx = _mock_playwright(BOOK_DETAIL_HTML)
        mock_ctx.__enter__.return_value.chromium.launch.return_value \
            .new_context.return_value.new_page.return_value \
            .wait_for_selector.side_effect = PlaywrightTimeout("timed out")
        with patch("scripts.client.sync_playwright", return_value=mock_ctx):
            result = self.client.get_book_details("https://www.goodreads.com/book/show/375802")
        assert "error" not in result
        assert result["title"] == "The Hobbit"

    def test_get_book_details_playwright_error(self):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Exception("browser crashed"))
        mock_ctx.__exit__ = MagicMock(return_value=False)
        with patch("scripts.client.sync_playwright", return_value=mock_ctx):
            result = self.client.get_book_details("https://www.goodreads.com/book/show/1")
        assert "error" in result
        assert "browser crashed" in result["error"]
