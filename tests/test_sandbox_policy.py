"""Tests for sandbox policy and runner (G4)."""

from __future__ import annotations

from hashen.sandbox import SubprocessRunner, check_policy


def test_script_importing_os_blocked():
    """G4: Script importing os -> blocked (SANDBOX_POLICY_VIOLATION)."""
    allowed, reason = check_policy("import os\nprint(1)")
    assert allowed is False
    assert reason == "SANDBOX_POLICY_VIOLATION"


def test_script_importing_socket_blocked():
    """G4: Script importing socket -> blocked."""
    allowed, reason = check_policy("import socket\nx = 1")
    assert allowed is False
    assert reason == "SANDBOX_POLICY_VIOLATION"


def test_script_allowed_without_denylist():
    """Script with only allowed imports passes policy."""
    allowed, reason = check_policy("import json\nprint(json.dumps({}))")
    assert allowed is True
    assert reason is None


def test_runner_timeout_killed():
    """G4: Script exceeding timeout -> killed (TIMEOUT)."""
    runner = SubprocessRunner()
    result = runner.run_script(
        "import time\ntime.sleep(10)\nprint(1)",
        timeout_sec=0.2,
    )
    assert result["ok"] is False
    assert result.get("reason") == "TIMEOUT"


def test_runner_os_import_returns_violation():
    """Runner returns SANDBOX_POLICY_VIOLATION for os import."""
    runner = SubprocessRunner()
    result = runner.run_script("import os\nprint(os.getcwd())", timeout_sec=5.0)
    assert result["ok"] is False
    assert result.get("reason") == "SANDBOX_POLICY_VIOLATION"


def test_runner_ok_json_stdout():
    """Runner allows script that prints JSON."""
    runner = SubprocessRunner()
    result = runner.run_script('print("{}")', timeout_sec=5.0)
    assert result["ok"] is True
    assert "{}" in result.get("stdout", "")
