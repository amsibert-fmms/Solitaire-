#!/usr/bin/env python3
"""Automated Klondike solver used to benchmark human play."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Iterable, List, Optional


SUITS = ("spades", "hearts", "clubs", "diamonds")
SUIT_COLORS = {
    "spades": "black",
    "clubs": "black",
    "hearts": "red",
    "diamonds": "red",
}
RANKS = tuple(range(1, 14))


@dataclass
class Card:
    """Simple representation of a playing card."""

    rank: int
    suit: str
    face_up: bool = False

    @property
    def color(self) -> str:
        return SUIT_COLORS[self.suit]

    def label(self) -> str:
        mapping = {
            1: "A",
            11: "J",
            12: "Q",
            13: "K",
        }
        return mapping.get(self.rank, str(self.rank))

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.label()}{self.suit[0].upper()}"


class KlondikeSolver:
    """Greedy Klondike solver with deterministic shuffles."""

    def __init__(
        self,
        *,
        draw_count: int = 3,
        pass_limit: Optional[int] = None,
        shuffle_seed: int = 0,
        deck: Optional[Iterable[Card]] = None,
    ) -> None:
        if draw_count < 1:
            raise ValueError("draw_count must be at least 1")
        if pass_limit is not None and pass_limit < 0:
            raise ValueError("pass_limit must be non-negative")
        self.draw_count = int(draw_count)
        self.pass_limit = pass_limit
        self.shuffle_seed = shuffle_seed & 0xFFFFFFFF
        self._base_rng = random.Random(self.shuffle_seed)
        self._initial_deck = list(deck) if deck is not None else None
        self.setup()

    def setup(self) -> None:
        """Deal a fresh game using the configured shuffle seed."""

        deck = self._build_deck()
        self.tableau: List[List[Card]] = [list() for _ in range(7)]
        for column in range(7):
            for row in range(column + 1):
                card = deck.pop()
                card.face_up = row == column
                self.tableau[column].append(card)

        self.stock: List[Card] = deck
        for card in self.stock:
            card.face_up = False

        self.waste: List[Card] = []
        self.foundations = {suit: [] for suit in SUITS}
        self.moves = 0
        self.passes_used = 0

    # ------------------------------------------------------------------
    # Deck helpers
    # ------------------------------------------------------------------
    def _build_deck(self) -> List[Card]:
        if self._initial_deck is not None:
            deck = [Card(card.rank, card.suit, card.face_up) for card in self._initial_deck]
        else:
            deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
            self._base_rng.shuffle(deck)
        return deck

    # ------------------------------------------------------------------
    # Core move operations
    # ------------------------------------------------------------------
    def can_move_to_foundation(self, card: Card) -> bool:
        foundation = self.foundations[card.suit]
        if not foundation:
            return card.rank == 1
        return foundation[-1].rank == card.rank - 1

    def move_to_foundation(self, card: Card) -> None:
        self.foundations[card.suit].append(card)
        self.moves += 1

    def flip_tableau_if_needed(self, index: int) -> None:
        column = self.tableau[index]
        if column and not column[-1].face_up:
            column[-1].face_up = True

    def can_stack_on_tableau(self, card: Card, column: List[Card]) -> bool:
        if not column:
            return card.rank == 13
        top = column[-1]
        if not top.face_up:
            return False
        return top.color != card.color and top.rank == card.rank + 1

    def move_stack(self, src_index: int, start_idx: int, dest_index: int) -> None:
        column = self.tableau[src_index]
        stack = column[start_idx:]
        del column[start_idx:]
        self.tableau[dest_index].extend(stack)
        self.moves += 1
        self.flip_tableau_if_needed(src_index)

    def draw_from_stock(self) -> bool:
        if not self.stock:
            return False
        draw_count = min(self.draw_count, len(self.stock))
        for _ in range(draw_count):
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
        self.moves += 1
        return True

    def recycle_stock(self) -> bool:
        if not self.waste:
            return False
        if self.pass_limit is not None and self.passes_used >= self.pass_limit:
            return False
        cards = list(reversed(self.waste))
        self.waste.clear()
        for card in cards:
            card.face_up = False
        self.stock.extend(cards)
        self.passes_used += 1
        return True

    # ------------------------------------------------------------------
    # Greedy strategies
    # ------------------------------------------------------------------
    def try_promote_waste_to_foundation(self) -> bool:
        if not self.waste:
            return False
        card = self.waste[-1]
        if not self.can_move_to_foundation(card):
            return False
        self.waste.pop()
        self.move_to_foundation(card)
        return True

    def try_promote_tableau_to_foundation(self) -> bool:
        made_move = False
        for index, column in enumerate(self.tableau):
            if not column or not column[-1].face_up:
                continue
            card = column[-1]
            if self.can_move_to_foundation(card):
                column.pop()
                self.move_to_foundation(card)
                self.flip_tableau_if_needed(index)
                made_move = True
                break
        return made_move

    def try_move_waste_to_tableau(self) -> bool:
        if not self.waste:
            return False
        card = self.waste[-1]
        best_target: Optional[int] = None
        best_priority = -1
        for index, column in enumerate(self.tableau):
            if not self.can_stack_on_tableau(card, column):
                continue
            priority = 0
            if not column:
                priority = 2
            elif any(not c.face_up for c in column):
                priority = 3
            elif column and column[-1].face_up:
                priority = 1
            if priority > best_priority:
                best_target = index
                best_priority = priority
        if best_target is None:
            return False
        self.tableau[best_target].append(self.waste.pop())
        self.moves += 1
        return True

    def try_move_tableau_to_tableau(self) -> bool:
        for src_index, column in enumerate(self.tableau):
            if not column:
                continue
            first_face_up = next((i for i, card in enumerate(column) if card.face_up), None)
            if first_face_up is None:
                continue
            stack = column[first_face_up:]
            has_hidden_card = first_face_up > 0
            for dest_index, dest_column in enumerate(self.tableau):
                if dest_index == src_index:
                    continue
                if not self.can_stack_on_tableau(stack[0], dest_column):
                    continue
                if dest_column and not has_hidden_card:
                    continue
                if not dest_column and (stack[0].rank != 13 or not has_hidden_card):
                    continue
                self.move_stack(src_index, first_face_up, dest_index)
                return True
        return False

    def resolve_forced_moves(self) -> bool:
        moved = False
        while True:
            if self.try_promote_waste_to_foundation():
                moved = True
                continue
            if self.try_promote_tableau_to_foundation():
                moved = True
                continue
            if self.try_move_waste_to_tableau():
                moved = True
                continue
            if self.try_move_tableau_to_tableau():
                moved = True
                continue
            break
        return moved

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------
    def foundation_count(self) -> int:
        return sum(len(pile) for pile in self.foundations.values())

    def is_won(self) -> bool:
        return self.foundation_count() == 52

    def play(self, *, max_steps: int = 5000) -> dict:
        steps = 0
        while steps < max_steps and not self.is_won():
            steps += 1
            if self.resolve_forced_moves():
                continue
            if self.draw_from_stock():
                continue
            if not self.recycle_stock():
                break
        return {
            "won": self.is_won(),
            "moves": self.moves,
            "passes_used": self.passes_used,
            "seed": self.shuffle_seed,
            "draw_count": self.draw_count,
            "foundations": self.foundation_count(),
            "stock_remaining": len(self.stock),
            "waste": len(self.waste),
            "steps": steps,
        }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed for the first shuffle. Subsequent games advance the RNG deterministically.",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help="Number of games to simulate (default: 1).",
    )
    parser.add_argument(
        "--draw-count",
        type=int,
        default=3,
        help="Number of cards drawn from the stock at a time (default: 3).",
    )
    parser.add_argument(
        "--pass-limit",
        type=int,
        default=-1,
        help="Maximum number of stock recycles. Use -1 for unlimited (default).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=5000,
        help="Fail-safe iteration cap to avoid infinite loops (default: 5000).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-game output and only print the summary line.",
    )
    return parser.parse_args()


def run_cli() -> None:
    args = parse_arguments()
    master_seed = args.seed if args.seed is not None else random.randrange(0, 2**32)
    master_rng = random.Random(master_seed)
    pass_limit: Optional[int]
    pass_limit = None if args.pass_limit < 0 else args.pass_limit

    wins = 0
    total_moves = 0
    total_foundations = 0

    for game_index in range(args.games):
        if game_index == 0 and args.seed is not None:
            seed = args.seed & 0xFFFFFFFF
        else:
            seed = master_rng.randrange(0, 2**32)

        solver = KlondikeSolver(
            draw_count=args.draw_count,
            pass_limit=pass_limit,
            shuffle_seed=seed,
        )
        result = solver.play(max_steps=args.max_steps)
        total_moves += result["moves"]
        total_foundations += result["foundations"]
        if result["won"]:
            wins += 1

        if not args.quiet:
            status = "win" if result["won"] else "loss"
            print(
                f"Game {game_index + 1}: seed={seed} moves={result['moves']} "
                f"passes={result['passes_used']} foundations={result['foundations']} status={status}"
            )

        if result["won"] and args.games == 1:
            # One last pass to make sure we report the final tableau when helpful.
            continue

    win_rate = (wins / args.games) * 100 if args.games else 0.0
    average_moves = total_moves / args.games if args.games else 0.0
    average_foundations = total_foundations / args.games if args.games else 0.0

    print(
        "Summary: "
        f"games={args.games} wins={wins} ({win_rate:.1f}%) "
        f"avg_moves={average_moves:.1f} avg_foundations={average_foundations:.1f}"
    )


if __name__ == "__main__":
    run_cli()
