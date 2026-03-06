"""Text pathway: character n-gram frequency → values for TSEC (described alternative)."""

from __future__ import annotations


def text_to_values(text: str, window_chars: int = 100) -> list[float]:
    """Convert text to normalized character ordinal values for TSEC."""
    return [(ord(c) % 128) / 127.0 for c in text]
