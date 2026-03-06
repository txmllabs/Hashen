"""Content-fingerprint keyed cache with spot-check validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.utils.canonical_json import canonical_dumps, canonical_loads
from hashen.utils.hashing import sha256_bytes
from hashen.utils.paths import cache_dir


def _mean_abs_diff(a: list[float], b: list[float]) -> float:
    """Mean absolute difference; if lengths differ, compare up to min len."""
    if not a or not b:
        return float("inf") if a != b else 0.0
    n = min(len(a), len(b))
    return sum(abs(a[i] - b[i]) for i in range(n)) / n


def spot_check_pass(
    cached_h1_subset: list[float],
    computed_h1_subset: list[float],
    tolerance: float = 1e-6,
) -> bool:
    """Reuse only if mean abs diff <= tolerance."""
    return _mean_abs_diff(cached_h1_subset, computed_h1_subset) <= tolerance


def get_cache_path(root: Optional[Path], key: str) -> Path:
    d = cache_dir(root) if root else cache_dir()
    return d / f"{key}.json"


def cache_get(
    target_id: str,
    content_fingerprint: str,
    root: Optional[Path] = None,
) -> Optional[dict[str, Any]]:
    """Load cache entry if present."""
    key = sha256_bytes((target_id + content_fingerprint).encode())
    path = get_cache_path(root, key)
    if not path.exists():
        return None
    return canonical_loads(path.read_text())


def cache_set(
    target_id: str,
    content_fingerprint: str,
    entry: dict[str, Any],
    root: Optional[Path] = None,
) -> Path:
    """Store cache entry (content-fingerprint keyed)."""
    key = sha256_bytes((target_id + content_fingerprint).encode())
    path = get_cache_path(root, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(entry), encoding="utf-8")
    return path


def cache_lookup_with_spotcheck(
    target_id: str,
    content_fingerprint: str,
    computed_h1_subset: list[float],
    root: Optional[Path] = None,
    tolerance: float = 1e-6,
) -> tuple[bool, Optional[dict[str, Any]]]:
    """
    Cache hit only when entry exists AND spot-check passes.
    Returns (hit, entry or None).
    """
    entry = cache_get(target_id, content_fingerprint, root)
    if entry is None:
        return False, None
    cached_h1 = entry.get("h1_subset") or []
    if not spot_check_pass(cached_h1, computed_h1_subset, tolerance):
        return False, None
    return True, entry
