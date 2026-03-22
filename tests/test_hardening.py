"""
Tests for argument validation, edge cases, and regression checks.

Covers:
- CLI argument validation for run_synthetic.py
- greedy_fas edge cases (empty graph, DAG guarantee, isolated nodes)
- pairwise_inconsistency_count edge cases
- regression test for committed evidence values in key CSV files
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx
import pytest

from consistency_ranker.evaluation import pairwise_inconsistency_count
from consistency_ranker.greedy_fas import greedy_fas
from scripts.run_synthetic import parse_args, run_experiment

# ─── CLI argument validation ──────────────────────────────────────────────────


class TestRunSyntheticArgValidation:
    """Verify that run_experiment raises helpful errors for invalid inputs."""

    def test_negative_n_items_raises(self, tmp_path):
        with pytest.raises(ValueError, match="n-items"):
            run_experiment(n_items=-1, noise=0.1, seed=42, output_dir=tmp_path)

    def test_zero_n_items_raises(self, tmp_path):
        with pytest.raises(ValueError, match="n-items"):
            run_experiment(n_items=0, noise=0.1, seed=42, output_dir=tmp_path)

    def test_one_item_raises(self, tmp_path):
        with pytest.raises(ValueError, match="n-items"):
            run_experiment(n_items=1, noise=0.1, seed=42, output_dir=tmp_path)

    def test_noise_equal_to_one_raises(self, tmp_path):
        with pytest.raises(ValueError, match="noise"):
            run_experiment(n_items=5, noise=1.0, seed=42, output_dir=tmp_path)

    def test_noise_greater_than_one_raises(self, tmp_path):
        with pytest.raises(ValueError, match="noise"):
            run_experiment(n_items=5, noise=1.5, seed=42, output_dir=tmp_path)

    def test_negative_noise_raises(self, tmp_path):
        with pytest.raises(ValueError, match="noise"):
            run_experiment(n_items=5, noise=-0.1, seed=42, output_dir=tmp_path)

    def test_valid_zero_noise_runs(self, tmp_path):
        result = run_experiment(n_items=5, noise=0.0, seed=42, output_dir=tmp_path)
        assert "evaluation" in result

    def test_parse_args_defaults(self):
        args = parse_args([])
        assert args.n_items == 20
        assert args.noise == pytest.approx(0.2)
        assert args.seed == 42
        assert args.weight_scheme == "margin"

    def test_parse_args_custom_values(self):
        args = parse_args(["--n-items", "50", "--noise", "0.15", "--seed", "7"])
        assert args.n_items == 50
        assert args.noise == pytest.approx(0.15)
        assert args.seed == 7


# ─── greedy_fas edge cases ────────────────────────────────────────────────────


class TestGreedyFasEdgeCases:
    def test_empty_graph_returns_dag(self):
        g = nx.DiGraph()
        dag, removed = greedy_fas(g)
        assert nx.is_directed_acyclic_graph(dag)
        assert removed == []

    def test_single_node_returns_dag(self):
        g = nx.DiGraph()
        g.add_node("x")
        dag, removed = greedy_fas(g)
        assert nx.is_directed_acyclic_graph(dag)
        assert removed == []

    def test_single_edge_returns_dag(self):
        g = nx.DiGraph()
        g.add_edge("a", "b", weight=1.0)
        dag, removed = greedy_fas(g)
        assert nx.is_directed_acyclic_graph(dag)
        assert removed == []

    def test_result_is_always_dag(self):
        """Property test: greedy_fas output is always a DAG for various graphs."""
        import random

        rng = random.Random(0)
        for _ in range(20):
            g = nx.DiGraph()
            nodes = list(range(8))
            g.add_nodes_from(nodes)
            for u in nodes:
                for v in nodes:
                    if u != v and rng.random() < 0.4:
                        g.add_edge(u, v, weight=rng.random())
            dag, _ = greedy_fas(g)
            assert nx.is_directed_acyclic_graph(dag), "greedy_fas must always return a DAG"

    def test_isolated_nodes_preserved(self):
        g = nx.DiGraph()
        g.add_nodes_from(["a", "b", "c"])
        g.add_edge("a", "b", weight=1.0)
        g.add_edge("b", "a", weight=0.5)
        dag, removed = greedy_fas(g)
        assert "c" in dag.nodes()
        assert nx.is_directed_acyclic_graph(dag)

    def test_self_loop_removed(self):
        g = nx.DiGraph()
        g.add_edge("a", "a", weight=1.0)
        g.add_edge("a", "b", weight=1.0)
        dag, removed = greedy_fas(g)
        assert nx.is_directed_acyclic_graph(dag)
        assert len(removed) >= 1

    def test_complex_cycle_becomes_dag(self):
        g = nx.DiGraph()
        # 4-cycle plus extra edge
        g.add_edge("a", "b", weight=3.0)
        g.add_edge("b", "c", weight=3.0)
        g.add_edge("c", "d", weight=3.0)
        g.add_edge("d", "a", weight=1.0)  # weakest
        g.add_edge("a", "c", weight=5.0)
        dag, removed = greedy_fas(g)
        assert nx.is_directed_acyclic_graph(dag)


# ─── pairwise_inconsistency_count edge cases ─────────────────────────────────


class TestPairwiseInconsistencyCountEdgeCases:
    def test_empty_graph(self):
        g = nx.DiGraph()
        assert pairwise_inconsistency_count(g, []) == 0

    def test_empty_graph_nonempty_reference(self):
        g = nx.DiGraph()
        assert pairwise_inconsistency_count(g, ["a", "b", "c"]) == 0

    def test_graph_node_absent_from_reference_is_skipped(self):
        ref = ["a", "b"]
        g = nx.DiGraph()
        g.add_edge("a", "x")  # 'x' not in reference
        # Should not raise; edge is silently skipped
        result = pairwise_inconsistency_count(g, ref)
        assert result == 0

    def test_single_node_reference(self):
        g = nx.DiGraph()
        g.add_node("a")
        assert pairwise_inconsistency_count(g, ["a"]) == 0

    def test_no_edges(self):
        g = nx.DiGraph()
        g.add_nodes_from(["a", "b", "c"])
        assert pairwise_inconsistency_count(g, ["a", "b", "c"]) == 0

    def test_mixed_nodes_in_and_out_of_reference(self):
        # Edge between a node in reference and one not — should be skipped
        ref = ["a", "b", "c"]
        g = nx.DiGraph()
        g.add_edge("a", "b")  # consistent
        g.add_edge("b", "z")  # 'z' not in ref → skipped
        g.add_edge("z", "a")  # 'z' not in ref → skipped
        assert pairwise_inconsistency_count(g, ref) == 0


# ─── Regression: committed evidence values ────────────────────────────────────


PAPER_PACKAGE = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "pub_vote_cmp_v2"
    / "paper_package"
    / "tables"
)


@pytest.mark.skipif(
    not PAPER_PACKAGE.exists(),
    reason="Canonical paper package not present (outputs/pub_vote_cmp_v2/paper_package/tables/)",
)
class TestCommittedEvidenceRegression:
    """Smoke-test committed evidence tables to catch accidental overwrites."""

    def _load_csv(self, filename: str) -> list[dict]:
        path = PAPER_PACKAGE / filename
        with path.open() as f:
            return list(csv.DictReader(f))

    def test_graph_consistency_table_has_expected_datasets(self):
        rows = self._load_csv("table_graph_ndcg_and_consistency.csv")
        datasets = {r["dataset"] for r in rows}
        assert "scidocs" in datasets
        assert "hotpotqa" in datasets

    def test_scidocs_ms1_is_high_cyclicity(self):
        rows = self._load_csv("table_graph_ndcg_and_consistency.csv")
        row = next((r for r in rows if r["dataset"] == "scidocs" and r["variant"] == "ms1"), None)
        assert row is not None, "scidocs/ms1 row missing from table"
        pct_cyclic = float(row["pct_cyclic"])
        assert pct_cyclic > 90.0, f"Expected >90% cyclic for scidocs/ms1, got {pct_cyclic}"

    def test_scidocs_ms2_is_near_acyclic(self):
        rows = self._load_csv("table_graph_ndcg_and_consistency.csv")
        row = next((r for r in rows if r["dataset"] == "scidocs" and r["variant"] == "ms2"), None)
        assert row is not None
        pct_cyclic = float(row["pct_cyclic"])
        assert pct_cyclic < 5.0, f"Expected <5% cyclic for scidocs/ms2, got {pct_cyclic}"

    def test_bootstrap_table_has_expected_rows(self):
        rows = self._load_csv("table_bootstrap_delta_ndcg.csv")
        pairs = {(r["dataset"], r["variant"], r["pair"]) for r in rows}
        assert ("scidocs", "ms1", "copeland") in pairs
        assert ("scidocs", "ms2", "copeland") in pairs
        assert ("hotpotqa", "ms1", "copeland") in pairs

    def test_scidocs_ms1_copeland_ci_is_negative(self):
        rows = self._load_csv("table_bootstrap_delta_ndcg.csv")
        row = next(
            (
                r
                for r in rows
                if r["dataset"] == "scidocs"
                and r["variant"] == "ms1"
                and r["pair"] == "copeland"
            ),
            None,
        )
        assert row is not None
        ci_high = float(row["ci95_high"])
        assert ci_high < 0.0, (
            f"Expected CI upper bound < 0 for scidocs/ms1/copeland, got {ci_high}"
        )
        mean_delta = float(row["mean_delta_ndcg"])
        assert mean_delta < 0.0, f"Expected negative mean ΔnDCG, got {mean_delta}"

    def test_scidocs_ms2_copeland_delta_is_zero(self):
        rows = self._load_csv("table_bootstrap_delta_ndcg.csv")
        row = next(
            (
                r
                for r in rows
                if r["dataset"] == "scidocs"
                and r["variant"] == "ms2"
                and r["pair"] == "copeland"
            ),
            None,
        )
        assert row is not None
        mean_delta = float(row["mean_delta_ndcg"])
        assert abs(mean_delta) < 1e-6, f"Expected ΔnDCG ≈ 0 for ms2, got {mean_delta}"


# ─── Regression: key synthetic output values ─────────────────────────────────


NOISE_SWEEP_JSON = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "noise_sweep_n0.20"
    / "synthetic_results.json"
)


@pytest.mark.skipif(
    not NOISE_SWEEP_JSON.exists(),
    reason="outputs/noise_sweep_n0.20/synthetic_results.json not present",
)
class TestSyntheticOutputRegression:
    """Ensure committed synthetic result JSON has not been accidentally changed."""

    def _load(self) -> dict:
        with NOISE_SWEEP_JSON.open() as f:
            return json.load(f)

    def test_n_items_is_20(self):
        data = self._load()
        assert data["config"]["n_items"] == 20

    def test_noise_is_0_2(self):
        data = self._load()
        assert abs(data["config"]["noise"] - 0.2) < 1e-9

    def test_borda_tau_is_positive(self):
        data = self._load()
        tau = data["evaluation"]["kendall_tau"]["borda"]
        assert tau > 0.5, f"Expected borda τ > 0.5 at noise=0.2, got {tau}"

    def test_greedy_fas_topological_tau_lower_than_borda(self):
        data = self._load()
        tau = data["evaluation"]["kendall_tau"]
        assert tau["greedy_fas_topological"] < tau["borda"], (
            "greedy_fas_topological should underperform borda at noise=0.2"
        )
