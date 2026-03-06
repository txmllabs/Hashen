# Verification model

Unified verification checks seal, audit chain, manifest, and optional report and returns a structured result with explicit pass/fail and reason codes.

## Single authoritative path

The verification command (e.g. `hashen verify <bundle_dir>`) runs one coherent flow:

1. **Artifact and seal presence**: Bundle must contain artifact (artifact.bin or artifact) and seal (seal.json or seals/*.seal.json).
2. **Seal JSON**: Parse seal; optionally validate against seal schema (warnings only); recompute EPW from artifact + config_vector; compare with stored epw_hash.
3. **Audit chain** (if audit.jsonl present): Verify prev_hash/event_hash chain; confirm audit_head_hash matches seal’s audit_head_hash.
4. **Manifest** (if manifest.json present):
   - All listed files must exist and match their SHA-256.
   - If present, `content_fingerprint`, `seal_hash`, `audit_head_hash`, and `report_hash` must match their corresponding objects/files.
5. **Report** (if report.json present): Optionally validate report schema; ensure report’s seal_hash and audit_head_hash match seal and audit chain.

## Output shape

The verification result is a JSON object (default output of `hashen verify`). All of `hashen verify`, `hashen-verify --json`, and `hashen bundle doctor` use the same underlying `verify_bundle` path; `hashen-verify` and bundle doctor map this result to their own output shapes for backward compatibility.

**Full `VerificationResult` fields (e.g. `hashen verify`):**

- **ok**: `true` only if all required checks pass and there are no fatal errors.
- **seal_valid**: Seal recomputation matched stored epw_hash.
- **audit_chain_valid**: Audit chain verified and head matched seal (or no audit file).
- **report_present** / **report_valid**: Report file presence and schema validity.
- **manifest_present** / **manifest_valid**: Manifest file and per-file hash checks.
- **errors**: List of fatal error messages (e.g. `EPW_MISMATCH`, `REPORT_INCONSISTENT`).
- **warnings**: Non-fatal findings (e.g. schema validation warnings).
- **reason**: Short reason code (e.g. first error code).
- **reason_codes**: Sorted list of stable codes derived from errors and warnings (e.g. `MISSING_FILE`, `EPW_MISMATCH`, `MANIFEST_INCONSISTENT`).
- **checked_files**: List of bundle files actually checked (e.g. `artifact.bin`, `seal.json`, `audit.jsonl`, `manifest.json`, `report.json`).
- **seal_hash**, **audit_head_hash**: When available.

**Legacy `hashen-verify --json`** outputs a subset: `ok`, `reason`, `audit_head_hash`, `seal_hash` (unchanged for backward compatibility). **`hashen bundle doctor`** outputs `ok`, `fatal` (same as `errors`), `warnings`, `path`.

## Reason codes

| Code | Meaning |
|------|---------|
| MISSING_FILE | Required file absent (artifact, seal, or manifest-listed file). |
| MALFORMED_JSON | Invalid JSON in seal, report, or manifest. |
| SCHEMA_INVALID | Schema validation failed (often reported as warning). |
| EPW_MISMATCH | Recomputed EPW does not match seal (artifact or seal tampered). |
| AUDIT_CHAIN_BROKEN | prev_hash/event_hash chain invalid or head mismatch. |
| SEAL_REPRODUCE_FAILED | Seal recomputation failed (e.g. CONFIG_VECTOR_MISSING). |
| REPORT_INCONSISTENT | Report seal_hash or audit_head_hash does not match seal/audit. |
| MANIFEST_INCONSISTENT | Manifest missing, invalid, or file hash mismatch. |
| UNSUPPORTED_SCHEMA_VERSION | Seal or manifest schema version not supported. |

## Fatal vs warning semantics

Verification **fails** (exit non-zero, `ok` false) when any **fatal** condition is present. **Warnings** do not by themselves cause failure.

- **Fatal** (verification fails): missing required bundle files (artifact, seal); malformed JSON in seal, report, or manifest; seal EPW mismatch (artifact or seal tampered); audit chain broken or seal/audit head mismatch; manifest missing/invalid or any manifest-listed file missing or hash mismatch; manifest metadata mismatch (content_fingerprint, seal_hash, audit_head_hash, report_hash when present); report present but seal_hash or audit_head_hash inconsistent with seal/audit; unsupported schema version (seal or manifest).
- **Warnings** (verification can still pass): schema validation failures for seal or report when core recomputation and cross-checks pass (e.g. extra or unknown fields). These are recorded in `warnings` and may appear in `reason_codes`.

See [REASON_CODES.md](REASON_CODES.md) for the full code list and verification-specific fatal vs warning mapping.

## Exit codes

- **0**: Verification passed (`ok` is true).
- **Non-zero**: Verification failed or bundle invalid; `ok` is false; details in `errors` and `reason`.
