"""Subprocess runner with timeout and import denylist (MVP)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from hashen.sandbox.models import run_result
from hashen.sandbox.policy import check_policy
from hashen.sandbox.runner_interface import RunnerInterface

SANDBOX_POLICY_VIOLATION = "SANDBOX_POLICY_VIOLATION"


class SubprocessRunner(RunnerInterface):
    """MVP: subprocess with timeout; Windows = timeout only; Linux/macOS can add resource limits."""

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
            return run_result(ok=False, reason="SCRIPT_SHA256_MISMATCH")
        env_clean = env or {}
        with tempfile.TemporaryDirectory(prefix="hashen_sandbox_") as tmp:
            script_path = Path(tmp) / "script.py"
            script_path.write_text(script_source, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    cwd=tmp,
                    env={**env_clean},
                )
                return run_result(
                    ok=(proc.returncode == 0),
                    stdout=proc.stdout or "",
                    stderr=proc.stderr or "",
                    reason=None if proc.returncode == 0 else "NONZERO_EXIT",
                    resource_usage={"returncode": proc.returncode},
                )
            except subprocess.TimeoutExpired:
                return run_result(ok=False, reason="TIMEOUT", stderr="Script exceeded timeout")
