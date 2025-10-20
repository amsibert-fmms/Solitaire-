#!/usr/bin/env python3
"""Difficulty scorer for solitaire win logs.

This utility reads unsized win entries from ``data/wins.parquet`` and assigns
``difficulty_score`` plus a categorical ``difficulty_level`` bucket.  It is
intended to run as a nightly cron job so downstream analytics can rely on the
labels being populated.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_DATA_PATH = Path("data/wins.parquet")
DEFAULT_SEED_PATH = Path("data/wins_seed.csv")

LOGGER = logging.getLogger("update_difficulty")


class DifficultyUpdateError(RuntimeError):
    """Raised when the difficulty update job cannot be completed."""


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise DifficultyUpdateError(
            "--since must be provided in YYYY-MM-DD format"
        ) from exc


def _normalise_level_column(raw: pd.Series) -> pd.Series:
    if raw.dtype == "O":
        return raw.fillna("").astype(str).str.strip()
    return raw


def _select_candidate_rows(
    frame: pd.DataFrame, since: datetime | None, limit: int | None
) -> pd.Index:
    if "difficulty_level" in frame:
        levels = _normalise_level_column(frame["difficulty_level"])
        mask = levels.isna() if levels.dtype != "O" else levels.eq("")
    else:
        mask = np.ones(len(frame), dtype=bool)

    if since is not None and "timestamp_utc" in frame:
        timestamps = pd.to_datetime(frame["timestamp_utc"], errors="coerce")
        mask &= timestamps >= np.datetime64(since)

    candidates = frame[mask]
    if limit is not None:
        candidates = candidates.head(limit)
    return candidates.index


def _compute_score(subset: pd.DataFrame) -> pd.Series:
    node_term = np.log10(subset["node_count"].astype(float) + 1.0)
    time_term = np.log10(subset["solve_time_ms"].astype(float) + 1.0)
    return node_term + time_term


def _assign_levels(group: pd.DataFrame) -> pd.Series:
    if group.empty:
        return pd.Series(dtype="object")

    scores = group["difficulty_score"]
    p30 = np.percentile(scores, 30)
    p70 = np.percentile(scores, 70)

    buckets = np.full(len(group), "medium", dtype=object)
    buckets[scores < p30] = "easy"
    buckets[scores > p70] = "hard"
    return pd.Series(buckets, index=group.index)


def _load_frame(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)

    if DEFAULT_SEED_PATH.exists():
        LOGGER.info(
            "Primary Parquet log %s missing; hydrating from seed CSV %s",
            path,
            DEFAULT_SEED_PATH,
        )
        seeded = pd.read_csv(DEFAULT_SEED_PATH)
        seeded.to_parquet(path, index=False)
        return seeded

    raise DifficultyUpdateError(
        f"Win log not found: {path} (and seed {DEFAULT_SEED_PATH} missing)"
    )


def update_difficulty(
    *,
    path: Path = DEFAULT_DATA_PATH,
    since: datetime | None = None,
    limit: int | None = None,
) -> tuple[int, dict[str, int]]:
    frame = _load_frame(path)
    if frame.empty:
        LOGGER.info("No records to process")
        return 0, {}

    candidate_index = _select_candidate_rows(frame, since, limit)
    if candidate_index.empty:
        LOGGER.info("No new wins require difficulty scoring")
        return 0, {}

    working = frame.loc[candidate_index].copy()
    working["difficulty_score"] = _compute_score(working)

    grouped = working.groupby("draw_mode", sort=False, group_keys=False)
    levels = grouped.apply(_assign_levels)
    working["difficulty_level"] = levels.values

    frame.loc[working.index, "difficulty_score"] = working["difficulty_score"]
    frame.loc[working.index, "difficulty_level"] = working["difficulty_level"]

    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)

    counts: dict[str, int] = (
        working["difficulty_level"].value_counts().sort_index().to_dict()
    )

    return int(working.shape[0]), counts


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="Only update wins logged on or after this date",
    )
    parser.add_argument(
        "--limit",
        metavar="N",
        type=int,
        help="Only update the first N matching records",
    )
    parser.add_argument(
        "--path",
        default=str(DEFAULT_DATA_PATH),
        help="Path to the Parquet file containing win logs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    since = _parse_since(args.since)
    limit = args.limit if args.limit is None or args.limit > 0 else None
    path = Path(args.path)

    try:
        updated, counts = update_difficulty(path=path, since=since, limit=limit)
    except DifficultyUpdateError as exc:
        LOGGER.error("%s", exc)
        return 1

    if updated:
        total = updated or 1
        parts = []
        for label in ("easy", "medium", "hard"):
            count = counts.get(label, 0)
            percentage = count / total * 100 if total else 0.0
            parts.append(f"{percentage:.1f}% {label}")
        LOGGER.info(
            "Updated %s rows: %s", f"{updated:,}", ", ".join(parts)
        )
    else:
        LOGGER.info("No rows updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
