"""
Central schema version constants for Hashen serialized artifacts.
Verifiers and writers use these; unsupported versions are rejected at verify time.
"""

from __future__ import annotations

from hashen.audit.models import AUDIT_SCHEMA_VERSION
from hashen.cache.models import CACHE_SCHEMA_VERSION
from hashen.compliance.reporting import REPORT_SCHEMA_VERSION
from hashen.provenance.bundle_manifest import MANIFEST_SCHEMA_VERSION
from hashen.provenance.seal import SEAL_SCHEMA_VERSION

__all__ = [
    "SEAL_SCHEMA_VERSION",
    "AUDIT_SCHEMA_VERSION",
    "CACHE_SCHEMA_VERSION",
    "REPORT_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
]
