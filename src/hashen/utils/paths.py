"""Path helpers for seals, audit, cache, reports, c2pa_stub."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def ensure_dir(path: Path | str) -> Path:
    """Create directory if it does not exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def base_dir() -> Path:
    """Project base directory (parent of src)."""
    # utils -> hashen -> src -> project root
    return Path(__file__).resolve().parent.parent.parent


def seals_dir(root: Optional[Path] = None) -> Path:
    if root is None:
        root = base_dir()
    return ensure_dir(root / "seals")


def audit_dir(root: Optional[Path] = None) -> Path:
    if root is None:
        root = base_dir()
    return ensure_dir(root / "audit")


def c2pa_stub_dir(root: Optional[Path] = None) -> Path:
    if root is None:
        root = base_dir()
    return ensure_dir(root / "c2pa_stub")


def reports_dir(root: Optional[Path] = None) -> Path:
    if root is None:
        root = base_dir()
    return ensure_dir(root / "reports")


def cache_dir(root: Optional[Path] = None) -> Path:
    if root is None:
        root = base_dir()
    return ensure_dir(root / "cache")
