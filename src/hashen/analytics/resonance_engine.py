"""Resonance engine: optional scalar for seal."""

from __future__ import annotations

from typing import Any


def compute_resonance(values: list[float], config: dict[str, Any]) -> float:
    """Optional resonance scalar (deterministic from values + config)."""
    if not values:
        return 0.0
    # Simple deterministic: normalized variance-like measure
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    scale = config.get("resonance_scale", 1.0)
    return min(1.0, (var**0.5) * scale) if scale else 0.0
