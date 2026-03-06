# Hashen Threat Model

## Summary

The following threats are in scope: **cache poisoning**, **metadata stripping**, **audit tamper**, **script RCE**, and **supply chain** compromise. Mitigations are listed in the table below.

## Threats and Mitigations

| Threat | Mitigation |
|--------|------------|
| **Cache poisoning / stale reuse** | Cache key is content-based (`sha256(target_id + content_fingerprint)`). Spot-check recomputes reduced subset and compares mean abs diff ≤ tolerance; reuse only if pass. |
| **Script RCE** | Secure sandbox runner: import allowlist (denylist of `os`, `subprocess`, `socket`, `requests`, etc.), no network by default, read-only FS except sandbox temp, env cleared, CPU/memory/wall-clock limits. Optional ed25519 signature verification. |
| **Supply chain compromise** | Pinned dependencies, SBOM (CycloneDX) to `sbom/bom.json`, `pip-audit` in CI (fail on high severity). |
| **Audit log tampering** | Hash-chained audit log: each event has `prev_hash` and `event_hash`; verifier detects missing or modified lines and returns `AUDIT_CHAIN_BROKEN`. |
| **Metadata stripping** | Dual-channel seal (sidecar `seals/<digest>.seal.json` + C2PA-stub); verifier recomputes H1/H2 from artifact content using `config_vector`. |
| **Replay attacks** | Seal includes timestamp and content digest; optional nonce can be added. |
| **PII leakage** | Data minimization (no raw artifact persistence unless `retain_raw=true`), retention TTL, privacy tags; reports contain inputs summary without raw PII. |

## Zero-Trust Assumptions

- Commands, scripts, fetched data, and cache entries are treated as untrusted.
- Verification is deterministic: a third party can reproduce the EPW hash using the stored `config_vector` and artifact bytes.
