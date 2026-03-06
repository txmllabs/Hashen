"""Bundle manifest: file list and SHA-256 per file for integrity checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.utils.canonical_json import canonical_dumps, canonical_loads
from hashen.utils.hashing import sha256_bytes

MANIFEST_FILENAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = "hashen.manifest.v1"


def _file_sha256(path: Path) -> str:
    """SHA-256 of file contents."""
    return sha256_bytes(path.read_bytes())


def build_manifest(bundle_root: Path) -> dict[str, Any]:
    """Build manifest dict: schema_version, files (name -> sha256), seal_hash, audit_head_hash."""
    files: dict[str, str] = {}
    seal_hash: Optional[str] = None
    audit_head_hash: Optional[str] = None
    for name in ["artifact.bin", "artifact", "audit.jsonl", "seal.json", "verify.json"]:
        p = bundle_root / name
        if p.exists():
            files[name] = _file_sha256(p)
    seal_path = bundle_root / "seal.json"
    if seal_path.exists():
        try:
            rec = canonical_loads(seal_path.read_text())
            seal_hash = rec.get("epw_hash")
        except Exception:
            pass
    verify_path = bundle_root / "verify.json"
    if verify_path.exists():
        try:
            rec = canonical_loads(verify_path.read_text())
            audit_head_hash = rec.get("audit_head_hash")
        except Exception:
            pass
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "files": files,
        "seal_hash": seal_hash,
        "audit_head_hash": audit_head_hash,
    }


def write_bundle_manifest(bundle_root: Path) -> Path:
    """Write manifest.json into bundle_root. Returns path to manifest."""
    manifest = build_manifest(bundle_root)
    path = bundle_root / MANIFEST_FILENAME
    path.write_text(canonical_dumps(manifest), encoding="utf-8")
    return path


def verify_bundle_manifest(bundle_root: Path) -> tuple[bool, Optional[str]]:
    """Verify manifest: all listed files exist and match hashes. Returns (ok, reason)."""
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
    return True, None
