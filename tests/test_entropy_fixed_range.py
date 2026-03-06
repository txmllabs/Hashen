"""Tests for fixed entropy range: preconfigured, not per-sample auto-ranged."""

from __future__ import annotations

import pytest

from hashen.analytics.entropy_engine import entropy_h2, extract_h1_subset


@pytest.fixture
def fixed_config():
    """Config with explicit fixed range (no auto-ranging)."""
    return {
        "h2_min": 0.0,
        "h2_max": 4.0,
        "h2_bins": 16,
        "h1_subset_size": 32,
    }


def test_identical_data_same_config_stable_entropy(fixed_config):
    """Identical data under fixed range yields same H2 every time."""
    values = [0.1, 0.2, 0.3] * 20
    a = entropy_h2(values, fixed_config)
    b = entropy_h2(values, fixed_config)
    assert a == b
    assert a >= 0


def test_same_config_different_calls_deterministic(fixed_config):
    """Same artifact (as values) and same config -> same H2; no per-sample adaptation."""
    low_variance = [0.5] * 100  # all values in one bin
    h2_low = entropy_h2(low_variance, fixed_config)
    assert h2_low == 0.0  # single bin has zero entropy
    # Same config, different data still uses same range
    other = [0.5, 0.6, 0.7] * 33
    h2_other = entropy_h2(other, fixed_config)
    assert h2_other >= 0
    # Determinism: same input same output
    assert entropy_h2(other, fixed_config) == h2_other


def test_low_variance_data_no_autorange(fixed_config):
    """Low-variance data does not trigger any auto-range; range comes only from config."""
    # Data that would "want" a narrow range if we auto-ranged; we do not.
    narrow = [0.123] * 50
    h2 = entropy_h2(narrow, fixed_config)
    assert h2 == 0.0
    # Range is still fixed_config; values outside range are clamped
    below_range = [-1.0] * 20 + [0.0] * 20
    h2_below = entropy_h2(below_range, fixed_config)
    assert h2_below >= 0
    # Same config with only min/max from config
    config_minimal = {"h2_min": 0.0, "h2_max": 1.0}
    assert entropy_h2([0.5, 0.5], config_minimal) == 0.0


def test_defaults_used_when_config_omits_range():
    """When h2_min/h2_max omitted, defaults are used (still no sample-derived range)."""
    config = {}
    values = [0.25, 0.75]
    h2 = entropy_h2(values, config)
    assert h2 >= 0
    assert entropy_h2([0.5], {}) == 0.0


def test_extract_h1_subset_uses_config_only():
    """H1 subset size from config only; no per-sample auto-sizing."""
    config = {"h1_subset_size": 4}
    values = list(range(100))
    subset = extract_h1_subset(values, config)
    assert len(subset) == 4
    subset2 = extract_h1_subset(values, config)
    assert subset == subset2
