# Branch status review (main vs upgrade)

Date: 2026-03-06

This document summarizes the current state of `origin/main` and `origin/upgrade` after reconciliation work, and the recommended way to keep the repo clean and reviewable.

---

## 1. Current branch state

- **origin/main** (default): `a445bba` — merge commit "merge: reconcile upgrade into main". Main already contains the reconciled codebase: unified CLI, structured verification, manifest cross-checks, schema packaging, compliance policy, restricted-execution hardening, and doc updates.
- **origin/upgrade**: `fc7d2f7` — "hashen improvements" (two commits ahead of merge-base: Verification/Evidence SDK and hashen improvements).
- **Local branches**: `main`, `upgrade`, `codex/reconcile-main-upgrade`, `fix/github-normalization-pass`, `2026-03-05-a0wf`.

Reconciliation was done by creating `codex/reconcile-main-upgrade` from `origin/main`, merging `origin/upgrade` into it, then merging that branch into `main`. So **main is the canonical branch** and already has the best of upgrade plus post-merge fixes.

---

## 2. What exists only on main

Relative to `origin/upgrade`, **main** has:

- **docs/BRANCH_RECONCILIATION_NOTES.md** — present on main, absent on upgrade (reconciliation plan and file-preservation list).
- **Stronger manifest and verification**: `src/hashen/provenance/bundle_manifest.py` and `src/hashen/verification/verify.py` on main include enhanced cross-file consistency checks (manifest seal_hash, audit_head_hash, report_hash, content_fingerprint) and explicit fatal vs warning semantics.
- **CLI improvements**: `src/hashen/cli/main.py` and `src/hashen/cli/bundle.py` on main support `--target-id`, `--bundle-id`, and clearer config handling; no hardcoded `target_id` without an explicit fallback.
- **Docs**: More complete `CHANGELOG.md`, and expanded `docs/REASON_CODES.md`, `docs/bundle-format.md`, and `docs/verification-model.md` (manifest checks, fatal vs warning, reason codes).
- **README**: Small wording alignment on main for consistency with the trust model.

So all “reconciliation hardening” (verification semantics, manifest consistency, CLI flags, docs) exists **only on main**.

---

## 3. What exists only on upgrade

Nothing of value. **upgrade** is an older feature branch. The diff `origin/main..origin/upgrade` shows upgrade *removing* or *reverting* content that main has (e.g. no BRANCH_RECONCILIATION_NOTES, slimmer CHANGELOG, and older/simpler versions of the 10 files listed in the diff). Any unique code that was only on upgrade has already been integrated into main via the reconciliation merge.

---

## 4. Which branch has the better CLI / schema / verification surface

**main** has the better surface:

- **CLI**: Unified `hashen` with `run`, `verify`, `bundle inspect`, `bundle doctor`, `schema list`, `policy`, `retention`, `exec`; legacy `hashen-bundle`, `hashen-verify`, `hashen-retention` preserved; explicit `--target-id`, `--bundle-id`, `--pretty`; structured JSON and non-zero exit codes on verification failure.
- **Schema**: Schemas under `src/hashen/schemas/` and package data; loadable in editable and installed installs; validation helpers and `hashen schema list`.
- **Verification**: Single authoritative path in `hashen.verification`; `VerificationResult` with `ok`, `seal_valid`, `audit_chain_valid`, `report_present`, `report_valid`, `manifest_present`, `manifest_valid`, `errors`, `warnings`, `reason_codes`, `checked_files`; manifest cross-checks and clear fatal vs warning semantics.

---

## 5. Redundant or stale files / branches

- **origin/upgrade**: Stale. It does not contain the reconciliation fixes or the extra docs. Safe to archive or delete after confirming no external references.
- **codex/reconcile-main-upgrade**: Reconciled branch already merged into main; can be deleted locally (and remotely if it was pushed) to reduce clutter.
- **fix/github-normalization-pass**, **2026-03-05-a0wf**: Already merged into main via PRs; local copies can be deleted if no ongoing work.
- **docs/BRANCH_RECONCILIATION_NOTES.md** vs **docs/BRANCH_STATUS_REVIEW.md**: The former describes the plan and merge steps; this file (BRANCH_STATUS_REVIEW) is the current status and “what to do next”. Both can live in docs; no redundancy issue.

No redundant *files* inside the tree; only branch pointers are redundant once reconciliation is accepted.

---

## 6. Phase 1 step 3 — working branch for further work

Because reconciliation is already merged into main:

- **Do not** recreate the old working branch (`codex/reconcile-branches-verification-sdk`).
- If additional changes are needed (Phases 2–9: CLI/verification/manifest/schema/docs/tests/polish), create a **fresh** branch from main:
  - `codex/verification-sdk-hardening-pass`
- Proceed with Phases 2–9 on that branch. If you are already on an appropriate unmerged working branch with the intended changes, continue there.

---

## 7. Recommended reconciliation plan (current)

Reconciliation is **done** on main. Recommended next steps:

1. **Treat main as the only canonical branch.** All new work (PRs, fixes, features) should target main.
2. **Optional branch cleanup**  
   - Delete local branches that are fully merged: e.g. `codex/reconcile-main-upgrade`, `fix/github-normalization-pass`, `2026-03-05-a0wf`.  
   - If no one relies on `origin/upgrade`, consider `git push origin --delete upgrade` after team agreement.
3. **No further merge from upgrade into main.** Main already has the desired state; merging upgrade again would revert the hardening and doc improvements.
4. **Ongoing work**: Keep improving trust model, CLI, verification, and docs on main only; keep execution-security claims honest (restricted execution, best-effort, tamper-evident).

For the original merge plan and file-preservation list, see **docs/BRANCH_RECONCILIATION_NOTES.md**.

**Current session**: Branch `codex/verification-sdk-hardening-pass` created from main for any further hardening (Phases 2–9); new doc and subsequent commits go there until merged back to main.

---

## 8. Verification path reconciliation (completed)

The following was done to consolidate verification into a single path and extend the result model:

- **Legacy `hashen-verify`** routes through unified verification: `hashen.cli.verify` calls `verify_bundle_result(bundle_dir)` and maps the result to the legacy output shape (`ok`, `reason`, `audit_head_hash`, `seal_hash`). Exit code and `--json` / human output behavior are unchanged.
- **`hashen bundle doctor`** runs via unified verification: `_cmd_bundle_doctor` calls `verify_bundle(root)`, uses `result.errors` as fatal and `result.warnings` as warnings, and still adds a legal_hold warning from `report.json` when present. Output shape remains `ok`, `fatal`, `warnings`, `path`.
- **`VerificationResult`** extended with:
  - **`reason_codes`**: sorted list of stable codes derived from `errors` and `warnings` (e.g. `MISSING_FILE`, `EPW_MISMATCH`, `MANIFEST_INCONSISTENT`).
  - **`checked_files`**: list of bundle files actually checked (e.g. `artifact.bin`, `seal.json`, `audit.jsonl`, `manifest.json`, `report.json`). Both are set on every return (including early returns) and included in `to_dict()` for CLI/JSON.
- **Legacy CLI output** is unchanged: `hashen-verify --json` still prints only `ok`, `reason`, `audit_head_hash`, `seal_hash`; non-JSON still prints "Verification OK" or "Verification FAILED: …" (to stderr on failure).
- **Tests**: `test_evidence_bundle.py` accepts failure output on stderr for tamper-then-verify. `test_verification_unified.py` asserts that `verify_bundle_result` output includes `reason_codes` and `checked_files` and that `checked_files` contains the expected entries.

All verification now flows through `hashen.verification.verify_bundle` / `verify_bundle_result`; there is no duplicate seal/audit/manifest logic in the legacy CLI or bundle doctor.
