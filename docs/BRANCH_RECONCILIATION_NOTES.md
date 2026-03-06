## Branch reconciliation notes (origin/main vs origin/upgrade)

Date: 2026-03-06

This repo currently has two active remote branches:

- `origin/main` (default): contains recent PR merge commits
- `origin/upgrade`: contains the newer SDK/CLI/schema/verification surface

Merge base:

- `merge-base(origin/main, origin/upgrade)` = `d04d610d07148a11af8bd802230523f08cf7ea72` (`fix: repair public main state, rewrite multiline config/docs, and normalize branch cleanup`)

### Commit-level delta

**Unique commits on `origin/upgrade` (not on `origin/main`)**

- `75ede43` — Verification / Evidence SDK
- `fc7d2f7` — hashen improvements

**Unique commits on `origin/main` (not on `origin/upgrade`)**

- `0e072ad` — Merge pull request #5 from txmllabs/main
- `f35a542` — Merge pull request #6 from txmllabs/fix/github-normalization-pass

### File-level delta (three-dot diff: merge-base → upgrade)

`origin/upgrade` adds/changes the following areas relative to the merge base:

- **Unified CLI**
  - `src/hashen/cli/main.py` (new `hashen` CLI)
  - updates to `src/hashen/cli/bundle.py`
- **Schemas and packaging**
  - `schemas/*.schema.json` (repo-root schema sources)
  - `src/hashen/schemas/*` (package-data copy + loader/validators)
  - `pyproject.toml` updated to include `hashen` script + package data
- **Structured verification**
  - `src/hashen/verification/*`
  - tests: `tests/test_verification_unified.py`, `tests/test_schemas.py`
- **Compliance-aware provenance**
  - `src/hashen/compliance/*` additions (policy engine + lifecycle + redaction)
  - `src/hashen/orchestrator/orchestrator.py` integration (POLICY_EVALUATED event, deny path)
  - `src/hashen/audit/models.py` adds `POLICY_EVALUATED`
  - tests: `tests/test_compliance_policy.py`
- **Restricted execution hardening (best-effort)**
  - `src/hashen/sandbox/*` changes: posture, layered AST validation, structured exec result
  - tests: `tests/test_execution_hardening.py`
- **Docs**
  - `docs/bundle-format.md`, `docs/schema-versioning.md`, `docs/verification-model.md`
  - `docs/compliance-model.md`, `docs/policy-engine.md`, `docs/data-lifecycle.md`
  - `docs/execution-security.md`
  - updates to `README.md`, `docs/LIMITATIONS.md`, `docs/REASON_CODES.md`

### Files/behavior unique to `origin/main`

At the commit level, `origin/main` primarily carries the newer PR merge commits. These PR merges
must be preserved to keep the public default branch aligned with GitHub history and any release/CI
checks attached to those merges.

### Identified reconciliation risks / conflict hotspots

- **README / docs overlap**: both branches touch security/language; ensure wording is consistent and honest.
- **CLI contract**: `hashen` unified CLI must not break legacy entry points (`hashen-bundle`, `hashen-verify`, `hashen-retention`).
- **Verification semantics**: ensure `ok` and exit codes match a clear trust model (fatal vs warning).
- **Manifest/report consistency**: ensure manifest hashes and cross-link fields are consistently verified.
- **Schema packaging**: ensure schemas are loadable in editable install and packaged install.

### Recommended merge direction

Use `origin/main` as the base (final target branch remains `main`) to preserve PR merge history.
Then merge or cherry-pick the two `origin/upgrade` commits onto a reconciliation branch created
from `origin/main`.

Recommended working branch name:

- `codex/reconcile-main-upgrade` (created from `origin/main`)

### Files to preserve from each side

**Preserve from `upgrade` (port into `main`)**

- Unified CLI: `src/hashen/cli/main.py`
- Schemas + loader: `schemas/*.schema.json`, `src/hashen/schemas/*`
- Verification package: `src/hashen/verification/*`
- Compliance policy engine + lifecycle: `src/hashen/compliance/*`
- Restricted execution hardening: `src/hashen/sandbox/*`
- New docs: `docs/execution-security.md` and compliance/verification docs
- New tests: `tests/test_*` added on upgrade

**Preserve from `main`**

- PR merge commits and any associated CI/workflow fixes from `origin/main`
- Any public-state normalization work already merged into `origin/main`

### Next steps (implementation plan)

1. Create `codex/reconcile-main-upgrade` from `origin/main`.
2. Merge `origin/upgrade` into the reconciliation branch and resolve conflicts file-by-file.
3. Tighten unified CLI (`--target-id`, config handling, stable JSON, exit codes).
4. Tighten verification semantics (fatal vs warning) and manifest/report consistency checks.
5. Ensure schema packaging and tests cover both repo and installed-package schema loading.
6. Add/extend regression tests for merge-risk areas (legacy CLIs, unified CLI, schemas, verification).
7. Update `CHANGELOG.md` to document the reconciliation and any behavior changes.

