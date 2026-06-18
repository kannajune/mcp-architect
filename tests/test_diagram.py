"""Structural validity tests for the Mermaid diagram generator.

These assert invariants that, if held, mean the output is syntactically sound:
numeric node IDs, quoted labels, and every edge endpoint declared.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from mcp_architect.analysis import build_mermaid

_DECL = re.compile(r'^\s*(n\d+)\["(.*)"\]\s*$')
_EDGE = re.compile(r"^\s*(n\d+)\s*-->\s*(n\d+)\s*$")


def _parse(diagram: str):
    lines = diagram.splitlines()
    assert lines[0].startswith("flowchart "), "must start with a flowchart header"
    decls, edges = {}, []
    for line in lines[1:]:
        if not line.strip():
            continue
        m_decl = _DECL.match(line)
        m_edge = _EDGE.match(line)
        if m_decl:
            assert m_decl.group(1) not in decls, "duplicate node declaration"
            decls[m_decl.group(1)] = m_decl.group(2)
        elif m_edge:
            edges.append((m_edge.group(1), m_edge.group(2)))
        else:
            pytest.fail(f"unrecognized / unsafe Mermaid line: {line!r}")
    return decls, edges


@pytest.fixture
def nasty(tmp_path: Path) -> Path:
    """Modules whose names contain characters that classically break Mermaid."""
    pkg = tmp_path / "my-app.v2"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("x = 1\n")
    (pkg / "api.py").write_text("from pathlib import Path\n")
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "node[1].py").write_text("CONTENT = 1\n")
    return tmp_path


def test_header_and_grammar(nasty: Path):
    decls, edges = _parse(build_mermaid(nasty))
    # all ids are numeric-style and every edge endpoint is declared
    assert all(re.fullmatch(r"n\d+", nid) for nid in decls)
    for a, b in edges:
        assert a in decls and b in decls, "edge references an undeclared node"


def test_labels_are_escaped(nasty: Path):
    decls, _ = _parse(build_mermaid(nasty))
    for label in decls.values():
        assert '"' not in label  # quotes neutralized
        assert "[" not in label and "]" not in label  # brackets neutralized


def test_empty_graph_is_valid():
    decls, edges = _parse(build_mermaid_on_empty())
    assert len(decls) >= 1 and edges == []


def build_mermaid_on_empty():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "README.md").write_text("# nothing to import\n")
        return build_mermaid(d)


def test_node_cap_respected(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(20):
        (pkg / f"m{i}.py").write_text("from pkg import __init__\n")
    decls, _ = _parse(build_mermaid(tmp_path, max_nodes=5))
    assert len(decls) <= 5


def test_direction_is_sanitized(tmp_path: Path):
    (tmp_path / "a.py").write_text("import os\n")
    out = build_mermaid(tmp_path, direction="; rm -rf /")  # garbage direction
    assert out.splitlines()[0] == "flowchart LR"  # falls back safely


@pytest.mark.skipif(
    os.environ.get("MCP_ARCHITECT_MERMAID_E2E") != "1" or shutil.which("npx") is None,
    reason="set MCP_ARCHITECT_MERMAID_E2E=1 (needs npx) for the real Mermaid render check",
)
def test_renders_with_real_mermaid(tmp_path: Path):
    """Definitive check: the output renders through the actual Mermaid engine."""
    pkg = tmp_path / "weird-pkg.v2"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("from pathlib import Path\n")
    (pkg / "b.py").write_text("x = 1\n")
    mmd = tmp_path / "d.mmd"
    mmd.write_text(build_mermaid(tmp_path))
    out = tmp_path / "d.svg"
    subprocess.run(
        ["npx", "-y", "@mermaid-js/mermaid-cli@latest", "-i", str(mmd), "-o", str(out)],
        check=True, capture_output=True, timeout=180,
    )
    assert out.exists() and out.stat().st_size > 0
