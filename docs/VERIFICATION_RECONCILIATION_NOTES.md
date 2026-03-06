# Verification reconciliation notes

This document records the verification unification pass: one authoritative verification core, legacy verify as a thin wrapper, bundle doctor built on unified verification, and regression tests proving alignment.

## Current verification code paths (pre-unification)

1. **Unified core** (`src/hashen/verification/verify.py`)
   - `verify_bundle(bundle_root)` → `VerificationResult`
   - `verify_bundle_result(bundle_root)` → dict (to_dict())
   - Single flow: resolve artifact/seal/audit/manifest/report paths, run seal verification, audit chain, manifest, report checks; return structured result with ok, component flags, errors, warnings, reason, seal_hash, audit_head_hash.

2. **Legacy standalone verify** (`src/hashen/cli/verify.py`) — **duplicate logic**
   - Entry: `hashen-verify` / `tools/verify_bundle.py` → `main()`
   - Duplicated: artifact path resolution (artifact.bin vs artifact), seal path (seal.json vs seals/*.seal.json), audit path (audit.jsonl vs audit/*.jsonl).
   - Duplicated: direct calls to `verify_seal_file`, `verify_audit_chain`, `verify_bundle_manifest` in sequence; own failure handling and JSON output shape `{ok, reason, audit_head_hash, seal_hash}`.
   - Exit: 0 on success, 1 on failure; human "Verification OK" / "Verification FAILED: …".

3. **Main CLI verify** (`src/hashen/cli/main.py` `_cmd_verify`)
   - Already uses `verify_bundle_result(bundle_root)`; outputs full result dict; return 0/1. No duplication.

4. **Bundle doctor** (`src/hashen/cli/main.py` `_cmd_bundle_doctor`) — **duplicate logic**
   - Own consistency checks: manifest load, per-file existence + file_sha256; missing artifact/seal when no manifest; malformed JSON for seal/verify/report; legal_hold warning from report.
   - Does not call `verify_bundle`; duplicates missing-file, hash-mismatch, and malformed-JSON handling.

## Duplication summary

| Concern | Unified core | Legacy verify | Bundle doctor |
|--------|--------------|---------------|---------------|
| Artifact/seal/audit path resolution | ✓ | ✓ (duplicate) | ✓ (partial, via manifest or hardcoded) |
| Manifest verification | ✓ | ✓ (direct call) | ✓ (manual file list + hashes) |
| Seal verification | ✓ | ✓ (direct call) | ✗ (only malformed JSON check) |
| Audit chain verification | ✓ | ✓ (direct call) | ✗ |
| JSON output shaping | to_dict() | Legacy shape | Doctor shape (fatal/warnings/path) |
| Exit 0/1, human message | — | ✓ | ✓ |

## Single source of truth

- **Authoritative**: `src/hashen/verification/verify.py` — `verify_bundle()` and `verify_bundle_result()`.
- **Legacy verify**: Thin wrapper: resolve bundle dir, call `verify_bundle(root)`, map result to legacy output shape; preserve exit and human-readable messages.
- **Bundle doctor**: Call `verify_bundle(root)` first; fatal = result.errors, warnings = result.warnings; add only doctor-specific advisories (e.g. legal_hold); remove duplicated consistency checks.

## Legacy behavior to preserve

- **hashen-verify** (and `tools/verify_bundle.py`): Output shape `{ok, reason, audit_head_hash, seal_hash}`; exit 0 on success, 1 on failure; `--json` and human "Verification OK" / "Verification FAILED: …".
- **hashen verify**: Full structured result (ok, seal_valid, errors, warnings, reason_codes, checked_files, etc.); exit 0/1.
- **hashen bundle doctor**: Output shape `{ok, fatal, warnings, path}`; exit 0 when no fatal, 1 otherwise.

## Reason codes and checked_files

- **reason_codes**: List of stable machine-readable codes derived from errors/warnings (e.g. MISSING_FILE, MALFORMED_JSON, EPW_MISMATCH, AUDIT_CHAIN_BROKEN).
- **checked_files**: List of bundle files actually examined (artifact.bin, artifact, seal.json, audit.jsonl, manifest.json, report.json, etc.).
- Both populated in unified verification on all code paths (including early returns) and included in `to_dict()`.

## Fatal vs warning semantics

- Any entry in `errors` is fatal (verification fails unless explicitly carved out).
- Missing optional report does not fail a valid bundle.
- Unsupported schema version is fatal unless a compatibility mode is explicitly implemented.
- `result.reason`: first meaningful fatal code or mapped reason; prefer stable codes over free-text when available.
