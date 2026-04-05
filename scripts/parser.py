"""Parses Goodreads HTML pages into structured data."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup


class GoodreadsParser:
    """Parses Goodreads HTML pages into structured data."""

    BASE_URL = "https://www.goodreads.com"

    @staticmethod
    def parse_search_results(html: str) -> list:
        """Parse a Goodreads search results page into a list of book dicts."""
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
            book_url = urljoin(GoodreadsParser.BASE_URL, title_tag.get("href", ""))
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

    @staticmethod
    def parse_book_details(html: str, url: str = "") -> dict:
        """Parse a Goodreads book page (after JS render) into a details dict."""
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
