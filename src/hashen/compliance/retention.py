"""Retention: raw_ttl_hours, derived_ttl_days, legal_hold; delete raw by TTL."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hashen.utils.clock import get_time

# Defaults per spec
DEFAULT_RAW_TTL_HOURS = 24
DEFAULT_DERIVED_TTL_DAYS = 365


def retention_delete_raw_after_ttl(
    artifact_paths: list[Path],
    raw_ttl_hours: float = DEFAULT_RAW_TTL_HOURS,
    legal_hold: bool = False,
    now: Optional[float] = None,
) -> list[Path]:
    """
    Delete raw artifact files older than raw_ttl_hours (from mtime).
    If legal_hold=True, delete none. Returns list of deleted paths.
    """
    if legal_hold:
        return []
    now = now or get_time()
    cutoff = now - (raw_ttl_hours * 3600)
    deleted: list[Path] = []
    for p in artifact_paths:
        if not p.exists():
            continue
        try:
            mtime = p.stat().st_mtime
            if mtime < cutoff:
                p.unlink()
                deleted.append(p)
        except OSError:
            pass
    return deleted


def is_derived_expired(
    derived_path: Path,
    derived_ttl_days: float = DEFAULT_DERIVED_TTL_DAYS,
    now: Optional[float] = None,
) -> bool:
    """True if file mtime is older than derived_ttl_days."""
    if not derived_path.exists():
        return True
    now = now or get_time()
    cutoff = now - (derived_ttl_days * 86400)
    return derived_path.stat().st_mtime < cutoff
