# Data lifecycle

Lifecycle state and retention status are derived from retention policy, legal hold, and file timestamps. They support operational decisions (e.g. archive, delete) and bundle doctor / policy behavior.

## Lifecycle states

| State | Meaning |
|-------|---------|
| **held** | legal_hold is true; bundle/artifact must not be purged or deleted. |
| **active** | Artifact (or bundle) is within raw TTL window; still in active use. |
| **retained** | Past raw TTL but within derived TTL; retained for compliance/audit. |
| **expired** | Past raw TTL (and derived reference); may be eligible for archival. |
| **purge_eligible** | Past derived TTL and no legal hold; policy allows purge/delete. |

State is computed by `lifecycle_state(...)` from legal_hold, raw_ttl_hours, derived_ttl_days, and optional artifact_mtime / report_or_bundle_mtime. Legal hold always wins (state = held).

## Retention status (CLI)

**hashen retention status** &lt;bundle_dir&gt; [--raw-ttl-hours 24] [--derived-ttl-days 365] [--legal-hold]

Outputs:

- **lifecycle_state** – one of active, retained, expired, held, purge_eligible.
- **legal_hold** – from report or flag.
- **retention_raw_ttl_hours**, **retention_derived_ttl_days**
- **policy_notes** – e.g. "not deletable; legal hold", "purge_eligible", "within retention".
- **deletable** – false when state is held, true otherwise.

When the path is a bundle directory, retention and legal_hold are read from report.json if present.

## Bundle doctor and legal hold

When **hashen bundle doctor** finds report.json with legal_hold true, it adds a warning: "legal_hold: bundle not deletable". This does not fail the doctor check but signals that the bundle should not be purged.

## Retention cleanup (hashen-retention)

**hashen-retention** (or hashen retention cleanup, if implemented) deletes raw artifacts by TTL only when **legal_hold** is false. When legal_hold is true, no files are deleted. This is enforced in `retention_delete_raw_after_ttl` in the compliance.retention module.
