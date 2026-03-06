"""CLI: produce evidence bundle (artifact + audit + seal + verify)."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

from hashen.orchestrator import run_pipeline
from hashen.provenance.seal import verify_seal
from hashen.utils.canonical_json import canonical_loads


def main() -> int:
    """Entry point for hashen-bundle. Returns 0 on success, 1 on error."""
    ap = argparse.ArgumentParser(
        description="Run pipeline and produce evidence bundle",
    )
    ap.add_argument("artifact_path", type=Path, help="Path to artifact file")
    ap.add_argument("run_id", type=str, help="Run ID")
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Bundle output directory (default: ./bundle_<run_id>)",
    )
    ap.add_argument(
        "--config",
        action="append",
        default=[],
        help="Config KEY=VAL (e.g. h2_min=0)",
    )
    args = ap.parse_args()
    artifact_path = args.artifact_path
    if not artifact_path.exists():
        print(f"Error: artifact not found: {artifact_path}", file=sys.stderr)
        return 1
    artifact_bytes = artifact_path.read_bytes()
    h2_bins = 16
    config_vector = {
        "h2_min": 0.0,
        "h2_max": math.log2(h2_bins),
        "h2_bins": h2_bins,
        "h1_subset_size": 32,
        "fixed_range_policy": "preconfigured_no_autorange",
        "policy_version": "hashen.policy.v1",
    }
    for s in args.config:
        if "=" in s:
            k, v = s.split("=", 1)
            try:
                config_vector[k] = float(v)
            except ValueError:
                config_vector[k] = v
    out_dir = args.output_dir or Path(f"bundle_{args.run_id}")
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    root = out_dir
    result = run_pipeline(artifact_bytes, args.run_id, config_vector, root=root)
    artifact_copy = root / "artifact.bin"
    shutil.copy2(artifact_path, artifact_copy)
    audit_src = root / "audit" / f"{args.run_id}.jsonl"
    audit_dest = root / "audit.jsonl"
    if audit_src.exists():
        shutil.copy2(audit_src, audit_dest)
    seal_path = root / "seals" / f"{result['artifact_digest']}.seal.json"
    seal_dest = root / "seal.json"
    if seal_path.exists():
        shutil.copy2(seal_path, seal_dest)
    seal_record = canonical_loads(seal_path.read_text()) if seal_path.exists() else {}
    audit_for_verify = root / "audit" / f"{args.run_id}.jsonl"
    ok, reason = verify_seal(
        artifact_bytes,
        seal_record,
        audit_log_path=audit_for_verify if audit_for_verify.exists() else None,
    )
    verify_out = {
        "ok": ok,
        "reason": reason,
        "audit_head_hash": result["audit_head_hash"],
        "seal_hash": result["seal_hash"],
    }
    (root / "verify.json").write_text(json.dumps(verify_out, sort_keys=True, indent=2))
    if ok:
        (root / "verify_ok.json").write_text(
            json.dumps(verify_out, sort_keys=True, indent=2),
        )
    tampered_bytes = (
        artifact_bytes[:1] + b"X" + artifact_bytes[2:] if len(artifact_bytes) >= 2 else b"tampered"
    )
    artifact_tampered = root / "artifact_tampered.bin"
    artifact_tampered.write_bytes(tampered_bytes)
    ok_fail, reason_fail = verify_seal(
        tampered_bytes,
        seal_record,
        audit_log_path=audit_for_verify if audit_for_verify.exists() else None,
    )
    verify_fail_out = {
        "ok": ok_fail,
        "reason": reason_fail,
        "audit_head_hash": result["audit_head_hash"],
        "seal_hash": result["seal_hash"],
    }
    (root / "verify_fail.json").write_text(
        json.dumps(verify_fail_out, sort_keys=True, indent=2),
    )
    from hashen import __version__
    from hashen.provenance.bundle_manifest import write_bundle_manifest
    from hashen.utils.clock import utc_iso_now

    report_src = root / "reports" / f"{args.run_id}.json"
    if report_src.exists():
        shutil.copy2(report_src, root / "report.json")
    write_bundle_manifest(
        root,
        created_at=utc_iso_now(),
        bundle_id=args.run_id,
        target_id="default",
        content_fingerprint=result["artifact_digest"],
        seal_hash_value=result["seal_hash"],
        audit_head_hash_value=result["audit_head_hash"],
        tool_version=__version__,
    )
    print(f"Bundle written to {out_dir}")
    print(f"  artifact: {artifact_copy.name}")
    print("  audit: audit.jsonl")
    print("  seal: seal.json")
    print(f"  verify: verify.json (ok={ok})")
    return 0
