# Schema and policy versions

Hashen uses versioned schema and policy identifiers for forward compatibility and audit binding.

## Current versions

| Identifier            | Value               | Where used                          |
|-----------------------|---------------------|-------------------------------------|
| Seal schema           | `hashen.seal.v1`    | Seal payload (`schema_version`)     |
| Sandbox policy        | `hashen.policy.v1`  | Config vector, sandbox policy digest |

## Compatibility rules

- **Verifier**: Accepts seal records with **extra unknown fields** (ignored). Verification fails only when **required fields** are missing or invalid (e.g. `config_vector`, `epw_hash`, audit chain).
- **Seal payload**: The hashed payload includes `schema_version` and `config_vector` (including `policy_version` when set). Same artifact + same config + same schema → same EPW hash.
- **Future changes**: New optional fields may be added without bumping the schema version. Breaking changes (e.g. required field removal or meaning change) will use a new version (e.g. `hashen.seal.v2`).
