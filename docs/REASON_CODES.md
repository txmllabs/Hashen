# Hashen Reason Codes

Standard failure reasons used by the seal verifier, audit verifier, sandbox, and cache.

| Code | Meaning |
|------|---------|
| `EPW_MISMATCH` | Recomputed EPW hash does not match stored seal; artifact or seal was tampered. |
| `CONFIG_VECTOR_MISSING` | Seal record has no `config_vector`; verification cannot recompute. |
| `AUDIT_CHAIN_BROKEN` | Audit log chain invalid: `prev_hash` or `event_hash` mismatch or invalid line. |
| `ARTIFACT_DECODE_FAILED` | Artifact could not be decoded (e.g. invalid format). |
| `INSUFFICIENT_MODALITIES` | Required modality data missing for seal/report. |
| `SANDBOX_POLICY_VIOLATION` | Script uses denylisted import (e.g. `os`, `socket`, `subprocess`). |
| `SCRIPT_SIGNATURE_INVALID` | Optional ed25519 script signature verification failed. |
| `CACHE_SPOTCHECK_FAILED` | Cache entry existed but spot-check (mean abs diff) exceeded tolerance; entry not reused. |

These codes are returned in verification results and in compliance reports (`reason_codes`).
