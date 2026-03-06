"""Benchmark runner: TSEC on synthetic datasets → AUC/accuracy reports."""

from __future__ import annotations

import math
from typing import Any

from hashen.analytics.tsec import compute_h1_windows, compute_h2_fixed_range


def run_benchmark(
    dataset: dict[str, list[list[float]]],
    config: dict[str, Any] | None = None,
    domain: str = "generic",
) -> dict[str, Any]:
    """
    Run TSEC on {"authentic": [...], "attack": [...]}.

    Each item is list[float] (values to window) or, if pre_computed_h1=True, H1 values.
    Returns structured benchmark report.
    """
    if config is None:
        config = {
            "window_size": 512,
            "h1_bins": 64,
            "h2_min": 0.0,
            "h2_max": 6.0,
            "h2_bins": 64,
        }

    ws = config.get("window_size", 512)
    h1_bins = config.get("h1_bins", 64)
    h2_min = config.get("h2_min", 0.0)
    h2_max = config.get("h2_max", 6.0)
    h2_bins = config.get("h2_bins", 64)
    pre_h1 = config.get("pre_computed_h1", False)

    auth_h2 = []
    for values in dataset["authentic"]:
        if pre_h1:
            h2 = compute_h2_fixed_range(values, h2_min, h2_max, h2_bins)
        else:
            h1 = compute_h1_windows(values, ws, ws // 2, h1_bins)
            h2 = compute_h2_fixed_range(h1, h2_min, h2_max, h2_bins)
        auth_h2.append(h2)

    attack_h2 = []
    for values in dataset["attack"]:
        if pre_h1:
            h2 = compute_h2_fixed_range(values, h2_min, h2_max, h2_bins)
        else:
            h1 = compute_h1_windows(values, ws, ws // 2, h1_bins)
            h2 = compute_h2_fixed_range(h1, h2_min, h2_max, h2_bins)
        attack_h2.append(h2)

    def mean(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    def std(lst: list[float]) -> float:
        if len(lst) < 2:
            return 0.0
        m = mean(lst)
        return math.sqrt(sum((x - m) ** 2 for x in lst) / (len(lst) - 1))

    auth_mean, auth_std = mean(auth_h2), std(auth_h2)
    att_mean, att_std = mean(attack_h2), std(attack_h2)

    pooled = math.sqrt((auth_std**2 + att_std**2) / 2) + 1e-10
    cohens_d = abs(auth_mean - att_mean) / pooled

    count = 0
    total = 0
    for a in auth_h2:
        for b in attack_h2:
            total += 1
            if a > b:
                count += 1
            elif a == b:
                count += 0.5
    auc = count / total if total > 0 else 0.5
    if auth_mean < att_mean:
        auc = 1 - auc

    all_vals = auth_h2 + attack_h2
    best_acc, best_thresh = 0.0, 0.0
    for t_idx in range(200):
        t = min(all_vals) + (max(all_vals) - min(all_vals)) * t_idx / 199 if all_vals else 0.0
        if auth_mean > att_mean:
            tp = sum(1 for a in auth_h2 if a > t)
            tn = sum(1 for b in attack_h2 if b <= t)
        else:
            tp = sum(1 for a in auth_h2 if a < t)
            tn = sum(1 for b in attack_h2 if b >= t)
        acc = (tp + tn) / (len(auth_h2) + len(attack_h2))
        if acc > best_acc:
            best_acc, best_thresh = acc, t

    return {
        "domain": domain,
        "n_authentic": len(auth_h2),
        "n_attack": len(attack_h2),
        "auth_h2_mean": round(auth_mean, 4),
        "auth_h2_std": round(auth_std, 4),
        "attack_h2_mean": round(att_mean, 4),
        "attack_h2_std": round(att_std, 4),
        "cohens_d": round(cohens_d, 2),
        "auc": round(max(auc, 1 - auc), 3),
        "best_accuracy": round(best_acc, 3),
        "best_threshold": round(best_thresh, 4),
        "signal": "normal" if auth_mean > att_mean else "inverted",
        "config": config,
    }
