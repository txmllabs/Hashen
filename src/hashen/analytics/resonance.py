"""
Cross-Modal Entropy Resonance (CMER) — Patent Claim 4, P6 Component 150.

Computes correlation matrix across H1 arrays from different modalities.
Mean absolute upper-triangular correlation = resonance score.
Pure Python only (no numpy).
"""

from __future__ import annotations

import math
from typing import Any


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _pearson(a: list[float], b: list[float]) -> float:
    """Pearson correlation between two equal-length lists. Truncate to min length."""
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a_sub = a[:n]
    b_sub = b[:n]
    ma, mb = _mean(a_sub), _mean(b_sub)
    sa, sb = _std(a_sub), _std(b_sub)
    if sa < 1e-10 or sb < 1e-10:
        return 0.0
    cov = sum((a_sub[i] - ma) * (b_sub[i] - mb) for i in range(n)) / (n - 1)
    return cov / (sa * sb)


def cross_modal_resonance(
    modality_h1_arrays: dict[str, list[float]],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    CMER: correlation matrix across H1 arrays from different modalities.

    Patent Claim 4: construct correlation matrix, compute mean absolute
    upper-triangular correlation as resonance score.

    If < 2 modalities: return resonance 0.0. Single modality runs have
    no cross-modal data. Pads shorter arrays to max length (edge-value).
    Returns resonance score and per-pair correlations.
    """
    del config  # reserved for future use
    names = sorted(modality_h1_arrays.keys())
    if len(names) < 2:
        return {
            "resonance": 0.0,
            "pairs": {},
            "modality_count": len(names),
        }
    if any(not modality_h1_arrays[n] for n in names):
        return {
            "resonance": 0.0,
            "pairs": {},
            "modality_count": len(names),
        }
    max_len = max(len(modality_h1_arrays[n]) for n in names)
    if max_len < 2:
        return {
            "resonance": 0.0,
            "pairs": {},
            "modality_count": len(names),
        }
    padded: dict[str, list[float]] = {}
    for name in names:
        arr = modality_h1_arrays[name]
        if len(arr) < max_len:
            if arr:
                arr = arr + [arr[-1]] * (max_len - len(arr))
            else:
                arr = [0.0] * max_len
        padded[name] = arr[:max_len]

    pairs: dict[str, float] = {}
    abs_corrs: list[float] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            r = _pearson(padded[names[i]], padded[names[j]])
            pair_key = f"{names[i]}:{names[j]}"
            pairs[pair_key] = r
            abs_corrs.append(abs(r))

    resonance = _mean(abs_corrs) if abs_corrs else 0.0
    return {
        "resonance": resonance,
        "pairs": pairs,
        "modality_count": len(names),
    }
