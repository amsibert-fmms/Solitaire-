from __future__ import annotations

from pathlib import Path

import pytest

from scripts.summary import Summary, format_summary, main, summarise_records
from scripts.validate import Record


def build_record(**overrides):
    defaults = {
        "tag": "hand-1",
        "result": "win",
        "timestamp_utc": "2023-01-01T00:00:00Z",
        "seed": "42",
        "moves": 120,
        "duration_ms": 90000,
        "notes": None,
        "raw": {},
    }
    defaults.update(overrides)
    return Record(**defaults)


def test_summarise_records_computes_statistics():
    records = [
        build_record(result="win", moves=120, duration_ms=90000),
        build_record(result="loss", moves=110, duration_ms=87000),
        build_record(result="win", moves=None, duration_ms=None),
    ]

    summary = summarise_records(records)

    assert isinstance(summary, Summary)
    assert summary.total_records == 3
    assert summary.result_counts == {"loss": 1, "win": 2}
    assert summary.win_rate == pytest.approx(2 / 3)
    assert summary.average_moves == pytest.approx(115.0)
    assert summary.median_moves == pytest.approx(115.0)
    assert summary.average_duration_ms == pytest.approx(88500.0)


def test_format_summary_includes_key_metrics(tmp_path: Path):
    summary = Summary(
        total_records=2,
        result_counts={"loss": 1, "win": 1},
        win_rate=0.5,
        average_moves=100.0,
        median_moves=100.0,
        average_duration_ms=80000.0,
    )
    path = tmp_path / "attempts.csv"
    output = format_summary(path, summary)

    assert f"{path}" in output
    assert "win rate: 50.0%" in output
    assert "moves: mean=100.0 median=100.0" in output
    assert "average duration: 80000.0 ms" in output


def test_main_prints_summary_for_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "tag,result,timestamp_utc,moves,duration_ms\n"
        "hand-1,win,2023-01-01T00:00:00Z,120,90000\n"
        "hand-2,loss,2023-01-02T00:00:00Z,100,80000\n",
        encoding="utf-8",
    )

    exit_code = main([str(csv_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "sample.csv" in captured.out
    assert "win rate: 50.0%" in captured.out

