# Hashen Threat Model

## Summary

The following threats are in scope: **cache poisoning**, **metadata stripping**, **audit tamper**, **script RCE**, and **supply chain** compromise. This document describes attacker goals, assumptions, non-goals, and mitigations by component.

## Attacker goals (in scope)

- **Tamper with artifact or seal** so that verification incorrectly passes, or to strip provenance.
- **Tamper with audit log** to hide or alter execution history.
- **Force cache reuse** with wrong or stale results (poison cache or bypass spot-check).
- **Run arbitrary code** via script execution (RCE, exfil) in the restricted runner.
- **Introduce malicious dependencies** (supply chain).

## Assumptions

- **Verifier and config**: The verifier binary and the `config_vector` stored in the seal are trusted at verification time. An attacker who can replace the verifier or the seal’s config can change verification outcomes.
- **No secret at verify**: Verification uses only artifact bytes and the seal record (which contains config). There is no server-side secret; anyone with artifact + seal can verify.
- **Determinism**: Same artifact + same config → same EPW. Recomposition is reproducible.
- **Runner host**: The host running the restricted runner is not fully compromised; the runner is defense-in-depth, not a security boundary for untrusted code.

## Non-goals

- **Protection against a fully compromised host**: If the OS or process is compromised, seals and audit can be forged or modified.
- **Protection against physical or social engineering**: Out of scope.
- **Full C2PA or regulatory certification**: C2PA stub is a placeholder; we do not claim certification.
- **Container or VM isolation**: The script runner is subprocess + policy, not a sandbox. See [LIMITATIONS.md](LIMITATIONS.md).

## Mitigations by component

| Component | Threat | Mitigation |
|-----------|--------|------------|
| **Seal (EPW)** | Artifact or seal tampering | Recomputation from artifact + config; EPW mismatch → fail. Dual-channel (sidecar + c2pa stub) is convenience; root of trust is recomputation. |
| **Audit log** | Tampering, deletion, reorder | Hash chain (prev_hash, event_hash); verifier rejects broken chain with `AUDIT_CHAIN_BROKEN`. |
| **Cache** | Poisoning, stale reuse | Content + config fingerprint; schema/config version check; spot-check (mean abs diff). Corrupted or mismatched entry → miss (fail closed). |
| **Runner** | Script RCE / exfil | Denylist (e.g. os, socket, subprocess), no network by default, timeout, optional resource limits (Unix). Not container-grade. |
| **Supply chain** | Malicious deps | SBOM (CycloneDX), pip-audit in CI, pinned dev deps. |
| **Manifest** | Missing/altered files in bundle | manifest.json lists files and hashes; verify step checks presence and hash. |
| **PII / retention** | Leakage, over-retention | Data minimization, retention TTL, legal_hold flag, privacy tags in reports. |

## Threats and mitigations (reference table)

| Threat | Mitigation |
|--------|------------|
| **Cache poisoning / stale reuse** | Cache key is content-based. Spot-check recomputes subset; reuse only if pass. Schema/config match required. |
| **Script RCE** | Restricted execution runner: denylist, no network by default, timeout, optional limits. Not container-grade. |
| **Supply chain** | Pinned deps, SBOM, pip-audit in CI. |
| **Audit tampering** | Hash-chained log; verifier detects missing/modified lines → `AUDIT_CHAIN_BROKEN`. |
| **Metadata stripping** | Verifier recomputes from artifact + config_vector; dual-channel is convenience. |
| **Replay** | Seal includes timestamp and content digest. |
| **PII leakage** | Minimization, TTL, legal_hold, privacy tags. |

## Zero-Trust Assumptions

- Commands, scripts, fetched data, and cache entries are treated as untrusted.
- Verification is deterministic: a third party can reproduce the EPW hash using the stored `config_vector` and artifact bytes.
