"""Tests for retention: raw TTL deletion, derived retained (G6)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hashen.compliance.retention import (
    DEFAULT_DERIVED_TTL_DAYS,
    DEFAULT_RAW_TTL_HOURS,
    is_derived_expired,
    retention_delete_raw_after_ttl,
)


@pytest.fixture
def raw_artifact(tmp_path: Path) -> Path:
    p = tmp_path / "raw_artifact.bin"
    p.write_bytes(b"raw data")
    return p


def test_raw_artifacts_deleted_after_ttl(raw_artifact: Path):
    """G6: Raw artifacts deleted after TTL."""
    # Set mtime to past
    past = time.time() - (DEFAULT_RAW_TTL_HOURS + 1) * 3600
    raw_artifact.touch()
    import os

    os.utime(raw_artifact, (past, past))
    deleted = retention_delete_raw_after_ttl(
        [raw_artifact],
        raw_ttl_hours=DEFAULT_RAW_TTL_HOURS,
        legal_hold=False,
        now=time.time(),
    )
    assert len(deleted) == 1
    assert deleted[0] == raw_artifact
    assert not raw_artifact.exists()


def test_raw_artifacts_retained_within_ttl(raw_artifact: Path):
    """Raw artifacts not deleted if within TTL."""
    raw_artifact.touch()
    deleted = retention_delete_raw_after_ttl(
        [raw_artifact],
        raw_ttl_hours=DEFAULT_RAW_TTL_HOURS,
        legal_hold=False,
        now=time.time(),
    )
    assert len(deleted) == 0
    assert raw_artifact.exists()


def test_legal_hold_prevents_deletion(raw_artifact: Path):
    """G6: legal_hold prevents deletion."""
    import os

    past = time.time() - (DEFAULT_RAW_TTL_HOURS + 1) * 3600
    raw_artifact.touch()
    os.utime(raw_artifact, (past, past))
    deleted = retention_delete_raw_after_ttl(
        [raw_artifact],
        raw_ttl_hours=DEFAULT_RAW_TTL_HOURS,
        legal_hold=True,
        now=time.time(),
    )
    assert len(deleted) == 0
    assert raw_artifact.exists()


def test_derived_expired(tmp_path: Path):
    """Derived file is expired when older than derived_ttl_days."""
    p = tmp_path / "derived.json"
    p.write_text("{}")
    past = time.time() - (DEFAULT_DERIVED_TTL_DAYS + 1) * 86400
    import os

    os.utime(p, (past, past))
    assert is_derived_expired(p, derived_ttl_days=DEFAULT_DERIVED_TTL_DAYS, now=time.time()) is True
