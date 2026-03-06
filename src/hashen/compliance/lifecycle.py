"""Lifecycle state and retention status (active, retained, expired, held, purge_eligible)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.compliance.models import LifecycleState
from hashen.compliance.retention import (
    DEFAULT_DERIVED_TTL_DAYS,
    DEFAULT_RAW_TTL_HOURS,
)
from hashen.utils.clock import get_time


def lifecycle_state(
    *,
    legal_hold: bool = False,
    raw_ttl_hours: float = DEFAULT_RAW_TTL_HOURS,
    derived_ttl_days: float = DEFAULT_DERIVED_TTL_DAYS,
    artifact_mtime: Optional[float] = None,
    report_or_bundle_mtime: Optional[float] = None,
    now: Optional[float] = None,
) -> LifecycleState:
    """
    Compute lifecycle state from metadata.
    - held: legal_hold is True (not deletable).
    - purge_eligible: no legal hold, and both raw and derived retention windows have passed.
    - expired: derived TTL passed (report/bundle age).
    - retained: within retention window, no hold.
    - active: within raw TTL (artifact still "active").
    """
    if legal_hold:
        return "held"
    now = now or get_time()
    # Use report/bundle mtime as reference for "derived" age; fallback to artifact
    ref_mtime = report_or_bundle_mtime if report_or_bundle_mtime is not None else artifact_mtime
    if ref_mtime is None:
        return "active"  # unknown age, treat as active
    raw_cutoff = now - (raw_ttl_hours * 3600)
    derived_cutoff = now - (derived_ttl_days * 86400)
    if artifact_mtime is not None and artifact_mtime >= raw_cutoff:
        return "active"
    if ref_mtime < derived_cutoff:
        return "purge_eligible"  # past derived TTL, no hold
    if ref_mtime < raw_cutoff:
        return "expired"  # past raw TTL, within derived
    return "retained"


def retention_status(
    bundle_or_report_dir: Path,
    *,
    raw_ttl_hours: float = DEFAULT_RAW_TTL_HOURS,
    derived_ttl_days: float = DEFAULT_DERIVED_TTL_DAYS,
    legal_hold: bool = False,
    now: Optional[float] = None,
) -> dict[str, Any]:
    """
    Return retention status for a bundle directory or report path: lifecycle_state,
    legal_hold, retention window, policy notes (e.g. not deletable when held).
    Reads report.json or manifest.json for retention/legal_hold when present.
    """
    now = now or get_time()
    report_path = (
        bundle_or_report_dir / "report.json"
        if bundle_or_report_dir.is_dir()
        else bundle_or_report_dir
    )
    legal_hold_val = legal_hold
    raw_ttl = raw_ttl_hours
    derived_ttl = derived_ttl_days
    artifact_mtime: Optional[float] = None
    report_mtime: Optional[float] = None
    if bundle_or_report_dir.is_dir():
        art_path = bundle_or_report_dir / "artifact.bin"
        if not art_path.exists():
            art_path = bundle_or_report_dir / "artifact"
        if art_path.exists():
            try:
                artifact_mtime = art_path.stat().st_mtime
            except OSError:
                pass
        rp = bundle_or_report_dir / "report.json"
        if rp.exists():
            try:
                report_mtime = rp.stat().st_mtime
                import json

                data = json.loads(rp.read_text(encoding="utf-8"))
                ret = data.get("retention") or {}
                legal_hold_val = ret.get("legal_hold", legal_hold)
                raw_ttl = ret.get("raw_ttl_hours", raw_ttl_hours)
                derived_ttl = ret.get("derived_ttl_days", derived_ttl_days)
            except Exception:
                pass
        elif (bundle_or_report_dir / "manifest.json").exists():
            try:
                report_mtime = (bundle_or_report_dir / "manifest.json").stat().st_mtime
            except OSError:
                pass
    else:
        if report_path.exists():
            try:
                report_mtime = report_path.stat().st_mtime
                data = json.loads(report_path.read_text(encoding="utf-8"))
                ret = data.get("retention") or {}
                legal_hold_val = ret.get("legal_hold", legal_hold)
                raw_ttl = ret.get("raw_ttl_hours", raw_ttl_hours)
                derived_ttl = ret.get("derived_ttl_days", derived_ttl_days)
            except Exception:
                pass

    state = lifecycle_state(
        legal_hold=legal_hold_val,
        raw_ttl_hours=raw_ttl,
        derived_ttl_days=derived_ttl,
        artifact_mtime=artifact_mtime,
        report_or_bundle_mtime=report_mtime,
        now=now,
    )
    return {
        "lifecycle_state": state,
        "legal_hold": legal_hold_val,
        "retention_raw_ttl_hours": raw_ttl,
        "retention_derived_ttl_days": derived_ttl,
        "policy_notes": "not deletable; legal hold"
        if state == "held"
        else ("purge_eligible" if state == "purge_eligible" else "within retention"),
        "deletable": state != "held",
    }
