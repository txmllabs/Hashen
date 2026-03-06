"""Privacy-aware output: redact report fields by view (internal, customer, auditor)."""

from __future__ import annotations

from typing import Any

from hashen.compliance.models import OutputView

# Keys that may be redacted for customer view (identifiers, raw paths)
REDACT_KEYS_CUSTOMER = frozenset({"local_path", "path", "file_path", "inputs_summary"})
# For auditor we keep most; only strip truly internal-only if needed
REDACT_KEYS_AUDITOR = frozenset()


def redact_report(report: dict[str, Any], view: OutputView) -> dict[str, Any]:
    """
    Return a copy of the report with optional redaction by view.
    - internal: no redaction.
    - customer: redact local paths, raw inputs_summary (retain structure, redact values).
    - auditor: same as internal for now (full evidence).
    """
    if view == "internal" or view == "auditor":
        return dict(report)
    out: dict[str, Any] = {}
    for k, v in report.items():
        if k in REDACT_KEYS_CUSTOMER:
            if k == "inputs_summary" and isinstance(v, dict):
                out[k] = {"_redacted": "customer_view"}
            else:
                out[k] = "[redacted]"
        elif isinstance(v, dict):
            out[k] = redact_report(v, view)
        elif isinstance(v, list):
            out[k] = [redact_report(x, view) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


def report_for_view(
    report: dict[str, Any],
    include_sensitive: bool = True,
    view: OutputView = "internal",
) -> dict[str, Any]:
    """
    Produce report view. If include_sensitive=False and pii_presence is yes,
    use customer view (redacted). Otherwise use given view.
    """
    compliance = report.get("compliance") or {}
    pii = (compliance.get("pii_presence") or report.get("privacy", {}).get("pii_present")) == "yes"
    if pii and not include_sensitive:
        view = "customer"
    return redact_report(report, view)
