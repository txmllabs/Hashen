"""CLI: verify evidence bundle (legacy hashen-verify). Thin wrapper over unified verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hashen.verification import verify_bundle


def main() -> int:
    """Entry point for hashen-verify. Returns 0 on success, 1 on failure."""
    ap = argparse.ArgumentParser(
        description="Verify evidence bundle (artifact + seal + audit chain)",
    )
    ap.add_argument(
        "bundle_dir",
        type=Path,
        help="Bundle directory (artifact.bin, seal.json, audit.jsonl)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output result as a single JSON object (ok, reason, audit_head_hash, seal_hash)",
    )
    args = ap.parse_args()
    root = args.bundle_dir.resolve()

    result = verify_bundle(root)

    # Legacy output shape
    out = {
        "ok": result.ok,
        "reason": result.reason,
        "audit_head_hash": result.audit_head_hash,
        "seal_hash": result.seal_hash,
    }

    if not result.ok:
        if args.json:
            print(json.dumps(out, sort_keys=True))
        else:
            msg = result.reason or result.errors[0] if result.errors else "Verification failed"
            print(f"Verification FAILED: {msg}")
        return 1

    if args.json:
        print(json.dumps(out, sort_keys=True))
    else:
        print("Verification OK")
    return 0
