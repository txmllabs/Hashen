"""Regression tests: hashen verify, hashen-verify, and hashen bundle doctor use the same
underlying verification path and detect the same tampered-bundle conditions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
TOOLS_VERIFY = REPO_ROOT / "tools" / "verify_bundle.py"
TOOLS_RUN_BUNDLE = REPO_ROOT / "tools" / "run_evidence_bundle.py"


def _run_hashen_verify(bundle_dir: Path, json_out: bool = True) -> subprocess.CompletedProcess:
    """Run unified hashen verify (hashen.cli.main verify)."""
    cmd = [sys.executable, "-m", "hashen.cli.main", "verify", str(bundle_dir)]
    if not json_out:
        cmd.append("--pretty")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


def _run_legacy_verify(bundle_dir: Path, json_out: bool = True) -> subprocess.CompletedProcess:
    """Run legacy hashen-verify (tools/verify_bundle.py)."""
    cmd = [sys.executable, str(TOOLS_VERIFY), str(bundle_dir)]
    if json_out:
        cmd.append("--json")
    return subprocess.run(cmd, capture_output=True, text=True)


def _run_bundle_doctor(bundle_dir: Path) -> subprocess.CompletedProcess:
    """Run hashen bundle doctor (hashen.cli.main bundle doctor)."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "hashen.cli.main",
            "bundle",
            "doctor",
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


@pytest.fixture
def valid_bundle_from_tools(tmp_path: Path) -> Path:
    """Create a valid bundle using run_evidence_bundle (same as evidence_bundle tests)."""
    artifact_file = tmp_path / "in.bin"
    artifact_file.write_bytes(b"contract-test-valid")
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(TOOLS_RUN_BUNDLE),
            str(artifact_file),
            "contract-run",
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    return bundle_dir


def test_verification_contract_valid_bundle_all_pass(valid_bundle_from_tools: Path):
    """hashen verify, hashen-verify, and hashen bundle doctor all pass on valid bundle."""
    bundle = valid_bundle_from_tools
    p_verify = _run_hashen_verify(bundle)
    p_legacy = _run_legacy_verify(bundle)
    p_doctor = _run_bundle_doctor(bundle)

    assert p_verify.returncode == 0, (p_verify.stdout, p_verify.stderr)
    assert p_legacy.returncode == 0, (p_legacy.stdout, p_legacy.stderr)
    assert p_doctor.returncode == 0, (p_doctor.stdout, p_doctor.stderr)

    data_verify = json.loads(p_verify.stdout)
    assert data_verify.get("ok") is True
    assert "reason_codes" in data_verify
    assert "checked_files" in data_verify
    assert "seal.json" in data_verify["checked_files"]
    assert data_verify.get("seal_valid") is True

    data_legacy = json.loads(p_legacy.stdout)
    assert data_legacy.get("ok") is True

    data_doctor = json.loads(p_doctor.stdout)
    assert data_doctor.get("ok") is True
    assert data_doctor.get("fatal") == []


def test_verification_contract_tampered_artifact_all_fail(valid_bundle_from_tools: Path):
    """After tampering artifact, all three commands fail and detect the same condition."""
    bundle = valid_bundle_from_tools
    (bundle / "artifact.bin").write_bytes(b"tampered-content-xyz")

    p_verify = _run_hashen_verify(bundle)
    p_legacy = _run_legacy_verify(bundle)
    p_doctor = _run_bundle_doctor(bundle)

    assert p_verify.returncode != 0
    assert p_legacy.returncode != 0
    assert p_doctor.returncode != 0

    data_verify = json.loads(p_verify.stdout)
    assert data_verify.get("ok") is False
    errors = data_verify.get("errors") or []
    reason_codes = data_verify.get("reason_codes") or []
    assert (
        any("EPW_MISMATCH" in e or "SEAL_REPRODUCE_FAILED" in e for e in errors)
        or "EPW_MISMATCH" in reason_codes
        or any("MANIFEST" in c for c in reason_codes)
    ), (errors, reason_codes)

    legacy_out = p_legacy.stdout + p_legacy.stderr
    assert "EPW_MISMATCH" in legacy_out or "FAILED" in legacy_out or "MANIFEST" in legacy_out

    data_doctor = json.loads(p_doctor.stdout)
    assert data_doctor.get("ok") is False
    fatal = data_doctor.get("fatal") or []
    assert len(fatal) > 0
    fatal_str = " ".join(fatal)
    assert (
        "EPW_MISMATCH" in fatal_str or "SEAL_REPRODUCE" in fatal_str or "MANIFEST" in fatal_str
    ), fatal


def test_verification_contract_tampered_seal_all_fail(valid_bundle_from_tools: Path):
    """After tampering seal epw_hash, all three commands fail (same underlying path)."""
    bundle = valid_bundle_from_tools
    seal_path = bundle / "seal.json"
    seal_data = json.loads(seal_path.read_text())
    seal_data["epw_hash"] = "0" * 64
    seal_path.write_text(json.dumps(seal_data, sort_keys=True))

    p_verify = _run_hashen_verify(bundle)
    p_legacy = _run_legacy_verify(bundle)
    p_doctor = _run_bundle_doctor(bundle)

    assert p_verify.returncode != 0
    assert p_legacy.returncode != 0
    assert p_doctor.returncode != 0

    data_verify = json.loads(p_verify.stdout)
    assert data_verify.get("ok") is False
    reason_codes = data_verify.get("reason_codes") or []
    errors = data_verify.get("errors") or []
    assert "EPW_MISMATCH" in reason_codes or any(
        "EPW_MISMATCH" in e or "MANIFEST_SEAL" in e for e in errors
    )


def test_verification_contract_legacy_json_shape_unchanged(valid_bundle_from_tools: Path):
    """hashen-verify --json keeps legacy shape: ok, reason, audit_head_hash, seal_hash."""
    bundle = valid_bundle_from_tools
    p = _run_legacy_verify(bundle)
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert "ok" in data
    assert "reason" in data
    assert "audit_head_hash" in data
    assert "seal_hash" in data
    assert data.get("ok") is True
