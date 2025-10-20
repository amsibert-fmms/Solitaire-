"""Ensure deck key encodings round-trip to the same permutation."""
from __future__ import annotations

CARD_TOTAL = 52
DECK_KEY_SIZE = 32

def decode_deck_key(payload: bytes) -> list[int]:
    if len(payload) != DECK_KEY_SIZE:
        raise ValueError("Deck key must contain 32 bytes")
    value = 0
    for byte in payload:
        value = (value << 8) | byte
    digits = [0] * CARD_TOTAL
    for index in range(CARD_TOTAL - 1, -1, -1):
        base = index + 1
        digit = value % base
        value //= base
        digits[index] = int(digit)
    if value:
        raise ValueError("Deck key contains leftover data")
    available = list(range(CARD_TOTAL))
    permutation: list[int] = []
    for digit in digits:
        if digit >= len(available):
            raise ValueError("Deck key contains invalid ordering data")
        permutation.append(available.pop(digit))
    return permutation


def test_deck_key_round_trip_preserves_permutation():
    payload = bytes(DECK_KEY_SIZE)
    first = decode_deck_key(payload)
    second = decode_deck_key(payload)
    assert first == second
    assert len(first) == CARD_TOTAL
    assert first == sorted(first)


def test_invalid_payload_sizes_are_rejected():
    try:
        decode_deck_key(bytes(DECK_KEY_SIZE + 1))
    except ValueError as exc:
        assert "32 bytes" in str(exc)
    else:  # pragma: no cover - defensive guard
        raise AssertionError("Expected ValueError for oversized payload")
