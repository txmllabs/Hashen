"""Audit event types and constants."""

from __future__ import annotations

from typing import Any, Literal, Optional

AUDIT_SCHEMA_VERSION = "hashen.audit.v1"

AuditEventType = Literal[
    "COMMAND_RECEIVED",
    "FETCH",
    "FEATURE_EXTRACT",
    "TSEC",
    "CMER",
    "ROUTE",
    "CACHE_HIT",
    "CACHE_MISS",
    "SANDBOX_START",
    "SANDBOX_END",
    "SEAL_EMIT",
    "VERIFY",
]

INITIAL_PREV_HASH = "0" * 64


REQUIRED_EVENT_KEYS = frozenset({"event_type", "prev_hash"})


def event_payload(
    event_type: AuditEventType,
    prev_hash: str,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build event dict without event_hash (caller hashes and sets it)."""
    out: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "event_type": event_type,
        "prev_hash": prev_hash,
    }
    if payload:
        out.update(payload)
    return out
