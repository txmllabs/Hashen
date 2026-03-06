"""
Uncertainty-Based Path Selector — Patent Claim 6(f), P6 Component 160.

Routes processing based on entropy-derived uncertainty:
  uncertainty < T1 → edge
  T1 ≤ uncertainty < T2 → classical_cloud
  T2 ≤ uncertainty < T3 → federated
  uncertainty ≥ T3 → human_in_loop
"""

from __future__ import annotations

from typing import Any

DEFAULT_THRESHOLDS = {
    "t1": 0.2,
    "t2": 0.5,
    "t3": 0.8,
}


def compute_uncertainty(
    h2: float,
    resonance: float,
    config: dict[str, Any],
) -> float:
    """
    Derive uncertainty metric from H2 and resonance.

    Patent Claim 6(f): weighted combination of H2 distance from threshold
    and resonance factor. High H2 + high resonance → low uncertainty.
    """
    h2_max = config.get("h2_max", 6.0)
    h2_normalized = min(h2 / (h2_max + 1e-9), 1.0)
    h2_distance = 1.0 - h2_normalized
    resonance_factor = 1.0 - min(resonance, 1.0)
    w_h2 = config.get("uncertainty_weight_h2", 0.7)
    w_res = config.get("uncertainty_weight_resonance", 0.3)
    return w_h2 * h2_distance + w_res * resonance_factor


def select_path(uncertainty: float, config: dict[str, Any]) -> str:
    """Select processing pathway based on uncertainty thresholds."""
    t1 = config.get("routing_t1", DEFAULT_THRESHOLDS["t1"])
    t2 = config.get("routing_t2", DEFAULT_THRESHOLDS["t2"])
    t3 = config.get("routing_t3", DEFAULT_THRESHOLDS["t3"])
    if uncertainty < t1:
        return "edge"
    if uncertainty < t2:
        return "classical_cloud"
    if uncertainty < t3:
        return "federated"
    return "human_in_loop"


def route(
    h2: float,
    resonance: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute uncertainty → select path; return full routing result."""
    uncertainty = compute_uncertainty(h2, resonance, config)
    selected = select_path(uncertainty, config)
    return {
        "uncertainty": uncertainty,
        "selected_path": selected,
        "routing_config": {
            "t1": config.get("routing_t1", DEFAULT_THRESHOLDS["t1"]),
            "t2": config.get("routing_t2", DEFAULT_THRESHOLDS["t2"]),
            "t3": config.get("routing_t3", DEFAULT_THRESHOLDS["t3"]),
        },
    }
