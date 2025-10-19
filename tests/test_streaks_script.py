from pathlib import Path

import pytest

from scripts.streaks import (
    StreakSummary,
    compute_streak_summary,
    format_streak_summary,
    main,
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


def test_compute_streak_summary_tracks_longest_and_current():
    records = [
        build_record(result="win"),
        build_record(result="win"),
        build_record(result="loss"),
        build_record(result="loss"),
        build_record(result="loss"),
        build_record(result="abandoned"),
        build_record(result="loss"),
        build_record(result="win"),
        build_record(result="win"),
    ]

    summary = compute_streak_summary(records)

    assert isinstance(summary, StreakSummary)
    assert summary.total_records == len(records)
    assert summary.wins == 4
    assert summary.losses == 4
    assert summary.longest_win_streak == 2
    assert summary.longest_loss_streak == 3
    assert summary.current_streak_result == "win"
    assert summary.current_streak_length == 2


def test_format_streak_summary_includes_current_streak(tmp_path: Path):
    summary = StreakSummary(
        total_records=5,
        wins=3,
        losses=2,
        longest_win_streak=3,
        longest_loss_streak=2,
        current_streak_result="loss",
        current_streak_length=2,
    )
    path = tmp_path / "attempts.csv"

    output = format_streak_summary(path, summary)

    assert f"{path}" in output
    assert "wins=3 losses=2" in output
    assert "longest win streak: 3" in output
    assert "current loss streak: 2" in output


def test_main_prints_streak_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "tag,result,timestamp_utc\n"
        "hand-1,win,2023-01-01T00:00:00Z\n"
        "hand-2,win,2023-01-02T00:00:00Z\n"
        "hand-3,loss,2023-01-03T00:00:00Z\n",
        encoding="utf-8",
    )

    exit_code = main([str(csv_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "sample.csv" in captured.out
    assert "longest win streak" in captured.out
