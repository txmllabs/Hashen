"""Execution modes and security posture for restricted execution.

This module defines configuration for best-effort restricted execution. It is not a
security boundary: enforcement varies by platform and Python runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ExecutionMode = Literal[
    "disabled",
    "restricted_local",
    "isolated_subprocess",
    "container_unsupported",
]


@dataclass(frozen=True)
class SecurityPosture:
    """Security posture for executing a script.

    Even in the strictest configuration, this is best-effort. Use OS/container isolation
    for untrusted code.
    """

    mode: ExecutionMode = "isolated_subprocess"
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_subprocess_spawn: bool = False

    allowed_imports: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "math",
                "json",
                "time",
                "datetime",
                "hashlib",
                "base64",
                "re",
                "statistics",
            }
        )
    )

    # Static validation limits
    max_source_bytes: int = 64_000
    max_ast_nodes: int = 5_000

    # Runtime limits (best-effort; some only on Unix)
    max_runtime_seconds: float = 5.0
    max_output_bytes: int = 64_000  # applied separately to stdout and stderr
    max_cpu_seconds: float | None = 5.0  # Unix: RLIMIT_CPU (seconds)
    max_memory_mb: float | None = 128.0  # Unix: RLIMIT_AS (MB)
    max_file_size_mb: float | None = 1.0  # Unix: RLIMIT_FSIZE (MB)
    max_processes: int | None = 0  # Unix: RLIMIT_NPROC (0 == no children)

    # Environment allowlist: only these keys are passed through when env is provided
    env_allowlist: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "LANG",
                "LC_ALL",
                "PYTHONIOENCODING",
            }
        )
    )


def default_posture() -> SecurityPosture:
    """Default best-effort posture: isolated subprocess, no network, no writes."""

    return SecurityPosture()
