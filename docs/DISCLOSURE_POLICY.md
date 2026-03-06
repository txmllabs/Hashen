# Disclosure and prohibited uploads

This document explicitly lists content that **must not** be uploaded to the Hashen repository, issue tracker, or any public channel.

## Prohibited uploads

Do **not** commit, paste, or attach:

- **Keys and credentials**: Private keys, API keys, tokens, passwords, or any secret material.
- **Attorney–client materials**: Legal advice, attorney notes, or privileged communications.
- **Private claim drafts**: Unpublished patent claims, confidential prosecution drafts, or internal allowance strategies.
- **Raw user data**: Unredacted user content, PII, or identifiable data.
- **Sensitive evidence bundles**: Evidence bundles (artifact + audit + seal) that contain confidential or proprietary content, unless redacted and approved for disclosure.

## Evidence and artifacts

- Evidence bundles produced by `tools/run_evidence_bundle.py` may contain hashes and metadata derived from your inputs. Do not share such bundles publicly if the source artifact or run is sensitive.
- Use retention and legal-hold settings appropriately; do not rely on the repo as a store for raw artifacts or long-term evidence.

## Compliance

By contributing, you agree not to introduce the above into the repository. Violations may be removed and reported as appropriate.
