# Fixed entropy range

## Why the H2 range is preconfigured

The H2 (second-order entropy) histogram is built over a **fixed, preconfigured** range defined in the config vector (`h2_min`, `h2_max`, `h2_bins`). The range is **not** derived from the sample (e.g. not from min/max of the current artifact).

Reasons:

1. **Determinism**: Same artifact + same config → same H2 and same seal hash. If the range were adapted per sample, two runs on the same artifact could yield different hashes if the pipeline or input ordering changed.

2. **Avoiding auto-scaling artifacts**: When histogram bins are auto-ranged from sample min/max, small changes in the sample (e.g. one extra value at the tail) can shift bin boundaries and change entropy. That would make verification unstable and reduce the value of content-derived provenance.

3. **Reproducibility**: A verifier with the artifact and the seal (which stores `config_vector`) can recompute H2 exactly. Fixed range guarantees the same bin boundaries.

## Implementation

- **Config fields**: `h2_min`, `h2_max`, `h2_bins` in `config_vector`. Optional policy marker: `fixed_range_policy: "preconfigured_no_autorange"`.
- **Code**: `entropy_h2()` in `hashen.analytics.entropy_engine` uses only these config values. Values outside the range are clamped into the first or last bin.
- **Low-variance data**: Even when the sample has very low variance (e.g. all values near one number), the same fixed range is used; there is no fallback to “auto-range” or per-sample scaling.

## Modality-specific defaults

For a single modality (e.g. raw bytes normalized to [0,1]), typical defaults are `h2_min=0`, `h2_max=log2(h2_bins)` or `h2_max=1`, `h2_bins=16`. Callers should set these explicitly in config for reproducible runs.
