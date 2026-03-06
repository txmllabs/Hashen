# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **Branch reconciliation**
  - Reconciled `upgrade` work onto `main` (unified CLI, schemas, verification, compliance policy, restricted execution hardening).
- **CLI**
  - Unified `hashen run` supports `--target-id` and `--bundle-id` for manifest/audit binding (legacy entry points preserved).
- **Verification**
  - Manifest verification now cross-checks `content_fingerprint`, `seal_hash`, `audit_head_hash`, and `report_hash` when present.

- **Docs**
  - README: "What Hashen guarantees" vs "does not guarantee", threat model summary, verification flow, evidence bundle contents, development status.
  - `docs/ARCHITECTURE.md`: ingest → analytics → cache → audit → seal → verify; trust boundaries; config vector; audit_head_hash; runner policy boundary.
  - `docs/LIMITATIONS.md`: subprocess vs container isolation, AST/policy as defense-in-depth, signature support status, platform caveats.
- **Packaging**
  - Console scripts: `hashen-bundle`, `hashen-verify`, `hashen-retention` (CLI under `src/hashen/cli/`).
  - `__version__` in `src/hashen/__init__.py`.
  - Dev extra: pytest, pytest-cov, ruff, pip-audit, cyclonedx-bom, pre-commit.
- **Seal**
  - Deterministic binding: `config_vector_hash`, optional `policy_digest`, `schema_version` in payload.
  - Reason codes: `SCHEMA_VERSION_UNSUPPORTED`, `POLICY_DIGEST_MISMATCH`, `MANIFEST_HASH_MISMATCH`, `REQUIRED_FIELD_MISSING`.
  - Backward compatibility: old seals without `config_vector_hash` still verify.
- **Audit**
  - `schema_version` on events; required-field validation; structured errors for malformed JSONL; explicit prev_hash linkage checks.
- **Cache**
  - `schema_version`, `config_vector_hash`, `created_at` in entries; reuse only when fingerprint, config hash, schema version match and spot-check passes; corrupted entry fails closed.
- **Runner**
  - Wording: "restricted execution runner" (no "secure sandbox" overclaim). Optional `strict_mode` (requires `script_sha256`), `max_stdout_bytes`; constants `STRICT_MODE_REQUIRES_SCRIPT_HASH`, `STDOUT_OVERSIZED`.
- **Bundle**
  - `manifest.json` in each evidence bundle (file list + SHA-256 per file, seal_hash, audit_head_hash); verify step checks manifest when present.
- **CI**
  - Install dev extras; pytest; ruff check/format; pip-audit; CycloneDX SBOM artifact.
- **Release**
  - Workflow skeleton: build sdist/wheel, SHA256SUMS, upload artifacts (`.github/workflows/release.yml`).

### Changed

- README and threat model: removed "enterprise-grade secure sandbox"; runner described as restricted execution.
- SECURITY.md: supported versions, implementation caveats.

### Security

- Fail-closed cache on corrupted or mismatched config/schema.
- Seal and audit verification reject tampering with explicit reason codes.
- Manifest verification fails on missing or altered files.

### Fixed / Repairs (branch integrity pass)

- **Multiline source/config**: No flattened or single-line files found in audit; `.gitattributes` enforces LF so GitHub raw views and CI stay consistent. Key files (pyproject.toml, ci.yml, seal.py, event_log.py, bundle.py, verify.py, README.md) are valid multiline.
- **Package and CLI**: Validated `pip install -e ".[dev]"`, console scripts (hashen-bundle, hashen-verify, hashen-retention), compileall, pytest, ruff, pip check. CLI exit codes: 0 on success, 1 on failure; tamper detected (MANIFEST_HASH_MISMATCH or EPW_MISMATCH).
- **CI workflow**: `.github/workflows/ci.yml` is valid multiline YAML with checkout, Python setup, editable install, compile, pytest, ruff check/format, pip-audit, SBOM, evidence-bundle smoke test.
- **Cleanup**: Removed duplicate/stale `README.txt` and `Makefile.txt`; canonical files are `README.md` and `Makefile`.
- **GitHub normalization**: README, pyproject.toml, and .github/workflows/ci.yml stored with LF line endings so raw GitHub serves multiline; accidental branch removed.
- **Main branch normalization**: Honest README on default branch; multiline pyproject.toml and ci.yml on raw.
- **Public main repair**: Explicit LF normalization and multiline config/docs; branch cleanup verified.

## [0.1.0] - (pre-hardening)

- Initial prototype: seal (EPW), audit chain, cache, subprocess runner, evidence bundle tooling.
