# Solitaire Hand Tracker

This project delivers a browser-based Klondike Solitaire experience whose primary goal is to catalogue which hands are winnable. Every deal is assigned a deterministic hand tag so it can be recorded, shared, and revisited when compiling win-rate statistics.

## Features

- **Playable Klondike implementation.** Interact with `index.html` to click-select card stacks, double-click promotions to the foundation, recycle the stock, and play full games in the browser.
- **Deterministic hand tags.** Each shuffle is encoded into a canonical string (hash tag) so identical hands are recognized even when dealt on different devices.
- **Outcome logging hooks.** The front end exposes lightweight events you can integrate with analytics or a solver backend to mark hands as won, lost, or unresolved.
- **Statistics-friendly storage.** Recommended dataset structures make it straightforward to aggregate winnability metrics over time.
- **Automatic attempt persistence.** Logged attempts are cached in the browser so progress survives page refreshes until you clear the log.

## Running the game locally

1. Start a lightweight static server from the repository root—for example:
   ```bash
   python -m http.server 8000
   ```
2. Visit [http://localhost:8000](http://localhost:8000) in your browser.
3. Use the **New Game** button to redeal the deck. The hand tag for the active deal is available via the `window.solitaireHandTag()` helper.

### Controls at a glance

| Action | Effect |
| --- | --- |
| Click the **New Game** button | Deals a fresh deterministic layout and updates the hand tag/seed readouts. |
| Click a face-up card | Selects the card (and any cards stacked beneath it) so it can be moved to another tableau column. |
| Click an empty tableau column | Drops the currently selected stack if a legal move is available. |
| Double-click a face-up card | Sends the card to the appropriate foundation when legal. |
| Click the stock pile | Draws up to three new cards from the stock; clicking again when empty recycles the waste (respecting pass limits). |
| Click the waste pile | Selects the top waste card for tableau moves or double-click to promote to the foundation. |

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

### Runtime helpers

| Helper | Purpose |
| --- | --- |
| `window.solitaireUI.startNewGame(seed?)` | Deals a new game. Pass a numeric seed to replay a specific layout or omit it for a fresh randomised seed. |
| `window.solitaireUI.getStateSnapshot()` | Returns the current seed, hand tag, stock/waste counts, foundation totals, and move count for analytics dashboards. |

## Attempt persistence

| Behaviour | Details |
| --- | --- |
| Local caching | Attempts added through `window.solitaireUI.logAttempt` are automatically persisted to `localStorage` under the key `solitaire.attemptLog.v1`. They are restored on page load so you can export even after a refresh. |
| Clearing entries | Call `window.solitaireUI.clearAttemptLog()` to remove attempts from both the in-memory list and local storage. |
| Fallback behaviour | If the browser disallows storage (for example, in privacy modes), the helpers still work in-memory; only persistence is skipped. |

## Validating exported datasets

Run the validation script whenever you append records to your dataset. It checks for missing columns, duplicate attempts, and suspicious result distributions.

| Command | Purpose |
| --- | --- |
| `python scripts/validate.py data/raw/*.csv` | Validate one or more CSV files exported from the UI. |
| `python scripts/validate.py data/raw/*.parquet` | Validate Parquet files (requires the optional `pyarrow` dependency). |
| `python scripts/summary.py data/raw/*.csv` | Print aggregate statistics (win rate, move counts, durations, fastest wins) for exported datasets. |
| `python scripts/streaks.py data/raw/*.csv` | Compute win/loss streak metrics to highlight momentum across attempts. |

The streaks helper spotlights both the longest and current win/loss runs so you can spot heater stretches or cold spells at a glance when reviewing exported logs.

The script prints a summary for each file and exits with status code `1` when any errors are encountered.

## Automated solver CLI

Use the solver to benchmark deal difficulty or generate baseline datasets.

| Command | Description |
| --- | --- |
| `python scripts/solver.py --games 25 --draw-count 1 --pass-limit 3` | Simulate 25 games using draw-one rules and up to three stock recycles. |
| `python scripts/solver.py --seed 123456 --max-steps 8000` | Replay a specific shuffle seed with a higher iteration cap for more exhaustive exploration. |

### Solver options

| Option | Purpose |
| --- | --- |
| `--games <n>` | Number of games to simulate in a batch run. |
| `--draw-count <n>` | Cards drawn from the stock at a time (defaults to three). |
| `--pass-limit <n>` | Maximum stock recycles; use `-1` for unlimited. |
| `--max-steps <n>` | Safety cap that stops runaway simulations. |
| `--quiet` | Suppress individual game summaries and print only the aggregate line. |

### Summary CLI options

| Option | Description |
| --- | --- |
| `--include-result <label>` | Restrict calculations to attempts whose result matches the provided label. Repeat to include multiple results. |
| `--exclude-result <label>` | Skip attempts that match the provided result label without altering the source file. |
| `--json` | Emit structured output that lists each path alongside the computed summary metrics. |

### Streaks CLI options

| Option | Description |
| --- | --- |
| `--treat-abandoned-as-loss` | Count `abandoned` attempts as losses so they extend loss streak calculations. |

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
