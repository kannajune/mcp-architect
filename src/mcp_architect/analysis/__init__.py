"""Pure, dependency-free codebase-analysis functions.

These are intentionally decoupled from MCP so they can be unit-tested and
reused on their own.
"""
from .deps import build_graph, get_dependency_graph
from .diagram import build_mermaid
from .hotspots import find_hotspots
from .modules import explain_module
from .stack import get_overview

__all__ = [
    "get_overview",
    "get_dependency_graph",
    "build_graph",
    "build_mermaid",
    "find_hotspots",
    "explain_module",
]
