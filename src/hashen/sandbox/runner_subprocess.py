"""Subprocess runner with timeout, import denylist, and (Unix) resource limits."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from hashen.sandbox.models import run_result
from hashen.sandbox.policy import check_policy
from hashen.sandbox.runner_interface import RunnerInterface
from hashen.sandbox.signing import SCRIPT_SIGNATURE_INVALID

SANDBOX_POLICY_VIOLATION = "SANDBOX_POLICY_VIOLATION"
TIMEOUT = "TIMEOUT"
RESOURCE_LIMIT = "RESOURCE_LIMIT"


def _set_resource_limits(max_cpu_seconds: Optional[float], max_mem_mb: Optional[float]) -> None:
    """Unix only: set RLIMIT_CPU and RLIMIT_AS before exec. No-op on Windows."""
    if sys.platform == "win32":
        return
    try:
        import resource

        if max_cpu_seconds is not None and max_cpu_seconds > 0:
            soft = int(max_cpu_seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (soft, soft + 1))
        if max_mem_mb is not None and max_mem_mb > 0:
            bytes_limit = int(max_mem_mb * 1024 * 1024)
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
    except (ImportError, OSError, ValueError):
        pass


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
    ) -> dict[str, Any]:
        allowed, reason = check_policy(script_source)
        if not allowed:
            return run_result(ok=False, reason=reason or SANDBOX_POLICY_VIOLATION)
        computed_sha = hashlib.sha256(script_source.encode()).hexdigest()
        if script_sha256 and computed_sha != script_sha256:
            return run_result(ok=False, reason=SCRIPT_SIGNATURE_INVALID)
        env_clean = env or {}

        def _preexec() -> None:
            _set_resource_limits(self.max_cpu_seconds, self.max_mem_mb)

        preexec_fn = None if sys.platform == "win32" else _preexec

        with tempfile.TemporaryDirectory(prefix="hashen_sandbox_") as tmp:
            script_path = Path(tmp) / "script.py"
            script_path.write_text(script_source, encoding="utf-8")
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=tmp,
                    env={**env_clean},
                    start_new_session=True,
                    preexec_fn=preexec_fn,
                )
                try:
                    stdout, stderr = proc.communicate(timeout=timeout_sec)
                    return run_result(
                        ok=(proc.returncode == 0),
                        stdout=stdout or "",
                        stderr=stderr or "",
                        reason=None if proc.returncode == 0 else "NONZERO_EXIT",
                        resource_usage={"returncode": proc.returncode},
                    )
                except subprocess.TimeoutExpired:
                    _kill_process_group(proc.pid)
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return run_result(
                        ok=False,
                        reason=TIMEOUT,
                        stderr="Script exceeded timeout",
                    )
            except OSError as e:
                if "Cannot allocate memory" in str(e) or "memory" in str(e).lower():
                    return run_result(ok=False, reason=RESOURCE_LIMIT, stderr=str(e))
                raise
            except MemoryError:
                return run_result(ok=False, reason=RESOURCE_LIMIT, stderr="Memory limit exceeded")


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
