"""Tests for evidence bundle tool and verify (G7, e2e)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add src for imports when running run_evidence_bundle logic in-process
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


def test_pipeline_audit_chain_verifies_in_process(tmp_path: Path):
    """In-process: run_pipeline then verify_audit_chain and verify_seal (no subprocess)."""
    from hashen.audit.verify import verify_audit_chain
    from hashen.orchestrator import run_pipeline
    from hashen.provenance.seal import verify_seal
    from hashen.utils.canonical_json import canonical_loads

    artifact_bytes = b"in process test"
    config = {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}
    run_id = "inproc"
    result = run_pipeline(artifact_bytes, run_id, config, root=tmp_path)
    audit_path = tmp_path / "audit" / f"{run_id}.jsonl"
    chain_result = verify_audit_chain(audit_path)
    assert chain_result.ok, chain_result.reason
    assert chain_result.audit_head_hash == result["audit_head_hash"]
    seal_path = tmp_path / "seals" / f"{result['artifact_digest']}.seal.json"
    seal_record = canonical_loads(seal_path.read_text())
    ok, reason = verify_seal(artifact_bytes, seal_record, audit_log_path=audit_path)
    assert ok, reason


def test_evidence_bundle_produces_artifact_audit_seal_verify(tmp_path: Path):
    """G7: Tool produces bundle folder with artifact, audit.jsonl, seal.json, verify outputs."""
    artifact_file = tmp_path / "input.bin"
    artifact_file.write_bytes(b"evidence bundle test content")
    run_id = "e2e-run-1"
    out_dir = tmp_path / "bundle_out"
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            run_id,
            "--output-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert (out_dir / "artifact.bin").exists()
    assert (out_dir / "audit.jsonl").exists()
    assert (out_dir / "seal.json").exists()
    assert (out_dir / "verify.json").exists()
    # Verify output says ok
    import json

    verify = json.loads((out_dir / "verify.json").read_text())
    assert verify.get("ok") is True


def test_verify_bundle_ok(tmp_path: Path):
    """Run bundle then verify -> OK."""
    artifact_file = tmp_path / "in.bin"
    artifact_file.write_bytes(b"verify me")
    run_id = "verify-run"
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            run_id,
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_tamper_then_verify_fails(tmp_path: Path):
    """E2E: Run -> verify OK -> tamper artifact -> verify fail."""
    artifact_file = tmp_path / "orig.bin"
    artifact_file.write_bytes(b"original")
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            "tamper-run",
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    proc_ok = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc_ok.returncode == 0
    # Tamper artifact in bundle
    (bundle_dir / "artifact.bin").write_bytes(b"tampered")
    proc_fail = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc_fail.returncode != 0
    assert (
        "FAILED" in proc_fail.stdout
        or "EPW_MISMATCH" in proc_fail.stdout
        or "Error" in proc_fail.stderr
    )
