# Security

## What Hashen helps protect

- **Provenance integrity**: Tampering with the artifact or seal is detected by recomputing the EPW; verification fails with a defined reason code (e.g. `EPW_MISMATCH`).
- **Audit integrity**: The hash-chained audit log detects missing, reordered, or modified events (`AUDIT_CHAIN_BROKEN`).
- **Cache integrity**: Reuse is gated by content fingerprint, config/schema, and spot-check; corrupted or mismatched entries are not reused (fail closed).
- **Supply chain visibility**: SBOM (CycloneDX) and pip-audit in CI help detect known vulnerable dependencies.

## What Hashen does not protect

- **Fully compromised host**: If the OS or process is compromised, an attacker can forge or alter seals and audit logs. Hashen does not provide tamper-proof storage.
- **Untrusted script execution**: The restricted runner is subprocess + denylist + timeout, **not** container or VM isolation. A determined attacker can bypass the denylist. Use for defense-in-depth only (see [docs/LIMITATIONS.md](docs/LIMITATIONS.md)).
- **Secrets in artifacts**: Hashen does not encrypt or redact artifact content. Do not put secrets in artifacts.
- **Third-party services**: Out of scope.

## Supported versions

We provide security updates for the **current minor** (e.g. 0.1.x). Upgrade to the latest patch in that line to receive fixes.

## Reporting vulnerabilities

If you believe you have found a security vulnerability in Hashen, please report it responsibly:

- **Do not** open a public GitHub issue for security-sensitive findings.
- Email **developer@txmllabs.com** with a description of the issue, steps to reproduce, and impact.
- We will acknowledge receipt and work with you to understand and address the finding.

## Safe deployment guidance

- **Install from PyPI or a trusted build**: Prefer `pip install hashen` or install from a verified wheel/sdist and checksum (e.g. SHA256SUMS from the release).
- **Run verifier in a trusted environment**: Verification is deterministic but relies on the verifier binary and the seal’s config_vector; protect the deployment from substitution.
- **Do not commit secrets**: Use environment variables or a secrets manager for any keys; never commit `.env`, API keys, or signing keys. CI runs secret scanning (gitleaks).
- **Evidence bundles**: Use dummy or synthetic input for demos and tests in the repo. Do not commit bundles containing real customer or production data.
- **Runner**: Do not run untrusted scripts in the restricted runner and assume strong isolation; treat it as defense-in-depth only.

## Implementation caveats

- **Runner**: Subprocess + denylist; not container or VM isolation.
- **Seal/Audit**: Verification is deterministic; tampering is detected with reason codes. Ed25519 script signing is optional (signing extra).
- **Cache**: Fail closed on corrupted or mismatched entries.

## Do not commit

- **Secrets**: API keys, passwords, tokens, signing keys.
- **Raw artifacts** that contain sensitive or personal data.
- **Personal data** or confidential information.

See also [docs/DISCLOSURE_POLICY.md](docs/DISCLOSURE_POLICY.md) for prohibited uploads and evidence handling.

## Secrets & public repo rules

- **Never commit**: `.env` files, API keys, passwords, tokens, signing keys, or any secret material.
- **Never commit** evidence bundles that contain real customer or production data; use dummy/synthetic input only (e.g. `echo "hashen-ci" > sample.bin`).
- **Sensitive docs**: Use the `private/` folder for attorney notes, claim drafts, or confidential docs. This folder is gitignored; put a copy of `private/README.txt` there and keep it out of version control.
- CI runs secret scanning (gitleaks); fix or allow-list any findings before merging.
