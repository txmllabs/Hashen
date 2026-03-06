"""Attack-oriented tests for restricted execution hardening."""

from __future__ import annotations

import pytest

from hashen.sandbox.posture import default_posture
from hashen.sandbox.runner_subprocess import (
    EXECUTION_DISABLED,
    STDOUT_OVERSIZED,
    TIMEOUT,
    SubprocessRunner,
)
from hashen.sandbox.validation import (
    V_BUILTIN_BLOCKED,
    V_IMPORT_NOT_ALLOWED,
    V_NETWORK_NOT_ALLOWED,
    validate_source,
)


def test_validate_blocks_socket_import_by_default():
    posture = default_posture()
    ok, violations = validate_source("import socket\nprint(1)", posture)
    assert ok is False
    codes = {v.code for v in violations}
    assert V_IMPORT_NOT_ALLOWED in codes or V_NETWORK_NOT_ALLOWED in codes


def test_validate_blocks_eval_and___import__():
    posture = default_posture()
    ok, violations = validate_source('eval("1")\nprint(1)', posture)
    assert ok is False
    assert any(v.code == V_BUILTIN_BLOCKED for v in violations)
    ok2, violations2 = validate_source('__import__("os")\nprint(1)', posture)
    assert ok2 is False
    assert any(v.code == V_BUILTIN_BLOCKED for v in violations2)


def test_runner_disabled_mode_rejects_cleanly():
    runner = SubprocessRunner()
    result = runner.run_script("print(1)", timeout_sec=1.0, mode="disabled")
    assert result["ok"] is False
    assert result["policy_rejected"] is True
    assert result["reason"] == EXECUTION_DISABLED


def test_runner_timeout_infinite_loop():
    runner = SubprocessRunner()
    result = runner.run_script("while True: pass", timeout_sec=0.2)
    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["reason"] == TIMEOUT


def test_runner_output_truncation_sets_flags():
    runner = SubprocessRunner()
    posture = default_posture()
    result = runner.run_script(
        'print("x" * 200000)',
        timeout_sec=2.0,
        mode=posture.mode,
        security_posture={**posture.__dict__, "max_output_bytes": 500},
        max_stdout_bytes=500,
    )
    assert result["ok"] is False
    assert result["stdout_truncated"] is True
    assert result["reason"] in (STDOUT_OVERSIZED, "RUNTIME_ERROR")


def test_runner_uses_temp_workdir_and_sanitizes_env(monkeypatch: pytest.MonkeyPatch):
    # Allow os for this test (to read cwd/env), and allow filesystem import.
    posture = default_posture()
    posture_dict = {
        **posture.__dict__,
        "allow_filesystem_write": True,
        "allowed_imports": posture.allowed_imports.union({"os"}),
    }
    runner = SubprocessRunner()

    monkeypatch.setenv("SECRET_TOKEN", "shh")
    src = "import os\nprint(os.getcwd())\nprint(os.environ.get('SECRET_TOKEN',''))\n"
    result = runner.run_script(
        src,
        timeout_sec=2.0,
        mode=posture.mode,
        security_posture=posture_dict,
    )
    assert result["ok"] is True
    # Workdir should be the per-run temp directory prefix.
    assert "hashen_exec_" in result.get("stdout", "")
    # Secret should not be inherited.
    assert "shh" not in result.get("stdout", "")


def test_runner_safe_script_succeeds():
    runner = SubprocessRunner()
    result = runner.run_script('print("ok")', timeout_sec=2.0)
    assert result["ok"] is True
    assert "ok" in result.get("stdout", "")
