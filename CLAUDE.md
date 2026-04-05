# bestreads

A Claude Code skill that searches Goodreads for books and reviews by scraping the site (Goodreads shut down their public API in 2020).

## Structure

```
scripts/
├── parser.py        # GoodreadsParser — pure HTML parsing, no I/O
├── client.py        # GoodreadsClient — fetches pages via requests + Playwright
├── main.py          # CLI entry point (argparse only)
└── tests/
    ├── test_parser.py
    └── test_client.py
```

## Key design decisions

- **Search** uses `requests` (search results are in static HTML)
- **Book details + reviews** use Playwright/Chromium because Goodreads renders reviews via React
- Playwright needs stealth settings to avoid Goodreads 403s: `--disable-blink-features=AutomationControlled`, realistic user agent/viewport, and `navigator.webdriver` masked via `add_init_script`
- `GoodreadsParser` is intentionally stateless (all static methods) — easy to test without mocks
- `GoodreadsClient` accepts a `timeout` parameter (default 15s)

## Package management

Uses `uv`. Common commands:

```bash
uv sync                        # install deps from lockfile
uv run pytest                  # run tests
uv run python -m scripts.main "Dune"          # search
uv run python -m scripts.main --book-url <url>  # book details + reviews
uv run playwright install chromium            # (re)install browser after fresh clone
```

## Testing approach

- `TestGoodreadsParser` — no mocks, passes HTML fixtures directly
- `TestGoodreadsClient` — patches `scripts.client.requests.get` and `scripts.client.sync_playwright`

## Skill invocation

Defined in `SKILL.md`. Claude runs `python -m scripts.main` via `uv run --project "${CLAUDE_SKILL_DIR}"`. Both user and model can invoke it.
