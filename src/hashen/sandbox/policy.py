"""Import denylist and policy digest for sandbox. policy_version for audit binding."""

from __future__ import annotations

import ast
import hashlib

POLICY_VERSION = "hashen.policy.v1"

# Denylist: scripts importing these are blocked (SANDBOX_POLICY_VIOLATION)
# Includes network/data exfil: socket, urllib, http, ftplib, ssl, requests, shutil, etc.
DENYLIST_IMPORTS: set[str] = {
    "os",
    "subprocess",
    "socket",
    "urllib",
    "urllib2",
    "http",
    "ftplib",
    "ssl",
    "requests",
    "shutil",
    "smtplib",
    "telnetlib",
    "poplib",
    "imaplib",
    "nntplib",
    "pickle",
    "shelve",
    "marshal",
    "ctypes",
    "sys",
    "builtins",
    "__builtins__",
}


def get_imports_from_source(source: str) -> list[str]:
    """Parse Python source with AST and return list of top-level import names."""
    names: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names


def check_policy(source: str) -> tuple[bool, str | None]:
    """Return (allowed, reason). Denylisted import -> (False, SANDBOX_POLICY_VIOLATION)."""
    imports = get_imports_from_source(source)
    for name in imports:
        if name in DENYLIST_IMPORTS:
            return False, "SANDBOX_POLICY_VIOLATION"
    return True, None


def policy_digest() -> str:
    """Hash of policy (denylist) for audit binding."""
    blob = ",".join(sorted(DENYLIST_IMPORTS))
    return hashlib.sha256(blob.encode()).hexdigest()
