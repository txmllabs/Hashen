"""Cache entry model: content-fingerprint keyed, H1_subset, H2, resonance."""

from __future__ import annotations

from typing import Any, Optional


def cache_key(target_id: str, content_fingerprint: str) -> str:
    """key = sha256(target_id + content_fingerprint). Caller hashes."""
    import hashlib

    return hashlib.sha256((target_id + content_fingerprint).encode()).hexdigest()


def cache_entry(
    h1_subset: list[float],
    per_modality_h2: list[float],
    resonance: Optional[float] = None,
) -> dict[str, Any]:
    return {
        "h1_subset": h1_subset,
        "per_modality_h2": per_modality_h2,
        "resonance": resonance,
    }
