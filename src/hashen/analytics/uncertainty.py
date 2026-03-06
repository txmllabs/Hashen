"""Uncertainty metrics for compliance/reporting."""

from __future__ import annotations


def uncertainty_score(values: list[float]) -> float:
    """Deterministic uncertainty score (e.g. inverse of confidence)."""
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return (variance**0.5) / (abs(mean) + 1e-9)
