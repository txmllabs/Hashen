"""Compliance context and policy result models (JSON-serializable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

PolicyStrictness = Literal["permissive", "standard", "strict"]
PolicyDecision = Literal["allow", "warn", "deny"]
LifecycleState = Literal["active", "retained", "expired", "held", "purge_eligible"]
OutputView = Literal["internal", "customer", "auditor"]


@dataclass
class PolicyReason:
    """Single policy reason (code, severity, message)."""

    code: str
    severity: Literal["error", "warning", "info"]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class PolicyResult:
    """Policy evaluation result: decision, reasons, effective policy, trace."""

    decision: PolicyDecision
    reasons: list[PolicyReason] = field(default_factory=list)
    effective_policy: dict[str, Any] = field(default_factory=dict)
    evaluated_at: str = ""
    policy_version: str = "hashen.policy.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": [r.to_dict() for r in self.reasons],
            "effective_policy": self.effective_policy,
            "evaluated_at": self.evaluated_at,
            "policy_version": self.policy_version,
        }

    @property
    def allowed(self) -> bool:
        return self.decision != "deny"

    @property
    def denied(self) -> bool:
        return self.decision == "deny"


@dataclass
class RunContext:
    """Input context for policy evaluation (run-level metadata)."""

    run_id: str = ""
    target_id: str = "default"
    # Data classification and source
    data_classification: Optional[str] = None  # public, internal, confidential, restricted
    data_source_type: Optional[str] = None  # public, user_provided, partner
    # Retention and hold
    retention_raw_ttl_hours: Optional[float] = None
    retention_derived_ttl_days: Optional[float] = None
    legal_hold: bool = False
    # Privacy / lawful basis
    pii_present: Optional[str] = None  # yes, no, unknown
    consent_basis: Optional[str] = None  # consent, legitimate_interest, contract
    lawful_basis: Optional[str] = None  # alias or extended
    purpose_of_processing: Optional[str] = None
    sharing_restrictions: Optional[str] = None  # e.g. "internal_only", "no_export"
    # Action being performed (for rule evaluation)
    action: str = "run"  # run, export, share, purge, delete
    strictness: PolicyStrictness = "standard"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "target_id": self.target_id,
            "data_classification": self.data_classification,
            "data_source_type": self.data_source_type,
            "retention_raw_ttl_hours": self.retention_raw_ttl_hours,
            "retention_derived_ttl_days": self.retention_derived_ttl_days,
            "legal_hold": self.legal_hold,
            "pii_present": self.pii_present,
            "consent_basis": self.consent_basis,
            "lawful_basis": self.lawful_basis,
            "purpose_of_processing": self.purpose_of_processing,
            "sharing_restrictions": self.sharing_restrictions,
            "action": self.action,
            "strictness": self.strictness,
        }
