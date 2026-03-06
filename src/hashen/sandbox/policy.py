"""Compatibility policy API for restricted execution.

Historically this module implemented a denylist-only AST import gate.
It now delegates to layered validation (allowlist imports + blocked builtins
+ reflection heuristics) while keeping `check_policy()` for backwards compatibility.
"""

from __future__ import annotations

import hashlib

from hashen.sandbox.constants import DENYLIST_IMPORTS
from hashen.sandbox.posture import SecurityPosture, default_posture
from hashen.sandbox.validation import POLICY_REJECTED, validate_source

# Execution policy version (for audit binding; distinct from compliance policy)
POLICY_VERSION = "hashen.exec_policy.v1"


def check_policy(source: str, posture: SecurityPosture | None = None) -> tuple[bool, str | None]:
    """Return (allowed, reason) for compatibility.

    Any validation violation maps to SANDBOX_POLICY_VIOLATION. Use `validate_source`
    directly to get structured violations.
    """
    posture = posture or default_posture()
    ok, violations = validate_source(source, posture)
    if not ok:
        return False, POLICY_REJECTED
    return True, None


def policy_digest() -> str:
    """Hash of policy for audit binding (denylist + default allowlist)."""
    p = default_posture()
    blob = ",".join(sorted(DENYLIST_IMPORTS)) + "|" + ",".join(sorted(p.allowed_imports))
    return hashlib.sha256(blob.encode()).hexdigest()
