"""
run_synthetic.py
================
CLI entry-point for the first end-to-end synthetic ranking experiment.

Usage
-----
::

    python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42

The script:

1. Generates *N* synthetic items with latent quality scores.
2. Produces noisy pairwise preferences.
3. Builds a weighted directed preference graph.
4. Reports cycle statistics.
5. Ranks items with score-sum and Borda baselines.
6. Applies the greedy FAS heuristic to obtain a DAG, then ranks by topological sort.
7. Evaluates all rankings against the ground truth with Kendall τ.
8. Saves the results to ``<output_dir>/synthetic_results.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx

# Allow running as `python scripts/run_synthetic.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.baseline_ranking import borda_ranking, score_sum_ranking, topological_ranking
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.evaluation import kendall_tau, n_violations, pairwise_inconsistency_count
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import generate_preferences
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking, quality_map


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the end-to-end synthetic consistency-ranking experiment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n-items", type=int, default=20, help="Number of items to rank")
    parser.add_argument(
        "--noise", type=float, default=0.2, help="Noise level in pairwise preferences [0, 1)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--weight-scheme",
        choices=["uniform", "margin"],
        default="margin",
        help="Edge weight scheme",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory to save experiment results",
    )
    return parser.parse_args(argv)


def run_experiment(
    n_items: int,
    noise: float,
    seed: int,
    weight_scheme: str = "margin",
    output_dir: Path = Path("outputs"),
) -> dict:
    """Run the full synthetic experiment and return a results dict.

    Parameters
    ----------
    n_items:
        Number of items.
    noise:
        Noise level for pairwise preferences.
    seed:
        Random seed.
    weight_scheme:
        ``"uniform"`` or ``"margin"``.
    output_dir:
        Directory where ``synthetic_results.json`` will be written.

    Returns
    -------
    dict
        All experiment results, suitable for JSON serialisation.
    """
    print(f"\n{'='*60}")
    print("  Consistency-Aware Ranking — Synthetic Experiment")
    print(f"{'='*60}")
    print(f"  n_items      : {n_items}")
    print(f"  noise        : {noise}")
    print(f"  seed         : {seed}")
    print(f"  weight_scheme: {weight_scheme}")
    print(f"  output_dir   : {output_dir}\n")

    # ------------------------------------------------------------------
    # 1. Generate items and ground-truth ranking
    # ------------------------------------------------------------------
    items = generate_items(n=n_items, seed=seed)
    qmap = quality_map(items)
    gt_ranking = ground_truth_ranking(items)
    print(f"[1] Ground-truth ranking (top 5): {gt_ranking[:5]}")

    # ------------------------------------------------------------------
    # 2. Generate noisy pairwise preferences
    # ------------------------------------------------------------------
    prefs = generate_preferences(qmap, noise=noise, weight_scheme=weight_scheme, seed=seed)
    print(f"[2] Generated {len(prefs)} pairwise preferences")

    # ------------------------------------------------------------------
    # 3. Build weighted directed preference graph
    # ------------------------------------------------------------------
    graph = build_graph(prefs)
    g_summary = graph_summary(graph)
    print(f"[3] Graph summary: {g_summary}")

    # ------------------------------------------------------------------
    # 4. Cycle detection (fast check — full enumeration skipped for large graphs)
    # ------------------------------------------------------------------
    g_has_cycle = has_cycle(graph)
    n_sccs = g_summary["n_sccs"]
    # Estimate cycles via SCC sizes instead of full enumeration (which is
    # exponential on dense graphs).  A non-trivial SCC of size k can contain
    # many cycles; we report the number of SCCs with size > 1 as a proxy.
    large_sccs = sum(
        1
        for scc in nx.strongly_connected_components(graph)
        if len(scc) > 1
    )
    c_summary = {
        "has_cycle": g_has_cycle,
        "n_sccs": n_sccs,
        "n_non_trivial_sccs": large_sccs,
        "note": "Full cycle enumeration skipped (exponential cost on dense graphs)",
    }
    print(f"[4] Cycle info: {c_summary}")

    # ------------------------------------------------------------------
    # 5. Baseline rankings
    # ------------------------------------------------------------------
    ss_ranking = score_sum_ranking(graph)
    borda = borda_ranking(graph)
    print(f"[5] Score-sum ranking (top 5) : {ss_ranking[:5]}")
    print(f"    Borda ranking (top 5)     : {borda[:5]}")

    # ------------------------------------------------------------------
    # 6. Greedy FAS → topological ranking
    # ------------------------------------------------------------------
    dag, removed_edges = greedy_fas(graph)
    fas_weight = greedy_fas_total_weight(removed_edges)
    topo_ranking = topological_ranking(dag)
    print(f"[6] Greedy FAS removed {len(removed_edges)} edges (total weight={fas_weight:.4f})")
    print(f"    Topological ranking (top 5): {topo_ranking[:5]}")

    # Verify the dag produced is truly acyclic
    assert not has_cycle(dag), "BUG: greedy FAS produced a graph that still has cycles!"

    # ------------------------------------------------------------------
    # 7. Evaluation
    # ------------------------------------------------------------------
    tau_ss = kendall_tau(ss_ranking, gt_ranking)
    tau_borda = kendall_tau(borda, gt_ranking)
    tau_topo = kendall_tau(topo_ranking, gt_ranking)

    viol_ss = n_violations(ss_ranking, gt_ranking)
    viol_borda = n_violations(borda, gt_ranking)
    viol_topo = n_violations(topo_ranking, gt_ranking)

    incons_original = pairwise_inconsistency_count(graph, gt_ranking)
    incons_dag = pairwise_inconsistency_count(dag, gt_ranking)

    print("\n[7] Evaluation results:")
    print(f"    {'Method':<20} {'Kendall τ':>10} {'Violations':>12}")
    print(f"    {'-'*44}")
    print(f"    {'Score-sum':<20} {tau_ss:>10.4f} {viol_ss:>12}")
    print(f"    {'Borda':<20} {tau_borda:>10.4f} {viol_borda:>12}")
    print(f"    {'Greedy-FAS + Topo':<20} {tau_topo:>10.4f} {viol_topo:>12}")
    print(f"\n    Pairwise inconsistencies (original graph) : {incons_original}")
    print(f"    Pairwise inconsistencies (after FAS DAG)  : {incons_dag}")

    # ------------------------------------------------------------------
    # 8. Save results
    # ------------------------------------------------------------------
    results = {
        "config": {
            "n_items": n_items,
            "noise": noise,
            "seed": seed,
            "weight_scheme": weight_scheme,
        },
        "ground_truth_ranking": gt_ranking,
        "graph_summary": g_summary,
        "cycle_summary": c_summary,
        "rankings": {
            "score_sum": ss_ranking,
            "borda": borda,
            "greedy_fas_topological": topo_ranking,
        },
        "evaluation": {
            "kendall_tau": {
                "score_sum": tau_ss,
                "borda": tau_borda,
                "greedy_fas_topological": tau_topo,
            },
            "n_violations": {
                "score_sum": viol_ss,
                "borda": viol_borda,
                "greedy_fas_topological": viol_topo,
            },
            "pairwise_inconsistency_count": {
                "original_graph": incons_original,
                "after_fas_dag": incons_dag,
            },
        },
        "fas": {
            "n_removed_edges": len(removed_edges),
            "total_removed_weight": fas_weight,
            "removed_edges": [[u, v, w] for u, v, w in removed_edges],
        },
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "synthetic_results.json"
    with out_path.open("w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n[8] Results saved to {out_path}")
    print(f"{'='*60}\n")

    return results


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    run_experiment(
        n_items=args.n_items,
        noise=args.noise,
        seed=args.seed,
        weight_scheme=args.weight_scheme,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
