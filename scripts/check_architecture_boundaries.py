#!/usr/bin/env python
"""
check_architecture_boundaries.py
=================================
Detects circular import dependencies among ``consistency_ranker``'s
top-level subpackages (e.g. ``multi_provider_eval``, ``multifactor_acquisition``,
``repair_frontier``, ...).

Motivation: a repository-wide architectural review (2026-07-30) found a real
circular package dependency between ``multi_provider_eval`` and
``multifactor_acquisition`` -- neither package could be understood, tested,
or extracted independently of the other, even though no single file pair
triggered a Python ``ImportError``. This check exists so that specific cycle
(and any other package-level cycle) cannot silently reappear.

Scope
-----
Only ``src/consistency_ranker/<package>/*.py`` files are examined -- i.e.
files that live inside a *subpackage* (a directory with its own ``.py``
files under ``src/consistency_ranker/``), not the top-level single-file
modules (``baseline_ranking.py``, ``mwfas_solver.py``, etc.), not
``scripts/``, and not ``tests/``. The package level is where a cycle
actually prevents independent testing/extraction; top-level modules already
form a clean dependency-free "core algorithm" layer per the same review,
and test files legitimately import many otherwise-unrelated modules for
testing purposes without that constituting an architectural coupling.

Imports inside ``if TYPE_CHECKING:`` blocks are ignored: they never execute
at runtime and cannot cause a real circular-import failure or runtime
coupling. Ordinary function-scoped (deferred) imports ARE still counted --
a package that only imports another lazily still cannot be tested or
vendored without it, so deferring an import is not treated as a fix for a
genuine architectural cycle (per the review's explicit finding that a
lazy import should not be the primary fix for a cycle).

Usage
-----
    python scripts/check_architecture_boundaries.py           # normal
    python scripts/check_architecture_boundaries.py --verbose # print the full graph
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "src" / "consistency_ranker"


def _own_subpackage(path: Path) -> str | None:
    """Return the subpackage name *path* belongs to, or None if *path* is a
    top-level module (not inside any subpackage) or otherwise out of scope."""
    rel = path.relative_to(PACKAGE_ROOT)
    parts = rel.parts
    if len(parts) < 2:
        return None
    if parts[0] in {"__pycache__"}:
        return None
    return parts[0]


def _is_type_checking_test(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _nodes_inside_type_checking_blocks(tree: ast.AST) -> set[int]:
    """Return the id() of every AST node nested inside an
    ``if TYPE_CHECKING:`` block, so those imports can be excluded."""
    excluded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_test(node.test):
            for sub in ast.walk(node):
                excluded.add(id(sub))
    return excluded


def imported_subpackages(path: Path, own_package: str) -> set[str]:
    """Return every consistency_ranker subpackage *path* imports from,
    excluding TYPE_CHECKING-only imports and self-references."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()

    excluded = _nodes_inside_type_checking_blocks(tree)
    found: set[str] = set()

    for node in ast.walk(tree):
        if id(node) in excluded:
            continue
        module_name = None
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            module_name = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("consistency_ranker."):
                    parts = alias.name.split(".")
                    if len(parts) >= 2 and parts[1] != own_package:
                        found.add(parts[1])
            continue

        if module_name and module_name.startswith("consistency_ranker."):
            parts = module_name.split(".")
            if len(parts) >= 2 and parts[1] != own_package:
                found.add(parts[1])

    return found


def build_package_graph() -> dict[str, set[str]]:
    """Return {subpackage: {subpackages it imports from}} across the tree."""
    graph: dict[str, set[str]] = defaultdict(set)
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        pkg = _own_subpackage(path)
        if pkg is None:
            continue
        graph[pkg] |= imported_subpackages(path, pkg)
        graph.setdefault(pkg, set())
    return dict(graph)


def find_one_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return one concrete cycle (list of package names, first==last) if the
    graph has any, else None. Standard white/gray/black DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in graph}
    parent: dict[str, str] = {}

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        for v in sorted(graph.get(u, ())):
            if v not in color:
                color[v] = WHITE
            if color[v] == WHITE:
                parent[v] = u
                found = dfs(v)
                if found is not None:
                    return found
            elif color[v] == GRAY:
                cycle = [v]
                cur = u
                while cur != v:
                    cycle.append(cur)
                    cur = parent[cur]
                cycle.append(v)
                cycle.reverse()
                return cycle
        color[u] = BLACK
        return None

    for node in sorted(graph):
        if color[node] == WHITE:
            found = dfs(node)
            if found is not None:
                return found
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="print the full package graph")
    args = parser.parse_args(argv)

    graph = build_package_graph()

    if args.verbose:
        print(f"Scanned {len(graph)} subpackages under {PACKAGE_ROOT}:")
        for pkg in sorted(graph):
            deps = ", ".join(sorted(graph[pkg])) or "(none)"
            print(f"  {pkg} -> {deps}")
        print()

    cycle = find_one_cycle(graph)
    if cycle is not None:
        chain = " -> ".join(cycle)
        print(f"FAIL: circular subpackage dependency detected: {chain}", file=sys.stderr)
        print(
            "Each package in this cycle imports (directly or transitively) from "
            "another package in the same cycle, so none of them can be understood, "
            "tested, or extracted independently. See docs/ARCHITECTURE.md for the "
            "intended layering, and extract the smallest shared concern causing the "
            "cycle into a neutral module both sides can depend on one-directionally.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: no circular subpackage dependency found among {len(graph)} subpackages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
