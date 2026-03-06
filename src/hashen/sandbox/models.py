"""Sandbox runner models: script ref, result, policy digest."""

from __future__ import annotations

from typing import Any, Literal, Optional

ScriptRef = Literal["script_id", "url", "inline"]

ExecutionMode = Literal[
    "disabled",
    "restricted_local",
    "isolated_subprocess",
    "container_unsupported",
]


def run_result(
    ok: bool,
    stdout: str = "",
    stderr: str = "",
    reason: Optional[str] = None,
    resource_usage: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
        "reason": reason,
        "resource_usage": resource_usage or {},
    }


def exec_result(
    *,
    ok: bool,
    mode: ExecutionMode,
    exit_code: Optional[int] = None,
    timed_out: bool = False,
    policy_rejected: bool = False,
    reason: Optional[str] = None,
    stdout: str = "",
    stderr: str = "",
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
    violations: Optional[list[dict[str, Any]]] = None,
    limits: Optional[dict[str, Any]] = None,
    security_notes: Optional[list[str]] = None,
    resource_usage: Optional[dict[str, Any]] = None,
    workdir: Optional[str] = None,
) -> dict[str, Any]:
    """Structured execution result (machine-readable; suitable for audit/report embedding)."""
    return {
        "ok": ok,
        "mode": mode,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "policy_rejected": policy_rejected,
        "reason": reason,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "violations": violations or [],
        "limits": limits or {},
        "security_notes": security_notes or [],
        "resource_usage": resource_usage or {},
        "workdir": workdir,
    }
