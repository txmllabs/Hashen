# Implementation limitations

This document describes current limits of the Hashen implementation. Claims in marketing or docs should not exceed these.

---

## Subprocess isolation is not container isolation

- The script **runner** runs code in a **subprocess** with a timeout and an AST-based import denylist. It does **not** use containers, VMs, or kernel namespaces.
- A determined attacker with the ability to run arbitrary Python could bypass the denylist (e.g. via builtins, C extensions, or other means). The runner is **restricted execution**, not a secure sandbox.
- Use the runner for defense-in-depth and policy enforcement, not as the only barrier against malicious code.

---

## AST / policy restrictions are defense-in-depth

- The denylist is enforced by parsing the script’s AST and rejecting certain import names. This blocks many common escape paths but is not a complete sandbox.
- Dynamic imports, `__import__`, or reflection may circumvent the check if not explicitly blocked. The policy is versioned and digest-bound for auditability, not for cryptographic confinement.

---

## Current signature support

- **Script integrity**: Optional `script_sha256` and optional Ed25519 signature verification (requires `cryptography` and the `signing` extra). Not enabled by default.
- **Seal**: The seal is signed in the sense that the EPW hash binds its contents; there is no separate PKI or HSM signing of the seal in the default build.
- **Artifacts**: No built-in signing of artifact bytes; integrity is via recomputation of the seal from artifact + config.

---

## Platform-specific caveats

- **Windows**: No `RLIMIT_CPU` / `RLIMIT_AS`; only wall-clock timeout and process terminate. No process-group kill (no `killpg`).
- **Unix**: Resource limits and process-group kill on timeout are supported. Behavior may vary by OS (e.g. macOS vs Linux).
- **SBOM / pip-audit**: Generated and run in CI; local environments may have other packages that affect pip-audit results.

---

## Cache and TTL

- Cache entries may include `created_at` and `last_validated_at`. TTL-based revalidation is supported in the model; exact behavior depends on configuration. Stale or corrupted cache entries should cause a miss or revalidation, not silent reuse (fail closed).

---

## Evidence bundles

- Bundles are intended for verification and retention. They are not encrypted or access-controlled by Hashen. Store and transmit them according to your data policy.
- Manifest verification (file list + hashes) detects missing or altered files in the bundle; it does not authenticate the origin of the bundle.
