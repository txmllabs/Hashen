"""Sandbox runner models: script ref, result, policy digest."""

from __future__ import annotations

from typing import Any, Literal, Optional

ScriptRef = Literal["script_id", "url", "inline"]


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
