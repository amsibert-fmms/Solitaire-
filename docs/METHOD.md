# Methodology

## 10. Data Generation and Storage

The dataset is built through systematic seed evaluation using deterministic shuffles, controlled solver configurations, and well-defined output formats.
Every recorded row corresponds to one combination of:

> (seed, profile, draw_size, time_cap) → outcome

This section defines how those are produced and stored.

### 10.1 Seed generation

Each layout derives from a 32-bit unsigned integer seed (0 ≤ seed ≤ 2³²−1).
The shuffle algorithm is fixed and deterministic:

```
rng = Random(seed)
shuffle(deck)
```

No additional entropy sources (timestamps, process IDs) are used.
Seeds are sampled either sequentially (0…N−1) or by pseudorandom sampling from the full range; the sampling method is recorded in the batch metadata.

| Strategy | Purpose |
| --- | --- |
| Sequential 0–99999 | Baseline 100k-seed sample for reproducibility. |
| Stratified (low/mid/high rank coverage) | Balanced exploration of initial tableau variety. |
| Challenge subset | Seeds that exceeded time limit in prior runs. |

### 10.2 Batch runner workflow

Each compute node or process executes:

```
python runner/batch.py \
  --profile max_relax \
  --draw 1 \
  --time-cap-ms 500 \
  --seed-range 0 10000 \
  --out data/parquet/batch_0001.parquet
```

The batch runner:

1. Generates or reads the seed list.
2. Loads the requested rule profile.
3. Solves each seed under the given configuration (time-capped).
4. Streams results into memory-efficient parquet chunks (≈10k rows per file).
5. Writes an accompanying `meta.json` describing engine version, seed range, profile parameters, and environment details.

### 10.3 File layout

```
data/
  parquet/
    batch_0001.parquet
    batch_0002.parquet
    ...
  meta/
    batch_0001_meta.json
    ...
  summaries/
    solvability_summary.parquet
    feature_ablation.parquet
```

Parquet files contain raw per-seed results.

Meta JSON files describe the context of each batch (solver version, host info, profile JSON, and date).

Summaries are aggregated analyses periodically regenerated from the parquet directory.

### 10.4 Parquet schema

| Field | Type | Description |
| --- | --- | --- |
| seed | uint32 | 32-bit seed value |
| profile | str | rule profile name |
| draw | int | 1 or 3 |
| passes | str | "unlimited" or integer |
| supermove | str | "free" / "staged" |
| foundation_takeback | bool | profile setting |
| peek_xray | bool | visibility flag |
| solved | bool | true if solved |
| solution_len | int | number of moves |
| solver_time_ms | int | runtime |
| nodes | int | search nodes expanded |
| reason_if_unsolved | str | "time_cap", "deadlock", etc. |
| bf_mean | float | average branching factor |
| bf_p95 | float | 95th percentile branching factor |
| engine_version | str | git hash or semver |
| timestamp_utc | datetime | run timestamp |
| hostname | str | optional; anonymized compute node ID |

### 10.5 Metadata JSON example

```
{
  "batch_id": "0001",
  "engine_version": "e5a92f4",
  "profile": "max_relax",
  "draw": 1,
  "time_cap_ms": 500,
  "seed_start": 0,
  "seed_end": 9999,
  "num_workers": 16,
  "host": "solver01",
  "start_time": "2025-10-18T04:12:00Z",
  "end_time": "2025-10-18T04:43:12Z"
}
```

### 10.6 Reproducibility and validation

To guarantee deterministic results:

1. The shuffle, move generator, and search are pure functions of `(seed, profile, draw, time_cap, engine_version)`.
2. Runs are idempotent—re-running the same batch regenerates identical parquet rows.
3. A `make validate` target verifies:
   - Parquet schema matches expected columns and types.
   - Re-run checksums match prior runs.
   - No duplicate `(seed, profile, draw)` keys.

Example validation command:

```
make validate-parquet
```

### 10.7 Aggregation and summaries

After N batches, a nightly job concatenates all parquet files using DuckDB or Pandas:

```
import duckdb
duckdb.sql("""
  CREATE TABLE solvability AS
  SELECT
    profile,
    draw,
    COUNT(*) AS seeds,
    SUM(solved)::FLOAT / COUNT(*) AS solvable_rate,
    AVG(solver_time_ms) AS mean_time
  FROM parquet_scan('data/parquet/*.parquet')
  GROUP BY profile, draw;
""")
```

These summary tables feed dashboards and published statistics.

### 10.8 Long-term storage

Raw data: Parquet + metadata archived under `data/parquet/` (versioned).

Processed data: Aggregations (e.g., solvability rates, feature ablations) saved to `data/summaries/`.

Cold storage: `.tar.zst` archives periodically synced to `/mnt/backups/solitaire/` or cloud storage for reproducibility.

All generated datasets are immutable; newer runs are appended rather than overwritten.

### 10.9 Optional visualization

A lightweight FastAPI server exposes read-only endpoints:

```
/api/solvable_rate?profile=max_relax&draw=1
/api/seed_detail?seed=12345
```

These power static dashboards showing:

- Solvability rates by profile/draw.
- Distribution of solution lengths and solver times.
- Example replay sequences.

### 10.10 Provenance summary

Each record in the dataset can be traced via:

`(seed, profile, draw) → batch_id → meta.json → engine_version`

This guarantees that every published solvability statistic can be re-generated bit-for-bit.
