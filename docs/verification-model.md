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

Verification result is a JSON object (default output of `hashen verify`):

- **ok**: `true` only if all required checks pass and there are no fatal errors.
- **seal_valid**: Seal recomputation matched stored epw_hash.
- **audit_chain_valid**: Audit chain verified and head matched seal (or no audit file).
- **report_present** / **report_valid**: Report file and schema validity.
- **manifest_present** / **manifest_valid**: Manifest file and per-file hash checks.
- **errors**: List of fatal error messages (e.g. EPW_MISMATCH, REPORT_INCONSISTENT).
- **warnings**: Non-fatal findings (e.g. schema validation warnings).
- **reason**: Short reason code (e.g. first error code).
- **seal_hash**, **audit_head_hash**: When available.

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

- **Fatal** (verification fails, exit non-zero): missing required bundle files (artifact/seal), malformed JSON, seal EPW mismatch, audit chain broken, manifest mismatch (when manifest exists), report inconsistencies (when report exists), unsupported schema version.
- **Warnings** (verification can still pass): schema validation failures for seal/report when core recomputation checks pass.

See [REASON_CODES.md](REASON_CODES.md) for the full list used across seal, audit, runner, and cache.

## Exit codes

- **0**: Verification passed (`ok` is true).
- **Non-zero**: Verification failed or bundle invalid; `ok` is false; details in `errors` and `reason`.
