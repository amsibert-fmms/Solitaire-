"""Minimal Flask API for ingesting solitaire wins and exposing summaries."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from flask import Flask, jsonify, request

DATA_DIR = Path("data")
WINS_PATH = DATA_DIR / "wins.parquet"
SUMMARY_PATH = DATA_DIR / "deck_summary.parquet"

REQUIRED_FIELDS = {
    "deck_key": str,
    "draw_mode": int,
    "solve_time_ms": (int, float),
    "node_count": (int, float),
    "timestamp_utc": str,
    "solver_id": str,
    "solver_version": str,
}

OPTIONAL_FIELDS = {
    "difficulty_score": (int, float),
    "difficulty_level": str,
}

app = Flask(__name__)


def _load_wins_frame() -> pd.DataFrame:
    if WINS_PATH.exists():
        return pd.read_parquet(WINS_PATH)
    return pd.DataFrame(columns=list(REQUIRED_FIELDS) + list(OPTIONAL_FIELDS))


def _load_summary_frame() -> pd.DataFrame:
    if SUMMARY_PATH.exists():
        return pd.read_parquet(SUMMARY_PATH)
    return pd.DataFrame(
        columns=[
            "deck_key",
            "draw_mode",
            "median_nodes",
            "median_time",
            "median_difficulty",
            "difficulty_level",
        ]
    )


def _normalise_timestamp(candidate: str | None) -> str:
    if not candidate:
        return datetime.now(timezone.utc).isoformat()
    try:
        timestamp = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp_utc must be ISO-8601 formatted") from exc
    return timestamp.astimezone(timezone.utc).isoformat()


def _validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for field, expected in REQUIRED_FIELDS.items():
        if field not in payload:
            raise ValueError(f"Missing field: {field}")
        value = payload[field]
        if not isinstance(value, expected):
            raise ValueError(f"{field} has invalid type: {type(value).__name__}")
        cleaned[field] = value

    cleaned["timestamp_utc"] = _normalise_timestamp(cleaned["timestamp_utc"])

    for field, expected in OPTIONAL_FIELDS.items():
        if field in payload and payload[field] is not None:
            if not isinstance(payload[field], expected):
                raise ValueError(
                    f"{field} has invalid type: {type(payload[field]).__name__}"
                )
            cleaned[field] = payload[field]
        else:
            cleaned[field] = None
    return cleaned


@app.post("/api/win")
def ingest_win():
    payload = request.get_json(silent=True) or {}
    try:
        record = _validate_payload(payload)
    except ValueError as exc:
        response = {"error": str(exc)}
        return jsonify(response), 400

    frame = _load_wins_frame()
    frame = pd.concat([frame, pd.DataFrame([record])], ignore_index=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(WINS_PATH, index=False)

    return jsonify({"status": "accepted"}), 201


@app.get("/api/deck/<deck_key>")
def get_deck_summary(deck_key: str):
    frame = _load_summary_frame()
    if frame.empty:
        return jsonify({"error": "deck summary unavailable"}), 404

    subset = frame[frame["deck_key"] == deck_key]
    if subset.empty:
        return jsonify({"error": "deck not found"}), 404

    # Convert to native Python types for JSON serialisation.
    result = subset.to_dict(orient="records")
    return jsonify({"deck_key": deck_key, "summaries": result})


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    app.run(host="0.0.0.0", port=5000, debug=True)
