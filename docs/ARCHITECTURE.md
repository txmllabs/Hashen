# Architecture

## Ingest → analytics → cache → audit → seal → verify

1. **Ingest**: Artifact bytes (e.g. file content) are read. No assumption about format beyond bytes; normalization to a value vector is deterministic (e.g. byte/255).

2. **Analytics**: From the value vector, the pipeline computes:
   - **H1 subset**: Configurable subset of the vector (e.g. for fingerprinting).
   - **H2**: Entropy over a **fixed, preconfigured** range (from `config_vector`). No per-sample auto-ranging.
   - **Combined H2**, **resonance**: Derived metrics for the seal.

3. **Cache**: Key is content-based (`target_id` + content fingerprint). A cache hit is allowed only if:
   - Entry exists for that key.
   - Schema/config version and (optional) config_vector_hash match.
   - Spot-check (e.g. mean absolute difference on H1 subset) passes.
   Cache is an optimization; it does not replace seal verification.

4. **Audit**: Every significant step is appended to an append-only JSONL log. Each event has:
   - `event_type`, `prev_hash`, payload fields, and `event_hash` (hash of the event minus `event_hash`).
   - Events form a chain: `prev_hash` of event N = `event_hash` of event N−1.
   - **audit_head_hash**: The `event_hash` of the last event. This is the value bound into the seal.

5. **Seal**: A deterministic payload is built from artifact, `config_vector`, `audit_head_hash`, and optional routing/resonance/sandbox metadata. Non-deterministic fields (e.g. `issued_at`) are excluded from the hashed body. The **EPW hash** is SHA-256 of the canonical JSON of that payload. The seal record stores the payload, `issued_at`, and `epw_hash`.

6. **Verify**: Load artifact and seal; recompute the deterministic payload from artifact and seal’s `config_vector`; recompute EPW; compare to seal’s `epw_hash`. If an audit log path is provided, verify the chain and that its head equals the seal’s `audit_head_hash`.

---

## Trust boundaries

- **Artifact**: Untrusted. Verification recomputes from it; tampering changes the EPW.
- **Config vector**: Trusted at verification time (stored in the seal). Mismatch or omission can be detected via config_vector_hash or schema checks.
- **Audit log**: Untrusted storage. Integrity is enforced by the hash chain and binding to the seal via `audit_head_hash`.
- **Cache**: Untrusted. Entries are validated by content key, config/schema, and spot-check before reuse.
- **Runner**: Scripts are untrusted. The runner enforces a denylist and timeout; it is not a full sandbox (see LIMITATIONS).

---

## Config vector role

The **config vector** drives deterministic behavior:

- **H1/H2**: e.g. `h1_subset_size`, `h2_min`, `h2_max`, `h2_bins`. Same config + same artifact → same derived values and thus same seal hash.
- **Stored in seal**: Verifier reads `config_vector` from the seal to recompute the payload. No separate secret; verification is reproducible by anyone with artifact + seal.
- **config_vector_hash** (optional): A hash of the config vector can be stored and checked so that reuse (e.g. cache) or verification fails if config is changed.

---

## audit_head_hash binding

- The audit log’s last event has an `event_hash`. That value is **audit_head_hash**.
- The seal stores `audit_head_hash` in its (hashed) payload. So the seal commits to a specific audit chain head.
- Verification can: (1) verify the audit chain from the log file, (2) compare the chain’s head to the seal’s `audit_head_hash`. If either fails, verification fails with `AUDIT_CHAIN_BROKEN`.

---

## Runner policy boundary

- The **restricted execution runner** runs user scripts in a subprocess with:
  - **Policy**: AST-based import denylist (e.g. `os`, `socket`, `subprocess`), no network by default, timeout, optional resource limits (Unix).
  - **Policy version / digest**: A fixed policy version and a digest of the denylist can be used for audit binding and to reject runs when policy has changed.
- The runner does **not** provide container or VM isolation. It is defense-in-depth only. See [LIMITATIONS.md](LIMITATIONS.md).
