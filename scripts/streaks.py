"""Compute win/loss streak statistics for solitaire attempt datasets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from scripts.validate import DatasetError, Record, load_records


TRACKED_RESULTS = {"win", "loss"}


@dataclass(frozen=True)
class StreakSummary:
    """Aggregate streak statistics for a sequence of attempt records."""

    total_records: int
    wins: int
    losses: int
    longest_win_streak: int
    longest_loss_streak: int
    current_streak_result: str | None
    current_streak_length: int


def _normalise_result(result: str | None) -> str:
    return (result or "").strip().lower()


def compute_streak_summary(records: Sequence[Record]) -> StreakSummary:
    total = len(records)
    wins = 0
    losses = 0
    longest = {"win": 0, "loss": 0}
    current_result: str | None = None
    current_length = 0

    for record in records:
        result = _normalise_result(record.result)
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1

        if result not in TRACKED_RESULTS:
            current_result = None
            current_length = 0
            continue

        if result == current_result:
            current_length += 1
        else:
            current_result = result
            current_length = 1

        if current_length > longest[result]:
            longest[result] = current_length

    if current_result not in TRACKED_RESULTS:
        current_result = None
        current_length = 0

    return StreakSummary(
        total_records=total,
        wins=wins,
        losses=losses,
        longest_win_streak=longest["win"],
        longest_loss_streak=longest["loss"],
        current_streak_result=current_result,
        current_streak_length=current_length,
    )


def format_streak_summary(path: Path, summary: StreakSummary) -> str:
    lines = [f"{path}: {summary.total_records} records"]
    lines.append(f"  wins={summary.wins} losses={summary.losses}")
    lines.append(f"  longest win streak: {summary.longest_win_streak}")
    lines.append(f"  longest loss streak: {summary.longest_loss_streak}")
    if summary.current_streak_result:
        lines.append(
            f"  current {summary.current_streak_result} streak: {summary.current_streak_length}"
        )
    else:
        lines.append("  current streak: none")
    return "\n".join(lines)


def summarise_path(path: Path) -> StreakSummary:
    records = load_records(path)
    return compute_streak_summary(records)


def run(paths: Iterable[str]) -> list[tuple[Path, StreakSummary]]:
    results: list[tuple[Path, StreakSummary]] = []
    for raw_path in paths:
        path = Path(raw_path)
        summary = summarise_path(path)
        results.append((path, summary))
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute win/loss streak statistics for solitaire attempt datasets.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to dataset files. Use shell globs to analyse multiple files at once.",
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
        print(format_streak_summary(path, summary))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
