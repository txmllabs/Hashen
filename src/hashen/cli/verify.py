"""CLI: verify evidence bundle (artifact + seal + audit; optional manifest).

Thin wrapper around the unified verification path (hashen.verification.verify_bundle_result).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hashen.verification import verify_bundle_result


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

    result = verify_bundle_result(root)

    # Legacy output shape for --json: ok, reason, audit_head_hash, seal_hash
    out = {
        "ok": result.get("ok", False),
        "reason": result.get("reason"),
        "audit_head_hash": result.get("audit_head_hash"),
        "seal_hash": result.get("seal_hash"),
    }
    if args.json:
        print(json.dumps(out, sort_keys=True))
    else:
        if out["ok"]:
            print("Verification OK")
        else:
            err = result.get("errors") or []
            msg = out["reason"] or (err[0] if err else "Verification failed")
            print(f"Verification FAILED: {msg}", file=sys.stderr)
    return 0 if out["ok"] else 1
