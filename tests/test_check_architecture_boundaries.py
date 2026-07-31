"""Tests for scripts/check_architecture_boundaries.py (repo hygiene Stage 5,
2026-07-30): the import-cycle detector added after finding and fixing a real
circular dependency between multi_provider_eval and multifactor_acquisition.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_architecture_boundaries import (  # noqa: E402
    build_package_graph,
    find_one_cycle,
    imported_subpackages,
)

# ---------------------------------------------------------------------------
# Cycle detection on synthetic graphs
# ---------------------------------------------------------------------------


def test_find_one_cycle_returns_none_for_acyclic_graph():
    graph = {"a": {"b"}, "b": {"c"}, "c": set()}
    assert find_one_cycle(graph) is None


def test_find_one_cycle_detects_direct_two_cycle():
    graph = {"a": {"b"}, "b": {"a"}}
    cycle = find_one_cycle(graph)
    assert cycle is not None
    assert set(cycle) == {"a", "b"}
    assert cycle[0] == cycle[-1]


def test_find_one_cycle_detects_indirect_three_cycle():
    graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
    cycle = find_one_cycle(graph)
    assert cycle is not None
    assert set(cycle) == {"a", "b", "c"}
    assert cycle[0] == cycle[-1]


def test_find_one_cycle_handles_disconnected_components():
    """A cycle in one component must be found even if other components are
    acyclic and processed first/after."""
    graph = {"x": set(), "y": {"z"}, "z": set(), "a": {"b"}, "b": {"a"}}
    cycle = find_one_cycle(graph)
    assert cycle is not None
    assert set(cycle) == {"a", "b"}


def test_find_one_cycle_ignores_self_loops_correctly():
    """A package that (oddly) references itself should not itself be
    reported as a cycle by this checker -- imported_subpackages() already
    excludes self-references, so the graph builder never produces true
    self-loops; this documents that expectation at the cycle-finder level
    too, for a graph that simply omits self-edges."""
    graph = {"a": {"b"}, "b": set()}
    assert find_one_cycle(graph) is None


# ---------------------------------------------------------------------------
# imported_subpackages(): AST-based import extraction, incl. TYPE_CHECKING
# exclusion and self-reference exclusion
# ---------------------------------------------------------------------------


def test_imported_subpackages_finds_top_level_from_import(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("from consistency_ranker.other_pkg.sub import thing\n")
    assert imported_subpackages(f, own_package="this_pkg") == {"other_pkg"}


def test_imported_subpackages_finds_plain_import(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("import consistency_ranker.other_pkg.sub\n")
    assert imported_subpackages(f, own_package="this_pkg") == {"other_pkg"}


def test_imported_subpackages_excludes_self_references(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("from consistency_ranker.this_pkg.sibling import thing\n")
    assert imported_subpackages(f, own_package="this_pkg") == set()


def test_imported_subpackages_excludes_type_checking_only_imports(tmp_path):
    """A TYPE_CHECKING-guarded import never executes at runtime and must
    not be treated as a real architectural coupling."""
    f = tmp_path / "mod.py"
    f.write_text(
        textwrap.dedent(
            """
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from consistency_ranker.other_pkg.types import SomeType

            def f(x: "SomeType") -> None:
                pass
            """
        )
    )
    assert imported_subpackages(f, own_package="this_pkg") == set()


def test_imported_subpackages_counts_function_scoped_deferred_imports(tmp_path):
    """A deferred (function-scoped, non-TYPE_CHECKING) import still
    represents a real dependency -- per the review, a lazy import should
    not be treated as a way to hide a genuine architectural coupling."""
    f = tmp_path / "mod.py"
    f.write_text(
        textwrap.dedent(
            """
            def build():
                from consistency_ranker.other_pkg.thing import Thing
                return Thing()
            """
        )
    )
    assert imported_subpackages(f, own_package="this_pkg") == {"other_pkg"}


def test_imported_subpackages_ignores_non_consistency_ranker_imports(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("import numpy\nfrom pathlib import Path\n")
    assert imported_subpackages(f, own_package="this_pkg") == set()


def test_imported_subpackages_ignores_syntax_errors_gracefully(tmp_path):
    """Must not crash the whole check on an unrelated malformed file --
    returns an empty set rather than raising."""
    f = tmp_path / "broken.py"
    f.write_text("def f(:\n")
    assert imported_subpackages(f, own_package="this_pkg") == set()


# ---------------------------------------------------------------------------
# End-to-end: the real repository graph must currently be acyclic, and must
# specifically not contain the historical multi_provider_eval <->
# multifactor_acquisition cycle.
# ---------------------------------------------------------------------------


def test_real_repository_package_graph_is_currently_acyclic():
    graph = build_package_graph()
    cycle = find_one_cycle(graph)
    assert cycle is None, f"unexpected circular subpackage dependency: {cycle}"


def test_real_repository_graph_no_longer_has_the_historical_cycle():
    graph = build_package_graph()
    assert "multifactor_acquisition" not in graph.get("multi_provider_eval", set()), (
        "multi_provider_eval must not import multifactor_acquisition "
        "(this was the specific cycle this checker was built to catch)"
    )


def test_check_architecture_boundaries_script_exits_zero_on_current_repo():
    import subprocess

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_architecture_boundaries.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
