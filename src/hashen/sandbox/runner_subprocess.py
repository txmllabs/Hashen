"""Restricted execution runner (best-effort).

This runner is **not** a secure sandbox. It uses layered AST validation plus a subprocess
with a sanitized environment, temp working directory, and best-effort resource limits.
Platform capabilities vary (notably Windows vs Unix).
"""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

from hashen.sandbox.models import exec_result
from hashen.sandbox.policy import check_policy
from hashen.sandbox.posture import SecurityPosture, default_posture
from hashen.sandbox.runner_interface import RunnerInterface
from hashen.sandbox.signing import SCRIPT_SIGNATURE_INVALID
from hashen.sandbox.validation import validate_source

SANDBOX_POLICY_VIOLATION = "SANDBOX_POLICY_VIOLATION"
TIMEOUT = "TIMEOUT"
RESOURCE_LIMIT = "RESOURCE_LIMIT"
RUNTIME_ERROR = "RUNTIME_ERROR"
STRICT_MODE_REQUIRES_SCRIPT_HASH = "STRICT_MODE_REQUIRES_SCRIPT_HASH"
STDOUT_OVERSIZED = "STDOUT_OVERSIZED"
EXECUTION_DISABLED = "EXECUTION_DISABLED"
EXECUTION_MODE_UNSUPPORTED = "EXECUTION_MODE_UNSUPPORTED"


def _set_resource_limits(posture: SecurityPosture) -> None:
    """Unix only: set best-effort rlimits before exec. No-op on Windows."""
    if sys.platform == "win32":
        return
    try:
        import resource

        if posture.max_cpu_seconds is not None and posture.max_cpu_seconds > 0:
            soft = int(posture.max_cpu_seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (soft, soft + 1))
        if posture.max_memory_mb is not None and posture.max_memory_mb > 0:
            bytes_limit = int(posture.max_memory_mb * 1024 * 1024)
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        if posture.max_file_size_mb is not None and posture.max_file_size_mb > 0:
            bytes_limit = int(posture.max_file_size_mb * 1024 * 1024)
            resource.setrlimit(resource.RLIMIT_FSIZE, (bytes_limit, bytes_limit))
        if posture.max_processes is not None and posture.max_processes >= 0:
            # Best-effort; may fail for unprivileged users or on some OSes.
            resource.setrlimit(
                resource.RLIMIT_NPROC, (posture.max_processes, posture.max_processes)
            )
    except (ImportError, OSError, ValueError):
        pass  # Caller may see RESOURCE_LIMIT only when the process actually hits the limit


def _sanitize_env(env: Optional[dict[str, str]], posture: SecurityPosture) -> dict[str, str]:
    """Remove inherited environment; pass only allowlisted keys from provided env."""
    out: dict[str, str] = {}
    # Windows stability: keep minimal OS paths for child process startup.
    if sys.platform == "win32":
        for k in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
            v = os.environ.get(k)
            if v:
                out[k] = v
    if not env:
        return out
    for k, v in env.items():
        if k in posture.env_allowlist:
            out[k] = v
    return out


def _communicate_limited(
    proc: subprocess.Popen[bytes],
    *,
    timeout_sec: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[bytes, bytes, bool, bool, bool]:
    """Read stdout/stderr with size limits.

    Returns (stdout, stderr, out_trunc, err_trunc, timed_out).
    """
    out_buf = bytearray()
    err_buf = bytearray()

    def _reader(stream: Any, buf: bytearray, limit: int, trunc_flag: list[bool]) -> None:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            remaining = limit - len(buf)
            if remaining > 0:
                buf.extend(chunk[:remaining])
            if len(buf) >= limit:
                trunc_flag[0] = True
                # Continue draining but discard to avoid blocking the subprocess.
                continue

    out_flag = [False]
    err_flag = [False]
    t_out = threading.Thread(
        target=_reader, args=(proc.stdout, out_buf, max_stdout_bytes, out_flag), daemon=True
    )
    t_err = threading.Thread(
        target=_reader, args=(proc.stderr, err_buf, max_stderr_bytes, err_flag), daemon=True
    )
    t_out.start()
    t_err.start()
    try:
        proc.wait(timeout=timeout_sec)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    # Best-effort join
    t_out.join(timeout=0.2)
    t_err.join(timeout=0.2)
    return bytes(out_buf), bytes(err_buf), out_flag[0], err_flag[0], timed_out


class SubprocessRunner(RunnerInterface):
    """
    Subprocess runner: timeout, denylist, process group kill on timeout.
    Unix only: RLIMIT_CPU, RLIMIT_AS via preexec_fn. Windows: timeout only.
    """

    def __init__(
        self,
        max_cpu_seconds: Optional[float] = 60,
        max_mem_mb: Optional[float] = 128,
    ) -> None:
        self.max_cpu_seconds = max_cpu_seconds
        self.max_mem_mb = max_mem_mb

    def run_script(
        self,
        script_source: str,
        timeout_sec: float,
        script_sha256: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        strict_mode: bool = False,
        max_stdout_bytes: Optional[int] = None,
        mode: Optional[str] = None,
        security_posture: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        posture = default_posture()
        if security_posture:
            posture = SecurityPosture(**{**posture.__dict__, **security_posture})

        if mode is not None:
            # best-effort: accept only known string modes
            if mode not in (
                "disabled",
                "restricted_local",
                "isolated_subprocess",
                "container_unsupported",
            ):
                return exec_result(
                    ok=False,
                    mode="restricted_local",
                    policy_rejected=True,
                    reason=EXECUTION_MODE_UNSUPPORTED,
                    security_notes=["Unknown execution mode."],
                )
            posture = SecurityPosture(**{**posture.__dict__, "mode": mode})

        if posture.mode == "disabled":
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=EXECUTION_DISABLED,
                security_notes=["Execution disabled by configuration."],
            )
        if posture.mode == "container_unsupported":
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=EXECUTION_MODE_UNSUPPORTED,
                security_notes=["Container backend not implemented in this build."],
            )

        if strict_mode and not script_sha256:
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=STRICT_MODE_REQUIRES_SCRIPT_HASH,
            )

        # Layered policy validation (structured)
        ok_policy, violations = validate_source(script_source, posture)
        if not ok_policy:
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=SANDBOX_POLICY_VIOLATION,
                violations=[v.to_dict() for v in violations],
                limits={
                    "max_source_bytes": posture.max_source_bytes,
                    "max_ast_nodes": posture.max_ast_nodes,
                },
                security_notes=[
                    "Policy rejection via AST validation (best-effort).",
                    "Do not treat AST validation as a security boundary.",
                ],
            )

        # Compatibility gate (maps any violation to SANDBOX_POLICY_VIOLATION)
        allowed, reason = check_policy(script_source, posture=posture)
        if not allowed:
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=reason or SANDBOX_POLICY_VIOLATION,
            )

        computed_sha = hashlib.sha256(script_source.encode()).hexdigest()
        if script_sha256 and computed_sha != script_sha256:
            return exec_result(
                ok=False,
                mode=posture.mode,
                policy_rejected=True,
                reason=SCRIPT_SIGNATURE_INVALID,
            )

        env_clean = _sanitize_env(env, posture)

        def _preexec() -> None:
            _set_resource_limits(posture)

        preexec_fn = None if sys.platform == "win32" else _preexec

        max_out = max_stdout_bytes if max_stdout_bytes is not None else posture.max_output_bytes
        max_err = posture.max_output_bytes
        timeout = (
            min(timeout_sec, posture.max_runtime_seconds)
            if posture.max_runtime_seconds
            else timeout_sec
        )

        with tempfile.TemporaryDirectory(prefix="hashen_exec_") as tmp:
            tmp_path = Path(tmp)
            if not posture.allow_filesystem_write and sys.platform != "win32":
                try:
                    os.chmod(tmp, 0o555)
                except OSError:
                    pass
            script_path = tmp_path / "script.py"
            script_path.write_text(script_source, encoding="utf-8")

            argv = [sys.executable]
            if posture.mode == "isolated_subprocess":
                argv += ["-I", "-S"]
            argv += [str(script_path)]

            try:
                proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    cwd=str(tmp_path),
                    env=env_clean,
                    start_new_session=True,
                    close_fds=(sys.platform != "win32"),
                    preexec_fn=preexec_fn,
                    text=False,
                )
                stdout_b, stderr_b, out_trunc, err_trunc, timed_out = _communicate_limited(
                    proc,
                    timeout_sec=timeout,
                    max_stdout_bytes=max_out,
                    max_stderr_bytes=max_err,
                )
                if timed_out:
                    _kill_process_group(proc.pid)
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return exec_result(
                        ok=False,
                        mode=posture.mode,
                        exit_code=None,
                        timed_out=True,
                        reason=TIMEOUT,
                        stderr="Script exceeded timeout",
                        stdout=stdout_b.decode("utf-8", errors="replace"),
                        stderr_truncated=err_trunc,
                        stdout_truncated=out_trunc,
                        limits={
                            "timeout_sec": timeout,
                            "max_output_bytes": max_out,
                            "max_memory_mb": posture.max_memory_mb,
                            "max_cpu_seconds": posture.max_cpu_seconds,
                        },
                        workdir=str(tmp_path),
                        security_notes=[
                            "Timeout is wall-clock; not a full containment mechanism.",
                            "Subprocess isolation is best-effort only.",
                        ],
                    )
                rc = int(proc.returncode) if proc.returncode is not None else None
                stdout_s = stdout_b.decode("utf-8", errors="replace")
                stderr_s = stderr_b.decode("utf-8", errors="replace")

                if out_trunc:
                    # Keep compatibility reason code while still returning structured result.
                    reason_code = STDOUT_OVERSIZED if rc == 0 else RUNTIME_ERROR
                    ok = False
                else:
                    reason_code = None if rc == 0 else RUNTIME_ERROR
                    ok = rc == 0
                return exec_result(
                    ok=ok,
                    mode=posture.mode,
                    exit_code=rc,
                    timed_out=False,
                    policy_rejected=False,
                    reason=reason_code,
                    stdout=stdout_s,
                    stderr=stderr_s,
                    stdout_truncated=out_trunc,
                    stderr_truncated=err_trunc,
                    limits={
                        "timeout_sec": timeout,
                        "max_output_bytes": max_out,
                        "max_memory_mb": posture.max_memory_mb,
                        "max_cpu_seconds": posture.max_cpu_seconds,
                    },
                    resource_usage={"returncode": rc if rc is not None else -1},
                    workdir=str(tmp_path),
                    security_notes=[
                        "AST validation + subprocess isolation are best-effort.",
                        "Use OS/container isolation for untrusted code.",
                    ],
                )
            except OSError as e:
                if "Cannot allocate memory" in str(e) or "memory" in str(e).lower():
                    return exec_result(
                        ok=False,
                        mode=posture.mode,
                        reason=RESOURCE_LIMIT,
                        stderr=str(e),
                        workdir=str(tmp_path),
                    )
                raise
            except MemoryError:
                return exec_result(
                    ok=False,
                    mode=posture.mode,
                    reason=RESOURCE_LIMIT,
                    stderr="Memory limit exceeded",
                    workdir=str(tmp_path),
                )


def _kill_process_group(pid: int) -> None:
    """Unix: kill entire process group (SIGKILL). Windows: terminate then kill."""
    if sys.platform == "win32":
        try:
            os.kill(pid, signal.SIGTERM)
        except (OSError, AttributeError):
            pass
        # Fallback: proc.kill() is used by caller after wait timeout
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
