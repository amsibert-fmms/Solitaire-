import csv
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate


def _write_csv(path: pathlib.Path, rows):
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_validate_records_success(tmp_path):
    csv_path = tmp_path / "attempts.csv"
    _write_csv(
        csv_path,
        [
            {
                "tag": "alpha",
                "result": "win",
                "timestamp_utc": "2024-01-01T00:00:00Z",
                "seed": "42",
                "moves": "120",
                "duration_ms": "60000",
            },
            {
                "tag": "beta",
                "result": "loss",
                "timestamp_utc": "2024-01-02T00:00:00Z",
                "seed": "43",
                "moves": "130",
                "duration_ms": "65000",
            },
        ],
    )

    records = validate.load_records(csv_path)
    result = validate.validate_records(csv_path, records)

    assert result.is_ok
    assert result.errors == []
    assert result.result_counts["win"] == 1
    assert result.result_counts["loss"] == 1


def test_duplicate_detection(tmp_path):
    csv_path = tmp_path / "duplicate.csv"
    row = {
        "tag": "gamma",
        "result": "abandoned",
        "timestamp_utc": "2024-01-03T00:00:00Z",
        "seed": "44",
    }
    _write_csv(csv_path, [row, row])

    result = validate.validate_records(csv_path, validate.load_records(csv_path))

    assert not result.is_ok
    assert any("Duplicate records detected" in error for error in result.errors)


def test_missing_required_column(tmp_path):
    csv_path = tmp_path / "missing.csv"
    _write_csv(
        csv_path,
        [
            {
                "tag": "delta",
                "result": "win",
            }
        ],
    )

    result = validate.validate_records(csv_path, validate.load_records(csv_path))

    assert not result.is_ok
    assert any("Missing required columns" in error for error in result.errors)


@pytest.mark.parametrize(
    "value",
    ["unexpected", "partial"],
)
def test_invalid_result_values(tmp_path, value):
    csv_path = tmp_path / f"invalid_{value}.csv"
    _write_csv(
        csv_path,
        [
            {
                "tag": "epsilon",
                "result": value,
                "timestamp_utc": "2024-01-04T00:00:00Z",
            }
        ],
    )

    result = validate.validate_records(csv_path, validate.load_records(csv_path))

    assert not result.is_ok
    assert any("Unexpected result values" in error for error in result.errors)


def test_run_reports_each_file(tmp_path, capsys):
    csv_one = tmp_path / "one.csv"
    csv_two = tmp_path / "two.csv"
    _write_csv(
        csv_one,
        [
            {
                "tag": "zeta",
                "result": "win",
                "timestamp_utc": "2024-01-05T00:00:00Z",
            }
        ],
    )
    _write_csv(
        csv_two,
        [
            {
                "tag": "zeta",
                "result": "win",
                "timestamp_utc": "",
            }
        ],
    )

    exit_code = validate.main([str(csv_one), str(csv_two)])

    captured = capsys.readouterr()
    assert "rows" in captured.out
    assert exit_code == 1
    assert "error" in captured.out


def test_parquet_without_pyarrow(tmp_path):
    parquet_path = tmp_path / "sample.parquet"
    parquet_path.write_bytes(b"")

    with pytest.raises(SystemExit) as exc:
        validate.main([str(parquet_path)])

    assert exc.value.code == 2
