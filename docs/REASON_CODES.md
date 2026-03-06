# Hashen Reason Codes

Standard failure reasons used by the seal verifier, audit verifier, sandbox, and cache.

| Code | Meaning |
|------|---------|
| `EPW_MISMATCH` | Recomputed EPW hash does not match stored seal; artifact or seal was tampered. |
| `CONFIG_VECTOR_MISSING` | Seal record has no `config_vector`; verification cannot recompute. |
| `REQUIRED_FIELD_MISSING` | Seal missing required field (e.g. `epw_hash`). |
| `SCHEMA_VERSION_UNSUPPORTED` | Seal `schema_version` is not supported by this verifier. |
| `POLICY_DIGEST_MISMATCH` | Policy digest in seal does not match (binding violation). |
| `MANIFEST_HASH_MISMATCH` | Bundle manifest file hash does not match listed hash. |
| `MANIFEST_CONTENT_FINGERPRINT_MISMATCH` | Manifest content_fingerprint does not match artifact digest. |
| `MANIFEST_SEAL_HASH_MISMATCH` | Manifest seal_hash does not match seal.json epw_hash. |
| `MANIFEST_REPORT_HASH_MISMATCH` | Manifest report_hash does not match report.json file hash. |
| `MANIFEST_AUDIT_HEAD_MISMATCH` | Manifest audit_head_hash does not match computed audit chain head. |
| `AUDIT_CHAIN_BROKEN` | Audit log chain invalid: `prev_hash` or `event_hash` mismatch or invalid line. |
| `ARTIFACT_DECODE_FAILED` | Artifact could not be decoded (e.g. invalid format). |
| `INSUFFICIENT_MODALITIES` | Required modality data missing for seal/report. |
| `SANDBOX_POLICY_VIOLATION` | Script rejected by restricted-execution policy (layered AST validation). |
| `TIMEOUT` | Script exceeded wall-clock time limit; process group killed. |
| `RESOURCE_LIMIT` | Script exceeded CPU or memory limit (Unix RLIMIT_CPU/RLIMIT_AS). |
| `SCRIPT_SIGNATURE_INVALID` | Script signature or script_sha256 mismatch; ed25519 verification failed if used. |
| `RUNTIME_ERROR` | Script exited with non-zero return code (runtime exception or explicit exit). |
| `CACHE_SPOTCHECK_FAILED` | Cache entry existed but spot-check (mean abs diff) exceeded tolerance; entry not reused. |
| `STRICT_MODE_REQUIRES_SCRIPT_HASH` | Runner in strict mode but `script_sha256` was not provided. |
| `STDOUT_OVERSIZED` | Script stdout exceeded `max_stdout_bytes` limit. |
| `EXECUTION_DISABLED` | Execution mode is disabled; script was not run. |
| `DUAL_CHANNEL_MISMATCH` | Sidecar seal and c2pa stub have different `epw_hash`. |
| `MANIFEST_FILE_MISSING` | Manifest lists a file that is not present in the bundle. |
| `MANIFEST_INVALID` | manifest.json is not valid JSON or is malformed. |

These codes are returned in verification results, runner results, and compliance reports (`reason_codes`). Verifiers and the CLI exit non-zero and emit the code to stderr or in structured output.

## Example failure scenarios

| Scenario | What happens | Code(s) |
|----------|----------------|--------|
| Attacker flips one byte in artifact | Verifier recomputes EPW; hash differs from seal. | `EPW_MISMATCH` |
| Seal file deleted from bundle | CLI cannot find seal; exits 1. | (Error: seal not found) |
| Audit line deleted | Chain verification: next event's `prev_hash` does not match previous event_hash. | `AUDIT_CHAIN_BROKEN` |
| Malformed JSON line in audit.jsonl | Parser fails; verifier returns chain broken with "invalid JSON". | `AUDIT_CHAIN_BROKEN` |
| Manifest lists wrong hash for artifact.bin | Manifest verification compares file SHA-256 to manifest; mismatch. | `MANIFEST_HASH_MISMATCH: artifact.bin` |
| Manifest seal_hash mismatch | Manifest seal_hash does not match seal.json epw_hash. | `MANIFEST_SEAL_HASH_MISMATCH` |
| Manifest content_fingerprint mismatch | Manifest digest does not match artifact digest. | `MANIFEST_CONTENT_FINGERPRINT_MISMATCH` |
| Script imports `os` | Policy check fails before execution. | `SANDBOX_POLICY_VIOLATION` |
| Script runs longer than timeout | Process group killed. | `TIMEOUT` |
| Cache entry corrupted (invalid JSON) | cache_get returns None; lookup returns miss (fail closed). | (cache_reason: miss_no_entry) |
| Seal from future schema v2 | Verifier only supports v1. | `SCHEMA_VERSION_UNSUPPORTED` |
