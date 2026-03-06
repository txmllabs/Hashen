"""Tests for Seal (EPW) determinism and tamper-evidence (G1, G2)."""

from __future__ import annotations

import pytest

from hashen.provenance.seal import (
    create_seal,
    verify_seal,
    verify_seal_file,
    write_seal,
)
from hashen.utils.hashing import sha256_bytes


@pytest.fixture
def config_vector():
    return {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}


def test_seal_determinism_G1(config_vector):
    """G1: Same artifact + same config -> same seal hash."""
    artifact = b"same bytes for reproducibility"
    audit_head = "a" * 64
    _, epw1 = create_seal(artifact, config_vector, audit_head)
    _, epw2 = create_seal(artifact, config_vector, audit_head)
    assert epw1 == epw2


def test_tamper_fails_G2(config_vector):
    """G2: Modify artifact bytes -> verify returns ok=False, reason=EPW_MISMATCH."""
    artifact = b"original content"
    audit_head = "b" * 64
    full_record, _ = create_seal(artifact, config_vector, audit_head)
    tampered = b"tampered content"
    ok, reason = verify_seal(tampered, full_record)
    assert ok is False
    assert reason == "EPW_MISMATCH"


def test_verify_ok_unchanged(config_vector):
    """Unchanged artifact verifies ok."""
    artifact = b"unchanged"
    audit_head = "c" * 64
    full_record, _ = create_seal(artifact, config_vector, audit_head)
    ok, reason = verify_seal(artifact, full_record)
    assert ok is True
    assert reason is None


def test_verify_config_vector_missing():
    """Missing config_vector in seal -> CONFIG_VECTOR_MISSING."""
    ok, reason = verify_seal(b"x", {"epw_hash": "y"})
    assert ok is False
    assert reason == "CONFIG_VECTOR_MISSING"


def test_seal_and_verify_file(config_vector, tmp_path):
    """Write seal to disk; verify from files."""
    artifact_file = tmp_path / "art.bin"
    artifact_file.write_bytes(b"file content")
    digest = sha256_bytes(b"file content")
    full_record, epw = create_seal(b"file content", config_vector, "d" * 64)
    write_seal(digest, full_record, root=tmp_path)
    seal_path = tmp_path / "seals" / f"{digest}.seal.json"
    ok, reason = verify_seal_file(artifact_file, seal_path)
    assert ok is True
    assert reason is None


def test_tamper_artifact_file_fails(config_vector, tmp_path):
    """G2 via file: tamper artifact file -> verify returns EPW_MISMATCH."""
    artifact_file = tmp_path / "art.bin"
    artifact_file.write_bytes(b"original")
    digest = sha256_bytes(b"original")
    full_record, _ = create_seal(b"original", config_vector, "e" * 64)
    write_seal(digest, full_record, root=tmp_path)
    artifact_file.write_bytes(b"tampered")
    seal_path = tmp_path / "seals" / f"{digest}.seal.json"
    ok, reason = verify_seal_file(artifact_file, seal_path)
    assert ok is False
    assert reason == "EPW_MISMATCH"
