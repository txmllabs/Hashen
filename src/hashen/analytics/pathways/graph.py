"""Graph pathway: degree distributions → values for TSEC (130d, Claim 29)."""

from __future__ import annotations

import json


def graph_degrees_to_values(edges: list[tuple[str, str]]) -> list[float]:
    """
    Build degree distribution from edge list, normalize for TSEC.

    Patent Claim 29: H1 on node degree distributions of interaction graphs.
    """
    degree_count: dict[str, int] = {}
    for src, dst in edges:
        degree_count[src] = degree_count.get(src, 0) + 1
        degree_count[dst] = degree_count.get(dst, 0) + 1
    if not degree_count:
        return []
    degrees = list(degree_count.values())
    max_deg = max(degrees) if degrees else 1
    return [d / max_deg for d in degrees]


def graph_from_bytes(data: bytes) -> list[float]:
    """
    Parse bytes as JSON edge list and return normalized degree values.

    Expected JSON format: [["addr1", "addr2"], ["addr2", "addr3"], ...]
    Falls back to treating bytes as raw values if JSON parse fails.
    """
    try:
        text = data.decode("utf-8")
        edges = json.loads(text)
        if isinstance(edges, list) and all(
            isinstance(e, (list, tuple)) and len(e) == 2 for e in edges
        ):
            return graph_degrees_to_values([(str(e[0]), str(e[1])) for e in edges])
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        pass
    return [b / 255.0 for b in data]
