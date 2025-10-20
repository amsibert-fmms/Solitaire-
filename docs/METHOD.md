# Methodology

This document outlines how solitaire hands are identified, logged, and analyzed so that contributors can reproduce statistics on winnability.

## 1. Hand tagging pipeline

1. **Seed selection.** Each new deal is produced from a 32-bit unsigned integer seed (`0 ≤ seed ≤ 2³² − 1`). Seeds can be sampled sequentially or from curated lists of noteworthy hands.
2. **Deterministic shuffle.** A Fisher–Yates shuffle driven solely by the seed arranges the 52-card deck. No external entropy sources are permitted.
3. **Canonical encoding.** The dealt layout is converted into a normalized tuple capturing:
   - Tableau columns (face-down boundary + face-up cards).
   - Stock order (top to bottom) and waste order (bottom to top).
   - Foundation progress for each suit.
4. **Hashing.** The tuple is serialized into bytes and digested with SHA-256. The resulting 64-character hexadecimal string is the hand tag exposed to the UI.

The combination `(seed, hash)` is stable across browsers, making it a reliable identifier when sharing or aggregating results.

In addition to the hand tag, the client derives a reversible 256-bit `deck_key` that directly encodes the shuffled deck order. This CRISPR-style key enables binary database columns (for example, `VARBINARY(32)`) to store and later rebuild the exact layout even when the seed is unavailable.

## 2. Event emission

The web client emits lifecycle events that you can intercept to log progress:

| Event | Fired when | Payload |
| --- | --- | --- |
| `hand:new` | A deal is generated. | `{ tag, seed }` |
| `hand:won` | Foundations complete. | `{ tag, moveCount, durationMs }` |
| `hand:lost` | Player abandons or deck exhausted. | `{ tag, reason }` |

Attach listeners via:

```javascript
document.addEventListener("hand:won", (event) => {
  enqueueRecord({
    tag: event.detail.tag,
    result: "win",
    moves: event.detail.moveCount,
    duration_ms: event.detail.durationMs,
  });
});
```

The helper `enqueueRecord` can persist data immediately or batch it for periodic uploads.

## 3. Storage layout

A lightweight, analytics-friendly dataset might adopt the following directories:

```
data/
  raw/
    2024-11-01_attempts.parquet
    2024-11-08_attempts.parquet
  derived/
    solvability_summary.parquet
    streaks.parquet
  meta/
    schema.json
    pipeline_version.txt
```

- **Raw files** contain one row per play attempt with columns such as `tag`, `seed`, `result`, `moves`, `duration_ms`, `timestamp_utc`, and optional player identifiers.
- **Derived files** hold aggregated statistics regenerated from the raw layer.
- **Metadata** documents schema revisions, hashing algorithm versions, and validation results.

## 4. Validation checklist

Before publishing statistics, verify the dataset with the following steps:

1. **Schema validation.** Confirm required columns exist and data types match expectations.
2. **Duplicate detection.** Ensure there are no conflicting records with the same `(tag, attempt_id)` combination.
3. **Determinism audit.** Recompute the hash for a sample of seeds and compare against stored tags.
4. **Outcome coverage.** Check that each raw file contains both wins and losses; flag runs where all games are abandoned.

A simple validation script lives under `scripts/validate.py` and can be invoked with the commands below:

| Command | When to use it |
| --- | --- |
| `python scripts/validate.py data/raw/*.csv` | Datasets exported directly from the browser helper. |
| `python scripts/validate.py data/raw/*.parquet` | Post-processed parquet files (requires `pyarrow`). |

## 5. Aggregation examples

Use DuckDB or Pandas to build rollups:

```python
import duckdb

duckdb.sql(
    """
    CREATE OR REPLACE TABLE solvability AS
    SELECT
      tag,
      ANY_VALUE(seed) AS seed,
      COUNT_IF(result = 'win')::FLOAT / COUNT(*) AS win_rate,
      COUNT(*) AS attempts,
      AVG(moves) AS avg_moves,
      AVG(duration_ms) AS avg_duration_ms
    FROM parquet_scan('data/raw/*.parquet')
    GROUP BY tag
    """
)
```

Extend this query to slice by player, time period, or rule variant as additional columns become available.

## 6. Reproducibility

- Version control any change to the shuffling algorithm, serialization format, or hashing strategy.
- Store the generator code alongside the dataset version in `meta/pipeline_version.txt`.
- Capture solver or UI release hashes so that historical statistics can be traced back to the exact logic that produced them.

Following these guidelines keeps the solitaire hand tracker dependable and enables community members to verify reported win rates.
