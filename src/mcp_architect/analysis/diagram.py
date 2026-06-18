"""Render the internal dependency graph as a Mermaid flowchart.

Robust by construction:
- **Numeric node IDs** (`n0`, `n1`, …) so module names / file paths can never
  break Mermaid's node-ID grammar.
- Real names go in **quoted labels**, with quotes/brackets/newlines escaped.
- The graph is **capped** to the most-connected nodes (huge graphs are both
  unreadable and more likely to hit renderer limits).
"""
from __future__ import annotations

from pathlib import Path

from .deps import build_graph

_VALID_DIRECTIONS = {"TB", "TD", "BT", "LR", "RL"}


def _escape_label(name: str) -> str:
    """Make a string safe to sit inside a Mermaid `["..."]` quoted label."""
    return (
        name.replace("\\", "/")
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("`", "'")
        .strip()
    )


def build_mermaid(
    root: str | Path,
    language: str = "auto",
    max_nodes: int = 40,
    direction: str = "LR",
) -> str:
    """Return a Mermaid `flowchart` string for the internal dependency graph."""
    if direction not in _VALID_DIRECTIONS:
        direction = "LR"
    max_nodes = max(1, min(int(max_nodes), 120))

    graph = build_graph(root, language)

    # Rank nodes by total degree (fan-in + fan-out) and keep the densest ones.
    degree: dict[str, int] = {}
    for src, dsts in graph.items():
        degree[src] = degree.get(src, 0) + len(dsts)
        for dst in dsts:
            degree[dst] = degree.get(dst, 0) + 1

    if not degree:
        return f'flowchart {direction}\n    n0["(no internal dependencies found)"]'

    selected = sorted(degree, key=lambda n: (degree[n], n), reverse=True)[:max_nodes]
    selected_set = set(selected)
    ids = {name: f"n{i}" for i, name in enumerate(selected)}

    lines = [f"flowchart {direction}"]
    for name in selected:
        lines.append(f'    {ids[name]}["{_escape_label(name)}"]')

    seen: set[tuple[str, str]] = set()
    for src in selected:
        for dst in sorted(graph.get(src, ())):
            if dst in selected_set and (src, dst) not in seen:
                seen.add((src, dst))
                lines.append(f"    {ids[src]} --> {ids[dst]}")

    return "\n".join(lines)
