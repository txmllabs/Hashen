"""Tests for JSON Schema loading and validation."""

from __future__ import annotations

from hashen.provenance.seal import create_seal
from hashen.schemas import list_schema_names, validate_seal
from hashen.schemas.loader import (
    get_schema,
    validate_audit_event,
    validate_bundle_manifest,
    validate_verification_result,
)


def test_list_schema_names():
    names = list_schema_names()
    assert "seal" in names
    assert "report" in names
    assert "bundle" in names
    assert "audit_event" in names
    assert "verification_result" in names


def test_get_schema_seal():
    schema = get_schema("seal")
    assert schema["type"] == "object"
    assert "schema_version" in schema["required"]
    assert schema["properties"]["schema_version"].get("const") == "hashen.seal.v1"


def test_validate_seal_valid():
    artifact = b"x"
    config = {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}
    _, _ = create_seal(artifact, config, "0" * 64)
    record = {
        "schema_version": "hashen.seal.v1",
        "config_vector": config,
        "audit_head_hash": "0" * 64,
        "epw_hash": "a" * 64,
    }
    valid, errs = validate_seal(record)
    assert valid is True
    assert errs == []


def test_validate_seal_invalid_schema_version():
    record = {
        "schema_version": "hashen.seal.v99",
        "config_vector": {},
        "audit_head_hash": "0" * 64,
        "epw_hash": "a" * 64,
    }
    valid, errs = validate_seal(record)
    assert valid is False
    assert errs


def test_validate_audit_event():
    ev = {
        "schema_version": "hashen.audit.v1",
        "event_type": "FETCH",
        "prev_hash": "0" * 64,
        "event_hash": "a" * 64,
    }
    valid, errs = validate_audit_event(ev)
    assert valid is True


def test_validate_bundle_manifest():
    manifest = {"schema_version": "hashen.manifest.v1", "files": {"artifact.bin": "a" * 64}}
    valid, errs = validate_bundle_manifest(manifest)
    assert valid is True


def test_validate_verification_result():
    result = {"ok": True, "seal_valid": True, "errors": [], "warnings": []}
    valid, errs = validate_verification_result(result)
    assert valid is True
