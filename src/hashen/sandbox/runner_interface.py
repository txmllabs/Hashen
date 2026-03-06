"""Runner interface: run_script(script_source, timeout_sec, ...) -> result dict."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class RunnerInterface(ABC):
    """Abstract runner; subprocess MVP implements this; Docker/gVisor can replace later."""

    @abstractmethod
    def run_script(
        self,
        script_source: str,
        timeout_sec: float,
        script_sha256: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        strict_mode: bool = False,
        max_stdout_bytes: Optional[int] = None,
    ) -> dict[str, Any]:
        """Execute script under policy; return run_result dict.
        strict_mode: require script_sha256 to be set."""
        ...
