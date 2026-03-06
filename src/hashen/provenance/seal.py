"""Hashen Seal (EPW): deterministic provenance record, dual-channel storage, offline verifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.analytics import (
    combined_h2,
    compute_resonance,
    entropy_h2,
    extract_h1_subset,
)
from hashen.audit.verify import verify_audit_chain
from hashen.utils.canonical_json import canonical_dumps, canonical_loads
from hashen.utils.clock import utc_iso_now
from hashen.utils.hashing import sha256_canonical
from hashen.utils.paths import c2pa_stub_dir, seals_dir

# Reason codes (align with docs/REASON_CODES.md)
EPW_MISMATCH = "EPW_MISMATCH"
CONFIG_VECTOR_MISSING = "CONFIG_VECTOR_MISSING"
AUDIT_CHAIN_BROKEN = "AUDIT_CHAIN_BROKEN"
ARTIFACT_DECODE_FAILED = "ARTIFACT_DECODE_FAILED"
INSUFFICIENT_MODALITIES = "INSUFFICIENT_MODALITIES"


def artifact_to_values(artifact_bytes: bytes) -> list[float]:
    """Decode artifact to list of floats (e.g. raw bytes as 0-255 normalized). Deterministic."""
    return [b / 255.0 for b in artifact_bytes]


def compute_seal_payload(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    audit_head_hash: str,
    routing_path: Optional[list[str]] = None,
    resonance: Optional[float] = None,
    sandbox_metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build canonical seal record (no epw_hash yet). Deterministic for same inputs."""
    values = artifact_to_values(artifact_bytes)
    h1_subset = extract_h1_subset(values, config_vector)
    h2 = entropy_h2(values, config_vector)
    per_modality_h2 = [h2]  # single modality for MVP
    comb_h2 = combined_h2(per_modality_h2, config_vector)
    if resonance is None:
        resonance = compute_resonance(values, config_vector)
    payload = {
        "h1_subset": h1_subset,
        "per_modality_h2": per_modality_h2,
        "combined_h2": comb_h2,
        "resonance": resonance,
        "routing_path": routing_path or [],
        "timestamp": utc_iso_now(),
        "config_vector": config_vector,
        "audit_head_hash": audit_head_hash,
        "sandbox_metadata": sandbox_metadata,
    }
    return payload


def create_seal(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    audit_head_hash: str,
    routing_path: Optional[list[str]] = None,
    resonance: Optional[float] = None,
    sandbox_metadata: Optional[dict[str, Any]] = None,
    root: Optional[Path] = None,
) -> tuple[dict[str, Any], str]:
    """
    Create seal record, compute EPW hash, return (full_record, epw_hash).
    Does NOT write to disk; caller may write to seals/ and c2pa_stub/.
    """
    if not config_vector:
        raise ValueError(CONFIG_VECTOR_MISSING)
    payload = compute_seal_payload(
        artifact_bytes,
        config_vector,
        audit_head_hash,
        routing_path=routing_path,
        resonance=resonance,
        sandbox_metadata=sandbox_metadata,
    )
    # EPW excludes timestamp so verifier can recompute same hash from artifact + config
    payload_no_ts = {k: v for k, v in payload.items() if k != "timestamp"}
    epw_hash = sha256_canonical(payload_no_ts)
    full_record = {**payload, "epw_hash": epw_hash}
    return full_record, epw_hash


def write_seal(
    artifact_digest: str,
    full_record: dict[str, Any],
    root: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Dual-channel: write seals/<digest>.seal.json and c2pa_stub/<digest>.json."""
    seals = seals_dir(root)
    c2pa = c2pa_stub_dir(root)
    seal_path = seals / f"{artifact_digest}.seal.json"
    c2pa_path = c2pa / f"{artifact_digest}.json"
    seal_path.write_text(canonical_dumps(full_record), encoding="utf-8")
    c2pa_path.write_text(canonical_dumps(full_record), encoding="utf-8")
    return seal_path, c2pa_path


def verify_seal(
    artifact_bytes: bytes,
    seal_record: dict[str, Any],
    audit_log_path: Optional[Path] = None,
) -> tuple[bool, Optional[str]]:
    """
    Recompute H1/H2 from artifact using config_vector; verify audit chain if path given;
    recompute EPW and compare. Return (ok, reason_code or None).
    """
    config = seal_record.get("config_vector")
    if not config:
        return False, CONFIG_VECTOR_MISSING
    audit_head = seal_record.get("audit_head_hash", "")
    if audit_log_path and audit_log_path.exists():
        result = verify_audit_chain(audit_log_path)
        if not result.ok:
            return False, AUDIT_CHAIN_BROKEN
        if result.audit_head_hash != audit_head:
            return False, AUDIT_CHAIN_BROKEN
    payload = compute_seal_payload(
        artifact_bytes,
        config,
        audit_head,
        routing_path=seal_record.get("routing_path"),
        resonance=seal_record.get("resonance"),
        sandbox_metadata=seal_record.get("sandbox_metadata"),
    )
    # EPW is over payload without timestamp so verification is deterministic.
    payload_no_ts = {k: v for k, v in payload.items() if k != "timestamp"}
    computed_epw = sha256_canonical(payload_no_ts)
    stored_epw = seal_record.get("epw_hash")
    if not stored_epw:
        return False, EPW_MISMATCH
    if computed_epw != stored_epw:
        return False, EPW_MISMATCH
    return True, None


def verify_seal_file(
    artifact_path: Path,
    seal_path: Path,
    audit_log_path: Optional[Path] = None,
) -> tuple[bool, Optional[str]]:
    """Load artifact and seal from paths; run verify_seal."""
    artifact_bytes = artifact_path.read_bytes()
    seal_record = canonical_loads(seal_path.read_text())
    return verify_seal(artifact_bytes, seal_record, audit_log_path)
