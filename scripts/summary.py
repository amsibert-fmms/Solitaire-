"""Dataset summarisation utility for solitaire attempt logs."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Sequence

from scripts.validate import DatasetError, Record, load_records


@dataclass(frozen=True)
class Summary:
    """Aggregate statistics describing a collection of attempt records."""

    total_records: int
    result_counts: dict[str, int]
    win_rate: float | None
    average_moves: float | None
    median_moves: float | None
    average_duration_ms: float | None


def summarise_records(records: Sequence[Record]) -> Summary:
    """Return aggregate statistics for *records*."""

    total = len(records)
    result_counts: dict[str, int] = {}
    wins = 0
    move_samples: list[int] = []
    duration_samples: list[int] = []

    for record in records:
        label = record.result or "unknown"
        result_counts[label] = result_counts.get(label, 0) + 1
        if label == "win":
            wins += 1

        if record.moves is not None:
            move_samples.append(record.moves)
        if record.duration_ms is not None:
            duration_samples.append(record.duration_ms)

    win_rate: float | None
    if total > 0:
        win_rate = wins / total
    else:
        win_rate = None

    average_moves: float | None
    median_moves: float | None
    if move_samples:
        average_moves = mean(move_samples)
        median_moves = median(move_samples)
    else:
        average_moves = None
        median_moves = None

    average_duration: float | None
    if duration_samples:
        average_duration = mean(duration_samples)
    else:
        average_duration = None

    return Summary(
        total_records=total,
        result_counts=result_counts,
        win_rate=win_rate,
        average_moves=average_moves,
        median_moves=median_moves,
        average_duration_ms=average_duration,
    )


def format_summary(path: Path, summary: Summary) -> str:
    """Return a human-readable description of *summary* for *path*."""

    lines = [f"{path}: {summary.total_records} records"]

    if summary.result_counts:
        ordered = ", ".join(
            f"{label or 'unknown'}={count}" for label, count in sorted(summary.result_counts.items())
        )
        lines.append(f"  results: {ordered}")

    if summary.win_rate is not None:
        lines.append(f"  win rate: {summary.win_rate * 100:.1f}%")

    if summary.average_moves is not None:
        lines.append(
            f"  moves: mean={summary.average_moves:.1f} median={summary.median_moves:.1f}"
        )

    if summary.average_duration_ms is not None:
        lines.append(f"  average duration: {summary.average_duration_ms:.1f} ms")

    return "\n".join(lines)


def summarise_path(path: Path) -> Summary:
    """Load records from *path* and return their summary."""

    records = load_records(path)
    return summarise_records(records)


def run(paths: Iterable[str]) -> list[tuple[Path, Summary]]:
    """Compute summaries for each path in *paths*."""

    results: list[tuple[Path, Summary]] = []
    for raw_path in paths:
        path = Path(raw_path)
        summary = summarise_path(path)
        results.append((path, summary))
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarise solitaire attempt datasets exported as CSV or Parquet.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to dataset files. Use shell globs to summarise multiple files at once.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summaries = run(args.paths)
    except DatasetError as exc:
        parser.error(str(exc))

    for path, summary in summaries:
        print(format_summary(path, summary))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
