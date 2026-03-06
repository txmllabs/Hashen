# Use cases

Restrained, credible positioning for Hashen. No claims about market dominance, compliance certification, or guaranteed security.

---

## Content provenance

**Use case**: Produce a tamper-evident binding between a digital artifact (e.g. file, blob) and a provenance record (seal). A third party can later verify that the artifact has not been altered by recomputing the seal from the artifact and the stored config.

**What Hashen provides**: Deterministic seal (EPW) from artifact bytes and config vector; dual-channel output (sidecar + optional c2pa stub); verifier that recomputes and compares. No server-side secret required for verification.

**Limitations**: Verification is as trustworthy as the verifier binary and the seal’s config; a fully compromised host can forge seals. Seal does not encrypt or redact content.

---

## Audit-ready analytic pipelines

**Use case**: Run a pipeline (ingest → analytics → cache → seal) and retain an append-only, hash-chained audit log of significant events. The seal binds to the audit chain head so that tampering with the log is detectable.

**What Hashen provides**: Event log with `prev_hash` / `event_hash` chain; audit_head_hash in the seal; verifier that validates the chain and the head binding. Reports can include config summary, fixed range, cache outcome, and retention metadata.

**Limitations**: Audit log is only as secure as the storage and the integrity of the verifier; no cryptographic timestamp authority by default.

---

## Reproducible verification artifacts

**Use case**: Distribute an evidence bundle (artifact + seal + audit + manifest) so that anyone with the same artifact and the bundle can verify integrity without relying on a live service.

**What Hashen provides**: Bundle layout (artifact, seal.json, audit.jsonl, manifest.json, verify output); `hashen-verify` with exit 0/1 and optional `--json`; manifest verification when present. Verification is deterministic given artifact and seal content.

**Limitations**: Bundle integrity depends on manifest and seal not being altered in transit; no built-in distribution or access control.

---

## Regulated workflow evidence support

**Use case**: Support workflows that need evidence of what was run, with what config, and whether results were reused from cache—for internal compliance or regulatory review.

**What Hashen provides**: Per-run reports with schema_version, config_vector_summary, fixed_range, cache outcome (hit/miss, reason, validation metrics), audit_head_hash, seal_hash, retention and privacy metadata. Reason codes for verification and runner failures. No claim to specific regulation (e.g. FDA, GDPR) certification; implementers map these artifacts to their own requirements.

**Limitations**: Hashen does not certify compliance with any particular regulation. Legal hold and retention are policy hooks; enforcement depends on deployment and process.
