"""
Two-Stage Entropy Cascade (TSEC) — Patent Claims 1-5.

Stage 1: Segment digital signal → compute H1 per window (modality-specific).
Stage 2: Construct histogram over H1 array with FIXED range → compute H2.

The fixed range is preconfigured and NOT derived from the input data distribution.
This prevents histogram auto-scaling artifacts (Claim 3).
"""

from __future__ import annotations

import math
from typing import Any, Optional


def compute_h1_windows(
    values: list[float],
    window_size: int = 512,
    step_size: Optional[int] = None,
    n_bins: int = 64,
) -> list[float]:
    """
    Stage 1: Compute first-order Shannon entropy H1 for each window.

    Patent Claim 1(b-d):
    - Segment the digital signal into fixed-length windows (b)
    - Transform each window into a histogram-based probability distribution (c)
    - Compute H1 for each window (d)

    Returns ordered array of H1 values capturing local entropy variation.
    """
    if step_size is None:
        step_size = max(1, window_size // 2)  # 50% overlap default

    h1_values: list[float] = []
    for i in range(0, len(values) - window_size + 1, step_size):
        window = values[i : i + window_size]

        # Build histogram-based probability distribution
        hist = [0] * n_bins
        v_min = 0.0  # Normalized values are in [0, 1]
        v_max = 1.0
        bin_width = (v_max - v_min) / n_bins if n_bins else 1.0

        for v in window:
            idx = int((v - v_min) / bin_width)
            idx = max(0, min(n_bins - 1, idx))
            hist[idx] += 1

        # Compute Shannon entropy
        n = len(window)
        h1 = 0.0
        for count in hist:
            if count > 0:
                p = count / n
                h1 -= p * math.log2(p)

        h1_values.append(h1)

    return h1_values


def compute_h2_fixed_range(
    h1_values: list[float],
    h2_min: float = 0.0,
    h2_max: Optional[float] = None,
    h2_bins: int = 64,
) -> float:
    """
    Stage 2: Compute second-order meta-entropy H2 over H1 distribution.

    Patent Claim 1(e-f):
    - Construct histogram over H1 array using FIXED entropy range (e)
    - Compute H2 as Shannon entropy of that histogram (f)

    Fixed range: [h2_min, h2_max] where h2_max defaults to log2(n_bins from stage 1).
    This is preconfigured and independent of the input data distribution (Claim 3).
    """
    if not h1_values or len(h1_values) < 2:
        return 0.0

    if h2_max is None:
        h2_max = 6.0  # log2(64) — default for 64-bin H1 histograms

    if h2_max <= h2_min:
        h2_max = h2_min + 1.0

    effective_bins = min(h2_bins, max(2, len(h1_values) // 3))
    bin_width = (h2_max - h2_min) / effective_bins
    hist = [0] * effective_bins

    for h1 in h1_values:
        idx = int((h1 - h2_min) / bin_width)
        idx = max(0, min(effective_bins - 1, idx))
        hist[idx] += 1

    n = len(h1_values)
    h2 = 0.0
    for count in hist:
        if count > 0:
            p = count / n
            h2 -= p * math.log2(p)

    return h2


def tsec_cascade(
    values: list[float],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Full TSEC pipeline: values → H1 windows → fixed-range H2 → classification.

    config keys:
      window_size: int (default 512)
      step_size: int (default window_size // 2)
      h1_bins: int (default 64)
      h2_min: float (default 0.0)
      h2_max: float (default log2(h1_bins))
      h2_bins: int (default 64)
      authenticity_threshold: float (default 4.0)

    Returns dict with h1_array, h2, is_authentic, config used.
    """
    ws = config.get("window_size", 512)
    ss = config.get("step_size", ws // 2)
    h1_bins = config.get("h1_bins", 64)

    h1_array = compute_h1_windows(values, ws, ss, h1_bins)

    h2_min = config.get("h2_min", 0.0)
    h2_max = config.get("h2_max", math.log2(max(h1_bins, 1)))
    h2_bins_cfg = config.get("h2_bins", 64)

    h2 = compute_h2_fixed_range(h1_array, h2_min, h2_max, h2_bins_cfg)

    threshold = config.get("authenticity_threshold", 4.0)
    is_authentic = h2 > threshold

    return {
        "h1_array": h1_array,
        "h1_count": len(h1_array),
        "h2": h2,
        "is_authentic": is_authentic,
        "threshold": threshold,
        "config_used": {
            "window_size": ws,
            "step_size": ss,
            "h1_bins": h1_bins,
            "h2_min": h2_min,
            "h2_max": h2_max,
            "h2_bins": h2_bins_cfg,
        },
    }


def artifact_to_values_raw(artifact_bytes: bytes) -> list[float]:
    """Normalize raw artifact bytes to [0, 1] for TSEC or legacy path."""
    return [b / 255.0 for b in artifact_bytes]


def _values_from_modality(
    artifact_bytes: bytes,
    modality: str,
    config_vector: dict[str, Any],
) -> tuple[list[float], Optional[list[float]]]:
    """
    Dispatch by modality: return (values for cascade, optional precomputed H1 array).
    If H1 array is returned (e.g. audio), caller skips compute_h1_windows.
    """
    if modality in ("raw", "") or not modality:
        return artifact_to_values_raw(artifact_bytes), None
    if modality == "image":
        from hashen.analytics.pathways.image import image_to_values

        return image_to_values(artifact_bytes), None
    if modality == "audio":
        from hashen.analytics.pathways.audio import audio_to_spectral_h1

        samples = [b / 127.5 - 1.0 for b in artifact_bytes]
        h1_array = audio_to_spectral_h1(
            samples,
            window_size=config_vector.get("window_size", 1024),
            hop_length=config_vector.get("hop_length", 512),
            n_freq_bins=config_vector.get("n_freq_bins", 64),
        )
        return [], h1_array
    if modality == "text":
        from hashen.analytics.pathways.text import text_to_values

        text = artifact_bytes.decode("utf-8", errors="replace")
        return text_to_values(text), None
    if modality == "timeseries":
        from hashen.analytics.pathways.timeseries import timeseries_to_values

        readings = [b / 255.0 for b in artifact_bytes]
        return timeseries_to_values(readings), None
    if modality == "graph":
        from hashen.analytics.pathways.graph import graph_from_bytes

        values = graph_from_bytes(artifact_bytes)
        return values, None
    return artifact_to_values_raw(artifact_bytes), None


def _h1_array_for_modality(
    artifact_bytes: bytes,
    modality: str,
    config_vector: dict[str, Any],
) -> tuple[list[float], float]:
    """Get H1 array and H2 for one modality. Returns (h1_array, h2)."""
    values_from_pathway, pre_h1 = _values_from_modality(artifact_bytes, modality, config_vector)
    if pre_h1 is not None:
        h1_array = pre_h1
        h2 = compute_h2_fixed_range(
            h1_array,
            config_vector.get("h2_min", 0.0),
            config_vector.get("h2_max"),
            config_vector.get("h2_bins", 64),
        )
        return h1_array, h2
    if values_from_pathway:
        result = tsec_cascade(values_from_pathway, config_vector)
        return result["h1_array"], result["h2"]
    result = tsec_cascade(artifact_to_values_raw(artifact_bytes), config_vector)
    return result["h1_array"], result["h2"]


def compute_seal_analytics(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    compute_resonance_fn: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Single place for seal/orchestrator analytics: TSEC or legacy.

    When config has "use_tsec" true or "modality" set, runs two-stage cascade
    (or modality pathway) and returns h1_subset, h2, per_modality_h2, resonance,
    routing_path, uncertainty, routing_config. Otherwise uses legacy entropy_h2.
    """
    from hashen.analytics.entropy_engine import (
        combined_h2,
        entropy_h2,
        extract_h1_subset,
    )
    from hashen.analytics.resonance import cross_modal_resonance
    from hashen.analytics.resonance_engine import compute_resonance
    from hashen.analytics.routing import route

    modality = config_vector.get("modality") or "raw"
    use_tsec = config_vector.get("use_tsec") is True or modality not in (
        "raw",
        "",
    )
    values = artifact_to_values_raw(artifact_bytes)
    resonance_fn = compute_resonance_fn or compute_resonance

    if use_tsec:
        modalities_list = config_vector.get("modalities")
        if modalities_list and len(modalities_list) >= 2:
            modality_h1_arrays: dict[str, list[float]] = {}
            per_modality_h2_list: list[float] = []
            for mod_cfg in modalities_list:
                mod_name = mod_cfg.get("modality", "raw") or "raw"
                h1_arr, h2_m = _h1_array_for_modality(artifact_bytes, mod_name, config_vector)
                modality_h1_arrays[mod_name] = h1_arr
                per_modality_h2_list.append(h2_m)
            cmer_result = cross_modal_resonance(modality_h1_arrays, config_vector)
            resonance = cmer_result["resonance"]
            per_modality_h2 = per_modality_h2_list
            h2 = combined_h2(per_modality_h2, config_vector)
            h1_array = modality_h1_arrays[modalities_list[0].get("modality", "raw") or "raw"]
        else:
            pre_h1: Optional[list[float]] = None
            values_from_pathway, pre_h1 = _values_from_modality(
                artifact_bytes, modality, config_vector
            )
            if pre_h1 is not None:
                h1_array = pre_h1
                h2 = compute_h2_fixed_range(
                    h1_array,
                    config_vector.get("h2_min", 0.0),
                    config_vector.get("h2_max"),
                    config_vector.get("h2_bins", 64),
                )
            elif values_from_pathway:
                result = tsec_cascade(values_from_pathway, config_vector)
                h1_array = result["h1_array"]
                h2 = result["h2"]
            else:
                result = tsec_cascade(values, config_vector)
                h1_array = result["h1_array"]
                h2 = result["h2"]
            per_modality_h2 = [h2]
            resonance = 0.0
        h1_subset = extract_h1_subset(h1_array, config_vector)
    else:
        h1_subset = extract_h1_subset(values, config_vector)
        h2 = entropy_h2(values, config_vector)
        per_modality_h2 = [h2]
        resonance = resonance_fn(values, config_vector)

    comb_h2 = combined_h2(per_modality_h2, config_vector)
    routing_result = route(h2, resonance, config_vector)

    return {
        "h1_subset": h1_subset,
        "h2": h2,
        "per_modality_h2": per_modality_h2,
        "combined_h2": comb_h2,
        "resonance": resonance,
        "values": values,
        "routing_path": [routing_result["selected_path"]],
        "uncertainty": routing_result["uncertainty"],
        "routing_config": routing_result["routing_config"],
    }
