"""Audit chain verifier: validates chain, detects tampering, returns audit_head_hash."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from hashen.audit.models import INITIAL_PREV_HASH
from hashen.utils.canonical_json import canonical_loads
from hashen.utils.hashing import sha256_canonical


class AuditVerifyResult(NamedTuple):
    ok: bool
    audit_head_hash: str
    reason: str | None = None


def verify_audit_chain(log_path: Path) -> AuditVerifyResult:
    """
    Read JSONL, validate each event_hash and prev_hash chain.
    Returns ok=False, reason=AUDIT_CHAIN_BROKEN on any break; else ok=True and head hash.
    """
    expected_prev = INITIAL_PREV_HASH
    head_hash = INITIAL_PREV_HASH

    with open(log_path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = canonical_loads(line)
            except Exception as e:
                return AuditVerifyResult(
                    ok=False,
                    audit_head_hash="",
                    reason=f"AUDIT_CHAIN_BROKEN: line {line_no} invalid JSON: {e}",
                )
            if ev.get("prev_hash") != expected_prev:
                return AuditVerifyResult(
                    ok=False,
                    audit_head_hash="",
                    reason="AUDIT_CHAIN_BROKEN: prev_hash mismatch",
                )
            # Recompute event_hash from event without event_hash
            ev_copy = {k: v for k, v in ev.items() if k != "event_hash"}
            computed = sha256_canonical(ev_copy)
            if ev.get("event_hash") != computed:
                return AuditVerifyResult(
                    ok=False,
                    audit_head_hash="",
                    reason="AUDIT_CHAIN_BROKEN: event_hash mismatch",
                )
            expected_prev = computed
            head_hash = computed

    return AuditVerifyResult(ok=True, audit_head_hash=head_hash)
