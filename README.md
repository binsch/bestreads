# 📚 bestreads

> Supercharge Claude with real book recommendations and reviews.

[![CI](https://github.com/binsch/bestreads/actions/workflows/ci.yml/badge.svg)](https://github.com/binsch/bestreads/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)

## Installation

Clone the repo into your Claude Code personal skills directory:

```bash
git clone https://github.com/binsch/bestreads ~/.claude/skills/bestreads
cd ~/.claude/skills/bestreads
uv sync
uv run playwright install chromium
```

## Usage

Once installed, invoke the skill directly in Claude Code:

```
/bestreads Dune
/bestreads Brandon Sanderson
```

Or just ask naturally — Claude will pick it up automatically:

- "Find me books about machine learning"
- "Show me reviews for The Way of Kings"
- "What do people think of Dune?"

## How it works

Goodreads shut down their public API in 2020, so this skill scrapes the site directly.

- **Search** uses `requests` to fetch static HTML search results
- **Book details and reviews** use a headless Chromium browser via Playwright, since Goodreads renders reviews with JavaScript

## Development

```bash
uv run pytest          # run tests
uv run pytest -v       # verbose output
```

## Requirements

- Python 3.14.2+
- [uv](https://docs.astral.sh/uv/)
- Chromium (installed via `uv run playwright install chromium`)
