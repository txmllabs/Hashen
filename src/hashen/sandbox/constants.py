"""Shared constants for restricted execution sandbox."""

from __future__ import annotations

# Always-denied imports (even if added to an allowlist).
# These are high-risk introspection/escape primitives for this runner.
DENYLIST_IMPORTS: frozenset[str] = frozenset(
    {
        "pickle",
        "shelve",
        "marshal",
        "ctypes",
        "builtins",
        "__builtins__",
        "importlib",
        "inspect",
    }
)
