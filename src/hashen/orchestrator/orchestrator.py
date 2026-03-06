"""Orchestrator: wire artifact -> audit, feature extract, cache, seal, report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.analytics import combined_h2, compute_resonance, entropy_h2, extract_h1_subset
from hashen.audit import EventLog
from hashen.cache import (
    cache_entry,
    cache_lookup_with_spotcheck_report,
    cache_set,
)
from hashen.cache.models import CACHE_SCHEMA_VERSION
from hashen.compliance.models import RunContext
from hashen.compliance.policy import evaluate as policy_evaluate
from hashen.compliance.reporting import build_report, write_report
from hashen.provenance.seal import config_vector_hash, create_seal, write_seal
from hashen.utils.clock import utc_iso_now
from hashen.utils.hashing import sha256_bytes


def run_pipeline(
    artifact_bytes: bytes,
    run_id: str,
    config_vector: dict[str, Any],
    root: Optional[Path] = None,
    target_id: str = "default",
    retain_raw: bool = False,
    sandbox_metadata: Optional[dict[str, Any]] = None,
    run_context: Optional[RunContext] = None,
    retention_raw_ttl_hours: float = 24,
    retention_derived_ttl_days: float = 365,
    legal_hold: bool = False,
    data_classification: Optional[str] = None,
    data_source_type: Optional[str] = "user_provided",
    pii_present: Optional[str] = "unknown",
    consent_basis: Optional[str] = "legitimate_interest",
    purpose_of_processing: Optional[str] = None,
    sharing_restrictions: Optional[str] = None,
    policy_strictness: str = "standard",
) -> dict[str, Any]:
    """
    Single artifact through: audit, policy check, feature extract, cache, seal, report.
    If policy denies, returns with policy_denied=True and no seal/report.
    """
    root = root or Path.cwd()
    audit_dir = root / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    log = EventLog(run_id, log_path=audit_dir / f"{run_id}.jsonl")
    log.append("COMMAND_RECEIVED", {"target_id": target_id})
    log.append("FETCH", {})
    ctx = run_context or RunContext(
        run_id=run_id,
        target_id=target_id,
        data_classification=data_classification,
        data_source_type=data_source_type or "user_provided",
        retention_raw_ttl_hours=retention_raw_ttl_hours,
        retention_derived_ttl_days=retention_derived_ttl_days,
        legal_hold=legal_hold,
        pii_present=pii_present or "unknown",
        consent_basis=consent_basis or "legitimate_interest",
        purpose_of_processing=purpose_of_processing,
        sharing_restrictions=sharing_restrictions,
        action="run",
        strictness=policy_strictness,
    )
    policy_result = policy_evaluate(ctx)
    log.append(
        "POLICY_EVALUATED",
        {
            "decision": policy_result.decision,
            "reasons": [r.to_dict() for r in policy_result.reasons],
            "policy_version": policy_result.policy_version,
        },
    )
    if policy_result.denied:
        return {
            "run_id": run_id,
            "policy_denied": True,
            "policy_decision": policy_result.decision,
            "policy_reasons": [r.to_dict() for r in policy_result.reasons],
            "audit_head_hash": log.head_hash,
            "audit_path": str(log.path),
            "seal_hash": None,
            "artifact_digest": None,
            "report_path": None,
            "seal_path": None,
        }
    values = [b / 255.0 for b in artifact_bytes]
    h1_subset = extract_h1_subset(values, config_vector)
    h2 = entropy_h2(values, config_vector)
    per_modality_h2 = [h2]
    combined_h2(per_modality_h2, config_vector)  # available for report if needed
    resonance = compute_resonance(values, config_vector)
    log.append("FEATURE_EXTRACT", {})
    content_fingerprint = sha256_bytes(artifact_bytes)
    cv_hash = config_vector_hash(config_vector)
    hit, cached, cache_report = cache_lookup_with_spotcheck_report(
        target_id,
        content_fingerprint,
        h1_subset,
        root=root,
        config_vector_hash=cv_hash,
        schema_version=CACHE_SCHEMA_VERSION,
    )
    if hit:
        log.append("CACHE_HIT", {})
    else:
        log.append("CACHE_MISS", {})
        cache_set(
            target_id,
            content_fingerprint,
            cache_entry(
                h1_subset,
                per_modality_h2,
                resonance,
                config_vector_hash=cv_hash,
                created_at=utc_iso_now(),
            ),
            root=root,
        )
    cache_outcome = dict(cache_report)
    log.append("ROUTE", {"path": []})
    artifact_digest = sha256_bytes(artifact_bytes)
    log.append("SEAL_EMIT", {"digest": artifact_digest})
    log.append("VERIFY", {})
    audit_head = log.head_hash
    # Ensure policy_version in seal for audit binding (if not already in config_vector)
    cv = dict(config_vector)
    if "policy_version" not in cv:
        from hashen.sandbox.policy import POLICY_VERSION

        cv["policy_version"] = POLICY_VERSION
    full_record, epw_hash = create_seal(
        artifact_bytes,
        cv,
        audit_head,
        resonance=resonance,
        sandbox_metadata=sandbox_metadata,
    )
    write_seal(artifact_digest, full_record, root=root)
    fixed_range = {
        "h2_min": config_vector.get("h2_min"),
        "h2_max": config_vector.get("h2_max"),
        "h2_bins": config_vector.get("h2_bins"),
    }
    policy_decision_dict = policy_result.to_dict()
    report = build_report(
        run_id,
        audit_head_hash=audit_head,
        seal_hash=epw_hash,
        retention_raw_ttl_hours=retention_raw_ttl_hours,
        retention_derived_ttl_days=retention_derived_ttl_days,
        legal_hold=legal_hold,
        config_vector_summary=dict(config_vector),
        fixed_range=fixed_range,
        cache_outcome=cache_outcome,
        data_source_type=data_source_type or "user_provided",
        pii_present=pii_present or "unknown",
        consent_basis=consent_basis or "legitimate_interest",
        data_classification=data_classification,
        purpose_of_processing=purpose_of_processing,
        sharing_restrictions=sharing_restrictions,
        policy_decision=policy_decision_dict,
    )
    report_path = write_report(run_id, report, root=root)
    return {
        "run_id": run_id,
        "audit_head_hash": audit_head,
        "seal_hash": epw_hash,
        "artifact_digest": artifact_digest,
        "audit_path": str(log.path),
        "report_path": str(report_path),
        "seal_path": str(root / "seals" / f"{artifact_digest}.seal.json"),
        "cache_hit": hit,
        "cache_outcome": cache_outcome,
    }
