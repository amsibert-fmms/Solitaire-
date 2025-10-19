# Solitaire Hand Tracker

This project delivers a browser-based Klondike Solitaire experience whose primary goal is to catalogue which hands are winnable. Every deal is assigned a deterministic hand tag so it can be recorded, shared, and revisited when compiling win-rate statistics.

## Features

- **Playable Klondike implementation.** Interact with `index.html` to drag cards, recycle the stock, and play full games in the browser.
- **Deterministic hand tags.** Each shuffle is encoded into a canonical string (hash tag) so identical hands are recognized even when dealt on different devices.
- **Outcome logging hooks.** The front end exposes lightweight events you can integrate with analytics or a solver backend to mark hands as won, lost, or unresolved.
- **Statistics-friendly storage.** Recommended dataset structures make it straightforward to aggregate winnability metrics over time.

## Running the game locally

1. Start a lightweight static server from the repository root—for example:
   ```bash
   python -m http.server 8000
   ```
2. Visit [http://localhost:8000](http://localhost:8000) in your browser.
3. Use the **New Game** button to redeal the deck. The hand tag for the active deal is available via the `window.solitaireHandTag()` helper.

## Recording outcomes

Integrate the following pattern to persist hand statistics:

```javascript
const tag = window.solitaireHandTag();
const outcome = {
  tag,
  result: "win", // or "loss" / "abandoned"
  timestamp: new Date().toISOString(),
};

fetch("/api/hands", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(outcome),
});
```

Backends should treat `tag` as the primary key when aggregating records. A single hand may appear multiple times if the same deal is replayed; in that case store each attempt separately or merge them according to your analytics needs.

## Exporting attempts

The UI exposes helpers for staging play attempts before exporting them as CSV. Logged entries populate the **Export Attempts** button in the controls panel; when at least one attempt is available the button triggers a download named `solitaire_attempts_YYYY-MM-DD-HH-MM-SS.csv`.

Use the helpers below to integrate with solvers or analytics pipelines:

| Helper | Purpose |
| --- | --- |
| `window.solitaireUI.logAttempt(attempt)` | Adds an attempt to the in-memory log. Accepts `tag`, `seed`, `result`, `moves`, `durationMs`, `timestampUtc`, and optional `notes`. Missing values are normalised to safe defaults. |
| `window.solitaireUI.exportAttempts()` | Downloads the current log as CSV using the same structure as the helper above. |
| `window.solitaireUI.clearAttemptLog()` | Empties the log, disabling the export button until new attempts arrive. |
| `window.solitaireUI.getAttemptLog()` | Returns a shallow copy of the staged attempts for inspection or custom tooling. |

```javascript
window.solitaireUI.logAttempt({
  tag: window.solitaireHandTag(),
  seed: window.solitaireSeed(),
  result: "win",
  moves: 115,
  durationMs: 92000,
  timestampUtc: new Date().toISOString(),
  notes: "First solver pass"
});

// When ready, download the CSV file.
window.solitaireUI.exportAttempts();
```

## Data model overview

The canonical hand tag is derived from:

1. A fixed shuffle algorithm seeded by a 32-bit integer.
2. Normalized encodings of tableau columns, stock, waste, and foundation state.
3. A SHA-256 digest of the serialized game state.

Persisted outcomes can be stored in one of the following formats:

| Storage option | Notes |
| --- | --- |
| CSV/Parquet files | Convenient for offline batch analysis and reproducible statistics. |
| SQLite/PostgreSQL | Enables ad-hoc queries and dashboards. |
| REST/GraphQL service | Useful when multiple clients report wins in real time. |

For detailed methodology—including batch processing workflows and reproducibility tips—see [`docs/METHOD.md`](docs/METHOD.md).

## Contributing

1. Fork or clone the repository.
2. Make targeted changes to the web client, data pipeline, or documentation.
3. Validate UI behaviour manually and keep documentation aligned with the tracking focus.
4. Submit pull requests describing how the change supports accurate solitaire hand tracking.

## Related resources

- [`docs/TODO.md`](docs/TODO.md) outlines future enhancements.
- [`AGENTS.md`](AGENTS.md) captures contributor guidance for this repository.
