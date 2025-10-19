from __future__ import annotations

from pathlib import Path

import pytest

from scripts.summary import (
    Summary,
    filter_records,
    format_summary,
    main,
    summarise_path,
    summarise_records,
    summary_to_dict,
)
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
    assert summary.median_duration_ms == pytest.approx(88500.0)
    assert summary.longest_duration_ms == 90000
    assert summary.fastest_win_moves == 120
    assert summary.fastest_win_duration_ms == 90000


def test_format_summary_includes_key_metrics(tmp_path: Path):
    summary = Summary(
        total_records=2,
        result_counts={"loss": 1, "win": 1},
        win_rate=0.5,
        average_moves=100.0,
        median_moves=100.0,
        average_duration_ms=80000.0,
        median_duration_ms=79000.0,
        fastest_win_moves=90,
        fastest_win_duration_ms=70000,
        longest_duration_ms=90000,
    )
    path = tmp_path / "attempts.csv"
    output = format_summary(path, summary)

    assert f"{path}" in output
    assert "win rate: 50.0%" in output
    assert "moves: mean=100.0 median=100.0" in output
    assert "average duration: 80000.0 ms" in output
    assert "median duration: 79000.0 ms" in output
    assert "longest attempt: 90000 ms" in output
    assert "fastest win: 90 moves, 70000 ms" in output


def test_filter_records_allows_include_and_exclude():
    records = [
        build_record(result="win"),
        build_record(result="loss"),
        build_record(result="abandoned"),
    ]

    filtered = filter_records(records, include_results=["win", "loss"])
    assert [record.result for record in filtered] == ["win", "loss"]

    filtered = filter_records(records, exclude_results=["loss"])
    assert [record.result for record in filtered] == ["win", "abandoned"]


def test_summarise_path_applies_filters(tmp_path: Path):
    csv_path = tmp_path / "attempts.csv"
    csv_path.write_text(
        "tag,result,timestamp_utc\n"
        "hand-1,win,2023-01-01T00:00:00Z\n"
        "hand-2,loss,2023-01-02T00:00:00Z\n"
        "hand-3,abandoned,2023-01-03T00:00:00Z\n",
        encoding="utf-8",
    )

    summary = summarise_path(csv_path, include_results=["win"])
    assert summary.total_records == 1
    assert summary.result_counts == {"win": 1}


def test_summary_to_dict_orders_result_counts():
    summary = Summary(
        total_records=2,
        result_counts={"win": 1, "loss": 1},
        win_rate=0.5,
        average_moves=None,
        median_moves=None,
        average_duration_ms=None,
        median_duration_ms=None,
        fastest_win_moves=None,
        fastest_win_duration_ms=None,
        longest_duration_ms=None,
    )

    payload = summary_to_dict(summary)
    assert payload["result_counts"] == {"loss": 1, "win": 1}


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


def test_main_supports_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "tag,result,timestamp_utc,moves,duration_ms\n"
        "hand-1,win,2023-01-01T00:00:00Z,120,90000\n"
        "hand-2,loss,2023-01-02T00:00:00Z,100,80000\n",
        encoding="utf-8",
    )

    exit_code = main(["--json", str(csv_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip().startswith("[")
    assert "\"path\"" in captured.out
    assert "\"summary\"" in captured.out

