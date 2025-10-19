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


def compute_streak_summary(
    records: Sequence[Record], *, abandoned_as_loss: bool = False
) -> StreakSummary:
    total = len(records)
    wins = 0
    losses = 0
    longest = {"win": 0, "loss": 0}
    current_result: str | None = None
    current_length = 0

    for record in records:
        result = _normalise_result(record.result)
        tracked_result = result
        if result == "abandoned" and abandoned_as_loss:
            tracked_result = "loss"

        if tracked_result == "win":
            wins += 1
        elif tracked_result == "loss":
            losses += 1

        if tracked_result not in TRACKED_RESULTS:
            current_result = None
            current_length = 0
            continue

        if tracked_result == current_result:
            current_length += 1
        else:
            current_result = tracked_result
            current_length = 1

        if current_length > longest[tracked_result]:
            longest[tracked_result] = current_length

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


def summarise_path(path: Path, *, abandoned_as_loss: bool = False) -> StreakSummary:
    records = load_records(path)
    return compute_streak_summary(records, abandoned_as_loss=abandoned_as_loss)


def run(
    paths: Iterable[str], *, abandoned_as_loss: bool = False
) -> list[tuple[Path, StreakSummary]]:
    results: list[tuple[Path, StreakSummary]] = []
    for raw_path in paths:
        path = Path(raw_path)
        summary = summarise_path(path, abandoned_as_loss=abandoned_as_loss)
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
    parser.add_argument(
        "--treat-abandoned-as-loss",
        dest="abandoned_as_loss",
        action="store_true",
        help="Count 'abandoned' attempts as losses when computing streaks.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summaries = run(args.paths, abandoned_as_loss=args.abandoned_as_loss)
    except DatasetError as exc:
        parser.error(str(exc))

    for path, summary in summaries:
        print(format_streak_summary(path, summary))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
