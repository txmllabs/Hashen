"""Tests for content-fingerprint cache and spot-check (G5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hashen.cache import (
    cache_get,
    cache_lookup_with_spotcheck,
    cache_set,
    spot_check_pass,
)
from hashen.cache.fingerprint_cache import get_cache_path
from hashen.cache.models import CACHE_SCHEMA_VERSION, cache_entry


@pytest.fixture
def cache_root(tmp_path):
    return tmp_path / "cache"


def test_cache_miss_when_fingerprint_changes(cache_root: Path):
    """G5: When content_fingerprint changes -> cache miss."""
    target_id = "t1"
    fp1 = "fp-aaa"
    fp2 = "fp-bbb"
    entry = cache_entry([0.1, 0.2], [0.5], 0.3)
    cache_set(target_id, fp1, entry, root=cache_root)
    assert cache_get(target_id, fp1, root=cache_root) is not None
    assert cache_get(target_id, fp2, root=cache_root) is None


def test_cache_hit_only_when_spotcheck_passes(cache_root: Path):
    """G5: Cache hit only when spot-check passes."""
    target_id = "t2"
    fp = "fp-same"
    # Store entry with h1_subset [0.1, 0.2]
    entry = cache_entry([0.1, 0.2], [0.5], None)
    cache_set(target_id, fp, entry, root=cache_root)
    # Same computed subset -> hit
    hit, e = cache_lookup_with_spotcheck(target_id, fp, [0.1, 0.2], root=cache_root, tolerance=1e-6)
    assert hit is True
    assert e is not None
    # Different computed subset -> miss (spot-check fails)
    hit2, e2 = cache_lookup_with_spotcheck(
        target_id, fp, [0.9, 0.8], root=cache_root, tolerance=1e-6
    )
    assert hit2 is False
    assert e2 is None


def test_spotcheck_tolerance():
    """Spot-check passes within tolerance."""
    assert spot_check_pass([1.0, 2.0], [1.0, 2.0], tolerance=0) is True
    assert spot_check_pass([1.0, 2.0], [1.0 + 1e-7, 2.0], tolerance=1e-6) is True
    assert spot_check_pass([1.0, 2.0], [1.1, 2.0], tolerance=1e-6) is False


def test_cache_set_get_roundtrip(cache_root: Path):
    """Set and get returns same entry."""
    entry = cache_entry([0.0, 1.0], [0.25, 0.75], 0.5)
    cache_set("tid", "cfp", entry, root=cache_root)
    got = cache_get("tid", "cfp", root=cache_root)
    assert got == entry


def test_cache_config_vector_hash_mismatch_invalidation(cache_root: Path):
    """When config_vector_hash does not match, cache returns miss."""
    target_id = "t3"
    fp = "fp-same"
    entry = cache_entry([0.1, 0.2], [0.5], None, config_vector_hash="hash1")
    cache_set(target_id, fp, entry, root=cache_root)
    hit, _ = cache_lookup_with_spotcheck(
        target_id, fp, [0.1, 0.2], root=cache_root, config_vector_hash="hash2"
    )
    assert hit is False
    hit2, _ = cache_lookup_with_spotcheck(
        target_id, fp, [0.1, 0.2], root=cache_root, config_vector_hash="hash1"
    )
    assert hit2 is True


def test_cache_schema_version_mismatch_invalidation(cache_root: Path):
    """When schema_version does not match, cache returns miss."""
    target_id = "t4"
    fp = "fp-same"
    entry = cache_entry([0.1], [0.5], None)
    cache_set(target_id, fp, entry, root=cache_root)
    hit, _ = cache_lookup_with_spotcheck(
        target_id, fp, [0.1], root=cache_root, schema_version="other.v1"
    )
    assert hit is False
    hit2, _ = cache_lookup_with_spotcheck(
        target_id, fp, [0.1], root=cache_root, schema_version=CACHE_SCHEMA_VERSION
    )
    assert hit2 is True


def test_cache_corrupted_entry_fails_closed(cache_root: Path):
    """Corrupted or invalid cache file yields miss, not reuse."""
    from hashen.utils.hashing import sha256_bytes

    target_id = "t5"
    fp = "fp-corrupt"
    key = sha256_bytes((target_id + fp).encode())
    path = get_cache_path(cache_root, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json {{{")
    hit, entry = cache_lookup_with_spotcheck(target_id, fp, [0.1], root=cache_root)
    assert hit is False
    assert entry is None
