"""Tests for Seal (EPW) determinism and tamper-evidence (G1, G2)."""

from __future__ import annotations

import pytest

from hashen.provenance.seal import (
    SEAL_SCHEMA_VERSION,
    build_hashed_payload,
    compute_epw_hash,
    create_seal,
    verify_seal,
    verify_seal_file,
    write_seal,
)
from hashen.sandbox.policy import POLICY_VERSION
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


def test_seal_hash_deterministic_even_if_issued_at_differs(config_vector):
    """Seal hash is deterministic; issued_at differs but epw_hash is identical."""
    artifact = b"deterministic content"
    audit_head = "f" * 64

    def clock1() -> str:
        return "2020-01-01T00:00:00Z"

    def clock2() -> str:
        return "2025-12-31T23:59:59Z"

    _, epw1 = create_seal(artifact, config_vector, audit_head, clock=clock1)
    _, epw2 = create_seal(artifact, config_vector, audit_head, clock=clock2)
    assert epw1 == epw2
    record1, _ = create_seal(artifact, config_vector, audit_head, clock=clock1)
    record2, _ = create_seal(artifact, config_vector, audit_head, clock=clock2)
    assert record1["issued_at"] != record2["issued_at"]
    assert record1["epw_hash"] == record2["epw_hash"]


def test_tamper_fails_with_EPW_MISMATCH(config_vector):
    """Tampered artifact -> verify returns ok=False, reason=EPW_MISMATCH."""
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


def test_seal_includes_schema_version_and_policy_version(config_vector):
    """Seal record includes schema_version; config_vector may include policy_version."""
    artifact = b"versioned"
    audit_head = "v" * 64
    config_with_policy = {**config_vector, "policy_version": POLICY_VERSION}
    full_record, _ = create_seal(artifact, config_with_policy, audit_head)
    assert full_record.get("schema_version") == SEAL_SCHEMA_VERSION
    assert full_record.get("config_vector", {}).get("policy_version") == POLICY_VERSION


def test_verifier_accepts_seal_with_extra_unknown_fields(config_vector):
    """Verifier ignores extra keys in seal record (forward-compatible)."""
    artifact = b"forward compatible"
    audit_head = "x" * 64
    full_record, _ = create_seal(artifact, config_vector, audit_head)
    record_with_extra = {**full_record, "unknown_field": 123, "another": "ignored"}
    ok, reason = verify_seal(artifact, record_with_extra)
    assert ok is True
    assert reason is None


def test_missing_config_returns_CONFIG_VECTOR_MISSING():
    """Seal without config_vector -> verify returns CONFIG_VECTOR_MISSING."""
    ok, reason = verify_seal(b"x", {"epw_hash": "y"})
    assert ok is False
    assert reason == "CONFIG_VECTOR_MISSING"


def test_build_hashed_payload_excludes_issued_at_and_epw_hash(config_vector):
    """build_hashed_payload drops issued_at, epw_hash; same payload -> same compute_epw_hash."""
    artifact = b"payload test"
    audit_head = "e" * 64
    full_record, epw = create_seal(artifact, config_vector, audit_head)
    payload = build_hashed_payload(full_record)
    assert "issued_at" not in payload
    assert "epw_hash" not in payload
    assert compute_epw_hash(payload) == epw


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
