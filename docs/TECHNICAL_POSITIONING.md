# Technical positioning

This document describes the implementation choices in this repository in factual, implementation-based terms. It does not make legal or patent conclusions.

## What this repo implements

Hashen is a **trust and provenance verification layer**: it turns artifact bytes plus configuration into a deterministic, content-derived proof (the seal/EPW) and an append-only execution record (the audit chain). Verification recomputes from the artifact and stored config; it does not rely on metadata copies alone.

## Where deterministic recomputation matters

- **Seal (EPW)**: The seal hash is computed from a canonical payload that includes artifact-derived values (H1 subset, H2 entropy, resonance), config vector, and audit head. The same artifact and config always yield the same hash. A verifier with the artifact and the seal record (which contains `config_vector`) can recompute the hash and compare. Tampered content or config produces a mismatch.
- **No secret at verify time**: Verification does not require a private key or server. Anyone with the artifact and the seal can verify. This supports third-party and adversarial verification.
- **Audit chain**: Each event in the audit log is hash-chained. The seal binds to the chain head. Tampering with the log breaks the chain or the head binding.

## Content-derived vs metadata-only provenance

- **Content-derived**: The seal payload is computed from the **artifact bytes** (normalized to a value vector) and the config. The EPW hash is therefore a function of content. Changing a single byte in the artifact (with the same config) changes the hash. Provenance is tied to what the artifact actually is, not only to tags or sidecar files.
- **Metadata copies**: The implementation writes the seal to multiple places (e.g. sidecar JSON, c2pa stub) for convenience and interoperability. These are **copies**. The root of verification is recomputation from artifact + config; if a copy is missing or tampered, verification can still succeed using another copy or the same record, as long as the artifact and the stored config are correct.

## Why fixed entropy range matters technically

The H2 (second-order entropy) histogram uses a **fixed, preconfigured** range from the config vector (`h2_min`, `h2_max`, `h2_bins`). The range is **not** adapted per sample (no auto-scaling from sample min/max).

- **Stability**: Same artifact + same config → same H2 and same seal. If the range were adapted per sample, small changes in pipeline or input could change bin boundaries and entropy, making the seal unstable.
- **Avoiding artifacts**: Auto-scaling histograms can produce different entropy for the same content under different preprocessing or batching. A fixed range removes that source of non-determinism.
- **Reproducibility**: A verifier with the seal (and thus the config) knows exactly which range was used and can recompute H2 identically.

See [FIXED_ENTROPY_RANGE.md](FIXED_ENTROPY_RANGE.md) for details.

## Why cache evidence matters technically

The content cache is an optimization: it avoids recomputing H1/H2/resonance when the same artifact and config are processed again. Reuse is **bounded and measurable**:

- Reuse is allowed only when content fingerprint, config hash, schema version, and a **spot-check** (mean absolute difference on the H1 subset) all pass.
- Each run records **cache_hit**, **cache_reason**, **validation_subset_size**, and **mean_abs_diff** in the report. There is no silent reuse; the evidence is machine-readable and retainable.
- This supports compliance and prosecution use cases where “we reused a prior result” must be justified with concrete metrics.

See [CACHE_SPOT_CHECK.md](CACHE_SPOT_CHECK.md) for the mechanism.

## Runner and routing

- **Restricted execution**: Scripts run in a subprocess with a denylist, timeout, and (on Unix) resource limits. This is **not** container or VM isolation; it is defense-in-depth. See [LIMITATIONS.md](LIMITATIONS.md).
- **Policy binding**: When the runner is used, script hash and policy digest can be bound into the seal via **sandbox_metadata**, so the provenance record includes which script and policy were in effect.
- **Routing**: The seal can store a routing path and other control metadata. Verification ensures these are part of the hashed payload so they cannot be changed without changing the EPW.

## Mapping implementation artifacts to technical value

| Artifact        | Technical role                                                                 |
|-----------------|---------------------------------------------------------------------------------|
| Seal (EPW)      | Tamper-evident, content-derived provenance; deterministic recomputation.        |
| Audit chain     | Append-only execution evidence; hash chain and head binding to seal.           |
| Fixed range     | Technical correction for histogram auto-scaling; stable, reproducible H2.       |
| Cache + report  | Measured compute efficiency; bounded reuse with evidence (reason, MAD, size).   |
| Config vector   | Stored in seal; verifier uses it to recompute. Enables deterministic verify.    |
| Runner policy   | System-control improvement; script and policy bound into seal when used.      |

## Novel aspects (implementation-focused)

- **Dual-channel seal with content-derived root**: Seal is written to sidecar and optional c2pa stub, but verification is defined as recomputation from artifact + config, not “trust the sidecar.”
- **Fixed-range H2 in a provenance pipeline**: Explicit choice to avoid per-sample range adaptation and to document the rationale.
- **Cache with evidence report**: Reuse is gated by spot-check and config/schema; every run gets a structured cache outcome (hit/miss, reason, validation metrics) in the report.
- **Seal binds audit head and optional runner metadata**: Single EPW commits to content, config, audit chain head, and (when present) script/policy evidence.
