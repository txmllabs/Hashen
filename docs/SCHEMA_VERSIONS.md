# Schema and policy versions

Hashen uses versioned schema and policy identifiers for forward compatibility and audit binding. All serialized artifacts include a `schema_version` field. Central constants live in `hashen.schemas` (re-exports from seal, audit, cache, compliance, manifest modules).

## Current versions

| Identifier       | Value               | Where used                          |
|------------------|---------------------|-------------------------------------|
| Seal             | `hashen.seal.v1`    | Seal payload (`schema_version`)     |
| Audit event      | `hashen.audit.v1`   | Each audit JSONL event             |
| Cache entry      | `hashen.cache.v1`   | Cache entry JSON                    |
| Report           | `hashen.report.v1`  | Compliance report JSON              |
| Manifest         | `hashen.manifest.v1`| Bundle `manifest.json`              |
| Sandbox policy   | `hashen.policy.v1`  | Config vector, sandbox policy digest |

## Verify-time guardrails

- **Seal**: Unsupported `schema_version` → `SCHEMA_VERSION_UNSUPPORTED`.
- **Audit**: Events without `schema_version` or required fields → `AUDIT_CHAIN_BROKEN` with structured reason.
- **Manifest**: Wrong `schema_version` → `MANIFEST_SCHEMA_VERSION_UNSUPPORTED` (or equivalent).
- **Cache**: Entry with mismatched `schema_version` is not reused (fail closed).

## Compatibility rules

- **Verifier**: Accepts records with **extra unknown fields** (ignored). Fails when required fields are missing or schema version is unsupported.
- **Seal payload**: The hashed payload includes `schema_version` and `config_vector`. Same artifact + same config + same schema → same EPW hash.
- **Future changes**: New optional fields may be added without bumping the schema version. Breaking changes will use a new version (e.g. `hashen.seal.v2`).
