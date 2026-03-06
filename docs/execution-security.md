# Execution security (restricted execution)

Hashen can run scripts under a **restricted execution** model. This is **not** a secure sandbox.
It is a best-effort, policy-enforced execution boundary designed to reduce risk and produce an
auditable decision trail.

Hashen does **not** provide legal advice or a certification guarantee.

---

## Threat model and trust assumptions

The restricted-execution runner is intended for:

- **Defense-in-depth** for *mostly-trusted* scripts (e.g. internal automation, deterministic steps).
- **Policy enforcement** (block obvious networking/subprocess/filesystem access).
- **Auditable execution metadata** (mode, posture, violations, timeouts, truncation).

It is **not** intended for:

- Running arbitrary untrusted attacker-controlled Python with security guarantees.
- Preventing all data exfiltration or escape attempts.
- Providing container/VM-grade isolation.

For truly untrusted code, use **OS/container isolation** (containers/VMs, seccomp/AppArmor, network
namespaces, filesystem mounts, etc.) and treat the runner as a frontend to that isolation backend.

---

## Execution modes

Hashen defines explicit execution modes:

- **disabled**: execution is rejected (`EXECUTION_DISABLED`).
- **restricted_local**: strongest static validation + subprocess limits, but fewer runtime isolation flags.
- **isolated_subprocess**: best-effort subprocess isolation (Python `-I -S`, sanitized env, temp workdir).
- **container_unsupported**: placeholder mode that returns unsupported (for future backend plug-in).

Even `isolated_subprocess` is best-effort: it is a Python subprocess, not a container.

---

## Layered controls (what is enforced)

### Static validation (AST)

Scripts are parsed and rejected if they violate policy, including:

- **Import allowlist**: only imports explicitly allowed by posture are permitted.
- **Dangerous builtins** blocked by name: `eval`, `exec`, `compile`, `open`, `input`, `__import__`,
  `globals`, `locals`, `vars`, `dir`, `getattr`, `setattr`, `delattr` (best-effort).
- **Reflection heuristics**: reject dunder-heavy attribute access (`__class__`, `__subclasses__`, etc.).
- **Complexity limits**: maximum source size and AST node count.

This reduces common escape paths, but **AST checks are bypassable** by a determined attacker.

### Subprocess execution hardening

When execution proceeds:

- Uses a **dedicated temporary working directory**.
- Uses a **sanitized environment** (no inherited secrets; minimal Windows stability vars kept).
- In `isolated_subprocess`, runs Python with **`-I -S`** (isolated mode, no site imports).
- Captures **stdout/stderr** with **size limits**, returning truncation flags.
- Enforces **wall-clock timeout**; kills process group on Unix best-effort.
- On Unix, sets best-effort **resource limits** (`RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_FSIZE`, `RLIMIT_NPROC`)
  when configured.
- Attempts read-only temp directory permissions when filesystem writes are disallowed (Unix best-effort).

---

## What is not enforced

- **No kernel-level isolation**: no namespaces, seccomp, AppArmor, containers, VM boundaries.
- **No network isolation**: network is blocked by policy checks (imports), not by the OS.
- **No filesystem jail**: temp dir is used, but scripts can still access the host filesystem if they can reach it.
- **No perfect reflection defense**: Python reflection and implementation details can bypass checks.

---

## Auditability

Execution results are structured and machine-readable:

- mode, exit_code, timed_out
- policy_rejected + structured violations
- stdout/stderr truncation flags
- limits and security notes

These results can be embedded into a report/audit trail by the caller.

---

## CLI

```bash
# Validate a script against policy
hashen exec validate script.py

# Run a script in isolated_subprocess mode (default)
hashen exec run script.py

# Explain default posture
hashen exec explain-policy
```

