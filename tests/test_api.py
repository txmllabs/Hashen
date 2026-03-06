"""Tests for FastAPI API (run only when fastapi is installed)."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from hashen.api.app import app

client = TestClient(app)


def test_health():
    """GET /api/v1/health returns status ok."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_config():
    """GET /api/v1/config returns supported_modalities and default_config."""
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    assert "raw" in r.json()["supported_modalities"]


def test_analyze_raw():
    """POST /api/v1/analyze with raw artifact returns seal_hash, h2, routing_path."""
    r = client.post(
        "/api/v1/analyze",
        files={"artifact": ("test.bin", b"hello world" * 100)},
    )
    assert r.status_code == 200
    data = r.json()
    assert "seal_hash" in data
    assert "h2" in data
    assert isinstance(data["is_authentic"], bool)
    assert data["routing_path"][0] in [
        "edge",
        "classical_cloud",
        "federated",
        "human_in_loop",
    ]


def test_analyze_with_config():
    """POST /api/v1/analyze with custom config and modality."""
    config = json.dumps(
        {"use_tsec": True, "window_size": 64, "h1_bins": 16, "h2_max": 4.0}
    )
    r = client.post(
        "/api/v1/analyze",
        files={"artifact": ("test.bin", b"custom config test" * 50)},
        data={"config": config, "modality": "raw"},
    )
    assert r.status_code == 200


def test_verify_ok():
    """Analyze then verify with same artifact → ok True."""
    r1 = client.post(
        "/api/v1/analyze",
        files={"artifact": ("test.bin", b"verify me" * 100)},
    )
    assert r1.status_code == 200
    data = r1.json()
    seal_record = data.get("seal_record") or data
    r2 = client.post(
        "/api/v1/verify",
        files={"artifact": ("test.bin", b"verify me" * 100)},
        data={"seal": json.dumps(seal_record)},
    )
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_verify_tampered():
    """Tampered artifact → verification fails."""
    r1 = client.post(
        "/api/v1/analyze",
        files={"artifact": ("test.bin", b"original content" * 100)},
    )
    assert r1.status_code == 200
    data = r1.json()
    seal_record = data.get("seal_record") or data
    r2 = client.post(
        "/api/v1/verify",
        files={"artifact": ("test.bin", b"TAMPERED content!" * 100)},
        data={"seal": json.dumps(seal_record)},
    )
    assert r2.status_code == 200
    assert r2.json()["ok"] is False


def test_analyze_empty_artifact():
    """Empty artifact returns 400."""
    r = client.post(
        "/api/v1/analyze",
        files={"artifact": ("empty.bin", b"")},
    )
    assert r.status_code == 400
