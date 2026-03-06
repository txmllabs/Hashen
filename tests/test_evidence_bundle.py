"""Tests for evidence bundle tool and verify (G7, e2e)."""

from __future__ import annotations

import json
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


def test_verify_cli_exits_nonzero_on_failure(tmp_path: Path):
    """hashen-verify exits with code 1 when bundle is invalid (e.g. missing seal)."""
    bundle_dir = tmp_path / "bad_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "artifact.bin").write_bytes(b"x")
    (bundle_dir / "audit.jsonl").write_text(
        '{"event_type":"INGEST","prev_hash":"","event_hash":"y"}\n'
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
    assert proc.returncode != 0


def test_verify_cli_json_mode(tmp_path: Path):
    """hashen-verify --json outputs machine-readable result; exit 0 on success, 1 on failure."""
    artifact_file = tmp_path / "in.bin"
    artifact_file.write_bytes(b"json demo")
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            "json-run",
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    # Use tools/verify_bundle.py so we can pass --json (same CLI as hashen-verify)
    verify_script = Path(__file__).parent.parent / "tools" / "verify_bundle.py"
    proc = subprocess.run(
        [sys.executable, str(verify_script), str(bundle_dir), "--json"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)
    assert data.get("ok") is True
    assert data.get("seal_hash")
    # Failure case: tamper artifact then verify --json
    (bundle_dir / "artifact.bin").write_bytes(b"tampered")
    proc_fail = subprocess.run(
        [sys.executable, str(verify_script), str(bundle_dir), "--json"],
        capture_output=True,
        text=True,
    )
    assert proc_fail.returncode != 0
    data_fail = json.loads(proc_fail.stdout)
    assert data_fail.get("ok") is False
    reason = data_fail.get("reason") or ""
    assert "EPW_MISMATCH" in reason or "MANIFEST_HASH_MISMATCH" in reason


def test_report_contains_prosecution_friendly_fields(tmp_path: Path):
    """Per-run report includes schema_version, config_vector_summary, fixed_range, cache."""
    from hashen.orchestrator import run_pipeline
    from hashen.utils.canonical_json import canonical_loads

    artifact_bytes = b"report test"
    config = {"h2_min": 0.0, "h2_max": 4.0, "h2_bins": 16, "h1_subset_size": 32}
    run_pipeline(artifact_bytes, "report_run", config, root=tmp_path)
    report_path = tmp_path / "reports" / "report_run.json"
    assert report_path.exists()
    report = canonical_loads(report_path.read_text())
    assert report.get("schema_version") == "hashen.report.v1"
    assert "config_vector_summary" in report
    assert report["config_vector_summary"].get("h2_min") == 0.0
    assert "fixed_range" in report
    assert report["fixed_range"].get("h2_bins") == 16
    assert "cache" in report
    assert "cache_hit" in report["cache"]
    assert "cache_reason" in report["cache"]
    assert "validation_subset_size" in report["cache"]
    assert report.get("audit_head_hash")
    assert report.get("seal_hash")


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
    assert (out_dir / "verify_ok.json").exists()
    assert (out_dir / "artifact_tampered.bin").exists()
    assert (out_dir / "verify_fail.json").exists()
    import json

    verify = json.loads((out_dir / "verify.json").read_text())
    assert verify.get("ok") is True
    verify_fail = json.loads((out_dir / "verify_fail.json").read_text())
    assert verify_fail.get("ok") is False
    assert verify_fail.get("reason") == "EPW_MISMATCH"


def test_verify_bundle_ok(tmp_path: Path):
    """Run bundle then verify_bundle -> exit 0 and required files exist."""
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
    assert (bundle_dir / "verify_ok.json").exists()
    assert (bundle_dir / "verify_fail.json").exists()
    assert (bundle_dir / "artifact_tampered.bin").exists()


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
    out, err = proc_fail.stdout, proc_fail.stderr
    assert (
        "FAILED" in out
        or "EPW_MISMATCH" in out
        or "Error" in err
        or "FAILED" in err
        or "EPW_MISMATCH" in err
    )


def test_missing_seal_fails_verify(tmp_path: Path):
    """Bundle missing seal.json fails verification."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "artifact.bin").write_bytes(b"x")
    (bundle_dir / "audit.jsonl").write_text(
        '{"event_type":"INGEST","prev_hash":"","event_hash":"y"}\n'
    )
    # No seal.json
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "seal" in proc.stderr.lower() or "Error" in proc.stderr


def test_altered_manifest_fails_manifest_verify(tmp_path: Path):
    """Altering manifest.json causes manifest verification to fail."""
    from hashen.provenance.bundle_manifest import verify_bundle_manifest, write_bundle_manifest

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "artifact.bin").write_bytes(b"a")
    (bundle_dir / "seal.json").write_text('{"epw_hash":"x"}')
    write_bundle_manifest(bundle_dir)
    ok, _ = verify_bundle_manifest(bundle_dir)
    assert ok is True
    # Alter manifest so a file hash is wrong
    manifest_path = bundle_dir / "manifest.json"
    import json

    m = json.loads(manifest_path.read_text())
    m["files"]["artifact.bin"] = "wrong_hash"
    manifest_path.write_text(json.dumps(m))
    ok2, reason = verify_bundle_manifest(bundle_dir)
    assert ok2 is False
    assert "MANIFEST_HASH_MISMATCH" in reason or "artifact" in reason


def test_altered_artifact_fails_seal_verify(tmp_path: Path):
    """Altering artifact in bundle causes seal (EPW) or manifest verification to fail."""
    artifact_file = tmp_path / "in.bin"
    artifact_file.write_bytes(b"original content")
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            "alter-run",
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    (bundle_dir / "artifact.bin").write_bytes(b"tampered content")
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


def test_altered_audit_fails_chain_or_manifest(tmp_path: Path):
    """Altering audit.jsonl causes audit chain or manifest verification to fail."""
    artifact_file = tmp_path / "in.bin"
    artifact_file.write_bytes(b"x")
    bundle_dir = tmp_path / "bundle"
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "run_evidence_bundle.py"),
            str(artifact_file),
            "audit-run",
            "--output-dir",
            str(bundle_dir),
        ],
        capture_output=True,
        cwd=str(tmp_path),
        check=True,
    )
    audit_path = bundle_dir / "audit.jsonl"
    lines = audit_path.read_text().strip().split("\n")
    if lines:
        lines[0] = lines[0][:-1] + " "
        audit_path.write_text("\n".join(lines) + "\n")
    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent.parent / "tools" / "verify_bundle.py"),
            str(bundle_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
