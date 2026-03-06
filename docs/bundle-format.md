# Bundle format

Evidence bundles produced by Hashen use a canonical layout and manifest for integrity and verification.

## Canonical layout

```
bundle/
  artifact.bin       # or "artifact" – copy of the input artifact
  seal.json         # Provenance seal (EPW hash, config_vector, audit_head_hash, etc.)
  audit.jsonl       # Hash-chained audit log (one JSON object per line)
  verify.json       # Verification result (ok, reason, seal_hash, audit_head_hash)
  report.json       # Optional per-run compliance report
  manifest.json     # File inventory and SHA-256 per file (does not list itself)
```

## Manifest (manifest.json)

The manifest lists every file in the bundle (except itself) and its SHA-256 hash. It may also include:

- **schema_version**: `hashen.manifest.v1`
- **created_at**: ISO 8601 timestamp when the bundle was created
- **bundle_id**: Run or bundle identifier
- **target_id**: Target identifier (e.g. `default`)
- **content_fingerprint**: Digest of the artifact (e.g. artifact SHA-256)
- **seal_hash**: EPW hash from the seal (for quick reference)
- **audit_head_hash**: Head of the audit chain (for quick reference)
- **report_hash**: SHA-256 of report.json if present
- **tool_version**: Hashen version that produced the bundle
- **files**: Object mapping file name → SHA-256 hex string

The manifest does **not** include itself in the file inventory to avoid circularity when verifying hashes.

## Verification

- **Seal**: Recompute deterministic payload from artifact + `config_vector` in seal; compare EPW hash.
- **Audit**: Verify each line’s `prev_hash` / `event_hash` chain; confirm head matches seal’s `audit_head_hash`.
- **Manifest**: For each entry in `files`, ensure the file exists and its SHA-256 matches.
- **Report** (if present): Optionally check schema and consistency of `seal_hash` / `audit_head_hash` with seal and audit.

See [verification-model.md](verification-model.md) for reason codes and pass/fail semantics.
