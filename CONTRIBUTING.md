# Contributing to Literature Clock

Contributions are welcome — especially new quotes.

## Adding Quotes

The most valuable contribution is a well-sourced literary quote that mentions a specific time.

### Requirements

1. **The exact time must appear in the text** — as words ("half past three"), digits ("3:30"), or narrative reference ("the clock struck three")
2. **Source must be published literature** — novels, short stories, poetry, essays, plays. No song lyrics, no screenplays, no social media posts.
3. **Verify against the original source** — don't quote from memory. Use a physical copy, a reputable ebook, or a digitized edition.
4. **Include all required fields** — see format below.

### Quote Format

Each quote is a JSON object with these fields:

```json
{
  "time": "15:30",
  "quote": "The clock on the mantelpiece said half past three. She had been sitting there for an hour without moving.",
  "title": "The Example Novel",
  "author": "Jane Author",
  "language": "en"
}
```

| Field | Required | Format | Notes |
|---|---|---|---|
| `time` | ✅ | `HH:MM` (24h) | The time referenced in the quote. `00:00`–`23:59`. |
| `quote` | ✅ | String | The passage containing the time reference. Keep it to 1–3 sentences — enough context to be meaningful, short enough to read in a minute. |
| `title` | ✅ | String | Book/work title. Use the established English title for translations. |
| `author` | ✅ | String | Author's name as commonly known (e.g. "Marcel Proust", not "Valentin Louis Georges Eugène Marcel Proust"). |
| `language` | ✅ | `en` or `de` | Language of the quote text (not the original work). |

### Guidelines

- **One quote, one time.** If a passage mentions multiple times, pick the most prominent one.
- **Trim carefully.** Start and end at natural sentence boundaries. Ellipsis (`…`) is acceptable for cuts within the passage, but don't overdo it.
- **No spoilers in isolation.** The quote should work without knowing the plot. Avoid death scenes, twist reveals, etc. that need context to be appropriate.
- **Diverse sources welcome.** We have Proust and Fitzgerald. We also want Murakami, Borges, Adichie, Jelinek, Lispector. Breadth over depth.
- **Duplicate times are fine.** Multiple quotes for the same minute add variety — the clock randomly selects one.
- **Gaps are valuable.** Run `npm test` to see which minutes have no quotes yet. Filling gaps is the highest-impact contribution.

### How to Submit

**Option A — Pull Request (preferred):**

1. Fork the repository
2. Add your quotes to `data/quotes.json` (maintain the sorted order by time)
3. Run `npm test` to validate the format
4. Open a Pull Request with a brief note on your sources

**Option B — Issue:**

Open an issue titled `Quote: [HH:MM] Author — Title` with the JSON entry in the body. We'll add it for you.

### Validation

The test suite checks:
- Valid JSON structure
- Required fields present
- Time format (`HH:MM`, valid range)
- No exact duplicate quotes
- Quote length within bounds

Run locally:
```bash
npm test
```

## Code Contributions

1. Fork the repository
2. Create a feature branch (`feature/your-change`)
3. Commit your changes
4. Run tests (`npm test`)
5. Open a Pull Request

### Design Principles

- **Typography is sacred** — don't clutter the screen
- **Performance matters** — this runs on nightstand tablets and e-ink displays
- **Accessibility** — readable contrast, screen reader support, keyboard navigation
- **No dependencies at runtime** — vanilla HTML/CSS/JS, no frameworks

## Current Stats

- ~1,100 quotes from 6+ authors
- Keyboard navigation: ←/→ time travel, Space next quote, F fullscreen
- Light/Dark theme
- Live at [simiono.com/clock/](https://simiono.com/clock/)

## License

By contributing, you agree that your contributions will be licensed under [AGPL-3.0](LICENSE).
