"""Hashing utilities for content fingerprints and chain hashes."""

from __future__ import annotations

import hashlib
from typing import Any

from hashen.utils.canonical_json import canonical_dumps


def sha256_bytes(data: bytes) -> str:
    """SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_canonical(obj: Any) -> str:
    """SHA-256 of canonical JSON serialization (deterministic)."""
    return sha256_bytes(canonical_dumps(obj).encode("utf-8"))
