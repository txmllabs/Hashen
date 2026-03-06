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
    """Load cache entry if present. Corrupted or invalid JSON yields None (fail closed)."""
    key = sha256_bytes((target_id + content_fingerprint).encode())
    path = get_cache_path(root, key)
    if not path.exists():
        return None
    try:
        return canonical_loads(path.read_text())
    except Exception:
        return None


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
    config_vector_hash: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> tuple[bool, Optional[dict[str, Any]]]:
    """
    Cache hit only when entry exists, spot-check passes, and (if provided)
    config_vector_hash and schema_version match. Returns (hit, entry or None).
    Fail closed: invalid or mismatched entry yields miss.
    """
    entry = cache_get(target_id, content_fingerprint, root)
    if entry is None:
        return False, None
    if schema_version is not None and entry.get("schema_version") != schema_version:
        return False, None
    if config_vector_hash is not None and entry.get("config_vector_hash") != config_vector_hash:
        return False, None
    cached_h1 = entry.get("h1_subset") or []
    if not spot_check_pass(cached_h1, computed_h1_subset, tolerance):
        return False, None
    return True, entry


def mean_abs_diff(a: list[float], b: list[float]) -> float:
    """Mean absolute difference for spot-check reporting; exported for evidence/reports."""
    return _mean_abs_diff(a, b)


def cache_lookup_with_spotcheck_report(
    target_id: str,
    content_fingerprint: str,
    computed_h1_subset: list[float],
    root: Optional[Path] = None,
    tolerance: float = 1e-6,
    config_vector_hash: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> tuple[bool, Optional[dict[str, Any]], dict[str, Any]]:
    """
    Like cache_lookup_with_spotcheck but also returns an evidence report dict:
    cache_hit, cache_reason, validation_subset_size, mean_abs_diff.
    Optional time_saved_ms can be set by caller from timing.
    """
    report: dict[str, Any] = {
        "cache_hit": False,
        "cache_reason": "miss",
        "validation_subset_size": len(computed_h1_subset),
        "mean_abs_diff": None,
    }
    entry = cache_get(target_id, content_fingerprint, root)
    if entry is None:
        report["cache_reason"] = "miss_no_entry"
        return False, None, report
    if schema_version is not None and entry.get("schema_version") != schema_version:
        report["cache_reason"] = "miss_schema_mismatch"
        return False, None, report
    if config_vector_hash is not None and entry.get("config_vector_hash") != config_vector_hash:
        report["cache_reason"] = "miss_config_mismatch"
        return False, None, report
    cached_h1 = entry.get("h1_subset") or []
    mad = _mean_abs_diff(cached_h1, computed_h1_subset)
    report["mean_abs_diff"] = mad
    if not spot_check_pass(cached_h1, computed_h1_subset, tolerance):
        report["cache_reason"] = "miss_spotcheck_failed"
        return False, None, report
    report["cache_hit"] = True
    report["cache_reason"] = "hit"
    return True, entry, report
