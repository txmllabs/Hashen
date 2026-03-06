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
| `AUDIT_CHAIN_BROKEN` | Audit log chain invalid: `prev_hash` or `event_hash` mismatch or invalid line. |
| `ARTIFACT_DECODE_FAILED` | Artifact could not be decoded (e.g. invalid format). |
| `INSUFFICIENT_MODALITIES` | Required modality data missing for seal/report. |
| `SANDBOX_POLICY_VIOLATION` | Script uses denylisted import (e.g. `os`, `socket`, `subprocess`). |
| `TIMEOUT` | Script exceeded wall-clock time limit; process group killed. |
| `RESOURCE_LIMIT` | Script exceeded CPU or memory limit (Unix RLIMIT_CPU/RLIMIT_AS). |
| `SCRIPT_SIGNATURE_INVALID` | Script signature or script_sha256 mismatch; ed25519 verification failed if used. |
| `RUNTIME_ERROR` | Script exited with non-zero return code (runtime exception or explicit exit). |
| `CACHE_SPOTCHECK_FAILED` | Cache entry existed but spot-check (mean abs diff) exceeded tolerance; entry not reused. |

These codes are returned in verification results and in compliance reports (`reason_codes`).
