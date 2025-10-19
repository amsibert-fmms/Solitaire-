"""Rules engine for solitaire solver profiles."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, MutableMapping


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Retrieve *key* from mappings or objects with a fallback."""
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    if hasattr(obj, key):
        return getattr(obj, key)
    return default


PASS_LIMITS = {
    "unlimited": None,
    "infinite": None,
    "max_relax": None,
    "three": 3,
    "triple": 3,
    "one": 1,
    "single": 1,
    "none": 0,
}

SUPERMOVE_STRENGTH = {
    "none": 0,
    "standard": 1,
    "relaxed": 2,
}


def _coerce_non_negative_int(value: Any, default: int = 0) -> int:
    """Best-effort conversion of *value* into a non-negative integer."""

    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if value >= 0 else default
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return default
        candidate = int(value)
        return candidate if candidate >= 0 else default
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return default
        try:
            candidate = int(token, 10)
        except ValueError:
            return default
        return candidate if candidate >= 0 else default
    return default


def _normalise_pass_limit(value: Any) -> int | None:
    """Convert *value* into a normalised pass limit.

    The rules engine historically used string identifiers (``"three"``,
    ``"unlimited"``) to describe how many times the stock may be recycled.  In
    practice configuration data often comes from user input where the value may
    already be an integer or a numeric string.  This helper accepts either form
    and guarantees that the result is ``None`` (meaning unlimited) or a
    non-negative integer.

    ``ValueError`` is raised when the content is recognised but invalid (for
    example a negative number) while ``TypeError`` flags unsupported data types.
    """

    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("Boolean values are not valid pass limits")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("Pass limit must be non-negative")
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if not token:
            return None
        if token in PASS_LIMITS:
            return PASS_LIMITS[token]
        try:
            parsed = int(token, 10)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Unknown pass limit value: {value!r}") from exc
        if parsed < 0:
            raise ValueError("Pass limit must be non-negative")
        return parsed
    raise TypeError(f"Unsupported pass limit type: {type(value).__name__}")


@dataclass(frozen=True)
class RuleProfile:
    """A configurable rules profile for the solitaire engine."""

    draw: int
    passes: str | int | None
    supermove: str
    foundation_takeback: bool
    peek_xray: bool
    autoplay_safe_only: bool
    undo_unlimited: bool

    def to_dict(self) -> MutableMapping[str, Any]:
        """Return the profile as a JSON-serialisable mapping."""
        return dict(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RuleProfile":
        """Create a profile from *data* produced by :meth:`to_dict`."""
        fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered = {k: data[k] for k in data if k in fields}
        return cls(**filtered)  # type: ignore[arg-type]

    def to_json(self) -> str:
        """Serialise the profile to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, payload: str) -> "RuleProfile":
        """Deserialise a :class:`RuleProfile` from *payload*."""
        return cls.from_dict(json.loads(payload))

    @property
    def pass_limit(self) -> int | None:
        """Return the numeric stock pass limit for the profile."""

        return _normalise_pass_limit(self.passes)

    def passes_remaining(self, state: Any) -> int | None:
        """Return how many stock passes remain for *state*.

        ``None`` is returned when the profile allows unlimited recycling.  The
        helper gracefully handles missing or malformed state values by
        interpreting them as zero passes made.
        """

        limit = self.pass_limit
        if limit is None:
            return None

        passes_made: Any = None
        for key in ("passes_made", "stock_passes", "pass_count"):
            passes_made = _get_value(state, key)
            if passes_made is not None:
                break
        count = _coerce_non_negative_int(passes_made)
        remaining = limit - count
        return remaining if remaining > 0 else 0

    def is_move_legal(self, state: Any, move: Any) -> bool:
        """Determine whether *move* is allowed within *state* for this profile."""
        action = _get_value(move, "type") or _get_value(move, "action")
        if not action:
            raise ValueError("Move must define a 'type' or 'action' attribute")
        action = action.lower()

        # Enforce draw size.
        requested_draw = _get_value(move, "draw_count")
        if requested_draw is not None and requested_draw != self.draw:
            return False

        if action == "draw":
            return requested_draw in (None, self.draw)

        if action == "stock_pass":
            limit = self.pass_limit
            if limit is None:
                return True
            passes_made = _get_value(state, "passes_made", 0)
            return passes_made < limit

        if action == "supermove":
            move_strength = SUPERMOVE_STRENGTH.get(
                (_get_value(move, "mode") or _get_value(move, "strength") or "standard").lower(),
                1,
            )
            allowed_strength = SUPERMOVE_STRENGTH.get(self.supermove.lower(), 0)
            return move_strength <= allowed_strength

        if action == "foundation_to_tableau":
            return self.foundation_takeback

        if action == "peek":
            return self.peek_xray

        if action == "autoplay":
            if not self.autoplay_safe_only:
                return True
            return bool(_get_value(move, "is_safe", False))

        if action == "undo":
            if self.undo_unlimited:
                return True
            remaining = _get_value(state, "undo_remaining")
            if remaining is None:
                remaining = max(0, 1 - _get_value(state, "undo_used", 0))
            return remaining > 0

        # Default to legal for unrecognised move types.
        return True


MAX_RELAX = RuleProfile(
    draw=1,
    passes="unlimited",
    supermove="relaxed",
    foundation_takeback=True,
    peek_xray=True,
    autoplay_safe_only=False,
    undo_unlimited=True,
)

FRIENDLY_APP = RuleProfile(
    draw=1,
    passes="unlimited",
    supermove="standard",
    foundation_takeback=True,
    peek_xray=False,
    autoplay_safe_only=False,
    undo_unlimited=True,
)

STANDARD = RuleProfile(
    draw=3,
    passes="three",
    supermove="standard",
    foundation_takeback=False,
    peek_xray=False,
    autoplay_safe_only=True,
    undo_unlimited=False,
)

XRAY = RuleProfile(
    draw=3,
    passes="three",
    supermove="standard",
    foundation_takeback=False,
    peek_xray=True,
    autoplay_safe_only=True,
    undo_unlimited=False,
)

__all__ = [
    "RuleProfile",
    "MAX_RELAX",
    "FRIENDLY_APP",
    "STANDARD",
    "XRAY",
]
