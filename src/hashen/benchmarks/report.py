"""Benchmark report output: write run results to JSON file or stdout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(
    result: dict[str, Any],
    path: Path | None = None,
    pretty: bool = False,
) -> None:
    """
    Write benchmark result to file or stdout.

    If path is None, print to stdout. Otherwise write to path.
    """
    payload = json.dumps(result, sort_keys=True, indent=2 if pretty else None)
    if path is None:
        print(payload)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
