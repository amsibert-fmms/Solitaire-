"""Dataset summarisation utility for solitaire attempt logs."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
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
    median_duration_ms: float | None
    fastest_win_moves: int | None
    fastest_win_duration_ms: int | None
    longest_duration_ms: int | None


def _normalise_result(value: str | None) -> str:
    """Return a lowercase representation of *value* suitable for comparisons."""

    return (value or "").strip().lower()


def _should_include(
    result: str,
    include_results: set[str] | None,
    exclude_results: set[str] | None,
) -> bool:
    """Return ``True`` when *result* passes the inclusion rules."""

    if include_results and result not in include_results:
        return False
    if exclude_results and result in exclude_results:
        return False
    return True


def filter_records(
    records: Sequence[Record],
    include_results: Sequence[str] | None = None,
    exclude_results: Sequence[str] | None = None,
) -> list[Record]:
    """Return *records* filtered by optional result inclusion/exclusion lists."""

    include_set = {_normalise_result(value) for value in include_results or []}
    exclude_set = {_normalise_result(value) for value in exclude_results or []}

    filtered: list[Record] = []
    for record in records:
        result = _normalise_result(record.result)
        if _should_include(result, include_set or None, exclude_set or None):
            filtered.append(record)
    return filtered


def summarise_records(records: Sequence[Record]) -> Summary:
    """Return aggregate statistics for *records*."""

    total = len(records)
    result_counts: dict[str, int] = {}
    wins = 0
    move_samples: list[int] = []
    win_move_samples: list[int] = []
    duration_samples: list[int] = []
    win_duration_samples: list[int] = []

    for record in records:
        result = _normalise_result(record.result) or "unknown"
        result_counts[result] = result_counts.get(result, 0) + 1
        if result == "win":
            wins += 1

        if record.moves is not None:
            move_samples.append(record.moves)
            if result == "win":
                win_move_samples.append(record.moves)
        if record.duration_ms is not None:
            duration_samples.append(record.duration_ms)
            if result == "win":
                win_duration_samples.append(record.duration_ms)

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
    median_duration: float | None
    longest_duration: int | None
    if duration_samples:
        average_duration = mean(duration_samples)
        median_duration = median(duration_samples)
        longest_duration = max(duration_samples)
    else:
        average_duration = None
        median_duration = None
        longest_duration = None

    fastest_win_moves = min(win_move_samples) if win_move_samples else None
    fastest_win_duration = (
        min(win_duration_samples) if win_duration_samples else None
    )

    return Summary(
        total_records=total,
        result_counts=result_counts,
        win_rate=win_rate,
        average_moves=average_moves,
        median_moves=median_moves,
        average_duration_ms=average_duration,
        median_duration_ms=median_duration,
        fastest_win_moves=fastest_win_moves,
        fastest_win_duration_ms=fastest_win_duration,
        longest_duration_ms=longest_duration,
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
    if summary.median_duration_ms is not None:
        lines.append(f"  median duration: {summary.median_duration_ms:.1f} ms")
    if summary.longest_duration_ms is not None:
        lines.append(f"  longest attempt: {summary.longest_duration_ms} ms")

    if summary.fastest_win_moves is not None or summary.fastest_win_duration_ms is not None:
        parts: list[str] = []
        if summary.fastest_win_moves is not None:
            parts.append(f"{summary.fastest_win_moves} moves")
        if summary.fastest_win_duration_ms is not None:
            parts.append(f"{summary.fastest_win_duration_ms} ms")
        lines.append("  fastest win: " + ", ".join(parts))

    return "\n".join(lines)


def summarise_path(
    path: Path,
    include_results: Sequence[str] | None = None,
    exclude_results: Sequence[str] | None = None,
) -> Summary:
    """Load records from *path* and return their summary."""

    records = load_records(path)
    filtered = filter_records(records, include_results, exclude_results)
    return summarise_records(filtered)


def run(
    paths: Iterable[str],
    *,
    include_results: Sequence[str] | None = None,
    exclude_results: Sequence[str] | None = None,
) -> list[tuple[Path, Summary]]:
    """Compute summaries for each path in *paths*."""

    results: list[tuple[Path, Summary]] = []
    for raw_path in paths:
        path = Path(raw_path)
        summary = summarise_path(path, include_results, exclude_results)
        results.append((path, summary))
    return results


def summary_to_dict(summary: Summary) -> dict[str, object]:
    """Return a JSON-serialisable representation of *summary*."""

    payload = asdict(summary)
    payload["result_counts"] = dict(sorted(payload["result_counts"].items()))
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarise solitaire attempt datasets exported as CSV or Parquet.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to dataset files. Use shell globs to summarise multiple files at once.",
    )
    parser.add_argument(
        "--include-result",
        dest="include_results",
        action="append",
        default=None,
        help="Only include attempts whose result matches the given value. Can be repeated.",
    )
    parser.add_argument(
        "--exclude-result",
        dest="exclude_results",
        action="append",
        default=None,
        help="Ignore attempts whose result matches the given value. Can be repeated.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the summary as JSON instead of formatted text.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summaries = run(
            args.paths,
            include_results=args.include_results,
            exclude_results=args.exclude_results,
        )
    except DatasetError as exc:
        parser.error(str(exc))

    if args.as_json:
        payload = [
            {"path": str(path), "summary": summary_to_dict(summary)}
            for path, summary in summaries
        ]
        print(json.dumps(payload, indent=2))
    else:
        for path, summary in summaries:
            print(format_summary(path, summary))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
