"""Tests for Cross-Modal Entropy Resonance (CMER) — Patent Claim 4."""

from __future__ import annotations

import math

from hashen.analytics.resonance import cross_modal_resonance


def test_identical_h1_arrays_high_resonance():
    """Two identical H1 arrays → resonance ≈ 1.0."""
    h1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = cross_modal_resonance({"a": h1, "b": h1}, {})
    assert result["resonance"] > 0.95


def test_uncorrelated_h1_arrays_low_resonance():
    """Two uncorrelated arrays → resonance near 0 (mean |r| well below 1)."""
    a = [math.sin(i) for i in range(50)]
    b = [math.cos(i * 7.3) for i in range(50)]
    result = cross_modal_resonance({"a": a, "b": b}, {})
    assert result["resonance"] < 0.5


def test_single_modality_zero_resonance():
    """Single modality → resonance = 0.0."""
    result = cross_modal_resonance({"only": [1.0, 2.0, 3.0]}, {})
    assert result["resonance"] == 0.0
    assert result["modality_count"] == 1


def test_three_modalities_three_pairs():
    """Three modalities → 3 correlation pairs computed."""
    result = cross_modal_resonance(
        {
            "a": [1.0, 2.0, 3.0],
            "b": [1.0, 2.0, 3.0],
            "c": [3.0, 2.0, 1.0],
        },
        {},
    )
    assert len(result["pairs"]) == 3
    assert result["modality_count"] == 3


def test_deterministic():
    """Same inputs → same resonance."""
    h1_a = [0.5, 1.5, 2.5, 3.5]
    h1_b = [0.6, 1.4, 2.6, 3.4]
    r1 = cross_modal_resonance({"x": h1_a, "y": h1_b}, {})
    r2 = cross_modal_resonance({"x": h1_a, "y": h1_b}, {})
    assert r1 == r2


def test_empty_modality_array():
    """Empty H1 array in one modality → resonance = 0.0."""
    result = cross_modal_resonance({"a": [], "b": [1.0, 2.0]}, {})
    assert result["resonance"] == 0.0


def test_different_length_arrays_padded():
    """Different length arrays are padded to max length."""
    result = cross_modal_resonance(
        {
            "short": [1.0, 2.0],
            "long": [1.0, 2.0, 3.0, 4.0, 5.0],
        },
        {},
    )
    assert "short:long" in result["pairs"] or "long:short" in result["pairs"]
