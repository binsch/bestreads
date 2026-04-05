---
name: bestreads
description: Search Goodreads for books and reviews. Use when the user asks to find a book, look up book reviews, search by title/author/genre, or wants recommendations from Goodreads.
argument-hint: <title, author, or topic>
allowed-tools: Bash(uv *)
---

Search Goodreads for books matching `$ARGUMENTS`.

## Steps

1. Run the search script:
   ```bash
   uv run --project "${CLAUDE_SKILL_DIR}" python -m scripts.main "$ARGUMENTS"
   ```
   The script prints JSON to stdout.

2. Display the results as a numbered list with:
   - **Title** and **Author**
   - Average Goodreads rating (★ stars out of 5)
   - The Goodreads URL

3. If the user wants reviews or more details on a specific book, run:
   ```bash
   uv run --project "${CLAUDE_SKILL_DIR}" python -m scripts.main --book-url "<url>"
   ```
   Then display the description and any review snippets found.

## Error handling

- If the script returns `{"error": "..."}`, tell the user Goodreads could not be reached and suggest trying again.
- If results are empty, tell the user no books were found and suggest a different search term.

## Notes

- Goodreads reviews are partially JavaScript-rendered; the script retrieves what is available in static HTML.
- Be concise: show the top 5 results by default, offer to show more if asked.
