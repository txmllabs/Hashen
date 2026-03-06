"""CLI: retention cleanup (delete raw artifacts by TTL)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hashen.compliance.retention import retention_delete_raw_after_ttl


def main() -> int:
    """Entry point for hashen-retention. Returns 0 on success, 1 on error."""
    ap = argparse.ArgumentParser(
        description="Retention cleanup: delete raw artifacts by TTL",
    )
    ap.add_argument("dir", type=Path, help="Directory to scan for raw artifacts")
    ap.add_argument("--raw-ttl-hours", type=float, default=24)
    ap.add_argument("--legal-hold", action="store_true")
    args = ap.parse_args()
    root = args.dir.resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        return 1
    candidates: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and (p.suffix in (".bin", ".raw", ".dat") or p.name == "artifact"):
            candidates.append(p)
    if not candidates:
        candidates = [p for p in root.iterdir() if p.is_file()]
    deleted = retention_delete_raw_after_ttl(
        candidates,
        raw_ttl_hours=args.raw_ttl_hours,
        legal_hold=args.legal_hold,
    )
    for d in deleted:
        print(f"Deleted: {d}")
    return 0
