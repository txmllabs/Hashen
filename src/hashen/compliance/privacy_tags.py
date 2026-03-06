"""Privacy tags per run: data_source_type, pii_present, consent_basis."""

from __future__ import annotations

from typing import Literal

DataSourceType = Literal["public", "user_provided", "partner"]
PIIPresent = Literal["yes", "no", "unknown"]
ConsentBasis = Literal["consent", "legitimate_interest", "contract"]


def privacy_tags(
    data_source_type: DataSourceType = "user_provided",
    pii_present: PIIPresent = "unknown",
    consent_basis: ConsentBasis = "legitimate_interest",
) -> dict[str, str]:
    return {
        "data_source_type": data_source_type,
        "pii_present": pii_present,
        "consent_basis": consent_basis,
    }
