Solitaire Research Project — Methodology

> Objective: determine which solitaire deals are theoretically solvable under varying rule sets, from the strictest classic rules to the most permissive, knowledge-rich versions.



---

1. Overview

This project explores the solvability space of Klondike-style solitaire.
Each unique 32-bit seed defines a complete shuffle and initial layout.
The solver evaluates that layout under a grid of rule profiles and draw sizes to answer a fundamental question:

> “Can this deal be won at least once, under some reasonable interpretation of the rules?”



The design captures both player realism and theoretical upper bounds.


---

2. Variants and Rule Profiles

Each seed is solved under multiple profiles, each reflecting a different philosophy of play.
Profiles form a monotonic ladder of increasing permissiveness—anything solvable under a stricter profile will also be solvable under all looser ones.

| Profile       | Description                                                                                                         | Intended Use                                                        |
|---------------|---------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| STANDARD      | Closest to “classic” Klondike rules (as found in physical decks and early PC versions).                             | Baseline reference for tradition-minded players.                    |
| FRIENDLY_APP  | Matches most modern mobile apps: free supermoves, unlimited passes, foundation takeback allowed.                    | Mirrors common user experience.                                     |
| MAX_RELAX     | Removes all play restrictions that don’t affect logical solvability: free supermoves, unlimited passes, foundation takeback, safe autoplay, no staging limits. | Estimates the maximum realistic solvable fraction for hidden-information play. |
| XRAY          | Identical to MAX_RELAX but with perfect information: the solver can see facedown cards.                             | Upper-bound theoretical solvability—used for research calibration.  |
2.1 Configurable dimensions

Each profile is parameterized by:

FieldMeaningTypical Values

drawCards drawn from stock at a time.1 or 3
passesAllowed stock recycles."unlimited" or integer
supermoveHow multi-card moves are treated."staged" or "free"
foundation_takebackWhether cards may return from foundation to tableau.true / false
peek_xrayWhether hidden cards are visible to solver.true / false
autoplay_safe_onlyWhether automatic plays avoid blocking builds.true / false
undo_unlimitedUndo limit (for interface parity; does not affect solvability).true


Each combination of (profile, draw) defines a rule instance.


---

3. What “Solvable” Means

A seed is solvable under a given rule instance if there exists at least one sequence of legal moves leading to four completed foundations.
All moves must obey the legality constraints of that rule set; X-ray only affects the solver’s information, not the legality of moves.


---

4. Legal Move Definition

Within any profile, the following constraints always hold:

1. Tableau building: descending rank, alternating color.


2. Face-down restriction: only fully face-up runs can move.


3. Empty column rule: only a King may occupy an empty tableau space.


4. Foundation order: same-suit, strictly ascending from Ace to King.


5. Stock/waste: only the top waste card may play; draw size = draw; stock may be recycled up to passes.


6. Uniqueness invariant: exactly 52 distinct cards across tableau, stock, waste, and foundations.


7. Auto-flip: any newly exposed face-down card must be turned up immediately.



Supermove and foundation-takeback options relax, but never violate, these core invariants.


---

5. Solver Logic Summary

1. Shuffler: deterministic 32-bit seed → unique layout.


2. State Encoding: compact bit representation with reversible moves.


3. Search: Iterative Deepening A* with heuristics prioritizing uncovering, safe foundation pushes, and tableau mobility.


4. Deadlock detection: repeated stock/waste cycles without net progress, blocked low ranks, or zero legal moves.


5. Termination: success (all foundations complete) or timeout.



---

6. Output Schema (excerpt)

| Field               | Type    | Description                                 |
|---------------------|---------|---------------------------------------------|
| seed                | uint32  | Shuffle seed.                               |
| profile             | str     | Rule profile name.                          |
| draw                | int     | Draw size (1 or 3).                         |
| peek_xray           | bool    | Whether X-ray information was enabled.      |
| solved              | bool    | True if a legal win sequence exists.        |
| solution_len        | int     | Number of moves in the minimal found sequence. |
| time_ms             | int     | Solver runtime.                             |
| nodes               | int     | Search nodes expanded.                      |
| reason_if_unsolved  | str     | Timeout, deadlock type, or unknown.         |
---

7. Interpretation

Comparing STANDARD → MAX_RELAX shows how much stricter play rules reduce solvability.

Comparing MAX_RELAX → XRAY isolates the impact of hidden information.

Aggregating across draw sizes lets players see whether 1-card or 3-card draw affects fairness or winnability.



---

8. Planned Extensions

Add other variants: Vegas, Limited-Pass, FreeCell, Spider(1-suit).

Integrate “supermove-capacity” experiments to mirror FreeCell-style constraints.

Release anonymized per-seed replay data for reproducibility.



---

9. Reproducibility Notes

Every result derives from a deterministic shuffle + rule profile pair.

Shuffler and rule logic are version-pinned (engine_version hash).

Golden seeds verify deterministic layout and solvability outcomes.
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
