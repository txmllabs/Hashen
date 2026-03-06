#!/usr/bin/env python3
"""
Verify evidence bundle: artifact + seal + audit chain.
Usage: python tools/verify_bundle.py <bundle_dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hashen.audit.verify import verify_audit_chain
from hashen.provenance.seal import verify_seal_file


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify evidence bundle")
    ap.add_argument(
        "bundle_dir",
        type=Path,
        help="Bundle directory (contains artifact.bin or artifact, seal.json, audit.jsonl)",
    )
    args = ap.parse_args()
    root = args.bundle_dir.resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        return 1
    artifact_path = root / "artifact.bin"
    if not artifact_path.exists():
        artifact_path = root / "artifact"
    if not artifact_path.exists():
        print(f"Error: artifact not found in {root}", file=sys.stderr)
        return 1
    seal_path = root / "seal.json"
    if not seal_path.exists():
        seal_path = next(root.glob("seals/*.seal.json"), None)
    if not seal_path or not seal_path.exists():
        print(f"Error: seal not found in {root}", file=sys.stderr)
        return 1
    audit_path = root / "audit.jsonl"
    if not audit_path.exists():
        audit_path = next(root.glob("audit/*.jsonl"), None)
    ok_seal, reason = verify_seal_file(
        artifact_path,
        seal_path,
        audit_log_path=audit_path if audit_path and audit_path.exists() else None,
    )
    if not ok_seal:
        print(f"Seal verification FAILED: {reason}")
        return 1
    if audit_path and audit_path.exists():
        result = verify_audit_chain(audit_path)
        if not result.ok:
            print(f"Audit chain verification FAILED: {result.reason}")
            return 1
    print("Verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
