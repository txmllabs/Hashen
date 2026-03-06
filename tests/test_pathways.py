"""Tests for modality pathways (Patent Claim 2, P6 130a-d)."""

from __future__ import annotations

from hashen.analytics.pathways.audio import audio_to_spectral_h1
from hashen.analytics.pathways.graph import graph_degrees_to_values, graph_from_bytes
from hashen.analytics.pathways.image import image_to_values
from hashen.analytics.pathways.text import text_to_values
from hashen.analytics.pathways.timeseries import timeseries_to_values
from hashen.analytics.tsec import tsec_cascade


def test_image_to_values_in_range():
    """Image pathway produces list[float] in [0, 1]."""
    raw = bytes(range(256))
    out = image_to_values(raw)
    assert isinstance(out, list)
    assert all(0 <= v <= 1 for v in out)
    assert len(out) == 256


def test_audio_to_spectral_h1_produces_h1_per_frame():
    """Audio pathway produces one H1 per STFT frame."""
    samples = [0.1 * (i % 10) for i in range(2048)]
    h1 = audio_to_spectral_h1(samples, window_size=512, hop_length=256)
    assert isinstance(h1, list)
    assert all(x >= 0 for x in h1)
    assert len(h1) > 0


def test_timeseries_to_values_in_range():
    """Timeseries pathway produces normalized [0, 1] values."""
    readings = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = timeseries_to_values(readings)
    assert out == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert timeseries_to_values([]) == []


def test_graph_degrees_to_values_empty():
    """Graph pathway handles empty edge list."""
    out = graph_degrees_to_values([])
    assert out == []


def test_graph_degrees_to_values_normalized():
    """Graph pathway returns normalized degree values."""
    edges = [("a", "b"), ("b", "c"), ("a", "c")]
    out = graph_degrees_to_values(edges)
    assert isinstance(out, list)
    assert all(0 <= v <= 1 for v in out)
    assert len(out) == 3


def test_text_to_values_in_range():
    """Text pathway produces [0, 1] character ordinals."""
    out = text_to_values("Hello")
    assert isinstance(out, list)
    assert all(0 <= v <= 1 for v in out)
    assert len(out) == 5


def test_graph_from_bytes_json():
    """graph_from_bytes parses JSON edge list and returns normalized degree values."""
    import json

    edges = [["a", "b"], ["b", "c"], ["c", "a"], ["a", "d"]]
    data = json.dumps(edges).encode()
    values = graph_from_bytes(data)
    assert len(values) > 0
    assert all(0.0 <= v <= 1.0 for v in values)


def test_graph_from_bytes_fallback():
    """Non-JSON bytes fall back to raw values."""
    values = graph_from_bytes(b"\x00\x80\xff")
    assert len(values) == 3


def test_pathway_output_feeds_tsec():
    """Each pathway output feeds into tsec_cascade without error."""
    config = {"window_size": 64, "step_size": 32, "h1_bins": 32, "h2_bins": 16}
    values_img = image_to_values(bytes(500))
    result = tsec_cascade(values_img, config)
    assert "h2" in result
    assert "h1_array" in result

    values_ts = timeseries_to_values([float(i) for i in range(200)])
    result2 = tsec_cascade(values_ts, config)
    assert result2["h2"] >= 0

    values_txt = text_to_values("x" * 200)
    result3 = tsec_cascade(values_txt, config)
    assert result3["h2"] >= 0
