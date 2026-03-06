"""Canonical JSON serialization for deterministic hashing (sorted keys, stable separators)."""

from __future__ import annotations

import json
from typing import Any


def canonical_dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize to canonical JSON: sorted keys, no extra whitespace, stable separators."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        **kwargs,
    )


def canonical_loads(s: str | bytes) -> Any:
    """Parse JSON (input may be from canonical_dumps)."""
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return json.loads(s)
