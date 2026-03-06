"""Entropy engine: H1 (raw/subset) and H2 with fixed preconfigured range (no auto-ranging)."""

from __future__ import annotations

import math
from typing import Any

# Fixed range for H2 is from config_vector; no per-sample auto-ranging (spec A.3)


def extract_h1_subset(
    values: list[float],
    config: dict[str, Any],
) -> list[float]:
    """Extract H1 subset: optionally limit indices or take full vector per config."""
    subset_size = config.get("h1_subset_size")
    if subset_size is not None and subset_size >= 0:
        step = max(1, len(values) // subset_size) if values else 1
        return [values[i] for i in range(0, len(values), step)][:subset_size]
    return list(values)


def entropy_h2(
    values: list[float],
    config: dict[str, Any],
) -> float:
    """
    H2 entropy over values using fixed preconfigured range (min_val, max_val).
    No auto-ranging: range comes from config_vector only.
    """
    if not values:
        return 0.0
    min_val = config.get("h2_min")
    max_val = config.get("h2_max")
    if min_val is None:
        min_val = 0.0
    if max_val is None:
        max_val = 1.0
    if max_val <= min_val:
        max_val = min_val + 1.0
    # Bin counts in fixed range (e.g. 16 bins)
    num_bins = max(2, config.get("h2_bins", 16))
    bins = [0.0] * num_bins
    width = (max_val - min_val) / num_bins
    for v in values:
        idx = int((v - min_val) / width)
        idx = max(0, min(num_bins - 1, idx))
        bins[idx] += 1
    n = len(values)
    ent = 0.0
    for c in bins:
        if c > 0:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def combined_h2(per_modality_h2: list[float], config: dict[str, Any]) -> float:
    """Combine per-modality H2 (e.g. mean)."""
    if not per_modality_h2:
        return 0.0
    return sum(per_modality_h2) / len(per_modality_h2)
