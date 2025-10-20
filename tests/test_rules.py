import json
import math
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rules import (
    RuleProfile,
    MAX_RELAX,
    FRIENDLY_APP,
    STANDARD,
    XRAY,
)


@pytest.mark.parametrize(
    "profile,expected",
    [
        (MAX_RELAX, True),
        (FRIENDLY_APP, False),
        (STANDARD, False),
        (XRAY, False),
    ],
)
def test_supermove_relaxed(profile, expected):
    state = {}
    move = {"type": "supermove", "strength": "relaxed"}
    assert profile.is_move_legal(state, move) is expected


def test_max_relax_allows_takeback_peek_and_autoplay():
    move_takeback = {"type": "foundation_to_tableau"}
    move_peek = {"type": "peek"}
    move_autoplay = {"type": "autoplay", "is_safe": False}
    assert MAX_RELAX.is_move_legal({}, move_takeback)
    assert MAX_RELAX.is_move_legal({}, move_peek)
    assert MAX_RELAX.is_move_legal({}, move_autoplay)


def test_standard_restricts_autoplay_and_takeback():
    assert not STANDARD.is_move_legal({}, {"type": "foundation_to_tableau"})
    assert not STANDARD.is_move_legal({}, {"type": "autoplay", "is_safe": False})
    assert STANDARD.is_move_legal({}, {"type": "autoplay", "is_safe": True})


def test_xray_allows_peek():
    assert XRAY.is_move_legal({}, {"type": "peek"})
    assert not STANDARD.is_move_legal({}, {"type": "peek"})


@pytest.mark.parametrize(
    "profile,state,expected",
    [
        (MAX_RELAX, {"passes_made": 5}, True),
        (FRIENDLY_APP, {"passes_made": 5}, True),
        (STANDARD, {"passes_made": 2}, True),
        (STANDARD, {"passes_made": 3}, False),
        (XRAY, {"passes_made": 3}, False),
    ],
)
def test_pass_limits(profile, state, expected):
    move = {"type": "stock_pass"}
    assert profile.is_move_legal(state, move) is expected


def test_passes_remaining_for_unlimited_profile():
    assert MAX_RELAX.passes_remaining({"passes_made": 20}) is None


def test_passes_remaining_counts_down():
    assert STANDARD.passes_remaining({"passes_made": 1}) == 2
    assert STANDARD.passes_remaining({"passes_made": "2"}) == 1
    assert STANDARD.passes_remaining({"stock_passes": 3}) == 0


def test_passes_remaining_handles_invalid_state_values():
    assert STANDARD.passes_remaining({}) == 3
    assert STANDARD.passes_remaining({"passes_made": -5}) == 3
    assert STANDARD.passes_remaining({"passes_made": True}) == 3


def test_draw_count_enforced():
    draw_move_one = {"type": "draw", "draw_count": 1}
    draw_move_three = {"type": "draw", "draw_count": 3}
    assert MAX_RELAX.is_move_legal({}, draw_move_one)
    assert not MAX_RELAX.is_move_legal({}, draw_move_three)
    assert STANDARD.is_move_legal({}, draw_move_three)
    assert not STANDARD.is_move_legal({}, draw_move_one)


def test_undo_rules():
    assert MAX_RELAX.is_move_legal({}, {"type": "undo"})
    assert not STANDARD.is_move_legal({"undo_remaining": 0}, {"type": "undo"})
    assert STANDARD.is_move_legal({"undo_remaining": 2}, {"type": "undo"})


def test_serialisation_round_trip():
    payload = MAX_RELAX.to_json()
    restored = RuleProfile.from_json(payload)
    assert restored == MAX_RELAX
    assert json.loads(payload)["draw"] == MAX_RELAX.draw


@pytest.mark.parametrize("profile", [MAX_RELAX, FRIENDLY_APP, STANDARD, XRAY])
def test_unknown_moves_are_allowed(profile):
    assert profile.is_move_legal({}, {"type": "custom"})


def _make_profile(passes):
    return RuleProfile(
        draw=1,
        passes=passes,
        supermove="standard",
        foundation_takeback=False,
        peek_xray=False,
        autoplay_safe_only=True,
        undo_unlimited=False,
    )


def test_numeric_string_pass_limit_is_respected():
    profile = _make_profile("5")
    assert profile.pass_limit == 5
    assert profile.is_move_legal({"passes_made": 4}, {"type": "stock_pass"})
    assert not profile.is_move_legal({"passes_made": 5}, {"type": "stock_pass"})


def test_integer_pass_limit_is_respected():
    profile = _make_profile(2)
    assert profile.pass_limit == 2
    assert profile.is_move_legal({"passes_made": 1}, {"type": "stock_pass"})
    assert not profile.is_move_legal({"passes_made": 2}, {"type": "stock_pass"})


def test_blank_pass_limit_treated_as_unlimited():
    profile = _make_profile("   ")
    assert profile.pass_limit is None
    assert profile.is_move_legal({"passes_made": 100}, {"type": "stock_pass"})


def test_float_pass_limit_is_respected():
    profile = _make_profile(4.0)
    assert profile.pass_limit == 4
    assert profile.is_move_legal({"passes_made": 3}, {"type": "stock_pass"})
    assert not profile.is_move_legal({"passes_made": 4}, {"type": "stock_pass"})


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        (-1, ValueError),
        ("-1", ValueError),
        ("bogus", ValueError),
        (True, TypeError),
        (3.5, ValueError),
        (math.nan, ValueError),
        (math.inf, ValueError),
    ],
)
def test_invalid_pass_limits_raise(value, expected_exception):
    profile = _make_profile(value)
    with pytest.raises(expected_exception):
        _ = profile.pass_limit
