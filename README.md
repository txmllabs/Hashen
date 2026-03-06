# Hashen

**Hashen** is a trust and provenance verification layer: it produces tamper-evident seals (EPW), a hash-chained audit log, a content-fingerprint cache with spot-check validation, and optional restricted execution for scripts. It is designed to support deterministic verification and evidence bundles suitable for compliance and prosecution-strength provenance.

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

A bundle (e.g. from `hashen-bundle` or `python tools/run_evidence_bundle.py`) typically contains:

- **artifact.bin** – Copy of the input artifact.
- **audit.jsonl** – Hash-chained audit log for the run.
- **seal.json** – Provenance seal (EPW hash, config vector, audit head, etc.).
- **verify.json** – Result of verifying artifact + seal (and optionally audit).
- **manifest.json** (if generated) – List of files and their hashes; used to detect missing or altered files in the bundle.

---

## Development status / maturity

- **Current**: Prototype-to-early-production. Core seal, audit, cache, and verification are implemented and tested. Runner is a restricted execution environment (subprocess + policy), not a hardened sandbox.
- **Future hardening**: Container or VM-based runner, full C2PA integration, optional HSM/signing integration. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

---

## Bootstrap

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -e ".[dev]"
pre-commit install   # optional
```

See [docs/DEV_SETUP.md](docs/DEV_SETUP.md) for full developer setup.

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

```bash
# Evidence bundle (artifact → pipeline → bundle dir)
hashen-bundle <artifact_path> <run_id> [--output-dir DIR]

# Verify bundle (artifact + seal + audit; optional manifest)
hashen-verify <bundle_dir>

# Retention cleanup (delete raw artifacts by TTL)
hashen-retention <dir> [--raw-ttl-hours 24] [--legal-hold]
```

Or run the scripts under `tools/` with the repo root on `PYTHONPATH` (or from repo root):

```bash
python tools/run_evidence_bundle.py sample.bin demo-run --output-dir bundle_demo
python tools/verify_bundle.py bundle_demo
python tools/retention_cleanup.py ./data --raw-ttl-hours 24
```

---

## CI

GitHub Actions (`.github/workflows/ci.yml`): pytest, ruff (check + format), pip-audit, CycloneDX SBOM, evidence-bundle smoke test. See workflow file for details.

---

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) – Ingest → analytics → cache → audit → seal → verify; trust boundaries; config vector; audit_head_hash; runner policy.
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md) – Implementation limits; runner vs container; signature support; platform caveats.
- [docs/SECURITY.md](docs/SECURITY.md) – Deterministic recomputation; fixed H2 range; seal and audit.
- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) – Threats and mitigations.
- [docs/REASON_CODES.md](docs/REASON_CODES.md) – Verification and runner failure codes.
