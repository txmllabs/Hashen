"""Layered script validation for restricted execution.

This is a best-effort gate intended to reduce risk. It is not a security boundary.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from hashen.sandbox.constants import DENYLIST_IMPORTS
from hashen.sandbox.posture import SecurityPosture


@dataclass(frozen=True)
class Violation:
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


POLICY_REJECTED = "SANDBOX_POLICY_VIOLATION"

V_IMPORT_NOT_ALLOWED = "IMPORT_NOT_ALLOWED"
V_IMPORT_DENYLISTED = "IMPORT_DENYLISTED"
V_BUILTIN_BLOCKED = "BUILTIN_BLOCKED"
V_DUNDER_REFLECTION = "DUNDER_REFLECTION"
V_DANGEROUS_ATTR = "DANGEROUS_ATTR"
V_COMPLEXITY_LIMIT = "COMPLEXITY_LIMIT"
V_SYNTAX_ERROR = "SYNTAX_ERROR"
V_NETWORK_NOT_ALLOWED = "NETWORK_NOT_ALLOWED"
V_SUBPROCESS_NOT_ALLOWED = "SUBPROCESS_NOT_ALLOWED"
V_FILESYSTEM_WRITE_NOT_ALLOWED = "FILESYSTEM_WRITE_NOT_ALLOWED"

_BLOCKED_CALL_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "__import__",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "breakpoint",
        "help",
    }
)

_DANGEROUS_ATTRS = frozenset(
    {
        "__class__",
        "__mro__",
        "__subclasses__",
        "__getattribute__",
        "__dict__",
        "__globals__",
        "__code__",
        "__closure__",
        "__func__",
    }
)

_NETWORK_IMPORTS = frozenset({"socket", "http", "urllib", "ssl", "ftplib", "requests"})
_SUBPROCESS_IMPORTS = frozenset({"subprocess", "multiprocessing"})
_FS_IMPORTS = frozenset({"os", "pathlib", "shutil"})


def _count_nodes(tree: ast.AST) -> int:
    return sum(1 for _ in ast.walk(tree))


def validate_source(source: str, posture: SecurityPosture) -> tuple[bool, list[Violation]]:
    violations: list[Violation] = []

    # Normalize common Windows UTF-8 BOM (e.g. produced by some editors).
    if source.startswith("\ufeff"):
        source = source.lstrip("\ufeff")

    if len(source.encode("utf-8")) > posture.max_source_bytes:
        violations.append(
            Violation(
                code=V_COMPLEXITY_LIMIT,
                message=f"Source exceeds max_source_bytes={posture.max_source_bytes}.",
            )
        )
        return False, violations

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        violations.append(Violation(code=V_SYNTAX_ERROR, message=f"SyntaxError: {e}"))
        return False, violations

    if _count_nodes(tree) > posture.max_ast_nodes:
        violations.append(
            Violation(
                code=V_COMPLEXITY_LIMIT,
                message=f"AST exceeds max_ast_nodes={posture.max_ast_nodes}.",
            )
        )
        return False, violations

    # Import controls: allowlist + denylist
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name in DENYLIST_IMPORTS:
                    violations.append(
                        Violation(code=V_IMPORT_DENYLISTED, message=f"Import denied: {name}")
                    )
                elif name not in posture.allowed_imports:
                    violations.append(
                        Violation(code=V_IMPORT_NOT_ALLOWED, message=f"Import not allowed: {name}")
                    )
                if not posture.allow_network and name in _NETWORK_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_NETWORK_NOT_ALLOWED,
                            message=f"Network import denied: {name}",
                        )
                    )
                if not posture.allow_subprocess_spawn and name in _SUBPROCESS_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_SUBPROCESS_NOT_ALLOWED,
                            message=f"Subprocess import denied: {name}",
                        )
                    )
                if not posture.allow_filesystem_write and name in _FS_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_FILESYSTEM_WRITE_NOT_ALLOWED,
                            message=f"Filesystem import denied: {name}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                name = node.module.split(".")[0]
                if name in DENYLIST_IMPORTS:
                    violations.append(
                        Violation(code=V_IMPORT_DENYLISTED, message=f"Import denied: {name}")
                    )
                elif name not in posture.allowed_imports:
                    violations.append(
                        Violation(code=V_IMPORT_NOT_ALLOWED, message=f"Import not allowed: {name}")
                    )
                if not posture.allow_network and name in _NETWORK_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_NETWORK_NOT_ALLOWED,
                            message=f"Network import denied: {name}",
                        )
                    )
                if not posture.allow_subprocess_spawn and name in _SUBPROCESS_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_SUBPROCESS_NOT_ALLOWED,
                            message=f"Subprocess import denied: {name}",
                        )
                    )
                if not posture.allow_filesystem_write and name in _FS_IMPORTS:
                    violations.append(
                        Violation(
                            code=V_FILESYSTEM_WRITE_NOT_ALLOWED,
                            message=f"Filesystem import denied: {name}",
                        )
                    )

        # Block direct use of dangerous builtins by name call
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in _BLOCKED_CALL_NAMES:
                violations.append(
                    Violation(code=V_BUILTIN_BLOCKED, message=f"Call blocked: {fn.id}()")
                )

        # Block dunder attributes and obvious reflection helpers
        if isinstance(node, ast.Attribute):
            if node.attr in _DANGEROUS_ATTRS:
                violations.append(
                    Violation(code=V_DANGEROUS_ATTR, message=f"Dangerous attribute: {node.attr}")
                )
            if node.attr.startswith("__") and node.attr.endswith("__"):
                violations.append(
                    Violation(
                        code=V_DUNDER_REFLECTION,
                        message=f"Dunder attribute access: {node.attr}",
                    )
                )
        if isinstance(node, ast.Name) and node.id.startswith("__") and node.id.endswith("__"):
            violations.append(
                Violation(code=V_DUNDER_REFLECTION, message=f"Dunder name usage: {node.id}")
            )

    ok = len([v for v in violations if v.code != ""]) == 0
    return ok, violations
