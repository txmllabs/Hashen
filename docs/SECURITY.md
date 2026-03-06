# Hashen Security

## Deterministic recomputation

Verification is **deterministic**: a third party can reproduce the EPW (seal) hash using:

- The artifact bytes
- The stored `config_vector` in the seal

No server-side secrets are required. The seal hashes a canonical payload (H1 subset, per-modality H2, combined H2, resonance, routing path, config vector, audit head hash, sandbox metadata); the timestamp is stored but excluded from the hash so the same artifact and config always yield the same EPW.

## Fixed entropy range (H2)

The H2 entropy range is **fixed and preconfigured** via `config_vector` (e.g. `h2_min`, `h2_max`, `h2_bins`). It is **not** derived from the input sample distribution—no per-sample auto-ranging. This ensures consistent, reproducible metrics and avoids manipulation via input distribution.

## Security artifact and audit chain

- **Seal (EPW)**: Cryptographic provenance certificate binding artifact content, config, and audit head. Tampering the artifact or the seal causes verification to fail with `EPW_MISMATCH`.
- **Audit chain**: Append-only, hash-chained event log per run. Tampering any event breaks the chain; verifier returns `AUDIT_CHAIN_BROKEN`.
- **Routing**: Routing path and decisions are recorded in the seal and audit for accountability.

## Measurable efficiency

- Cache is content-fingerprint keyed with spot-check validation; cache hit rate and speedup (wall time) are recorded in `reports/<run_id>.json` for evidence and tuning.

## Secure by default

- No network in sandbox unless explicitly allowed.
- Minimal storage; short TTL for raw artifacts (default 24 hours).
- Evidence bundles: every run can emit a reproducible bundle (artifact + audit + seal + verify outputs) for offline verification.

## Patent / prosecution alignment

The design emphasizes:

- Deterministic recomputation from `config_vector`
- Fixed preconfigured H2 range (no auto-ranging)
- Security artifact (seal) + audit chain + routing as technical improvements
- Measurable efficiency (cache hit rate, speedup logs)

These are the allowance levers for patent and prosecution strength.
