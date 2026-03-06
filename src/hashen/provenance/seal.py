"""Hashen Seal (EPW): deterministic provenance record, dual-channel storage, offline verifier."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

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

# Schema version for seal payload (forward-compatible; verifier ignores unknown fields)
SEAL_SCHEMA_VERSION = "hashen.seal.v1"

# Reason codes (align with docs/REASON_CODES.md)
EPW_MISMATCH = "EPW_MISMATCH"
CONFIG_VECTOR_MISSING = "CONFIG_VECTOR_MISSING"
AUDIT_CHAIN_BROKEN = "AUDIT_CHAIN_BROKEN"
ARTIFACT_DECODE_FAILED = "ARTIFACT_DECODE_FAILED"
INSUFFICIENT_MODALITIES = "INSUFFICIENT_MODALITIES"
SCHEMA_VERSION_UNSUPPORTED = "SCHEMA_VERSION_UNSUPPORTED"
POLICY_DIGEST_MISMATCH = "POLICY_DIGEST_MISMATCH"
MANIFEST_HASH_MISMATCH = "MANIFEST_HASH_MISMATCH"
REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"

SUPPORTED_SEAL_SCHEMA_VERSIONS = frozenset({SEAL_SCHEMA_VERSION})

# Keys excluded from hashed payload (non-deterministic or envelope-only)
_NON_DETERMINISTIC_KEYS = frozenset(
    {
        "issued_at",
        "timestamp",
        "epw_hash",
        "evidence_urls",
        "local_path",
        "path",
        "file_path",
    }
)


def build_hashed_payload(record: dict) -> dict[str, Any]:
    """Extract deterministic payload from a seal record; drops non-deterministic keys."""
    return {k: v for k, v in record.items() if k not in _NON_DETERMINISTIC_KEYS}


def compute_epw_hash(payload: dict[str, Any]) -> str:
    """Compute EPW hash from a deterministic payload dict (canonical JSON SHA-256)."""
    return sha256_canonical(payload)


def artifact_to_values(artifact_bytes: bytes) -> list[float]:
    """Decode artifact to list of floats (e.g. raw bytes as 0-255 normalized). Deterministic."""
    return [b / 255.0 for b in artifact_bytes]


def config_vector_hash(config_vector: dict[str, Any]) -> str:
    """Deterministic hash of config vector for binding and cache validation."""
    return sha256_canonical(config_vector)


def compute_deterministic_payload(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    audit_head_hash: str,
    routing_path: Optional[list[str]] = None,
    resonance: Optional[float] = None,
    sandbox_metadata: Optional[dict[str, Any]] = None,
    policy_digest: Optional[str] = None,
    include_config_vector_hash: bool = True,
) -> dict[str, Any]:
    """Build deterministic seal payload (no issued_at). Same inputs -> same dict."""
    values = artifact_to_values(artifact_bytes)
    h1_subset = extract_h1_subset(values, config_vector)
    h2 = entropy_h2(values, config_vector)
    per_modality_h2 = [h2]
    comb_h2 = combined_h2(per_modality_h2, config_vector)
    if resonance is None:
        resonance = compute_resonance(values, config_vector)
    payload = {
        "schema_version": SEAL_SCHEMA_VERSION,
        "h1_subset": h1_subset,
        "per_modality_h2": per_modality_h2,
        "combined_h2": comb_h2,
        "resonance": resonance,
        "routing_path": routing_path or [],
        "config_vector": config_vector,
        "audit_head_hash": audit_head_hash,
        "sandbox_metadata": sandbox_metadata,
    }
    if include_config_vector_hash:
        payload["config_vector_hash"] = config_vector_hash(config_vector)
    if policy_digest is not None:
        payload["policy_digest"] = policy_digest
    return payload


def compute_seal_payload(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    audit_head_hash: str,
    routing_path: Optional[list[str]] = None,
    resonance: Optional[float] = None,
    sandbox_metadata: Optional[dict[str, Any]] = None,
    policy_digest: Optional[str] = None,
) -> dict[str, Any]:
    """Alias for backward compatibility; returns deterministic payload only."""
    return compute_deterministic_payload(
        artifact_bytes,
        config_vector,
        audit_head_hash,
        routing_path=routing_path,
        resonance=resonance,
        sandbox_metadata=sandbox_metadata,
        policy_digest=policy_digest,
    )


def create_seal(
    artifact_bytes: bytes,
    config_vector: dict[str, Any],
    audit_head_hash: str,
    routing_path: Optional[list[str]] = None,
    resonance: Optional[float] = None,
    sandbox_metadata: Optional[dict[str, Any]] = None,
    policy_digest: Optional[str] = None,
    root: Optional[Path] = None,
    clock: Optional[Callable[[], str]] = None,
) -> tuple[dict[str, Any], str]:
    """
    Create seal record, compute EPW hash, return (full_record, epw_hash).
    Hashed payload is deterministic; issued_at is envelope-only (clock injection for tests).
    """
    if not config_vector:
        raise ValueError(CONFIG_VECTOR_MISSING)
    payload = compute_deterministic_payload(
        artifact_bytes,
        config_vector,
        audit_head_hash,
        routing_path=routing_path,
        resonance=resonance,
        sandbox_metadata=sandbox_metadata,
        policy_digest=policy_digest,
    )
    epw_hash = compute_epw_hash(payload)
    issued_at = utc_iso_now(clock=clock)
    full_record = {**payload, "issued_at": issued_at, "epw_hash": epw_hash}
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
    Recompute deterministic payload from artifact; verify audit chain if path given;
    recompute EPW and compare. issued_at does not affect verification.
    """
    config = seal_record.get("config_vector")
    if not config:
        return False, CONFIG_VECTOR_MISSING
    if not seal_record.get("epw_hash"):
        return False, REQUIRED_FIELD_MISSING
    schema_ver = seal_record.get("schema_version")
    if schema_ver and schema_ver not in SUPPORTED_SEAL_SCHEMA_VERSIONS:
        return False, SCHEMA_VERSION_UNSUPPORTED
    audit_head = seal_record.get("audit_head_hash", "")
    if audit_log_path and audit_log_path.exists():
        result = verify_audit_chain(audit_log_path)
        if not result.ok:
            return False, AUDIT_CHAIN_BROKEN
        if result.audit_head_hash != audit_head:
            return False, AUDIT_CHAIN_BROKEN
    include_cvh = "config_vector_hash" in seal_record
    payload = compute_deterministic_payload(
        artifact_bytes,
        config,
        audit_head,
        routing_path=seal_record.get("routing_path"),
        resonance=seal_record.get("resonance"),
        sandbox_metadata=seal_record.get("sandbox_metadata"),
        policy_digest=seal_record.get("policy_digest"),
        include_config_vector_hash=include_cvh,
    )
    computed_epw = compute_epw_hash(payload)
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
