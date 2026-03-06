# Schema versioning

Hashen artifacts (seal, report, bundle manifest, audit event, verification result) carry a **schema_version** field. Verifiers use it to accept or reject payloads and to preserve backward compatibility.

## Schema names and versions

| Artifact | Schema version (current) | Location |
|----------|--------------------------|----------|
| Seal | `hashen.seal.v1` | seal.json |
| Report | `hashen.report.v1` | report.json |
| Bundle manifest | `hashen.manifest.v1` | manifest.json |
| Audit event | `hashen.audit.v1` | each line of audit.jsonl |
| Verification result | (no fixed const) | output of `hashen verify` |

JSON Schema definitions are under `schemas/` in the repo and shipped in the package for validation.

## Backward compatibility

- **Seal**: Verifiers ignore unknown top-level fields. Old seals without `config_vector_hash` still verify; new seals include it when available.
- **Audit**: Events without `schema_version` or required fields yield `AUDIT_CHAIN_BROKEN` with a structured reason.
- **Manifest**: Unsupported `schema_version` yields manifest verification failure (e.g. `MANIFEST_SCHEMA_VERSION_UNSUPPORTED`).
- **Report**: Report schema validation is used for warnings; consistency checks (seal_hash, audit_head_hash) are enforced when report is present.

## Unsupported versions

If a seal or other artifact uses a **future** schema version the verifier does not support (e.g. `hashen.seal.v2` when only v1 is supported), the verifier returns a failure with a reason such as `SCHEMA_VERSION_UNSUPPORTED` or a schema validation warning. Emitted artifacts should use the current version; validators can be run via `hashen.schemas` (e.g. `validate_seal`, `validate_report`).

## Listing schemas

```bash
hashen schema list [--pretty]
```

Returns the list of supported schema names and their current version (const) from the JSON Schema files.
