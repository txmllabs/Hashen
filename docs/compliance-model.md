# Compliance model

Hashen does **not** provide legal advice. Compliance metadata (retention, legal hold, classification, consent basis, PII flags) is implemented as **operational controls** that can be enforced as policy gates. Policy decisions become part of the evidence trail and are recorded in the audit log and report.

## Scope

- **Enforceable**: Policy engine evaluates run context and returns allow / warn / deny. Denials stop the pipeline and produce a structured result (no seal/report written; audit log still contains POLICY_EVALUATED).
- **Traceable**: Every run that reaches policy evaluation gets a POLICY_EVALUATED audit event with decision, reasons, and policy_version. The report includes a compliance block with policy_decision, policy_reasons, and policy_version.
- **Configurable**: Strictness (permissive, standard, strict) controls how many rules are errors vs warnings and which fields are required.

## Compliance fields (report / manifest)

Reports and bundle manifests can include:

- **data_classification** – e.g. public, internal, confidential, restricted (required in strict mode).
- **pii_presence** – yes, no, unknown.
- **consent_basis** – consent, legitimate_interest, contract.
- **lawful_or_processing_basis** – lawful/processing basis for handling.
- **retention_policy** – raw_ttl_hours, derived_ttl_days.
- **legal_hold** – if true, purge/delete actions are denied and lifecycle state is "held".
- **purpose_of_processing** – required in strict mode.
- **sharing_restrictions** – e.g. internal_only, no_export.
- **policy_decision** – allow, warn, or deny from the policy engine.
- **policy_reasons** – list of { code, severity, message } from evaluation.
- **policy_version** – e.g. hashen.policy.v1.

## Legal hold and retention

- **Legal hold**: When true, retention cleanup (purge/delete) must not delete the bundle or artifact; policy denies such actions. Bundle doctor warns "legal_hold: bundle not deletable".
- **Retention**: Raw TTL (hours) and derived TTL (days) define retention windows. Lifecycle states (active, retained, expired, held, purge_eligible) are derived from these and legal_hold. See [data-lifecycle.md](data-lifecycle.md).

## Privacy and output views

- **Redaction**: Reports can be produced in different output views (internal, customer, auditor). When PII is present and include_sensitive is false, a customer view redacts local paths and raw inputs.
- **No legal certification**: Hashen produces machine-verifiable evidence and policy decision trails; it does not certify compliance with any specific regulation (e.g. GDPR, HIPAA). Implementers map artifacts to their own requirements.
