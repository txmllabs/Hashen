"""Time-series pathway: sliding window value distributions → values for TSEC (130c)."""

from __future__ import annotations


def timeseries_to_values(readings: list[float]) -> list[float]:
    """
    Normalize time-series readings to [0, 1] range for TSEC windowing.

    The TSEC cascade handles the actual H1 computation per window.
    """
    if not readings:
        return []
    v_min = min(readings)
    v_max = max(readings)
    spread = v_max - v_min if v_max > v_min else 1.0
    return [(r - v_min) / spread for r in readings]
