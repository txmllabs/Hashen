"""Bundle manifest: file list and SHA-256 per file for integrity checks.

Manifest does not include itself in the file inventory to avoid circularity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.utils.canonical_json import canonical_dumps, canonical_loads
from hashen.utils.hashing import sha256_bytes

MANIFEST_FILENAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = "hashen.manifest.v1"

BUNDLE_FILE_NAMES = [
    "artifact.bin",
    "artifact",
    "audit.jsonl",
    "seal.json",
    "verify.json",
    "report.json",
]


def file_sha256(path: Path) -> str:
    """SHA-256 of file contents. Public for use by verification and doctor."""
    return sha256_bytes(path.read_bytes())


def _file_sha256(path: Path) -> str:
    return file_sha256(path)


def build_manifest(
    bundle_root: Path,
    created_at: Optional[str] = None,
    bundle_id: Optional[str] = None,
    target_id: Optional[str] = None,
    content_fingerprint: Optional[str] = None,
    seal_hash_value: Optional[str] = None,
    audit_head_hash_value: Optional[str] = None,
    report_hash_value: Optional[str] = None,
    tool_version: Optional[str] = None,
) -> dict[str, Any]:
    """Build manifest dict: schema_version, files (name -> sha256), seal_hash, audit_head_hash, etc.

    Does not include manifest.json in files (no self-reference).
    """
    files: dict[str, str] = {}
    seal_hash: Optional[str] = seal_hash_value
    audit_head_hash: Optional[str] = audit_head_hash_value
    for name in BUNDLE_FILE_NAMES:
        p = bundle_root / name
        if p.exists():
            files[name] = _file_sha256(p)
    seal_path = bundle_root / "seal.json"
    if seal_path.exists() and seal_hash is None:
        try:
            rec = canonical_loads(seal_path.read_text())
            seal_hash = rec.get("epw_hash")
        except Exception:
            pass
    verify_path = bundle_root / "verify.json"
    if verify_path.exists() and audit_head_hash is None:
        try:
            rec = canonical_loads(verify_path.read_text())
            audit_head_hash = rec.get("audit_head_hash")
        except Exception:
            pass
    report_path = bundle_root / "report.json"
    report_hash: Optional[str] = report_hash_value
    if report_path.exists() and report_hash is None:
        report_hash = _file_sha256(report_path)
    out: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "files": files,
        "seal_hash": seal_hash,
        "audit_head_hash": audit_head_hash,
    }
    if created_at is not None:
        out["created_at"] = created_at
    if bundle_id is not None:
        out["bundle_id"] = bundle_id
    if target_id is not None:
        out["target_id"] = target_id
    if content_fingerprint is not None:
        out["content_fingerprint"] = content_fingerprint
    if report_hash is not None:
        out["report_hash"] = report_hash
    if tool_version is not None:
        out["tool_version"] = tool_version
    return out


def write_bundle_manifest(bundle_root: Path, **kwargs: Any) -> Path:
    """Write manifest.json into bundle_root. Returns path to manifest.
    Kwargs are passed to build_manifest (created_at, bundle_id, target_id, etc.).
    """
    manifest = build_manifest(bundle_root, **kwargs)
    path = bundle_root / MANIFEST_FILENAME
    path.write_text(canonical_dumps(manifest), encoding="utf-8")
    return path


def verify_bundle_manifest(bundle_root: Path) -> tuple[bool, Optional[str]]:
    """Verify manifest: inventory hashes and key metadata. Returns (ok, reason)."""
    manifest_path = bundle_root / MANIFEST_FILENAME
    if not manifest_path.exists():
        return False, "MANIFEST_MISSING"
    try:
        manifest = canonical_loads(manifest_path.read_text())
    except Exception as e:
        return False, f"MANIFEST_INVALID: {e}"
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        return False, "MANIFEST_SCHEMA_VERSION_UNSUPPORTED"
    files = manifest.get("files") or {}
    for name, stored_hash in files.items():
        p = bundle_root / name
        if not p.exists():
            return False, f"MANIFEST_FILE_MISSING: {name}"
        if _file_sha256(p) != stored_hash:
            return False, f"MANIFEST_HASH_MISMATCH: {name}"

    # Metadata cross-checks (when fields are present)
    artifact_path = bundle_root / "artifact.bin"
    if not artifact_path.exists():
        artifact_path = bundle_root / "artifact"
    content_fp = manifest.get("content_fingerprint")
    if content_fp and artifact_path.exists():
        if _file_sha256(artifact_path) != content_fp:
            return False, "MANIFEST_CONTENT_FINGERPRINT_MISMATCH"

    seal_hash = manifest.get("seal_hash")
    seal_path = bundle_root / "seal.json"
    if seal_hash and seal_path.exists():
        try:
            seal_rec = canonical_loads(seal_path.read_text())
            if seal_rec.get("epw_hash") and seal_rec.get("epw_hash") != seal_hash:
                return False, "MANIFEST_SEAL_HASH_MISMATCH"
        except Exception as e:
            return False, f"MANIFEST_INVALID: seal.json: {e}"

    report_hash = manifest.get("report_hash")
    report_path = bundle_root / "report.json"
    if report_hash and report_path.exists():
        if _file_sha256(report_path) != report_hash:
            return False, "MANIFEST_REPORT_HASH_MISMATCH"

    audit_head = manifest.get("audit_head_hash")
    audit_path = bundle_root / "audit.jsonl"
    if audit_head and audit_path.exists():
        from hashen.audit.verify import verify_audit_chain

        chain_result = verify_audit_chain(audit_path)
        if not chain_result.ok:
            return False, chain_result.reason or "AUDIT_CHAIN_BROKEN"
        if chain_result.audit_head_hash != audit_head:
            return False, "MANIFEST_AUDIT_HEAD_MISMATCH"
    return True, None
