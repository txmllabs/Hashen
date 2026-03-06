"""Tests for hash-chained audit log and verifier (G3: tamper fails)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hashen.audit import EventLog, verify_audit_chain
from hashen.audit.models import AUDIT_SCHEMA_VERSION, INITIAL_PREV_HASH
from hashen.utils.canonical_json import canonical_dumps


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


def test_audit_events_include_schema_version(temp_audit_dir: Path):
    """Appended events include schema_version."""
    log = EventLog("run-schema", log_path=temp_audit_dir / "run-schema.jsonl")
    log.append("COMMAND_RECEIVED", {})
    ev = log.events()[0]
    assert ev.get("schema_version") == AUDIT_SCHEMA_VERSION


def test_audit_deleted_line_fails(temp_audit_dir: Path):
    """Deleting a line (middle event) breaks the chain: next event's prev_hash no longer matches."""
    log = EventLog("run-del", log_path=temp_audit_dir / "run-del.jsonl")
    log.append("COMMAND_RECEIVED", {})
    log.append("FETCH", {})
    log.append("CACHE_MISS", {})
    lines = log.path.read_text().strip().split("\n")
    # Remove middle line so third event's prev_hash points to missing second event
    log.path.write_text(lines[0] + "\n" + lines[2] + "\n")
    result = verify_audit_chain(log.path)
    assert result.ok is False
    assert "AUDIT_CHAIN_BROKEN" in (result.reason or "")


def test_audit_inserted_line_fails(temp_audit_dir: Path):
    """Inserting a line breaks prev_hash linkage."""
    log = EventLog("run-ins", log_path=temp_audit_dir / "run-ins.jsonl")
    log.append("COMMAND_RECEIVED", {})
    first_line = log.path.read_text().strip().split("\n")[0]
    fake_second = canonical_dumps(
        {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "event_type": "FETCH",
            "prev_hash": "0" * 64,
            "event_hash": "f" * 64,
        }
    )
    log.path.write_text(first_line + "\n" + fake_second + "\n")
    result = verify_audit_chain(log.path)
    assert result.ok is False


def test_audit_malformed_line_fails(temp_audit_dir: Path):
    """Malformed JSON line returns structured error."""
    log = EventLog("run-mal", log_path=temp_audit_dir / "run-mal.jsonl")
    log.append("COMMAND_RECEIVED", {})
    with open(log.path, "a", encoding="utf-8") as f:
        f.write("not valid json {{{ \n")
    result = verify_audit_chain(log.path)
    assert result.ok is False
    assert "invalid JSON" in (result.reason or "")


def test_audit_missing_prev_hash_fails(temp_audit_dir: Path):
    """Event missing prev_hash fails validation."""
    p = temp_audit_dir / "run-noprev.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    ev = {"schema_version": AUDIT_SCHEMA_VERSION, "event_type": "FETCH", "event_hash": "a" * 64}
    p.write_text(canonical_dumps(ev) + "\n")
    result = verify_audit_chain(p)
    assert result.ok is False
    assert "prev_hash" in (result.reason or "")


def test_audit_changed_event_type_fails(temp_audit_dir: Path):
    """Changing event_type changes event_hash -> chain breaks."""
    log = EventLog("run-type", log_path=temp_audit_dir / "run-type.jsonl")
    log.append("COMMAND_RECEIVED", {})
    log.append("FETCH", {})
    lines = log.path.read_text().strip().split("\n")
    ev = json.loads(lines[1])
    ev["event_type"] = "SEAL_EMIT"
    ev["event_hash"] = "x" * 64
    lines[1] = json.dumps(ev, sort_keys=True, separators=(",", ":"))
    log.path.write_text("\n".join(lines) + "\n")
    result = verify_audit_chain(log.path)
    assert result.ok is False
    assert "AUDIT_CHAIN_BROKEN" in (result.reason or "")
