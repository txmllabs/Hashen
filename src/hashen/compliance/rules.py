"""Concrete policy rules: retention, legal hold, PII, classification, consent, purpose, sharing."""

from __future__ import annotations

from typing import Callable

from hashen.compliance.models import PolicyReason, RunContext

# Reason codes (stable, for audit and CLI)
MISSING_RETENTION = "MISSING_RETENTION"
LEGAL_HOLD_CONFLICT = "LEGAL_HOLD_CONFLICT"
PII_HANDLING_ABSENT = "PII_HANDLING_ABSENT"
UNKNOWN_CLASSIFICATION_STRICT = "UNKNOWN_CLASSIFICATION_STRICT"
CONSENT_BASIS_ABSENT = "CONSENT_BASIS_ABSENT"
PURPOSE_ABSENT_STRICT = "PURPOSE_ABSENT_STRICT"
SHARING_FORBIDDEN = "SHARING_FORBIDDEN"
REPORT_FIELDS_INCOMPLETE = "REPORT_FIELDS_INCOMPLETE"
EXPORT_FORBIDDEN = "EXPORT_FORBIDDEN"


def rule_retention_required(ctx: RunContext) -> list[PolicyReason]:
    """Deny if required retention policy is missing (standard/strict)."""
    out: list[PolicyReason] = []
    if ctx.strictness == "permissive":
        return out
    if ctx.action in ("purge", "delete") and ctx.legal_hold:
        return out  # handled by legal_hold rule
    if ctx.retention_raw_ttl_hours is None and ctx.retention_derived_ttl_days is None:
        if ctx.strictness == "strict":
            out.append(
                PolicyReason(
                    code=MISSING_RETENTION,
                    severity="error",
                    message="Strict mode requires retention (raw_ttl_hours or derived_ttl_days).",
                )
            )
        elif ctx.strictness == "standard":
            out.append(
                PolicyReason(
                    code=MISSING_RETENTION,
                    severity="warning",
                    message="Retention policy not set; recommend setting retention for compliance.",
                )
            )
    return out


def rule_legal_hold_conflict(ctx: RunContext) -> list[PolicyReason]:
    """Deny if action is purge/delete and legal_hold is true."""
    out: list[PolicyReason] = []
    if ctx.action in ("purge", "delete") and ctx.legal_hold:
        out.append(
            PolicyReason(
                code=LEGAL_HOLD_CONFLICT,
                severity="error",
                message="Action not allowed while legal_hold is true.",
            )
        )
    return out


def rule_pii_handling(ctx: RunContext) -> list[PolicyReason]:
    """Warn or deny if PII present but processing basis/handling flags absent."""
    out: list[PolicyReason] = []
    if ctx.pii_present != "yes":
        return out
    missing = []
    if not ctx.consent_basis and not ctx.lawful_basis:
        missing.append("consent_basis or lawful_basis")
    if ctx.strictness == "strict" and not ctx.purpose_of_processing:
        missing.append("purpose_of_processing")
    if missing:
        msg = f"PII present but missing: {', '.join(missing)}."
        out.append(
            PolicyReason(
                code=PII_HANDLING_ABSENT,
                severity="error" if ctx.strictness == "strict" else "warning",
                message=msg,
            )
        )
    return out


def rule_classification_known(ctx: RunContext) -> list[PolicyReason]:
    """Deny if data_classification is unknown when strict mode is enabled."""
    out: list[PolicyReason] = []
    if ctx.strictness != "strict":
        return out
    if not ctx.data_classification or ctx.data_classification.strip() == "":
        out.append(
            PolicyReason(
                code=UNKNOWN_CLASSIFICATION_STRICT,
                severity="error",
                message="data_classification is required in strict mode.",
            )
        )
    return out


def rule_consent_user_data(ctx: RunContext) -> list[PolicyReason]:
    """Warn if consent basis absent for user-originated data."""
    out: list[PolicyReason] = []
    if ctx.data_source_type != "user_provided":
        return out
    if not ctx.consent_basis and not ctx.lawful_basis:
        out.append(
            PolicyReason(
                code=CONSENT_BASIS_ABSENT,
                severity="warning",
                message="User-provided data should have consent_basis or lawful_basis.",
            )
        )
    return out


def rule_purpose_strict(ctx: RunContext) -> list[PolicyReason]:
    """Deny if purpose_of_processing is absent in strict mode."""
    out: list[PolicyReason] = []
    if ctx.strictness != "strict":
        return out
    if not ctx.purpose_of_processing or not str(ctx.purpose_of_processing).strip():
        out.append(
            PolicyReason(
                code=PURPOSE_ABSENT_STRICT,
                severity="error",
                message="purpose_of_processing is required in strict mode.",
            )
        )
    return out


def rule_sharing_export(ctx: RunContext) -> list[PolicyReason]:
    """Deny if attempting export/share when classification or restrictions forbid it."""
    out: list[PolicyReason] = []
    if ctx.action not in ("export", "share"):
        return out
    if ctx.sharing_restrictions in ("internal_only", "no_export", "no_share"):
        out.append(
            PolicyReason(
                code=SHARING_FORBIDDEN if ctx.action == "share" else EXPORT_FORBIDDEN,
                severity="error",
                message=f"Action '{ctx.action}' is forbidden by sharing_restrictions.",
            )
        )
    if ctx.strictness == "strict" and ctx.data_classification in ("restricted", "confidential"):
        if ctx.action == "export" and ctx.sharing_restrictions != "no_export":
            pass  # already allowed or forbidden above
        elif ctx.action == "export":
            out.append(
                PolicyReason(
                    code=EXPORT_FORBIDDEN,
                    severity="error",
                    message="Export of restricted/confidential data requires explicit allowance.",
                )
            )
    return out


def rule_report_compliance_fields(ctx: RunContext) -> list[PolicyReason]:
    """Warn if report would omit compliance-required fields (for run action)."""
    out: list[PolicyReason] = []
    if ctx.action != "run":
        return out
    if ctx.strictness == "permissive":
        return out
    missing: list[str] = []
    if ctx.strictness == "strict":
        if ctx.retention_raw_ttl_hours is None:
            missing.append("retention_raw_ttl_hours")
        if ctx.retention_derived_ttl_days is None:
            missing.append("retention_derived_ttl_days")
    if missing:
        out.append(
            PolicyReason(
                code=REPORT_FIELDS_INCOMPLETE,
                severity="warning",
                message=f"Report may omit: {', '.join(missing)}.",
            )
        )
    return out


def all_rules() -> list[tuple[str, Callable[[RunContext], list[PolicyReason]]]]:
    """Return list of (rule_name, rule_fn) for evaluation and explain."""
    return [
        ("retention_required", rule_retention_required),
        ("legal_hold_conflict", rule_legal_hold_conflict),
        ("pii_handling", rule_pii_handling),
        ("classification_known", rule_classification_known),
        ("consent_user_data", rule_consent_user_data),
        ("purpose_strict", rule_purpose_strict),
        ("sharing_export", rule_sharing_export),
        ("report_compliance_fields", rule_report_compliance_fields),
    ]
