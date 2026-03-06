# Policy engine

The policy engine evaluates run context (retention, legal hold, classification, PII, consent, purpose, sharing restrictions, action) and returns a **decision** (allow, warn, deny) with **reasons** and a **policy version**. Results are JSON-serializable and written into the audit trail and report.

## Input (RunContext)

- **run_id**, **target_id**
- **data_classification** – public, internal, confidential, restricted (required in strict mode if used).
- **data_source_type** – public, user_provided, partner.
- **retention_raw_ttl_hours**, **retention_derived_ttl_days**
- **legal_hold** – boolean.
- **pii_present** – yes, no, unknown.
- **consent_basis**, **lawful_basis**, **purpose_of_processing**, **sharing_restrictions**
- **action** – run, export, share, purge, delete.
- **strictness** – permissive, standard, strict.

## Output (PolicyResult)

- **decision**: `allow` | `warn` | `deny`
- **reasons**: list of `{ "code": "...", "severity": "error"|"warning"|"info", "message": "..." }`
- **effective_policy**: e.g. strictness, action, legal_hold
- **evaluated_at**: ISO timestamp
- **policy_version**: e.g. hashen.policy.v1

**Semantics**: If any reason has severity `error`, decision is **deny**. Otherwise, if any reason has severity `warning`, decision is **warn**. Otherwise **allow**. The pipeline proceeds only when decision is not deny (allow or warn).

## Rules (enforced)

| Rule | Description | Deny when |
|------|-------------|-----------|
| retention_required | Retention policy (raw/derived TTL) | Strict mode and both TTLs missing |
| legal_hold_conflict | Purge/delete while legal_hold=true | action in (purge, delete) and legal_hold |
| pii_handling | PII present but basis/purpose missing | Strict: PII yes and missing consent_basis or purpose |
| classification_known | data_classification set | Strict: classification missing/empty |
| consent_user_data | User-provided data has consent/lawful basis | Warning only (user_provided + no basis) |
| purpose_strict | purpose_of_processing set | Strict: purpose missing |
| sharing_export | Export/share allowed by restrictions | action export/share and sharing_restrictions forbid |
| report_compliance_fields | Report has required compliance fields | Warning only |

## Strictness

- **permissive**: Few requirements; mostly warnings.
- **standard**: Missing retention is warning; legal_hold vs purge/delete is error; PII handling can warn.
- **strict**: Missing retention, unknown classification, or missing purpose are errors. PII without basis/purpose is error.

## CLI

- **hashen policy check** [bundle_dir] [--strictness ...] [--action ...] [--legal-hold] ...  
  Evaluate policy for a bundle (from report.json) or from context flags. Exit 0 if allowed, 1 if deny/warn (or 1 on deny only depending on desired semantics; current: 0 if allowed, 1 if denied).
- **hashen policy explain**  
  Same as check; prints full reasons and triggered rules (same output shape, for human inspection).

## Integration

- **Orchestrator**: After COMMAND_RECEIVED and FETCH, the pipeline builds RunContext (from kwargs or run_context), calls `evaluate(ctx)`, appends POLICY_EVALUATED to the audit log, and if decision is deny returns a structured result (policy_denied=True, policy_decision, policy_reasons, audit_head_hash). No seal or report is written. If allow/warn, the run continues and the report includes the policy result in the compliance block.
