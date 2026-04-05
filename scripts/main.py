#!/usr/bin/env python3
"""CLI entry point for bestreads."""

import argparse
import io
import json
import sys

# Ensure stdout handles Unicode on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from .client import GoodreadsClient


def main():
    parser = argparse.ArgumentParser(description="Search Goodreads for books")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--book-url", metavar="URL", help="Fetch details for a book URL")
    parser.add_argument("--limit", type=int, default=10, help="Max search results")
    args = parser.parse_args()

    client = GoodreadsClient()

    if args.book_url:
        result = client.get_book_details(args.book_url)
    elif args.query:
        result = client.search(args.query, limit=args.limit)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
