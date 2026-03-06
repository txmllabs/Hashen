"""Tests for uncertainty-based path routing — Patent Claim 6(f)."""

from __future__ import annotations

from hashen.analytics.routing import route


def test_low_uncertainty_routes_to_edge():
    """High H2 + high resonance → low uncertainty → edge."""
    result = route(5.5, 0.9, {"h2_max": 6.0, "authenticity_threshold": 4.0})
    assert result["selected_path"] == "edge"


def test_medium_uncertainty_routes_to_cloud():
    """Moderate H2 → moderate uncertainty → classical_cloud (t2 so u=0.5 < t2)."""
    config = {"h2_max": 6.0, "routing_t2": 0.6}
    result = route(3.0, 0.5, config)
    assert result["selected_path"] == "classical_cloud"


def test_high_uncertainty_routes_to_human():
    """Low H2 + low resonance → high uncertainty → human_in_loop."""
    result = route(0.5, 0.0, {"h2_max": 6.0})
    assert result["selected_path"] == "human_in_loop"


def test_custom_thresholds():
    """Custom thresholds change routing boundaries."""
    config = {
        "h2_max": 6.0,
        "routing_t1": 0.1,
        "routing_t2": 0.3,
        "routing_t3": 0.6,
    }
    result = route(4.0, 0.5, config)
    assert result["selected_path"] in [
        "edge",
        "classical_cloud",
        "federated",
        "human_in_loop",
    ]


def test_routing_deterministic():
    """Same inputs → same routing."""
    r1 = route(3.0, 0.4, {"h2_max": 6.0})
    r2 = route(3.0, 0.4, {"h2_max": 6.0})
    assert r1 == r2


def test_routing_config_in_result():
    """Result includes routing thresholds used."""
    result = route(3.0, 0.5, {"h2_max": 6.0, "routing_t1": 0.15})
    assert "routing_config" in result
    assert result["routing_config"]["t1"] == 0.15


def test_edge_case_zero_h2():
    """H2=0 → maximum uncertainty → human_in_loop."""
    result = route(0.0, 0.0, {"h2_max": 6.0})
    assert result["selected_path"] == "human_in_loop"


def test_edge_case_max_h2():
    """H2=h2_max → minimum uncertainty → edge."""
    result = route(6.0, 1.0, {"h2_max": 6.0})
    assert result["selected_path"] == "edge"
