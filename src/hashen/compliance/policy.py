"""Policy engine: evaluate run context against rules, return allow/warn/deny with trail."""

from __future__ import annotations

from hashen.compliance.models import PolicyReason, PolicyResult, RunContext
from hashen.compliance.rules import all_rules
from hashen.utils.clock import utc_iso_now

POLICY_VERSION = "hashen.policy.v1"


def evaluate(ctx: RunContext, evaluated_at: str | None = None) -> PolicyResult:
    """
    Evaluate all rules against context. Returns PolicyResult with decision allow | warn | deny.
    - deny: any rule produced an error (severity "error").
    - warn: no errors but at least one warning.
    - allow: no errors, optionally warnings (decision still allow for pipeline to proceed).
    """
    reasons: list[PolicyReason] = []
    for _name, rule_fn in all_rules():
        reasons.extend(rule_fn(ctx))
    errors = [r for r in reasons if r.severity == "error"]
    warnings = [r for r in reasons if r.severity == "warning"]
    if errors:
        decision: str = "deny"
    elif warnings:
        decision = "warn"
    else:
        decision = "allow"
    effective = {
        "strictness": ctx.strictness,
        "action": ctx.action,
        "legal_hold": ctx.legal_hold,
    }
    return PolicyResult(
        decision=decision,
        reasons=reasons,
        effective_policy=effective,
        evaluated_at=evaluated_at or utc_iso_now(),
        policy_version=POLICY_VERSION,
    )


def explain(ctx: RunContext, evaluated_at: str | None = None) -> PolicyResult:
    """
    Same as evaluate but explicitly for explain output (full reasons and triggered rules).
    """
    return evaluate(ctx, evaluated_at=evaluated_at)
