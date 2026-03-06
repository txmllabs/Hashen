# Roadmap and prioritized work items

Prioritized list for maintainers and contributors. For each item: problem, why it matters, and suggested acceptance criteria.

---

## Implemented (Phases 1–4)

- **TSEC cascade** → DONE (Phase 1): `analytics/tsec.py` — windowed H1, fixed-range H2, classification.
- **Modality pathways** → DONE (Phase 2): image, audio, timeseries, graph, text; dispatch in `compute_seal_analytics`.
- **CMER** → DONE (Phase 3): `analytics/resonance.py::cross_modal_resonance()`; single-modality resonance = 0.
- **Routing** → DONE (Phase 3): `analytics/routing.py::route()`; uncertainty-based path (edge / cloud / federated / human_in_loop).
- **Benchmarks** → DONE (Phase 4): `hashen benchmark run --domain audio|financial|image|all`; AUC/accuracy/Cohen's d.
- **API** → DONE (Phase 4): FastAPI `/api/v1/analyze`, `/api/v1/verify`, `/api/v1/health`, `/api/v1/config`; optional `[api]` extra.

---

## P0 (packaging, schema, verification, cache)

### Packaging / dev extras correctness

- **Problem**: Dev install and CI must consistently use the same dev dependencies; optional extras (e.g. signing) must not break default install.
- **Why it matters**: Contributors and CI need a single source of truth for "how to run tests and lint."
- **Acceptance criteria**: `pip install -e ".[dev]"` installs all tools needed for `make quality`; CI uses the same; signing extra remains optional and documented.

### Schema versioning

- **Problem**: All serialized artifacts (seal, audit, cache, report, manifest) must carry a schema version; verifiers must reject unsupported versions with a clear reason.
- **Why it matters**: Forward compatibility and safe evolution; auditors can interpret versioned payloads.
- **Acceptance criteria**: Central constants in `hashen.schemas`; every writer sets `schema_version`; every verifier checks and returns a structured code (e.g. `SCHEMA_VERSION_UNSUPPORTED`) when unsupported.

### Manifest verification

- **Problem**: Bundle consumers must be able to verify that all listed files are present and match hashes.
- **Why it matters**: Detects missing or altered files in a bundle (evidence integrity).
- **Acceptance criteria**: `hashen-verify` runs manifest verification when `manifest.json` exists; fails with clear reason (e.g. `MANIFEST_HASH_MISMATCH`, `MANIFEST_FILE_MISSING`); documented in REASON_CODES.

### Cache fail-closed behavior

- **Problem**: Cache must never reuse an entry when schema, config, or spot-check fails; corrupted entries must not be used.
- **Why it matters**: Prevents stale or poisoned results from being treated as valid.
- **Acceptance criteria**: Corrupted cache file → miss (no reuse); config/schema mismatch → miss; spot-check failure → miss; all documented and tested.

---

## P1 (runner, releases, next features)

### Burst detector (NEXT)

- **Problem**: Leaky-integrate-and-fire or similar detector on H1 array to flag burst/compression artifacts.
- **Why it matters**: Strengthens discrimination for synthetic or heavily compressed content.
- **Acceptance criteria**: Design and implement; wired into TSEC or seal metadata; tests.

### Real-world validation (NEXT)

- **Problem**: Validate on public datasets (e.g. ASVspoof, FaceForensics++, COCO/StyleGAN3) for prosecution-grade evidence.
- **Why it matters**: Benchmarks on synthetic data; real-world datasets support patent and commercial claims.
- **Acceptance criteria**: Documented runs and reported metrics; optional CI or release artifact.

### Full C2PA manifest generation (NEXT)

- **Problem**: Current C2PA output is a stub. Full C2PA manifest generation is not implemented.
- **Why it matters**: Interoperability with C2PA-based toolchains.
- **Acceptance criteria**: Document current stub; outline or implement full manifest generation.

### Stricter runner policy

- **Problem**: Runner policy could be tightened (e.g. stricter allowlist, optional signature required) for higher-assurance use cases.
- **Why it matters**: Defense-in-depth for script execution; supports "script_id only" or "signed only" modes.
- **Acceptance criteria**: Optional strict mode(s) documented; policy digest and script hash bound in seal when used; tests for rejection paths.

### Signed release artifacts

- **Problem**: Release workflow produces sdist/wheel and SHA256SUMS but does not sign artifacts (e.g. GPG/sigstore).
- **Why it matters**: Consumers can verify that downloads match the intended release.
- **Acceptance criteria**: Release workflow or checklist documents how to produce and attach signatures; or document that current releases are checksum-only and signing is future work.

### Benchmark harness

- **Problem**: No standardized way to measure pipeline latency, cache hit impact, or verification time.
- **Why it matters**: Supports performance regression detection and capacity planning; avoids hand-waved "fast" claims.
- **Acceptance criteria**: Script or make target that runs a small fixed workload multiple times and reports timings (and optionally cache hit rate); documented as benchmark, not a guarantee.

### Richer report schemas

- **Problem**: Compliance report could expose more structured fields (e.g. full config_vector, cache_reason, fixed_range) for downstream tooling.
- **Why it matters**: Machine-readable evidence for compliance and prosecution support.
- **Acceptance criteria**: Report schema versioned; key fields documented; pipeline and tests assert presence where needed.

---

## P2 (future hardening)

### Container-based runner (Docker / gVisor)

- **Problem**: Current runner is subprocess + policy; stronger isolation would require a container or VM backend.
- **Why it matters**: Enables higher-assurance script execution for environments that need it.
- **Acceptance criteria**: Design doc or spike for runner interface extension; no requirement to implement in core repo; documented as optional/future.

### HSM / signing integration

- **Problem**: Seal or audit signing with HSM or key-based signing not implemented.
- **Why it matters**: Non-repudiation and key-bound provenance for high-assurance deployments.
- **Acceptance criteria**: Design or RFC; document as future work.

### Federated entropy consensus

- **Problem**: Multi-party or federated consensus on entropy/routing not implemented.
- **Why it matters**: Distributed trust and cross-site consistency.
- **Acceptance criteria**: Design or spike only; documented as future.

### Synthetic training module

- **Problem**: No in-repo module for training or calibrating detectors from synthetic data (Claim 13).
- **Why it matters**: Supports domain-specific tuning and prosecution evidence.
- **Acceptance criteria**: Design or placeholder; documented as future.

### C2PA integration

- **Problem**: Current C2PA output is a stub (same JSON as seal). Full C2PA manifest generation is not implemented.
- **Why it matters**: Interoperability with C2PA-based toolchains and claims.
- **Acceptance criteria**: Document current stub behavior and limitations; outline steps for full C2PA manifest if pursued.

### Remote verifier service

- **Problem**: Verification today is local (artifact + seal). A remote service could verify on behalf of clients (e.g. API).
- **Why it matters**: Centralized or delegated verification for some deployments.
- **Acceptance criteria**: Design or RFC only; no requirement to implement; clarify trust model (e.g. service must be trusted).
