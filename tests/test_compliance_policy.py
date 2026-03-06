"""Tests for compliance policy engine, rules, lifecycle, and pipeline integration."""

from __future__ import annotations

import json
from pathlib import Path

from hashen.compliance.lifecycle import lifecycle_state, retention_status
from hashen.compliance.models import RunContext
from hashen.compliance.policy import evaluate as policy_evaluate
from hashen.compliance.redaction import redact_report, report_for_view
from hashen.compliance.rules import (
    LEGAL_HOLD_CONFLICT,
    MISSING_RETENTION,
    PURPOSE_ABSENT_STRICT,
    rule_legal_hold_conflict,
    rule_retention_required,
)
from hashen.orchestrator import run_pipeline


def test_policy_allow_with_valid_metadata():
    """Allow path: valid retention, legal_hold false, standard strictness."""
    ctx = RunContext(
        run_id="r1",
        retention_raw_ttl_hours=24,
        retention_derived_ttl_days=365,
        legal_hold=False,
        consent_basis="legitimate_interest",
        strictness="standard",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "allow"
    assert result.allowed
    assert not result.denied


def test_policy_warn_with_incomplete_metadata():
    """Warn path: missing retention in standard mode (warning only)."""
    ctx = RunContext(
        run_id="r2",
        retention_raw_ttl_hours=None,
        retention_derived_ttl_days=None,
        legal_hold=False,
        strictness="standard",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "warn"
    assert result.allowed
    codes = [r.code for r in result.reasons]
    assert MISSING_RETENTION in codes


def test_policy_deny_missing_retention_strict():
    """Deny path: missing retention in strict mode."""
    ctx = RunContext(
        run_id="r3",
        retention_raw_ttl_hours=None,
        retention_derived_ttl_days=None,
        legal_hold=False,
        strictness="strict",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "deny"
    assert result.denied
    assert any(r.code == MISSING_RETENTION and r.severity == "error" for r in result.reasons)


def test_policy_deny_legal_hold_conflict():
    """Deny path: action purge with legal_hold true."""
    ctx = RunContext(
        run_id="r4",
        legal_hold=True,
        action="purge",
        strictness="standard",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "deny"
    assert any(r.code == LEGAL_HOLD_CONFLICT for r in result.reasons)


def test_policy_strict_unknown_classification():
    """Strict mode: unknown data_classification -> deny."""
    ctx = RunContext(
        run_id="r5",
        data_classification=None,
        retention_raw_ttl_hours=24,
        retention_derived_ttl_days=365,
        strictness="strict",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "deny"
    assert any(
        "classification" in r.code.lower() or "CLASSIFICATION" in r.code for r in result.reasons
    )


def test_policy_strict_purpose_absent():
    """Strict mode: purpose_of_processing absent -> deny."""
    ctx = RunContext(
        run_id="r6",
        purpose_of_processing=None,
        retention_raw_ttl_hours=24,
        retention_derived_ttl_days=365,
        data_classification="internal",
        strictness="strict",
    )
    result = policy_evaluate(ctx)
    assert result.decision == "deny"
    assert any(r.code == PURPOSE_ABSENT_STRICT for r in result.reasons)


def test_policy_decision_event_logged_in_audit(tmp_path: Path):
    """Pipeline logs POLICY_EVALUATED and policy denial returns structured result."""
    artifact_bytes = b"policy test"
    config = {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}
    result = run_pipeline(
        artifact_bytes,
        "policy-run",
        config,
        root=tmp_path,
        retention_raw_ttl_hours=None,
        retention_derived_ttl_days=None,
        policy_strictness="strict",
    )
    assert result.get("policy_denied") is True
    assert result.get("policy_decision") == "deny"
    assert "policy_reasons" in result
    audit_path = tmp_path / "audit" / "policy-run.jsonl"
    assert audit_path.exists()
    lines = [line for line in audit_path.read_text().splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    event_types = [e.get("event_type") for e in events]
    assert "POLICY_EVALUATED" in event_types
    policy_ev = next(e for e in events if e.get("event_type") == "POLICY_EVALUATED")
    assert policy_ev.get("decision") == "deny"


def test_policy_allow_run_produces_seal_and_report(tmp_path: Path):
    """Allow path: run proceeds and report contains policy_decision and compliance block."""
    artifact_bytes = b"allow run"
    config = {"h2_min": 0.0, "h2_max": 1.0, "h2_bins": 16, "h1_subset_size": 32}
    result = run_pipeline(
        artifact_bytes,
        "allow-run",
        config,
        root=tmp_path,
        retention_raw_ttl_hours=24,
        retention_derived_ttl_days=365,
        legal_hold=False,
        policy_strictness="standard",
    )
    assert result.get("policy_denied") is not True
    assert result.get("seal_hash")
    report_path = tmp_path / "reports" / "allow-run.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "compliance" in report
    assert report["compliance"].get("policy_decision") in ("allow", "warn")
    assert "retention_policy" in report["compliance"]
    assert report["compliance"].get("legal_hold") is False


def test_lifecycle_state_held():
    assert lifecycle_state(legal_hold=True) == "held"


def test_lifecycle_state_purge_eligible():
    # ref_mtime far in past, no hold
    state = lifecycle_state(
        legal_hold=False,
        raw_ttl_hours=24,
        derived_ttl_days=365,
        report_or_bundle_mtime=0.0,
        now=400 * 86400,
    )
    assert state == "purge_eligible"


def test_retention_status_bundle_with_report(tmp_path: Path):
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "run_id": "x",
                "retention": {"raw_ttl_hours": 24, "derived_ttl_days": 365, "legal_hold": True},
            }
        ),
        encoding="utf-8",
    )
    status = retention_status(tmp_path)
    assert status["lifecycle_state"] == "held"
    assert status["legal_hold"] is True
    assert status.get("deletable") is False


def test_redact_report_customer_view():
    report = {"run_id": "r1", "local_path": "/secret/path", "compliance": {"a": 1}}
    out = redact_report(report, "customer")
    assert out["local_path"] == "[redacted]"
    assert out["run_id"] == "r1"


def test_report_for_view_pii_sensitive():
    report = {
        "compliance": {"pii_presence": "yes"},
        "privacy": {"pii_present": "yes"},
        "run_id": "r1",
        "local_path": "/x",
    }
    out = report_for_view(report, include_sensitive=False, view="internal")
    assert out["local_path"] == "[redacted]"


def test_rule_legal_hold_conflict_delete():
    ctx = RunContext(legal_hold=True, action="delete")
    reasons = rule_legal_hold_conflict(ctx)
    assert len(reasons) == 1
    assert reasons[0].code == LEGAL_HOLD_CONFLICT


def test_rule_retention_required_permissive():
    ctx = RunContext(strictness="permissive", retention_raw_ttl_hours=None)
    reasons = rule_retention_required(ctx)
    assert len(reasons) == 0
