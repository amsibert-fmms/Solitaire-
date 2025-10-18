"""Rules engine for solitaire solver profiles."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping, MutableMapping
import json


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


@dataclass(frozen=True)
class RuleProfile:
    """A configurable rules profile for the solitaire engine."""

    draw: int
    passes: str
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
            limit = PASS_LIMITS.get(self.passes.lower(), None)
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
