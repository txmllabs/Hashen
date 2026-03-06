"""Tests for benchmark harness (TSEC on synthetic datasets)."""

from __future__ import annotations

import pytest


def test_audio_benchmark_produces_report():
    """Audio dataset + run_benchmark produces report with auc, cohens_d."""
    from hashen.benchmarks.datasets import generate_audio_dataset
    from hashen.benchmarks.runner import run_benchmark

    ds = generate_audio_dataset(n_samples=10, seed=42)
    config = {
        "pre_computed_h1": True,
        "h2_min": 0,
        "h2_max": 6.0,
        "h2_bins": 32,
    }
    report = run_benchmark(ds, config=config, domain="audio")
    assert "auc" in report
    assert "cohens_d" in report
    assert report["n_authentic"] == 10
    assert report["n_attack"] == 10


def test_financial_benchmark():
    """Financial dataset benchmark returns auc >= 0.5."""
    from hashen.benchmarks.datasets import generate_financial_dataset
    from hashen.benchmarks.runner import run_benchmark

    ds = generate_financial_dataset(n_samples=5, seed=42)
    config = {
        "window_size": 200,
        "h1_bins": 32,
        "h2_min": 0,
        "h2_max": 5.0,
        "h2_bins": 32,
    }
    report = run_benchmark(ds, config=config, domain="financial")
    assert report["auc"] >= 0.5


def test_benchmark_deterministic():
    """Same seed and config → same benchmark result."""
    from hashen.benchmarks.datasets import generate_audio_dataset
    from hashen.benchmarks.runner import run_benchmark

    ds1 = generate_audio_dataset(10, 42)
    ds2 = generate_audio_dataset(10, 42)
    cfg = {"pre_computed_h1": True, "h2_max": 6.0, "h2_bins": 32}
    r1 = run_benchmark(ds1, cfg, "audio")
    r2 = run_benchmark(ds2, cfg, "audio")
    assert r1["auc"] == r2["auc"]
