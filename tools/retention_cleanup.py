#!/usr/bin/env python3
"""
Retention cleanup: delete raw artifacts under a directory by TTL.
Usage: python tools/retention_cleanup.py <dir> [--raw-ttl-hours 24] [--legal-hold]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hashen.compliance.retention import retention_delete_raw_after_ttl


def main() -> int:
    ap = argparse.ArgumentParser(description="Retention cleanup: delete raw artifacts by TTL")
    ap.add_argument("dir", type=Path, help="Directory to scan for raw artifacts")
    ap.add_argument("--raw-ttl-hours", type=float, default=24)
    ap.add_argument("--legal-hold", action="store_true")
    args = ap.parse_args()
    root = args.dir.resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        return 1
    # Collect candidate raw files (e.g. *.bin or all files in a raw/ subdir)
    candidates: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".bin", ".raw", ".dat") or p.name == "artifact":
            candidates.append(p)
    if not candidates:
        # Fallback: any file in root
        candidates = [p for p in root.iterdir() if p.is_file()]
    deleted = retention_delete_raw_after_ttl(
        candidates,
        raw_ttl_hours=args.raw_ttl_hours,
        legal_hold=args.legal_hold,
    )
    for d in deleted:
        print(f"Deleted: {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
