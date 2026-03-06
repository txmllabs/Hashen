"""Unified verification: seal, audit chain, manifest, report with structured result."""

from __future__ import annotations

from hashen.verification.verify import (
    VerificationResult,
    verify_bundle,
    verify_bundle_result,
)

__all__ = [
    "VerificationResult",
    "verify_bundle",
    "verify_bundle_result",
]
