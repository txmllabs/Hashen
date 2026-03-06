# Cache spot-check mechanism

## Purpose

The content-fingerprint cache stores derived analytics (H1 subset, per-modality H2, resonance) so that repeated runs on the same artifact with the same config can reuse them. Reuse is **bounded and evidence-backed**: a hit is allowed only when several conditions hold, and each run records measurable evidence (hit/miss, reason, validation metrics).

## When reuse is allowed

A cache **hit** occurs only when:

1. **Entry exists** for the key `sha256(target_id + content_fingerprint)`.
2. **Schema version** of the entry matches the current `CACHE_SCHEMA_VERSION`.
3. **Config vector hash** of the entry matches the current config (if provided).
4. **Spot-check passes**: the cached H1 subset and the newly computed H1 subset have mean absolute difference ≤ tolerance (default 1e-6).

Any failure yields a **miss** (fail closed). The report records the reason (e.g. `miss_no_entry`, `miss_spotcheck_failed`).

## Spot-check in plain language

- The pipeline computes an H1 subset (a short list of floats) from the artifact using the config.
- The cache stores the H1 subset that was computed the first time for that (target_id, content_fingerprint, config).
- On a later run, we compute H1 again from the same artifact. Before reusing the cached entry, we compare the **cached H1 subset** and the **newly computed H1 subset**.
- We compute the **mean absolute difference** (MAD): average of `|cached[i] - computed[i]|` over the overlapping length.
- If MAD ≤ tolerance, we treat the run as identical for the purpose of reuse and return a hit; otherwise we return a miss and recompute.

This is a **validation subset**: we do not compare the full artifact, only this derived vector, so the check is cheap and deterministic. The size of the subset is recorded in the report (`validation_subset_size`).

## Report fields

Per-run reports (when using `cache_lookup_with_spotcheck_report`) include:

- **cache_hit**: boolean
- **cache_reason**: `"hit"` | `"miss_no_entry"` | `"miss_schema_mismatch"` | `"miss_config_mismatch"` | `"miss_spotcheck_failed"`
- **validation_subset_size**: length of the H1 subset used in the spot-check
- **mean_abs_diff**: the MAD value (null on miss when no comparison was done, or when reason is no_entry/schema/config)

Optional **time_saved_ms** can be set by the caller if wall time is measured (e.g. second run with hit vs first run without).

## Technical value

- **Measurable**: Every run has a recorded reason and, on hit, a numeric difference. No silent reuse.
- **Bounded**: Reuse is limited to same content, same config, and passing spot-check.
- **Evidence-backed**: Reports are machine-readable and can be retained for compliance or prosecution support.
