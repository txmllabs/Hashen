# Security

## Supported versions

We provide security updates for the **current minor** (e.g. 0.1.x). Upgrade to the latest patch in that line to receive fixes.

## Reporting vulnerabilities

If you believe you have found a security vulnerability in Hashen, please report it responsibly:

- **Do not** open a public GitHub issue for security-sensitive findings.
- Email **developer@txmllabs.com** with a description of the issue, steps to reproduce, and impact.
- We will acknowledge receipt and work with you to understand and address the finding.

## Implementation caveats

- **Runner**: The restricted execution runner uses a subprocess plus import denylist and resource limits. It is **not** container or VM isolation; a determined attacker can bypass the denylist. Use for defense-in-depth only (see [docs/LIMITATIONS.md](docs/LIMITATIONS.md)).
- **Seal/Audit**: Verification is deterministic and binding; tampering is detected with explicit reason codes. Signature support (e.g. ed25519) is optional and may not be enabled in your build.
- **Cache**: Reuse is keyed by content fingerprint and config; corrupted or mismatched cache entries are rejected (fail closed).

## In scope

- The Hashen trust layer codebase: seal (EPW), audit chain, restricted execution runner, cache, compliance, and CLI tools.
- Supply chain: dependency vulnerabilities (we use pip-audit and SBOM in CI).
- Configuration and usage that could lead to bypass of verification or runner policy.

## Out of scope

- Third-party services or infrastructure not maintained by this project.
- Social engineering or physical access issues.

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
