"""Tests for unified verification (VerificationResult, verify_bundle) and reason codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hashen.audit import EventLog
from hashen.provenance.bundle_manifest import (
    MANIFEST_FILENAME,
    write_bundle_manifest,
)
from hashen.provenance.seal import create_seal
from hashen.utils.canonical_json import canonical_dumps, canonical_loads
from hashen.verification import (
    VerificationResult,
    verify_bundle,
    verify_bundle_result,
)
from hashen.verification.verify import (
    AUDIT_CHAIN_BROKEN,
    MALFORMED_JSON,
    REPORT_INCONSISTENT,
    SEAL_REPRODUCE_FAILED,
    UNSUPPORTED_SCHEMA_VERSION,
)


@pytest.fixture
def config_vector():
    return {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}


@pytest.fixture
def valid_bundle(tmp_path: Path, config_vector):
    """Create a minimal valid bundle with artifact, seal, audit, manifest."""
    artifact_bytes = b"valid bundle content"
    (tmp_path / "artifact.bin").write_bytes(artifact_bytes)
    run_id = "test-run"
    log = EventLog(run_id, log_path=tmp_path / "audit" / f"{run_id}.jsonl")
    log.append("COMMAND_RECEIVED", {})
    log.append("SEAL_EMIT", {"digest": "x"})
    audit_head = log.head_hash
    full_record, epw_hash = create_seal(artifact_bytes, config_vector, audit_head)
    (tmp_path / "seal.json").write_text(canonical_dumps(full_record))
    (tmp_path / "audit.jsonl").write_text(
        "\n".join(canonical_dumps(ev) for ev in log.events()) + "\n"
    )
    verify_out = {"ok": True, "reason": None, "audit_head_hash": audit_head, "seal_hash": epw_hash}
    (tmp_path / "verify.json").write_text(json.dumps(verify_out, sort_keys=True))
    write_bundle_manifest(tmp_path)
    return tmp_path


def test_verify_bundle_ok(valid_bundle: Path):
    result = verify_bundle(valid_bundle)
    assert result.ok is True
    assert result.seal_valid is True
    assert result.audit_chain_valid is True
    assert result.manifest_valid is True
    assert not result.errors


def test_verify_bundle_result_dict(valid_bundle: Path):
    d = verify_bundle_result(valid_bundle)
    assert d["ok"] is True
    assert d["seal_valid"] is True
    assert "seal_hash" in d
    assert "errors" in d
    assert "reason_codes" in d
    assert "checked_files" in d
    assert isinstance(d["reason_codes"], list)
    assert isinstance(d["checked_files"], list)
    assert "artifact.bin" in d["checked_files"] or "artifact" in d["checked_files"]
    assert "seal.json" in d["checked_files"]


def test_verify_bundle_result_returns_reason_codes_on_failure(valid_bundle: Path):
    """verify_bundle_result() returns reason_codes on failure (e.g. tampered seal)."""
    seal_path = valid_bundle / "seal.json"
    rec = canonical_loads(seal_path.read_text())
    rec["epw_hash"] = "0" * 64
    seal_path.write_text(canonical_dumps(rec))
    write_bundle_manifest(valid_bundle)
    d = verify_bundle_result(valid_bundle)
    assert d["ok"] is False
    assert "reason_codes" in d
    assert len(d["reason_codes"]) >= 1
    assert any(
        c in ("EPW_MISMATCH", "SEAL_REPRODUCE_FAILED") for c in d["reason_codes"]
    )


def test_verify_bundle_result_returns_checked_files_on_failure(tmp_path: Path):
    """Missing required file: checked_files lists what was examined before failure."""
    (tmp_path / "artifact.bin").write_bytes(b"x")
    # no seal
    d = verify_bundle_result(tmp_path)
    assert d["ok"] is False
    assert "checked_files" in d
    assert "artifact.bin" in d["checked_files"]
    assert "reason_codes" in d
    assert "MISSING_FILE" in d["reason_codes"]


def test_verification_result_to_dict():
    r = VerificationResult(ok=True, seal_valid=True, errors=["x"])
    d = r.to_dict()
    assert d["ok"] is True
    assert d["seal_valid"] is True
    assert d["errors"] == ["x"]
    assert "reason_codes" in d
    assert "checked_files" in d


def test_tampered_seal_epw_hash_fails(valid_bundle: Path):
    """Tampering with the seal's epw_hash causes verification to fail (EPW_MISMATCH)."""
    seal_path = valid_bundle / "seal.json"
    rec = canonical_loads(seal_path.read_text())
    rec["epw_hash"] = "0" * 64  # wrong hash; recompute from artifact will differ
    seal_path.write_text(canonical_dumps(rec))
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert result.seal_valid is False
    assert any("EPW_MISMATCH" in e or SEAL_REPRODUCE_FAILED in e for e in result.errors)


def test_tampered_artifact_fails(valid_bundle: Path):
    (valid_bundle / "artifact.bin").write_bytes(b"tampered content")
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert not result.seal_valid


def test_broken_prev_hash_chain_fails(valid_bundle: Path):
    """Broken prev_hash in audit chain -> AUDIT_CHAIN_BROKEN."""
    lines = (valid_bundle / "audit.jsonl").read_text().strip().split("\n")
    ev = json.loads(lines[0])
    ev["prev_hash"] = "f" * 64
    ev["event_hash"] = "a" * 64
    lines[0] = json.dumps(ev, sort_keys=True, separators=(",", ":"))
    (valid_bundle / "audit.jsonl").write_text("\n".join(lines) + "\n")
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert any(AUDIT_CHAIN_BROKEN in e for e in result.errors)


def test_deleted_report_file_does_not_fail_verification(valid_bundle: Path):
    """Missing report is optional; verification can still pass."""
    assert (valid_bundle / "report.json").exists() is False
    result = verify_bundle(valid_bundle)
    assert result.ok is True
    assert result.report_present is False


def test_modified_manifest_file_hash_fails(valid_bundle: Path):
    """Manifest lists wrong hash for a file -> MANIFEST_INCONSISTENT / MANIFEST_HASH_MISMATCH."""
    manifest_path = valid_bundle / MANIFEST_FILENAME
    manifest = canonical_loads(manifest_path.read_text())
    manifest["files"]["artifact.bin"] = "0" * 64
    manifest_path.write_text(canonical_dumps(manifest))
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert not result.manifest_valid
    assert any("MANIFEST" in e for e in result.errors)


def test_malformed_json_seal_fails(valid_bundle: Path):
    (valid_bundle / "seal.json").write_text("not valid json {")
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert any(MALFORMED_JSON in e for e in result.errors)


def test_bundle_missing_required_file_fails(tmp_path: Path):
    """Bundle missing artifact or seal -> MISSING_FILE."""
    (tmp_path / "seal.json").write_text("{}")
    result = verify_bundle(tmp_path)
    assert result.ok is False
    assert any("MISSING_FILE" in e or "artifact" in e for e in result.errors)

    tmp_path2 = tmp_path / "b2"
    tmp_path2.mkdir()
    (tmp_path2 / "artifact.bin").write_bytes(b"x")
    result2 = verify_bundle(tmp_path2)
    assert result2.ok is False
    assert any("MISSING_FILE" in e or "seal" in e for e in result2.errors)


def test_report_seal_hash_mismatch(valid_bundle: Path):
    """Report with seal_hash != actual seal -> REPORT_INCONSISTENT."""
    (valid_bundle / "report.json").write_text(
        json.dumps(
            {
                "schema_version": "hashen.report.v1",
                "run_id": "x",
                "audit_head_hash": "a" * 64,
                "seal_hash": "wrong_seal_hash",
                "retention": {"raw_ttl_hours": 24, "derived_ttl_days": 365, "legal_hold": False},
            },
            sort_keys=True,
        )
    )
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert any(REPORT_INCONSISTENT in e for e in result.errors)


def test_unsupported_schema_version_seal(tmp_path: Path, config_vector):
    """Seal with future schema_version can be rejected (SCHEMA_INVALID / UNSUPPORTED)."""
    artifact_bytes = b"x"
    (tmp_path / "artifact.bin").write_bytes(artifact_bytes)
    full_record, _ = create_seal(artifact_bytes, config_vector, "0" * 64)
    full_record["schema_version"] = "hashen.seal.v99"
    (tmp_path / "seal.json").write_text(canonical_dumps(full_record))
    (tmp_path / "verify.json").write_text(json.dumps({"ok": False, "reason": "UNSUPPORTED"}))
    write_bundle_manifest(tmp_path)
    result = verify_bundle(tmp_path)
    # Seal with unknown schema: either seal_valid False or schema/version in errors or warnings
    errs_warns = result.errors + result.warnings
    assert not result.seal_valid or any(
        "SCHEMA_INVALID" in e or UNSUPPORTED_SCHEMA_VERSION in e for e in errs_warns
    )


def test_deterministic_seal_hash_stable(config_vector):
    """Deterministic seal hash is stable across runs (non-deterministic fields excluded)."""
    artifact = b"deterministic"
    audit_head = "e" * 64
    _, h1 = create_seal(artifact, config_vector, audit_head)
    _, h2 = create_seal(artifact, config_vector, audit_head)
    assert h1 == h2


def test_bundle_inspect_valid_bundle(valid_bundle: Path):
    """Bundle inspect on valid bundle returns file summary and manifest/seal info."""
    from types import SimpleNamespace

    from hashen.cli.main import _cmd_bundle_inspect

    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = SimpleNamespace(bundle_dir=valid_bundle, pretty=False)
    code = _cmd_bundle_inspect(parser, args)
    assert code == 0


def test_bundle_doctor_flags_missing_file(valid_bundle: Path):
    """Bundle doctor reports missing file when we remove one (unified verification)."""
    from types import SimpleNamespace

    from hashen.cli.main import _cmd_bundle_doctor

    (valid_bundle / "seal.json").unlink()
    parser = __import__("argparse").ArgumentParser()
    args = SimpleNamespace(bundle_dir=valid_bundle, pretty=False)
    code = _cmd_bundle_doctor(parser, args)
    assert code != 0


def test_legacy_verify_powered_by_unified(valid_bundle: Path):
    """Legacy hashen-verify (cli.verify.main) uses unified verification; same failures."""
    import sys
    from io import StringIO

    from hashen.cli.verify import main as verify_main

    # Tamper artifact so unified verification fails
    (valid_bundle / "artifact.bin").write_bytes(b"tampered")
    write_bundle_manifest(valid_bundle)

    # Simulate: hashen-verify bundle_dir --json
    sys.argv = ["hashen-verify", str(valid_bundle), "--json"]
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        code = verify_main()
    finally:
        out = sys.stdout.getvalue()
        sys.stdout, sys.stderr = old_stdout, old_stderr
    assert code == 1
    data = json.loads(out)
    assert data["ok"] is False
    assert data.get("reason") or data.get("seal_hash") is not None
    # Reason should reflect unified verification (EPW_MISMATCH or seal failure)
    assert "EPW_MISMATCH" in (data.get("reason") or "") or "Seal" in (data.get("reason") or "")


def test_verify_and_doctor_same_tampered_bundle_fail_aligned(valid_bundle: Path):
    """verify and bundle doctor both fail on same tampered bundle (unified verification)."""
    from types import SimpleNamespace

    from hashen.cli.main import _cmd_bundle_doctor, _cmd_verify
    from hashen.verification import verify_bundle

    # Tamper seal
    seal_path = valid_bundle / "seal.json"
    rec = canonical_loads(seal_path.read_text())
    rec["epw_hash"] = "0" * 64
    seal_path.write_text(canonical_dumps(rec))
    write_bundle_manifest(valid_bundle)

    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert any(
        c in result.reason_codes for c in ("EPW_MISMATCH", "SEAL_REPRODUCE_FAILED")
    )

    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = SimpleNamespace(bundle_dir=valid_bundle, pretty=False)

    assert _cmd_verify(parser, args) == 1
    assert _cmd_bundle_doctor(parser, args) == 1


def test_malformed_json_produces_stable_reason_codes(valid_bundle: Path):
    """Malformed JSON in seal produces MALFORMED_JSON in reason_codes."""
    (valid_bundle / "seal.json").write_text("not valid json {")
    write_bundle_manifest(valid_bundle)
    result = verify_bundle(valid_bundle)
    assert result.ok is False
    assert "MALFORMED_JSON" in result.reason_codes


def test_missing_required_files_produce_stable_reason_codes(tmp_path: Path):
    """Missing artifact or seal produces MISSING_FILE in reason_codes."""
    (tmp_path / "seal.json").write_text("{}")
    result = verify_bundle(tmp_path)
    assert result.ok is False
    assert "MISSING_FILE" in result.reason_codes
    assert "artifact" in str(result.errors).lower() or "artifact.bin" in str(result.checked_files)
