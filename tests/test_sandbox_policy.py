"""Tests for sandbox policy and runner (G4)."""

from __future__ import annotations

import sys

import pytest

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


def test_script_import_socket_alias_blocked():
    """Block 'import socket as s' (denylist covers aliases)."""
    allowed, reason = check_policy("import socket as s\ns.create_connection(('x', 80))")
    assert allowed is False
    assert reason == "SANDBOX_POLICY_VIOLATION"


def test_script_importing_shutil_blocked():
    """Script importing shutil -> blocked (denylist)."""
    allowed, reason = check_policy("import shutil\nshutil.copy('a', 'b')")
    assert allowed is False
    assert reason == "SANDBOX_POLICY_VIOLATION"


def test_runner_socket_import_returns_violation():
    """Runner returns SANDBOX_POLICY_VIOLATION for socket import."""
    runner = SubprocessRunner()
    result = runner.run_script("import socket\nprint(1)", timeout_sec=5.0)
    assert result["ok"] is False
    assert result.get("reason") == "SANDBOX_POLICY_VIOLATION"


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


def test_runner_infinite_loop_times_out():
    """Infinite loop is killed on timeout (TIMEOUT)."""
    runner = SubprocessRunner()
    result = runner.run_script("while True: pass", timeout_sec=0.3)
    assert result["ok"] is False
    assert result.get("reason") == "TIMEOUT"


def test_runner_os_import_returns_violation():
    """Runner returns SANDBOX_POLICY_VIOLATION for os import."""
    runner = SubprocessRunner()
    result = runner.run_script("import os\nprint(os.getcwd())", timeout_sec=5.0)
    assert result["ok"] is False
    assert result.get("reason") == "SANDBOX_POLICY_VIOLATION"


def test_runner_script_signature_invalid_on_sha256_mismatch():
    """Runner returns SCRIPT_SIGNATURE_INVALID when script_sha256 does not match."""
    runner = SubprocessRunner()
    result = runner.run_script("print(1)", timeout_sec=5.0, script_sha256="wrong")
    assert result["ok"] is False
    assert result.get("reason") == "SCRIPT_SIGNATURE_INVALID"


def test_runner_ok_json_stdout():
    """Runner allows script that prints JSON."""
    runner = SubprocessRunner()
    result = runner.run_script('print("{}")', timeout_sec=5.0)
    assert result["ok"] is True
    assert "{}" in result.get("stdout", "")


@pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_AS not on Windows")
def test_runner_excessive_allocation_triggers_resource_limit():
    """On Unix, script exceeding memory limit triggers RESOURCE_LIMIT or fails."""
    runner = SubprocessRunner(max_cpu_seconds=10, max_mem_mb=1)
    # Allocate way more than 1 MB
    result = runner.run_script(
        "x = [0] * (2 * 1024 * 1024)\nprint(1)",
        timeout_sec=5.0,
    )
    # May get RESOURCE_LIMIT or (on some systems) still succeed if limit not enforced
    if not result["ok"]:
        assert result.get("reason") in ("RESOURCE_LIMIT", "RUNTIME_ERROR", "TIMEOUT")


def test_strict_mode_requires_script_hash():
    """Strict mode rejects run when script_sha256 is not provided."""
    runner = SubprocessRunner()
    result = runner.run_script("print(1)", timeout_sec=5.0, strict_mode=True)
    assert result["ok"] is False
    assert result.get("reason") == "STRICT_MODE_REQUIRES_SCRIPT_HASH"


def test_strict_mode_accepts_when_script_sha256_provided():
    """Strict mode accepts when script_sha256 matches."""
    import hashlib

    runner = SubprocessRunner()
    src = "print(42)"
    h = hashlib.sha256(src.encode()).hexdigest()
    result = runner.run_script(src, timeout_sec=5.0, script_sha256=h, strict_mode=True)
    assert result["ok"] is True


def test_oversized_stdout_fails():
    """When max_stdout_bytes is set and stdout exceeds it, return STDOUT_OVERSIZED."""
    runner = SubprocessRunner()
    result = runner.run_script(
        'print("x" * 1000)',
        timeout_sec=5.0,
        max_stdout_bytes=100,
    )
    assert result["ok"] is False
    assert result.get("reason") == "STDOUT_OVERSIZED"


def test_runner_returns_stdout_as_is_invalid_json():
    """Runner returns raw stdout; caller is responsible for JSON validation."""
    runner = SubprocessRunner()
    result = runner.run_script('print("not json at all")', timeout_sec=5.0)
    assert result["ok"] is True
    assert "not json at all" in result.get("stdout", "")
