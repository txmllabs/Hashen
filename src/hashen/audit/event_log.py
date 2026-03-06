"""Append-only hash-chained audit log (JSONL) per run."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.audit.models import INITIAL_PREV_HASH, AuditEventType, event_payload
from hashen.utils.canonical_json import canonical_dumps
from hashen.utils.hashing import sha256_canonical
from hashen.utils.paths import audit_dir


class EventLog:
    """Append-only JSONL audit log with hash chaining."""

    def __init__(self, run_id: str, log_path: Optional[Path] = None) -> None:
        self.run_id = run_id
        self._path = log_path or (audit_dir() / f"{run_id}.jsonl")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = INITIAL_PREV_HASH
        self._events: list[dict[str, Any]] = []

    def append(
        self,
        event_type: AuditEventType,
        payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Append one event; compute event_hash and chain; persist line."""
        ev = event_payload(event_type, self._prev_hash, payload)
        # Hash excludes event_hash key; we set it after
        ev["event_hash"] = sha256_canonical(ev)
        self._prev_hash = ev["event_hash"]
        self._events.append(ev)
        line = canonical_dumps(ev) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
        return ev

    @property
    def head_hash(self) -> str:
        """Last event_hash in chain (audit_head_hash for seal binding)."""
        return self._prev_hash

    @property
    def path(self) -> Path:
        return self._path

    def events(self) -> list[dict[str, Any]]:
        """In-memory events appended this session (not re-read from file)."""
        return list(self._events)
