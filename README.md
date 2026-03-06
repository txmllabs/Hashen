# Hashen

[![CI](https://github.com/txmllabs/Hashen/actions/workflows/ci.yml/badge.svg)](https://github.com/txmllabs/Hashen/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

**Hashen** is a deterministic provenance, audit-chain, and evidence-bundle SDK for AI and digital artifact workflows. It produces tamper-evident seals (EPW), a hash-chained audit log, a content-fingerprint cache with spot-check validation, and optional restricted execution for scripts. Verification is recomputational: given artifact and seal record, a third party can verify without server-side secrets.

<!-- Repo topics (set in GitHub repo Settings): provenance, verification, audit, trust, evidence-bundle, python -->

---

## Overview

Hashen provides deterministic seal generation (EPW), hash-chained audit logs, content-fingerprint cache with spot-check validation, and a restricted execution runner for scripts. Verification is recomputational: given artifact and seal record, a third party can verify without server-side secrets.

**Important distinctions:**
- **Tamper-evident ≠ tamper-proof**: Verification detects modification; it does not prevent it.
- **Verification SDK ≠ legal certification**: Hashen produces machine-verifiable evidence; it does not certify compliance with any specific regulation.

---

## What Hashen guarantees

- **Deterministic seal (EPW)**: Same artifact, config vector, and audit head hash yield the same seal hash. A third party can recompute the EPW from the artifact and stored config; no server-side secrets required.
- **Tamper evidence**: If the artifact or seal is modified, verification fails with a defined reason code (e.g. `EPW_MISMATCH`).
- **Hash-chained audit log**: Events are appended with `prev_hash` and `event_hash`; verification detects missing, reordered, or modified lines and returns `AUDIT_CHAIN_BROKEN`.
- **Audit–seal binding**: The seal stores `audit_head_hash`; verification can confirm the chain and that its head matches the seal.
- **Content-fingerprint cache**: Cache key is derived from content (and config); reuse requires a passing spot-check. Cache does not substitute for integrity verification of the final seal.

---

## What Hashen does not guarantee

- **Strong process isolation**: The script runner uses a subprocess with timeout and import denylist (AST-based). It is **not** container or VM isolation. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).
- **Complete sandbox**: The denylist is defense-in-depth; it can be bypassed by other means. Do not rely on it as a full sandbox for untrusted code.
- **Cryptographic script signing**: Ed25519 script signature verification is optional and requires the `signing` extra; it is not enabled by default.
- **C2PA compliance**: The `c2pa_stub` output is a placeholder for future C2PA integration; it is not a full C2PA manifest.

---

## Threat model summary

| Threat | Mitigation |
|--------|------------|
| Artifact or seal tampering | EPW recomputation; verification fails on mismatch. |
| Audit log tampering | Hash chain; any change breaks `event_hash` / `prev_hash`. |
| Cache poisoning / stale reuse | Content + config fingerprint; spot-check; schema/version checks. |
| Script RCE / exfil | Restricted execution runner: denylist, no network by default, timeout, optional resource limits (Unix). Not container-grade. |
| Supply chain | SBOM (CycloneDX), pip-audit in CI, pinned dev deps. |

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Verification flow

1. **Produce evidence**: Ingest artifact → run pipeline (analytics, cache lookup, audit events, seal) → write bundle (artifact, audit, seal, verify output, optional manifest).
2. **Verify**: Load artifact and seal; recompute deterministic payload from artifact + `config_vector`; compare EPW hash to seal; if audit path given, verify chain and `audit_head_hash`.
3. **Outcome**: `ok` plus optional reason code (e.g. `EPW_MISMATCH`, `AUDIT_CHAIN_BROKEN`, `CONFIG_VECTOR_MISSING`). See [docs/REASON_CODES.md](docs/REASON_CODES.md).

---

## Evidence bundle contents

A bundle (e.g. from `hashen run` or `hashen-bundle`) typically contains:

| File | Description |
|------|-------------|
| **artifact.bin** | Copy of the input artifact. |
| **audit.jsonl** | Hash-chained audit log for the run. |
| **seal.json** | Provenance seal (EPW hash, config vector, audit head, etc.). |
| **verify.json** | Result of verifying artifact + seal (and optionally audit). |
| **report.json** | Optional per-run compliance report (when produced). |
| **manifest.json** | File inventory and SHA-256 per file; used to detect missing or altered files. |

See [docs/bundle-format.md](docs/bundle-format.md) and [docs/verification-model.md](docs/verification-model.md).

---

## Development status / maturity

- **Current**: Prototype-to-early-production. Core seal, audit, cache, and verification are implemented and tested. Runner is a restricted execution environment (subprocess + policy), not a hardened sandbox.
- **Future hardening**: Container or VM-based runner, full C2PA integration, optional HSM/signing integration. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -e ".[dev]"
pre-commit install   # optional
```

See [docs/DEV_SETUP.md](docs/DEV_SETUP.md) for full developer setup.

### Quickstart

```bash
echo -n "hashen-demo" > sample.bin
hashen-bundle sample.bin demo-run --output-dir bundle_demo
hashen-verify bundle_demo
# Expect: "Verification OK" and exit 0

# Tamper with artifact then re-verify; expect failure (e.g. MANIFEST_HASH_MISMATCH, exit 1)
# echo x >> bundle_demo/artifact.bin
# hashen-verify bundle_demo
```

---

## Tests

```bash
pytest -q
```

With coverage and ruff:

```bash
ruff check src tests && ruff format --check src tests
pytest -v
```

---

## CLI (after install)

Unified CLI (JSON by default; use `--pretty` for human-readable output):

```bash
# Run pipeline and produce evidence bundle
hashen run <artifact_path> [run_id] [--output-dir DIR] [--pretty]

# Verify bundle; exit 0 = OK, non-zero = failure. Output: ok, seal_valid, audit_chain_valid, errors, warnings
hashen verify <bundle_dir> [--pretty]

# Inspect bundle metadata (no mutation)
hashen bundle inspect <bundle_dir> [--pretty]

# Run consistency checks (missing files, hash mismatches, malformed JSON)
hashen bundle doctor <bundle_dir> [--pretty]

# List supported schema names and versions
hashen schema list [--pretty]
```

Legacy entry points (still supported):

```bash
hashen-bundle <artifact_path> <run_id> [--output-dir DIR]
hashen-verify <bundle_dir> [--json]
hashen-retention <dir> [--raw-ttl-hours 24] [--legal-hold]
```

---

## CI

GitHub Actions (`.github/workflows/ci.yml`): pytest, ruff (check + format), pip-audit, CycloneDX SBOM, evidence-bundle smoke test. See workflow file for details.

---

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) – Ingest → analytics → cache → audit → seal → verify; trust boundaries; config vector; audit_head_hash; runner policy.
- [docs/bundle-format.md](docs/bundle-format.md) – Canonical bundle layout, manifest fields, file inventory.
- [docs/schema-versioning.md](docs/schema-versioning.md) – Schema versions for seal, report, bundle, audit event; compatibility.
- [docs/verification-model.md](docs/verification-model.md) – Unified verification, reason codes, pass/fail semantics.
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md) – Implementation limits; runner vs container; signature support; platform caveats.
- [SECURITY.md](SECURITY.md) – Deterministic recomputation; fixed H2 range; seal and audit.
- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) – Threats and mitigations.
- [docs/REASON_CODES.md](docs/REASON_CODES.md) – Verification and runner failure codes.
- [docs/USE_CASES.md](docs/USE_CASES.md) – Content provenance, audit-ready pipelines, verification artifacts, evidence support.
- [docs/ROADMAP.md](docs/ROADMAP.md) – Prioritized work items (P0–P2).
