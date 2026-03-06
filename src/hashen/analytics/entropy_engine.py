"""
Entropy engine: H1 (raw/subset) and H2 with fixed preconfigured range.

H2 histogram range is taken only from config_vector (h2_min, h2_max, h2_bins).
It is preconfigured and not adapted per sample—no auto-ranging from sample min/max.
This avoids histogram auto-scaling artifacts and keeps verification deterministic.
"""

from __future__ import annotations

import math
from typing import Any

# Default H2 range when not in config; caller should set explicitly for reproducibility
DEFAULT_H2_MIN = 0.0
DEFAULT_H2_MAX = 1.0
DEFAULT_H2_BINS = 16


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
    Range is from config_vector only—preconfigured, not adapted per sample.
    Values outside [min_val, max_val] are clamped into the bin range.
    """
    if not values:
        return 0.0
    min_val = config.get("h2_min")
    max_val = config.get("h2_max")
    if min_val is None:
        min_val = DEFAULT_H2_MIN
    if max_val is None:
        max_val = DEFAULT_H2_MAX
    if max_val <= min_val:
        max_val = min_val + 1.0
    num_bins = max(2, config.get("h2_bins", DEFAULT_H2_BINS))
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
