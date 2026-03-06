"""Clock abstraction for deterministic tests and production timestamps."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Optional

# Optional override for tests
_get_time: Callable[[], float] = time.time


def utc_iso_now(clock: Optional[Callable[[], str]] = None) -> str:
    """Current UTC time as ISO 8601 string. If clock is provided (e.g. for tests), use it."""
    if clock is not None:
        return clock()
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def set_clock(fn: Callable[[], float]) -> None:
    """Set time source (for tests)."""
    global _get_time
    _get_time = fn


def get_time() -> float:
    """Current time as float (for duration/timeout)."""
    return _get_time()
