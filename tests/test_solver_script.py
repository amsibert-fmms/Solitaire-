import math

from scripts.solver import Card, KlondikeSolver


def test_solver_initialises_tableau_with_correct_counts():
    solver = KlondikeSolver(draw_count=1, shuffle_seed=42)
    assert len(solver.tableau) == 7
    assert sum(len(column) for column in solver.tableau) == 28
    assert all(column[-1].face_up for column in solver.tableau if column)


def test_recycle_stock_respects_pass_limit():
    solver = KlondikeSolver(draw_count=1, pass_limit=1, shuffle_seed=7)
    # Exhaust the stock by drawing until empty.
    while solver.draw_from_stock():
        pass
    assert solver.recycle_stock() is True
    # After one recycle the pass limit should prevent further recycling.
    assert solver.recycle_stock() is False


def test_play_returns_consistent_metadata():
    solver = KlondikeSolver(draw_count=1, pass_limit=2, shuffle_seed=12345)
    result = solver.play(max_steps=200)
    assert result["seed"] == 12345 & 0xFFFFFFFF
    assert result["draw_count"] == 1
    assert "won" in result
    assert result["moves"] >= 0
    assert math.isfinite(result["steps"])


def test_custom_deck_support_allows_controlled_state():
    # Build a custom deck that leads to immediate foundation promotions by
    # stacking identical aces throughout the layout.
    custom_deck = [Card(rank=1, suit="hearts") for _ in range(52)]

    solver = KlondikeSolver(draw_count=1, shuffle_seed=0, deck=custom_deck)
    # Promote anything that can move to the foundations.
    solver.resolve_forced_moves()
    assert solver.foundation_count() >= 1
