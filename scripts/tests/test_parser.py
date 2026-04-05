"""Tests for GoodreadsParser."""

from scripts.parser import GoodreadsParser

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
# Tests
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
        assert GoodreadsParser.parse_search_results("<html><body><p>No results.</p></body></html>") == []

    def test_parse_search_results_missing_author(self):
        html = """
        <html><body><table class="tableList">
          <tr>
            <td><a class="bookTitle" href="/book/show/1"><span>Orphan Book</span></a></td>
          </tr>
        </table></body></html>
        """
        results = GoodreadsParser.parse_search_results(html)
        assert results[0]["author"] == "Unknown"

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

    def test_parse_book_details_caps_reviews_at_five(self):
        reviews = "\n".join(
            f'<section class="ReviewText">Review number {i}.</section>'
            for i in range(6)
        )
        html = f"<html><body>{reviews}</body></html>"
        result = GoodreadsParser.parse_book_details(html)
        assert len(result["reviews"]) == 5

    def test_parse_book_details_data_testid_review_selector(self):
        html = """
        <html><body>
        <div data-testid="review">A mid-era review.</div>
        </body></html>
        """
        result = GoodreadsParser.parse_book_details(html)
        assert len(result["reviews"]) == 1
        assert result["reviews"][0] == "A mid-era review."

    def test_parse_book_details_legacy_review_selector(self):
        html = """
        <html><body>
        <div class="reviewText">A legacy review.</div>
        </body></html>
        """
        result = GoodreadsParser.parse_book_details(html)
        assert len(result["reviews"]) == 1
