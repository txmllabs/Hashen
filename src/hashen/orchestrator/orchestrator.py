"""Orchestrator: wire artifact -> audit, feature extract, cache, seal, report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.analytics import combined_h2, compute_resonance, entropy_h2, extract_h1_subset
from hashen.audit import EventLog
from hashen.cache import cache_entry, cache_lookup_with_spotcheck, cache_set
from hashen.cache.models import CACHE_SCHEMA_VERSION
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
) -> dict[str, Any]:
    """
    Single artifact through: audit events, feature extract (H1/H2), cache lookup,
    seal, report. Returns summary with audit_head_hash, seal hash, paths.
    """
    root = root or Path.cwd()
    audit_dir = root / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    log = EventLog(run_id, log_path=audit_dir / f"{run_id}.jsonl")
    log.append("COMMAND_RECEIVED", {"target_id": target_id})
    log.append("FETCH", {})
    values = [b / 255.0 for b in artifact_bytes]
    h1_subset = extract_h1_subset(values, config_vector)
    h2 = entropy_h2(values, config_vector)
    per_modality_h2 = [h2]
    combined_h2(per_modality_h2, config_vector)  # available for report if needed
    resonance = compute_resonance(values, config_vector)
    log.append("FEATURE_EXTRACT", {})
    content_fingerprint = sha256_bytes(artifact_bytes)
    cv_hash = config_vector_hash(config_vector)
    hit, cached = cache_lookup_with_spotcheck(
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
    )
    write_seal(artifact_digest, full_record, root=root)
    report = build_report(
        run_id,
        audit_head_hash=audit_head,
        seal_hash=epw_hash,
        retention_raw_ttl_hours=24,
        retention_derived_ttl_days=365,
        legal_hold=False,
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
    }
