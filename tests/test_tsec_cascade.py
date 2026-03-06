"""Tests for Two-Stage Entropy Cascade (TSEC) — Patent Claims 1-5."""

from __future__ import annotations

from hashen.analytics.tsec import (
    compute_h1_windows,
    compute_h2_fixed_range,
    tsec_cascade,
)


def test_two_stage_produces_h1_array():
    """H1 array length = expected window count."""
    values = [0.1 * (i % 10) for i in range(1000)]
    window_size = 100
    step_size = 50
    h1 = compute_h1_windows(values, window_size=window_size, step_size=step_size)
    # (1000 - 100) / 50 + 1 = 19
    expected_count = (len(values) - window_size) // step_size + 1
    assert len(h1) == expected_count
    assert all(x >= 0 for x in h1)


def test_fixed_range_deterministic():
    """Same values + config → same H2."""
    values = [0.5 + 0.3 * (i % 7) / 7 for i in range(600)]
    h1_a = compute_h1_windows(values, 128, 64, 32)
    h1_b = compute_h1_windows(values, 128, 64, 32)
    assert h1_a == h1_b
    h2_a = compute_h2_fixed_range(h1_a, 0.0, 5.0, 16)
    h2_b = compute_h2_fixed_range(h1_b, 0.0, 5.0, 16)
    assert h2_a == h2_b


def test_low_variance_input_low_h2():
    """Uniform values → low H2 (little variation in H1 across windows)."""
    values = [0.5] * 1000
    h1 = compute_h1_windows(values, window_size=100, step_size=50, n_bins=64)
    # All windows are constant → same H1 (min entropy) → histogram has one bin
    h2 = compute_h2_fixed_range(h1, 0.0, 6.0, 64)
    assert h2 >= 0
    assert h2 < 1.0  # single bin → zero entropy


def test_high_variance_input_high_h2():
    """Varied local statistics across windows → spread of H1 → non-zero H2."""
    # Two distinct regions so H1 differs across windows (low in flat, higher in ramp)
    values = [0.5] * 400 + [i / 399.0 for i in range(400)]
    h1 = compute_h1_windows(values, window_size=100, step_size=50, n_bins=64)
    h2 = compute_h2_fixed_range(h1, 0.0, 6.0, 64)
    assert h2 >= 0
    # We should have multiple distinct H1 values → H2 > 0
    assert h2 > 0.0


def test_fixed_range_prevents_inversion():
    """Uniform → single H1 bin → H2=0; mixed windows → spread of H1 → H2>0."""
    uniform = [0.5] * 800
    # Flat then alternating so H1 is 0 in flat windows and ~1 in alternating
    mixed = [0.0] * 600 + [0.0 if i % 2 == 0 else 1.0 for i in range(600)]
    h1_u = compute_h1_windows(uniform, 128, 64, 64)
    h1_v = compute_h1_windows(mixed, 128, 64, 64)
    h2_u = compute_h2_fixed_range(h1_u, 0.0, 6.0, 64)
    # Use smaller h2_max so H1=0 and H1~1 fall in different bins
    h2_v = compute_h2_fixed_range(h1_v, 0.0, 2.0, 8)
    assert h2_u == 0.0  # all same H1
    assert h2_v > 0.0  # distinct H1 values across windows


def test_config_vector_stored_in_result():
    """tsec_cascade result contains config_used."""
    values = [0.1 * (i % 10) for i in range(600)]
    config = {
        "window_size": 200,
        "step_size": 100,
        "h1_bins": 32,
        "h2_min": 0.0,
        "h2_max": 5.0,
        "h2_bins": 16,
        "authenticity_threshold": 4.0,
    }
    result = tsec_cascade(values, config)
    assert "config_used" in result
    assert result["config_used"]["window_size"] == 200
    assert result["config_used"]["h1_bins"] == 32
    assert result["h1_count"] == len(result["h1_array"])
    assert result["threshold"] == 4.0
    assert "is_authentic" in result


def test_tsec_cascade_h2_from_h1_not_raw():
    """H2 is computed from H1 array, not from raw values."""
    values = [0.5 + 0.1 * (i % 5) for i in range(600)]
    result = tsec_cascade(values, {"window_size": 128, "step_size": 64})
    assert "h1_array" in result
    assert "h2" in result
    assert result["h2"] >= 0
    # Same run through compute_h2_fixed_range on same h1_array should match
    h2_direct = compute_h2_fixed_range(
        result["h1_array"],
        result["config_used"]["h2_min"],
        result["config_used"]["h2_max"],
        result["config_used"]["h2_bins"],
    )
    assert h2_direct == result["h2"]


def test_use_tsec_in_pipeline_produces_valid_seal(tmp_path):
    """With use_tsec=True, pipeline produces seal that verifies (G14 backward compat)."""
    from hashen.analytics.tsec import compute_seal_analytics
    from hashen.provenance.seal import create_seal

    artifact = b"test artifact for tsec path"
    config = {
        "use_tsec": True,
        "window_size": 32,
        "step_size": 16,
        "h1_bins": 32,
        "h2_min": 0.0,
        "h2_max": 5.0,
        "h2_bins": 16,
        "h1_subset_size": 16,
    }
    analytics = compute_seal_analytics(artifact, config)
    assert "h1_array" not in analytics  # we return h1_subset
    assert len(analytics["h1_subset"]) <= 16
    assert analytics["h2"] >= 0
    full_record, epw_hash = create_seal(
        artifact, config, "a" * 64, resonance=analytics["resonance"]
    )
    assert full_record["epw_hash"] == epw_hash
    assert full_record["config_vector"].get("use_tsec") is True


def test_tsec_result_includes_routing():
    """TSEC cascade result includes routing path and uncertainty."""
    from hashen.analytics.tsec import compute_seal_analytics

    config = {
        "use_tsec": True,
        "h2_max": 6.0,
        "window_size": 10,
        "h1_bins": 8,
    }
    result = compute_seal_analytics(b"test artifact bytes" * 100, config)
    assert "routing_path" in result
    assert len(result["routing_path"]) > 0
    assert result["routing_path"][0] in [
        "edge",
        "classical_cloud",
        "federated",
        "human_in_loop",
    ]
    assert "uncertainty" in result


def test_empty_values_handled():
    """Empty or short values do not crash; return zeros or short array."""
    h1_empty = compute_h1_windows([], window_size=10, step_size=5)
    assert h1_empty == []
    h2_empty = compute_h2_fixed_range([], 0.0, 6.0, 16)
    assert h2_empty == 0.0
    h2_one = compute_h2_fixed_range([3.0], 0.0, 6.0, 16)
    assert h2_one == 0.0
    result = tsec_cascade([0.1, 0.2], {"window_size": 512})
    assert result["h1_count"] == 0
    assert result["h2"] == 0.0
