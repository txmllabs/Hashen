# Patent Claim → Code Mapping

This document maps patent claims (v5.3) to their implementation in this repository.

## Independent Claims

| Claim | Description | Implementation | Test |
|-------|-------------|----------------|------|
| 1 | TSEC signal transformation | `analytics/tsec.py::tsec_cascade()` | `test_tsec_cascade.py` |
| 6 | System with routing | `orchestrator/orchestrator.py::run_pipeline()` + `analytics/routing.py::route()` | `test_evidence_bundle.py` + `test_routing.py` |
| 15 | EPW provenance | `provenance/seal.py::create_seal()` | `test_seal_verify.py` |
| 18 | Audio forensics | `analytics/pathways/audio.py::audio_to_spectral_h1()` + `tsec.py` | `test_pathways.py` |
| 22 | Financial fraud | `benchmarks/datasets.py::generate_financial_dataset()` + `tsec.py` | `test_benchmarks.py` |

## Key Dependent Claims

| Claim | Description | Implementation | Test |
|-------|-------------|----------------|------|
| 2 | Modality pathways | `analytics/pathways/{image,audio,timeseries,graph,text}.py` | `test_pathways.py` |
| 3 | Fixed range | `tsec.py::compute_h2_fixed_range()` with h2_min/h2_max from config | `test_entropy_fixed_range.py` + `test_tsec_cascade.py` |
| 4 | CMER | `analytics/resonance.py::cross_modal_resonance()` | `test_resonance_cmer.py` |
| 5 | Burst detector | NOT YET IMPLEMENTED (future) | — |
| 11 | X-caching | `cache/fingerprint_cache.py::cache_lookup_with_spotcheck()` | `test_cache_correctness.py` |
| 12 | Script loading | `sandbox/runner_subprocess.py` + `sandbox/validation.py` | `test_sandbox_policy.py` |
| 13 | Synthetic training | NOT YET IMPLEMENTED (future) | — |
| 16 | C2PA integration | `provenance/seal.py::write_seal()` (stub) | `test_seal_verify.py` |
| 17 | Config vector | Stored in seal record; used for deterministic recomputation | `test_seal_verify.py` |

## Verification Flow (Claim 15)

1. Load artifact and seal record
2. Extract config_vector from seal
3. Recompute TSEC (H1 + H2) from artifact using config_vector
4. Recompute EPW hash from deterministic payload
5. Compare recomputed hash to stored hash
6. If match: authentic. If mismatch: tampered (EPW_MISMATCH).

Implemented in: `provenance/seal.py::verify_seal()`
