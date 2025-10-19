"""Dataset validation utility for solitaire attempt logs."""
from __future__ import annotations

import argparse
import csv
import importlib
import importlib.util
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

REQUIRED_COLUMNS = {"tag", "result", "timestamp_utc"}
RECOMMENDED_COLUMNS = {"seed", "moves", "duration_ms"}
ALLOWED_RESULTS = {"win", "loss", "abandoned", "unknown"}


class DatasetError(Exception):
    """Raised when a fatal dataset issue is encountered."""


@dataclass
class Record:
    """Normalised dataset record."""

    tag: str
    result: str
    timestamp_utc: str
    seed: str | None = None
    moves: int | None = None
    duration_ms: int | None = None
    notes: str | None = None
    raw: Mapping[str, object] = field(default_factory=dict)

    @property
    def identity(self) -> tuple[str, str | None, str]:
        """Return the record identity used for duplicate detection."""

        return (self.tag, self.seed, self.timestamp_utc)


def _load_csv(path: Path) -> Iterator[Mapping[str, object]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DatasetError(f"{path}: Missing header row")
        for row in reader:
            yield {key: value for key, value in row.items() if key is not None}


def _load_parquet(path: Path) -> Iterator[Mapping[str, object]]:
    spec = importlib.util.find_spec("pyarrow")
    if spec is None:
        raise DatasetError(
            f"{path}: Reading Parquet files requires the 'pyarrow' package to be installed"
        )
    pyarrow = importlib.import_module("pyarrow")
    table = pyarrow.parquet.read_table(path)
    for batch in table.to_batches():
        for row in batch.to_pylist():
            yield row


def load_records(path: Path) -> list[Record]:
    loaders = {
        ".csv": _load_csv,
        ".parquet": _load_parquet,
    }
    loader = loaders.get(path.suffix.lower())
    if loader is None:
        raise DatasetError(f"{path}: Unsupported file extension")

    records = []
    for raw in loader(path):
        record = _normalise_record(raw)
        records.append(record)
    return records


def _normalise_string(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return str(value)
    return str(value) if value is not None else None


def _normalise_int(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        candidate = int(value)
        return candidate if candidate >= 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            candidate = int(stripped, 10)
        except ValueError:
            return None
        return candidate if candidate >= 0 else None
    return None


def _normalise_record(raw: Mapping[str, object]) -> Record:
    tag = _normalise_string(raw.get("tag")) or ""
    result = (_normalise_string(raw.get("result")) or "").lower()
    timestamp = _normalise_string(raw.get("timestamp_utc")) or ""

    return Record(
        tag=tag,
        result=result,
        timestamp_utc=timestamp,
        seed=_normalise_string(raw.get("seed")),
        moves=_normalise_int(raw.get("moves")),
        duration_ms=_normalise_int(raw.get("duration_ms")),
        notes=_normalise_string(raw.get("notes")),
        raw=raw,
    )


@dataclass
class ValidationResult:
    path: Path
    records: list[Record]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return not self.errors

    @property
    def result_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.result] = counts.get(record.result, 0) + 1
        return counts


def validate_records(path: Path, records: Sequence[Record]) -> ValidationResult:
    result = ValidationResult(path=path, records=list(records))
    if not records:
        result.errors.append("No records found")
        return result

    header = {key.lower() for key in records[0].raw.keys()}
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing_columns:
        result.errors.append(
            "Missing required columns: " + ", ".join(sorted(missing_columns))
        )

    missing_recommended = [
        column for column in RECOMMENDED_COLUMNS if column not in header
    ]
    if missing_recommended:
        result.warnings.append(
            "Missing recommended columns: " + ", ".join(sorted(missing_recommended))
        )

    invalid_results = [
        record
        for record in records
        if record.result and record.result not in ALLOWED_RESULTS
    ]
    if invalid_results:
        unique_values = sorted({record.result for record in invalid_results})
        result.errors.append(
            "Unexpected result values: " + ", ".join(unique_values)
        )

    empty_tags = [record for record in records if not record.tag]
    if empty_tags:
        result.errors.append(f"{len(empty_tags)} records missing tag values")

    empty_timestamps = [record for record in records if not record.timestamp_utc]
    if empty_timestamps:
        result.errors.append(
            f"{len(empty_timestamps)} records missing timestamp_utc values"
        )

    duplicate_keys: dict[tuple[str, str | None, str], int] = {}
    duplicates = []
    for record in records:
        key = record.identity
        count = duplicate_keys.get(key, 0) + 1
        duplicate_keys[key] = count
        if count == 2:
            duplicates.append(key)
    if duplicates:
        formatted = ", ".join(
            f"(tag={tag}, seed={seed or '—'}, timestamp_utc={timestamp})"
            for tag, seed, timestamp in duplicates
        )
        result.errors.append(f"Duplicate records detected: {formatted}")

    result_only_values = [record.result for record in records if record.result]
    if result_only_values and len(set(result_only_values)) == 1:
        result.warnings.append(
            "All records share the same result value; outcome coverage may be incomplete"
        )

    return result


def format_result(result: ValidationResult) -> str:
    counts = " ".join(
        f"{label}={count}" for label, count in sorted(result.result_counts.items())
    )
    status = "ok" if result.is_ok else "failed"
    return f"{result.path}: {status} ({len(result.records)} rows) {counts}".strip()


def run(paths: Iterable[str]) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for raw_path in paths:
        path = Path(raw_path)
        records = load_records(path)
        validation = validate_records(path, records)
        results.append(validation)
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate solitaire attempt datasets exported as CSV or Parquet.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to dataset files. Use shell globs to validate multiple files at once.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        results = run(args.paths)
    except DatasetError as exc:
        parser.error(str(exc))

    has_error = False
    for result in results:
        print(format_result(result))
        for warning in result.warnings:
            print(f"  warning: {warning}")
        for error in result.errors:
            print(f"  error: {error}")
            has_error = True
    return 1 if has_error else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
