"""API server placeholder: orchestration entrypoint for HTTP (future)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hashen.orchestrator import run_pipeline


def handle_run(
    artifact_bytes: bytes,
    run_id: str,
    config_vector: dict[str, Any],
    root: Optional[Path] = None,
) -> dict[str, Any]:
    """HTTP handler entrypoint: run pipeline and return result."""
    return run_pipeline(artifact_bytes, run_id, config_vector, root=root)
