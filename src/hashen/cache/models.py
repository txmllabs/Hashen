"""Cache entry model: content-fingerprint keyed, H1_subset, H2, resonance."""

from __future__ import annotations

from typing import Any, Optional

CACHE_SCHEMA_VERSION = "hashen.cache.v1"


def cache_key(target_id: str, content_fingerprint: str) -> str:
    """key = sha256(target_id + content_fingerprint). Caller hashes."""
    import hashlib

    return hashlib.sha256((target_id + content_fingerprint).encode()).hexdigest()


def cache_entry(
    h1_subset: list[float],
    per_modality_h2: list[float],
    resonance: Optional[float] = None,
    config_vector_hash: Optional[str] = None,
    created_at: Optional[str] = None,
    last_validated_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build cache entry. Include schema_version and optional hashes/timestamps."""
    entry: dict[str, Any] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "h1_subset": h1_subset,
        "per_modality_h2": per_modality_h2,
        "resonance": resonance,
    }
    if config_vector_hash is not None:
        entry["config_vector_hash"] = config_vector_hash
    if created_at is not None:
        entry["created_at"] = created_at
    if last_validated_at is not None:
        entry["last_validated_at"] = last_validated_at
    return entry
