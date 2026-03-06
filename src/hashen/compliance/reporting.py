"""Compliance report per run: reports/<run_id>.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.compliance.privacy_tags import ConsentBasis, DataSourceType, PIIPresent, privacy_tags
from hashen.utils.canonical_json import canonical_dumps
from hashen.utils.paths import reports_dir

REPORT_SCHEMA_VERSION = "hashen.report.v1"


def build_report(
    run_id: str,
    audit_head_hash: str,
    seal_hash: str,
    retention_raw_ttl_hours: float,
    retention_derived_ttl_days: float,
    legal_hold: bool = False,
    inputs_summary: Optional[dict[str, Any]] = None,
    reason_codes: Optional[list[str]] = None,
    data_source_type: DataSourceType = "user_provided",
    pii_present: PIIPresent = "unknown",
    consent_basis: ConsentBasis = "legitimate_interest",
    schema_version: str = REPORT_SCHEMA_VERSION,
    config_vector_summary: Optional[dict[str, Any]] = None,
    fixed_range: Optional[dict[str, Any]] = None,
    cache_outcome: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build prosecution-friendly per-run report with config, fixed range, cache evidence."""
    report: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "audit_head_hash": audit_head_hash,
        "seal_hash": seal_hash,
        "retention": {
            "raw_ttl_hours": retention_raw_ttl_hours,
            "derived_ttl_days": retention_derived_ttl_days,
            "legal_hold": legal_hold,
        },
        "inputs_summary": inputs_summary or {},
        "reason_codes": reason_codes or [],
        "privacy": privacy_tags(data_source_type, pii_present, consent_basis),
    }
    if config_vector_summary:
        report["config_vector_summary"] = config_vector_summary
    if fixed_range:
        report["fixed_range"] = fixed_range
    if cache_outcome:
        report["cache"] = cache_outcome
    return report


def write_report(
    run_id: str,
    report: dict[str, Any],
    root: Optional[Path] = None,
) -> Path:
    path = (reports_dir(root) if root else reports_dir()) / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(report), encoding="utf-8")
    return path
