"""Tests for hash-chained audit log and verifier (G3: tamper fails)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hashen.audit import EventLog, verify_audit_chain
from hashen.audit.models import INITIAL_PREV_HASH


@pytest.fixture
def temp_audit_dir(tmp_path: Path):
    return tmp_path / "audit"


def test_audit_chain_append_and_verify(temp_audit_dir: Path):
    """Chain is valid after appending events."""
    log = EventLog("run-1", log_path=temp_audit_dir / "run-1.jsonl")
    log.append("COMMAND_RECEIVED", {"cmd": "hash"})
    log.append("FETCH", {"url": "file:///x"})
    log.append("SEAL_EMIT", {"digest": "abc"})
    result = verify_audit_chain(log.path)
    assert result.ok is True
    assert result.audit_head_hash == log.head_hash
    assert result.reason is None


def test_audit_chain_tamper_fails_G3(temp_audit_dir: Path):
    """G3: Change one audit event -> audit verifier fails, reason=AUDIT_CHAIN_BROKEN."""
    log = EventLog("run-tamper", log_path=temp_audit_dir / "run-tamper.jsonl")
    log.append("COMMAND_RECEIVED", {"cmd": "x"})
    log.append("FETCH", {"url": "y"})
    # Tamper: change second line (e.g. change payload)
    lines = log.path.read_text().strip().split("\n")
    ev = json.loads(lines[1])
    ev["url"] = "tampered"
    lines[1] = json.dumps(ev, sort_keys=True)  # not canonical but still tampered
    log.path.write_text("\n".join(lines) + "\n")
    result = verify_audit_chain(log.path)
    assert result.ok is False
    assert "AUDIT_CHAIN_BROKEN" in (result.reason or "")


def test_audit_chain_prev_hash_mismatch(temp_audit_dir: Path):
    """Breaking prev_hash breaks verification."""
    log = EventLog("run-prev", log_path=temp_audit_dir / "run-prev.jsonl")
    log.append("COMMAND_RECEIVED", {})
    lines = log.path.read_text().strip().split("\n")
    ev = json.loads(lines[0])
    ev["prev_hash"] = "f" * 64
    ev["event_hash"] = "a" * 64  # wrong hash too
    lines[0] = json.dumps(ev, sort_keys=True, separators=(",", ":"))
    log.path.write_text("\n".join(lines) + "\n")
    result = verify_audit_chain(log.path)
    assert result.ok is False
    assert "AUDIT_CHAIN_BROKEN" in (result.reason or "")


def test_audit_chain_empty_file(temp_audit_dir: Path):
    """Empty log yields head = INITIAL_PREV_HASH."""
    p = temp_audit_dir / "empty.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    result = verify_audit_chain(p)
    assert result.ok is True
    assert result.audit_head_hash == INITIAL_PREV_HASH


def test_audit_chain_single_event(temp_audit_dir: Path):
    """Single event chain verifies."""
    log = EventLog("run-one", log_path=temp_audit_dir / "run-one.jsonl")
    log.append("SEAL_EMIT", {"digest": "d1"})
    result = verify_audit_chain(log.path)
    assert result.ok is True
    assert len(result.audit_head_hash) == 64
