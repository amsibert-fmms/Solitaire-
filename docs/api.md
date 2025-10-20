# Solitaire Data API

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/win` | Append a single win record to the Parquet log. |
| `GET` | `/api/deck/<deck_key>` | Return aggregated difficulty summaries for the requested deck. |

## `POST /api/win`

```bash
curl -X POST http://localhost:5000/api/win \
  -H "Content-Type: application/json" \
  -d '{
        "deck_key": "deck42",
        "draw_mode": 3,
        "solve_time_ms": 12145,
        "node_count": 48321,
        "timestamp_utc": "2025-10-20T01:00:00Z",
        "solver_id": "CodexSolver",
        "solver_version": "1.3.0"
      }'
```

### JavaScript helper

```javascript
async function submitWin(record) {
  const response = await fetch("/api/win", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(record)
  });
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }
  return response.json();
}

submitWin({
  deck_key: window.solitaireDeckKey(),
  draw_mode: 3,
  solve_time_ms: 12145,
  node_count: 48321,
  timestamp_utc: new Date().toISOString(),
  solver_id: "CodexSolver",
  solver_version: "1.3.0"
}).catch(console.error);
```

## `GET /api/deck/<deck_key>`

```bash
curl http://localhost:5000/api/deck/deck42
```

The response contains aggregated medians and difficulty tiers produced by the nightly batch jobs.
