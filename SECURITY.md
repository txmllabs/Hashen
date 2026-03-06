# Security

## Reporting vulnerabilities

If you believe you have found a security vulnerability in Hashen, please report it responsibly:

- **Do not** open a public GitHub issue for security-sensitive findings.
- Email **developer@txmllabs.com** with a description of the issue, steps to reproduce, and impact.
- We will acknowledge receipt and work with you to understand and address the finding.

## In scope

- The Hashen trust layer codebase: seal (EPW), audit chain, sandbox runner, cache, compliance, and CLI tools.
- Supply chain: dependency vulnerabilities (we use pip-audit and SBOM in CI).
- Configuration and usage that could lead to bypass of sandbox or verification.

## Out of scope

- Third-party services or infrastructure not maintained by this project.
- Social engineering or physical access issues.

## Do not commit

- **Secrets**: API keys, passwords, tokens, signing keys.
- **Raw artifacts** that contain sensitive or personal data.
- **Personal data** or confidential information.

See also [docs/DISCLOSURE_POLICY.md](docs/DISCLOSURE_POLICY.md) for prohibited uploads and evidence handling.
