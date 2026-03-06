"""Unified bundle verification with structured result and stable reason codes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from hashen.audit.verify import verify_audit_chain
from hashen.provenance.bundle_manifest import (
    MANIFEST_FILENAME,
    verify_bundle_manifest,
)
from hashen.provenance.seal import SCHEMA_VERSION_UNSUPPORTED, verify_seal_file
from hashen.schemas.loader import validate_report, validate_seal
from hashen.utils.canonical_json import canonical_loads

# Stable reason codes for CLI and machine-readable output
MISSING_FILE = "MISSING_FILE"
MALFORMED_JSON = "MALFORMED_JSON"
SCHEMA_INVALID = "SCHEMA_INVALID"
HASH_MISMATCH = "HASH_MISMATCH"
AUDIT_CHAIN_BROKEN = "AUDIT_CHAIN_BROKEN"
AUDIT_EVENT_TAMPERED = "AUDIT_EVENT_TAMPERED"
SEAL_REPRODUCE_FAILED = "SEAL_REPRODUCE_FAILED"
REPORT_INCONSISTENT = "REPORT_INCONSISTENT"
MANIFEST_INCONSISTENT = "MANIFEST_INCONSISTENT"
UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"


def _extract_reason_codes(errors: list[str], warnings: list[str]) -> list[str]:
    """Derive stable reason codes from error/warning strings (e.g. 'CODE: detail' -> CODE)."""
    codes: set[str] = set()
    for s in errors + warnings:
        if ": " in s:
            codes.add(s.split(": ")[0].strip())
        elif s:
            codes.add(s.split(":")[0].strip() if ":" in s else s)
    return sorted(codes)


@dataclass
class VerificationResult:
    """Structured verification outcome: pass/fail, per-component validity, errors, warnings."""

    ok: bool
    seal_valid: bool = False
    audit_chain_valid: bool = False
    report_present: bool = False
    report_valid: bool = False
    manifest_present: bool = False
    manifest_valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason: Optional[str] = None
    seal_hash: Optional[str] = None
    audit_head_hash: Optional[str] = None
    reason_codes: list[str] = field(default_factory=list)
    checked_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Machine-readable dict (e.g. for JSON output)."""
        return {
            "ok": self.ok,
            "seal_valid": self.seal_valid,
            "audit_chain_valid": self.audit_chain_valid,
            "report_present": self.report_present,
            "report_valid": self.report_valid,
            "manifest_present": self.manifest_present,
            "manifest_valid": self.manifest_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "reason": self.reason,
            "seal_hash": self.seal_hash,
            "audit_head_hash": self.audit_head_hash,
            "reason_codes": self.reason_codes,
            "checked_files": self.checked_files,
        }


def verify_bundle(bundle_root: Path) -> VerificationResult:
    """
    Run full verification on a bundle directory: seal, audit chain, manifest, report.
    Returns structured result; ok=False if any required check fails.
    """
    root = bundle_root.resolve()
    result = VerificationResult(ok=False)
    checked: list[str] = []

    if not root.is_dir():
        result.errors.append(f"{MISSING_FILE}: not a directory: {root}")
        result.reason_codes = _extract_reason_codes(result.errors, result.warnings)
        result.checked_files = list(checked)
        return result

    # Artifact
    artifact_path = root / "artifact.bin"
    if not artifact_path.exists():
        artifact_path = root / "artifact"
    if not artifact_path.exists():
        result.errors.append(f"{MISSING_FILE}: artifact.bin or artifact")
        result.reason_codes = _extract_reason_codes(result.errors, result.warnings)
        result.checked_files = list(checked)
        return result
    checked.append(artifact_path.name)

    # Seal
    seal_path = root / "seal.json"
    if not seal_path.exists():
        seal_path = (
            next((root / "seals").glob("*.seal.json"), None) if (root / "seals").exists() else None
        )
    if not seal_path or not seal_path.exists():
        result.errors.append(f"{MISSING_FILE}: seal.json")
        return result
    checked.append("seal.json")

    try:
        seal_record = canonical_loads(seal_path.read_text())
    except Exception as e:
        result.errors.append(f"{MALFORMED_JSON}: seal.json: {e}")
        result.reason_codes = _extract_reason_codes(result.errors, result.warnings)
        result.checked_files = list(checked)
        return result

    valid_seal_schema, schema_errors = validate_seal(seal_record)
    if not valid_seal_schema:
        result.warnings.append(f"{SCHEMA_INVALID}: seal: {'; '.join(schema_errors)}")
    result.seal_hash = seal_record.get("epw_hash")

    ok_seal, reason_seal = verify_seal_file(
        artifact_path,
        seal_path,
        audit_log_path=None,
    )
    if not ok_seal:
        result.errors.append(reason_seal or SEAL_REPRODUCE_FAILED)
        result.reason = result.reason or reason_seal
    else:
        result.seal_valid = True
    if reason_seal == SCHEMA_VERSION_UNSUPPORTED:
        result.errors.append(UNSUPPORTED_SCHEMA_VERSION)
        result.reason = result.reason or UNSUPPORTED_SCHEMA_VERSION

    # Audit
    audit_path = root / "audit.jsonl"
    if not audit_path.exists():
        audit_path = (
            next((root / "audit").glob("*.jsonl"), None) if (root / "audit").exists() else None
        )
    if audit_path and audit_path.exists():
        chain_result = verify_audit_chain(audit_path)
        if not chain_result.ok:
            result.errors.append(chain_result.reason or AUDIT_CHAIN_BROKEN)
            result.reason = result.reason or AUDIT_CHAIN_BROKEN
        else:
            result.audit_chain_valid = True
            result.audit_head_hash = chain_result.audit_head_hash
        # Cross-check seal audit_head_hash
        if result.seal_valid and chain_result.ok and seal_record.get("audit_head_hash"):
            if seal_record.get("audit_head_hash") != chain_result.audit_head_hash:
                result.errors.append(f"{AUDIT_CHAIN_BROKEN}: seal audit_head_hash mismatch")
                result.reason = result.reason or AUDIT_CHAIN_BROKEN
                result.audit_chain_valid = False

    # Manifest
    manifest_path = root / MANIFEST_FILENAME
    result.manifest_present = manifest_path.exists()
    if result.manifest_present:
        checked.append(MANIFEST_FILENAME)
        ok_manifest, reason_manifest = verify_bundle_manifest(root)
        if not ok_manifest:
            result.errors.append(reason_manifest or MANIFEST_INCONSISTENT)
            result.reason = result.reason or reason_manifest
        else:
            result.manifest_valid = True

    # Report
    report_path = root / "report.json"
    result.report_present = report_path.exists()
    if result.report_present:
        checked.append("report.json")
        try:
            report_data = canonical_loads(report_path.read_text())
            valid_report, report_schema_errors = validate_report(report_data)
            if not valid_report:
                result.warnings.append(
                    f"{SCHEMA_INVALID}: report: {'; '.join(report_schema_errors)}"
                )
            else:
                result.report_valid = True
            if result.seal_hash and report_data.get("seal_hash") != result.seal_hash:
                result.errors.append(REPORT_INCONSISTENT + ": seal_hash mismatch")
                result.reason = result.reason or REPORT_INCONSISTENT
            if (
                result.audit_head_hash
                and report_data.get("audit_head_hash") != result.audit_head_hash
            ):
                result.errors.append(REPORT_INCONSISTENT + ": audit_head_hash mismatch")
                result.reason = result.reason or REPORT_INCONSISTENT
        except Exception as e:
            result.errors.append(f"{MALFORMED_JSON}: report.json: {e}")

    # Pass only if seal valid; audit/manifest if present must be valid; no fatal errors
    audit_required_ok = not (audit_path and audit_path.exists()) or result.audit_chain_valid
    manifest_required_ok = not result.manifest_present or result.manifest_valid
    # Fatal: any errors are fatal. REPORT_INCONSISTENT only applies when report exists.
    fatal_errors = list(result.errors)
    if not result.report_present:
        fatal_errors = [e for e in fatal_errors if REPORT_INCONSISTENT not in e]

    result.ok = (
        result.seal_valid and audit_required_ok and manifest_required_ok and not fatal_errors
    )
    if result.errors and not result.reason:
        result.reason = result.errors[0].split(":")[0] if result.errors else None
    result.reason_codes = _extract_reason_codes(result.errors, result.warnings)
    result.checked_files = checked
    return result


def verify_bundle_result(bundle_root: Path) -> dict[str, Any]:
    """Convenience: run verify_bundle and return to_dict() for JSON output."""
    return verify_bundle(bundle_root).to_dict()
