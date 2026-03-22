"""
run_synthetic.py
================
CLI entry-point for the first end-to-end synthetic ranking experiment.

Usage
-----
::

    python scripts/run_synthetic.py --n-items 20 --noise 0.2 --seed 42
    python scripts/run_synthetic.py --n-items 50 --noise 0.1 --save-timings
    python scripts/run_synthetic.py --n-items 100 --noise 0.15 --save-timings --profile

The script:

1. Generates *N* synthetic items with latent quality scores.
2. Produces noisy pairwise preferences.
3. Builds a weighted directed preference graph.
4. Reports cycle statistics.
5. Ranks items with score-sum and Borda baselines.
6. Applies the greedy FAS heuristic to obtain a DAG and runs multiple
   post-repair extraction variants.
7. Evaluates all rankings against the ground truth with Kendall τ.
8. Saves the results to ``<output_dir>/synthetic_results.json``.
9. Optionally saves per-stage timings to ``<output_dir>/timings/``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx

# Allow running as `python scripts/run_synthetic.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    borda_scores,
    copeland_ranking,
    fas_balance_score_prior_alpha_beta_ranking,
    fas_balance_score_prior_alpha_ranking,
    fas_balance_score_sum_borda_hybrid_ranking,
    hybrid_rrf_fas_regularized_ranking,
    priority_topological_ranking,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.evaluation import kendall_tau, n_violations, pairwise_inconsistency_count
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import generate_preferences
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking, quality_map
from consistency_ranker.utils.timing import Timer, TimingAccumulator


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
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        default=False,
        help=(
            "Allow overwriting existing synthetic outputs in --output-dir. "
            "By default, existing files cause an error to avoid accidental result clobbering."
        ),
    )
    parser.add_argument(
        "--save-timings",
        action="store_true",
        default=False,
        help="Save per-stage timing data to <output_dir>/timings/",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        default=False,
        help="Print detailed timing summary to stdout (implies --save-timings)",
    )
    parser.add_argument(
        "--fas-balance-alpha",
        type=float,
        default=0.5,
        help="Alpha for fas_balance_score_prior_alpha hybrid extraction",
    )
    parser.add_argument(
        "--fas-balance-alpha-beta-alpha",
        type=float,
        default=2.0,
        help="Alpha for fas_balance_score_prior_alpha_beta hybrid extraction",
    )
    parser.add_argument(
        "--fas-balance-alpha-beta-beta",
        type=float,
        default=1.0,
        help="Beta for fas_balance_score_prior_alpha_beta hybrid extraction",
    )
    parser.add_argument(
        "--fas-balance-ss-borda-alpha-s",
        type=float,
        default=1.0,
        help="Score-sum prior weight for fas_balance_score_sum_borda_hybrid",
    )
    parser.add_argument(
        "--fas-balance-ss-borda-alpha-b",
        type=float,
        default=1.0,
        help="Borda prior weight for fas_balance_score_sum_borda_hybrid",
    )
    parser.add_argument(
        "--fas-balance-ss-borda-beta",
        type=float,
        default=0.1,
        help="Repaired-balance weight for fas_balance_score_sum_borda_hybrid",
    )
    return parser.parse_args(argv)


def _validate_config(
    *,
    n_items: int,
    noise: float,
    output_dir: Path,
    save_timings: bool,
    overwrite_existing: bool,
) -> None:
    """Validate experiment parameters and output-path safety."""
    if n_items < 2:
        raise ValueError(f"--n-items must be >= 2. Got {n_items}.")
    if not (0.0 <= noise < 1.0):
        raise ValueError(f"noise must be in [0.0, 1.0). Got {noise}.")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"output_dir must be a directory path. Got file: {output_dir}")

    reserved = [output_dir / "synthetic_results.json"]
    if save_timings:
        reserved.extend(
            [
                output_dir / "timings" / "synthetic_timings.csv",
                output_dir / "timings" / "synthetic_timings.json",
            ]
        )
    collisions = [path for path in reserved if path.exists()]
    if collisions and not overwrite_existing:
        existing = ", ".join(str(path) for path in collisions)
        raise FileExistsError(
            "Refusing to overwrite existing synthetic output files: "
            f"{existing}. Use --overwrite-existing to allow overwrites."
        )


def run_experiment(
    n_items: int,
    noise: float,
    seed: int,
    weight_scheme: str = "margin",
    fas_balance_alpha: float = 0.5,
    fas_balance_alpha_beta_alpha: float = 2.0,
    fas_balance_alpha_beta_beta: float = 1.0,
    fas_balance_ss_borda_alpha_s: float = 1.0,
    fas_balance_ss_borda_alpha_b: float = 1.0,
    fas_balance_ss_borda_beta: float = 0.1,
    output_dir: Path = Path("outputs"),
    save_timings: bool = False,
    profile: bool = False,
    overwrite_existing: bool = False,
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
    fas_balance_alpha:
        Mixing coefficient for fas_balance_score_prior_alpha hybrid extraction.
    fas_balance_alpha_beta_alpha:
        Alpha for fas_balance_score_prior_alpha_beta hybrid extraction.
    fas_balance_alpha_beta_beta:
        Beta for fas_balance_score_prior_alpha_beta hybrid extraction.
    fas_balance_ss_borda_alpha_s:
        Score-sum prior weight for fas_balance_score_sum_borda_hybrid.
    fas_balance_ss_borda_alpha_b:
        Borda prior weight for fas_balance_score_sum_borda_hybrid.
    fas_balance_ss_borda_beta:
        Repaired-balance weight for fas_balance_score_sum_borda_hybrid.
    output_dir:
        Directory where ``synthetic_results.json`` will be written.
    save_timings:
        If ``True``, write per-stage timing data to
        ``<output_dir>/timings/``.
    profile:
        If ``True``, print a detailed timing summary to stdout (also
        activates ``save_timings``).
    overwrite_existing:
        If ``False`` (default), raises if output files already exist.

    Returns
    -------
    dict
        All experiment results, suitable for JSON serialisation.
    """
    if profile:
        save_timings = True
    output_dir = Path(output_dir)
    _validate_config(
        n_items=n_items,
        noise=noise,
        output_dir=output_dir,
        save_timings=save_timings,
        overwrite_existing=overwrite_existing,
    )
    if fas_balance_alpha < 0:
        raise ValueError(f"fas_balance_alpha must be non-negative. Got {fas_balance_alpha}.")
    if fas_balance_alpha_beta_alpha < 0:
        raise ValueError(
            "fas_balance_alpha_beta_alpha must be non-negative. "
            f"Got {fas_balance_alpha_beta_alpha}."
        )
    if fas_balance_alpha_beta_beta < 0:
        raise ValueError(
            "fas_balance_alpha_beta_beta must be non-negative. "
            f"Got {fas_balance_alpha_beta_beta}."
        )
    if fas_balance_ss_borda_alpha_s < 0:
        raise ValueError(
            "fas_balance_ss_borda_alpha_s must be non-negative. "
            f"Got {fas_balance_ss_borda_alpha_s}."
        )
    if fas_balance_ss_borda_alpha_b < 0:
        raise ValueError(
            "fas_balance_ss_borda_alpha_b must be non-negative. "
            f"Got {fas_balance_ss_borda_alpha_b}."
        )
    if fas_balance_ss_borda_beta < 0:
        raise ValueError(
            "fas_balance_ss_borda_beta must be non-negative. "
            f"Got {fas_balance_ss_borda_beta}."
        )

    acc = TimingAccumulator()
    acc.set_metadata(
        experiment="synthetic",
        n_items=n_items,
        noise=noise,
        seed=seed,
        weight_scheme=weight_scheme,
        fas_balance_alpha=fas_balance_alpha,
        fas_balance_alpha_beta_alpha=fas_balance_alpha_beta_alpha,
        fas_balance_alpha_beta_beta=fas_balance_alpha_beta_beta,
        fas_balance_ss_borda_alpha_s=fas_balance_ss_borda_alpha_s,
        fas_balance_ss_borda_alpha_b=fas_balance_ss_borda_alpha_b,
        fas_balance_ss_borda_beta=fas_balance_ss_borda_beta,
    )
    print(f"\n{'='*60}")
    print("  Consistency-Aware Ranking — Synthetic Experiment")
    print(f"{'='*60}")
    print(f"  n_items      : {n_items}")
    print(f"  noise        : {noise}")
    print(f"  seed         : {seed}")
    print(f"  weight_scheme: {weight_scheme}")
    print(f"  fas_bal_alpha: {fas_balance_alpha}")
    print(f"  fas_ab_alpha : {fas_balance_alpha_beta_alpha}")
    print(f"  fas_ab_beta  : {fas_balance_alpha_beta_beta}")
    print(f"  fas_s+b_a_s  : {fas_balance_ss_borda_alpha_s}")
    print(f"  fas_s+b_a_b  : {fas_balance_ss_borda_alpha_b}")
    print(f"  fas_s+b_beta : {fas_balance_ss_borda_beta}")
    print(f"  output_dir   : {output_dir}")
    print(f"  save_timings : {save_timings}\n")

    with Timer("total_experiment", accumulator=acc):

        # ------------------------------------------------------------------
        # 1. Generate items and ground-truth ranking
        # ------------------------------------------------------------------
        with Timer("data_generation", accumulator=acc):
            items = generate_items(n=n_items, seed=seed)
            qmap = quality_map(items)
            gt_ranking = ground_truth_ranking(items)
        print(f"[1] Ground-truth ranking (top 5): {gt_ranking[:5]}")

        # ------------------------------------------------------------------
        # 2. Generate noisy pairwise preferences
        # ------------------------------------------------------------------
        with Timer("pairwise_preference_generation", accumulator=acc):
            prefs = generate_preferences(qmap, noise=noise, weight_scheme=weight_scheme, seed=seed)
        print(f"[2] Generated {len(prefs)} pairwise preferences")

        # ------------------------------------------------------------------
        # 3. Build weighted directed preference graph
        # ------------------------------------------------------------------
        with Timer("graph_construction", accumulator=acc):
            graph = build_graph(prefs)
            g_summary = graph_summary(graph)
        print(f"[3] Graph summary: {g_summary}")

        # ------------------------------------------------------------------
        # 4. Cycle detection (fast check — full enumeration skipped for large graphs)
        # ------------------------------------------------------------------
        with Timer("cycle_detection", accumulator=acc):
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
        with Timer("ranking_score_sum", accumulator=acc):
            ss_ranking = score_sum_ranking(graph)
        with Timer("ranking_borda", accumulator=acc):
            borda = borda_ranking(graph)
        print(f"[5] Score-sum ranking (top 5) : {ss_ranking[:5]}")
        print(f"    Borda ranking (top 5)     : {borda[:5]}")

        # ------------------------------------------------------------------
        # 6. Greedy FAS repair + post-repair extraction variants
        # ------------------------------------------------------------------
        with Timer("greedy_fas_solver", accumulator=acc):
            dag, removed_edges = greedy_fas(graph)
            fas_weight = greedy_fas_total_weight(removed_edges)
        with Timer("ranking_topological", accumulator=acc):
            topo_ranking = topological_ranking(dag)
        score_sum_priority_scores = score_sum_scores(graph)
        borda_prior_scores = borda_scores(graph)
        with Timer("ranking_priority_topological_score_sum", accumulator=acc):
            priority_topo_ss = priority_topological_ranking(dag, score_sum_priority_scores)
        with Timer("ranking_fas_weighted_balance", accumulator=acc):
            fas_weighted_balance = weighted_out_minus_in_ranking(dag)
        with Timer("ranking_fas_copeland", accumulator=acc):
            fas_copeland = copeland_ranking(dag)
        with Timer("ranking_hybrid_rrf_fas_regularized", accumulator=acc):
            hybrid_rrf_fas_regularized = hybrid_rrf_fas_regularized_ranking(
                dag,
                score_sum_priority_scores,
                fas_regularization=0.2,
            )
        with Timer("ranking_fas_balance_score_prior_alpha", accumulator=acc):
            fas_balance_score_prior_alpha = fas_balance_score_prior_alpha_ranking(
                dag,
                score_sum_priority_scores,
                alpha=fas_balance_alpha,
            )
        with Timer("ranking_fas_balance_score_prior_alpha_beta", accumulator=acc):
            fas_balance_score_prior_alpha_beta = fas_balance_score_prior_alpha_beta_ranking(
                dag,
                score_sum_priority_scores,
                alpha=fas_balance_alpha_beta_alpha,
                beta=fas_balance_alpha_beta_beta,
            )
        with Timer("ranking_fas_balance_score_sum_borda_hybrid", accumulator=acc):
            fas_balance_score_sum_borda_hybrid = fas_balance_score_sum_borda_hybrid_ranking(
                dag,
                score_sum_priority_scores,
                borda_prior_scores,
                alpha_s=fas_balance_ss_borda_alpha_s,
                alpha_b=fas_balance_ss_borda_alpha_b,
                beta=fas_balance_ss_borda_beta,
            )
        print(f"[6] Greedy FAS removed {len(removed_edges)} edges (total weight={fas_weight:.4f})")
        print(f"    Topological ranking (top 5): {topo_ranking[:5]}")
        print(f"    Priority topo + score-sum   : {priority_topo_ss[:5]}")
        print(f"    FAS weighted balance (top 5): {fas_weighted_balance[:5]}")
        print(f"    FAS Copeland (top 5)        : {fas_copeland[:5]}")
        print(f"    Hybrid RRF FAS reg (top 5)  : {hybrid_rrf_fas_regularized[:5]}")
        print(f"    FAS bal+prior alpha (top 5) : {fas_balance_score_prior_alpha[:5]}")
        print(f"    FAS bal+prior a/b (top 5)   : {fas_balance_score_prior_alpha_beta[:5]}")
        print(f"    FAS bal+ss+borda (top 5)    : {fas_balance_score_sum_borda_hybrid[:5]}")
        # Verify the dag produced is truly acyclic
        assert not has_cycle(dag), "BUG: greedy FAS produced a graph that still has cycles!"

        # ------------------------------------------------------------------
        # 7. Evaluation
        # ------------------------------------------------------------------
        with Timer("evaluation", accumulator=acc):
            tau_ss = kendall_tau(ss_ranking, gt_ranking)
            tau_borda = kendall_tau(borda, gt_ranking)
            tau_topo = kendall_tau(topo_ranking, gt_ranking)
            tau_priority_topo_ss = kendall_tau(priority_topo_ss, gt_ranking)
            tau_fas_weighted_balance = kendall_tau(fas_weighted_balance, gt_ranking)
            tau_fas_copeland = kendall_tau(fas_copeland, gt_ranking)
            tau_hybrid_rrf_fas_regularized = kendall_tau(hybrid_rrf_fas_regularized, gt_ranking)
            tau_fas_balance_score_prior_alpha = kendall_tau(
                fas_balance_score_prior_alpha,
                gt_ranking,
            )
            tau_fas_balance_score_prior_alpha_beta = kendall_tau(
                fas_balance_score_prior_alpha_beta,
                gt_ranking,
            )
            tau_fas_balance_score_sum_borda_hybrid = kendall_tau(
                fas_balance_score_sum_borda_hybrid,
                gt_ranking,
            )

            viol_ss = n_violations(ss_ranking, gt_ranking)
            viol_borda = n_violations(borda, gt_ranking)
            viol_topo = n_violations(topo_ranking, gt_ranking)
            viol_priority_topo_ss = n_violations(priority_topo_ss, gt_ranking)
            viol_fas_weighted_balance = n_violations(fas_weighted_balance, gt_ranking)
            viol_fas_copeland = n_violations(fas_copeland, gt_ranking)
            viol_hybrid_rrf_fas_regularized = n_violations(
                hybrid_rrf_fas_regularized,
                gt_ranking,
            )
            viol_fas_balance_score_prior_alpha = n_violations(
                fas_balance_score_prior_alpha,
                gt_ranking,
            )
            viol_fas_balance_score_prior_alpha_beta = n_violations(
                fas_balance_score_prior_alpha_beta,
                gt_ranking,
            )
            viol_fas_balance_score_sum_borda_hybrid = n_violations(
                fas_balance_score_sum_borda_hybrid,
                gt_ranking,
            )

            incons_original = pairwise_inconsistency_count(graph, gt_ranking)
            incons_dag = pairwise_inconsistency_count(dag, gt_ranking)

    print("\n[7] Evaluation results:")
    print(f"    {'Method':<20} {'Kendall τ':>10} {'Violations':>12}")
    print(f"    {'-'*44}")
    print(f"    {'Score-sum':<20} {tau_ss:>10.4f} {viol_ss:>12}")
    print(f"    {'Borda':<20} {tau_borda:>10.4f} {viol_borda:>12}")
    print(f"    {'Greedy-FAS + Topo':<20} {tau_topo:>10.4f} {viol_topo:>12}")
    print(
        f"    {'Priority Topo + SS':<20} {tau_priority_topo_ss:>10.4f} "
        f"{viol_priority_topo_ss:>12}"
    )
    print(
        f"    {'FAS Weighted Balance':<20} {tau_fas_weighted_balance:>10.4f} "
        f"{viol_fas_weighted_balance:>12}"
    )
    print(f"    {'FAS Copeland':<20} {tau_fas_copeland:>10.4f} {viol_fas_copeland:>12}")
    print(
        f"    {'Hybrid RRF FAS Reg':<20} {tau_hybrid_rrf_fas_regularized:>10.4f} "
        f"{viol_hybrid_rrf_fas_regularized:>12}"
    )
    print(
        f"    {'FAS bal+prior alpha':<20} {tau_fas_balance_score_prior_alpha:>10.4f} "
        f"{viol_fas_balance_score_prior_alpha:>12}"
    )
    print(
        f"    {'FAS bal+prior a/b':<20} {tau_fas_balance_score_prior_alpha_beta:>10.4f} "
        f"{viol_fas_balance_score_prior_alpha_beta:>12}"
    )
    print(
        f"    {'FAS bal+ss+borda':<20} {tau_fas_balance_score_sum_borda_hybrid:>10.4f} "
        f"{viol_fas_balance_score_sum_borda_hybrid:>12}"
    )
    print(f"\n    Pairwise inconsistencies (original graph) : {incons_original}")
    print(f"    Pairwise inconsistencies (after FAS DAG)  : {incons_dag}")

    if profile:
        acc.print_summary()

    # ------------------------------------------------------------------
    # 8. Save results
    # ------------------------------------------------------------------
    timing_summary = {row["stage"]: row for row in acc.summary_rows()}
    stage_by_method = {
        "score_sum": "ranking_score_sum",
        "borda": "ranking_borda",
        "greedy_fas_topological": "ranking_topological",
        "priority_topological_score_sum": "ranking_priority_topological_score_sum",
        "fas_weighted_balance": "ranking_fas_weighted_balance",
        "fas_copeland": "ranking_fas_copeland",
        "hybrid_rrf_fas_regularized": "ranking_hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha": "ranking_fas_balance_score_prior_alpha",
        "fas_balance_score_prior_alpha_beta": "ranking_fas_balance_score_prior_alpha_beta",
        "fas_balance_score_sum_borda_hybrid": "ranking_fas_balance_score_sum_borda_hybrid",
    }
    fas_methods = {
        "greedy_fas_topological",
        "priority_topological_score_sum",
        "fas_weighted_balance",
        "fas_copeland",
        "hybrid_rrf_fas_regularized",
        "fas_balance_score_prior_alpha",
        "fas_balance_score_prior_alpha_beta",
        "fas_balance_score_sum_borda_hybrid",
    }
    method_metrics: dict[str, dict[str, float | int]] = {}
    for method, stage in stage_by_method.items():
        ranking_time = timing_summary.get(stage, {}).get("total_s", 0.0)
        repair_time = timing_summary.get("greedy_fas_solver", {}).get("total_s", 0.0)
        if method not in fas_methods:
            repair_time = 0.0
        method_metrics[method] = {
            "runtime_total_s": float(ranking_time + repair_time),
            "runtime_repair_s": float(repair_time),
            "removed_edges": int(len(removed_edges) if method in fas_methods else 0),
            "removed_weight": float(fas_weight if method in fas_methods else 0.0),
            "inconsistency_before": int(incons_original),
            "inconsistency_after": int(incons_dag if method in fas_methods else incons_original),
        }

    results = {
        "config": {
            "n_items": n_items,
            "noise": noise,
            "seed": seed,
            "weight_scheme": weight_scheme,
            "fas_balance_alpha": fas_balance_alpha,
            "fas_balance_alpha_beta_alpha": fas_balance_alpha_beta_alpha,
            "fas_balance_alpha_beta_beta": fas_balance_alpha_beta_beta,
            "fas_balance_ss_borda_alpha_s": fas_balance_ss_borda_alpha_s,
            "fas_balance_ss_borda_alpha_b": fas_balance_ss_borda_alpha_b,
            "fas_balance_ss_borda_beta": fas_balance_ss_borda_beta,
        },
        "ground_truth_ranking": gt_ranking,
        "graph_summary": g_summary,
        "cycle_summary": c_summary,
        "rankings": {
            "score_sum": ss_ranking,
            "borda": borda,
            "greedy_fas_topological": topo_ranking,
            "priority_topological_score_sum": priority_topo_ss,
            "fas_weighted_balance": fas_weighted_balance,
            "fas_copeland": fas_copeland,
            "hybrid_rrf_fas_regularized": hybrid_rrf_fas_regularized,
            "fas_balance_score_prior_alpha": fas_balance_score_prior_alpha,
            "fas_balance_score_prior_alpha_beta": fas_balance_score_prior_alpha_beta,
            "fas_balance_score_sum_borda_hybrid": fas_balance_score_sum_borda_hybrid,
        },
        "evaluation": {
            "kendall_tau": {
                "score_sum": tau_ss,
                "borda": tau_borda,
                "greedy_fas_topological": tau_topo,
                "priority_topological_score_sum": tau_priority_topo_ss,
                "fas_weighted_balance": tau_fas_weighted_balance,
                "fas_copeland": tau_fas_copeland,
                "hybrid_rrf_fas_regularized": tau_hybrid_rrf_fas_regularized,
                "fas_balance_score_prior_alpha": tau_fas_balance_score_prior_alpha,
                "fas_balance_score_prior_alpha_beta": tau_fas_balance_score_prior_alpha_beta,
                "fas_balance_score_sum_borda_hybrid": tau_fas_balance_score_sum_borda_hybrid,
            },
            "n_violations": {
                "score_sum": viol_ss,
                "borda": viol_borda,
                "greedy_fas_topological": viol_topo,
                "priority_topological_score_sum": viol_priority_topo_ss,
                "fas_weighted_balance": viol_fas_weighted_balance,
                "fas_copeland": viol_fas_copeland,
                "hybrid_rrf_fas_regularized": viol_hybrid_rrf_fas_regularized,
                "fas_balance_score_prior_alpha": viol_fas_balance_score_prior_alpha,
                "fas_balance_score_prior_alpha_beta": viol_fas_balance_score_prior_alpha_beta,
                "fas_balance_score_sum_borda_hybrid": viol_fas_balance_score_sum_borda_hybrid,
            },
            "pairwise_inconsistency_count": {
                "original_graph": incons_original,
                "after_fas_dag": incons_dag,
            },
        },
        "method_metrics": method_metrics,
        "fas": {
            "n_removed_edges": len(removed_edges),
            "total_removed_weight": fas_weight,
            "removed_edges": [[u, v, w] for u, v, w in removed_edges],
        },
        "timings": {
            stage: {"total_s": row["total_s"], "mean_s": row["mean_s"]}
            for stage, row in timing_summary.items()
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "synthetic_results.json"
    with out_path.open("w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n[8] Results saved to {out_path}")

    if save_timings:
        timings_dir = output_dir / "timings"
        csv_path = acc.save_csv(timings_dir / "synthetic_timings.csv")
        json_path = acc.save_json(timings_dir / "synthetic_timings.json")
        print(f"    Timings CSV  → {csv_path}")
        print(f"    Timings JSON → {json_path}")

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
        save_timings=args.save_timings,
        profile=args.profile,
        overwrite_existing=args.overwrite_existing,
        fas_balance_alpha=args.fas_balance_alpha,
        fas_balance_alpha_beta_alpha=args.fas_balance_alpha_beta_alpha,
        fas_balance_alpha_beta_beta=args.fas_balance_alpha_beta_beta,
        fas_balance_ss_borda_alpha_s=args.fas_balance_ss_borda_alpha_s,
        fas_balance_ss_borda_alpha_b=args.fas_balance_ss_borda_alpha_b,
        fas_balance_ss_borda_beta=args.fas_balance_ss_borda_beta,
    )


if __name__ == "__main__":
    main()
