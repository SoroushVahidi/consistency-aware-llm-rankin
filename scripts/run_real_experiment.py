"""
run_real_experiment.py
======================
Real-data experiment pipeline for the consistency-aware ranking project.

Loads a processed dataset (SciDocs, FiQA, …), runs the full pipeline for
each sampled query, and writes per-query metrics, aggregate summaries, and
timing files.

Quick start
-----------
::

    # SciDocs (first 50 queries, top-20 candidates per query)
    python scripts/run_real_experiment.py --dataset scidocs \\
        --max-queries 50 --top-k 20 --save-timings --profile

    # FiQA
    python scripts/run_real_experiment.py --dataset fiqa \\
        --max-queries 50 --top-k 20 --save-timings --profile

Outputs (under ``--output-dir``, default ``outputs/``):
- ``<dataset>_per_query.csv``        per-query × per-method results
- ``<dataset>_summary.csv``          aggregate statistics per method
- ``timings/<dataset>_timings.csv``  timing data (CSV)
- ``timings/<dataset>_timings.json`` timing data (JSON)
- ``plots/``                         timing plots (if matplotlib available)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

# Allow running as `python scripts/run_real_experiment.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    pagerank_ranking,
    score_sum_ranking,
    topological_ranking,
)
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    preferences_from_qrels,
)
from consistency_ranker.graph_construction import build_graph, graph_summary
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import Preference
from consistency_ranker.utils.timing import Timer, TimingAccumulator

logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_JUDGED_DOCS = 2
"""Minimum number of distinct relevance grades needed to produce any preference."""

METHODS = ("score_sum", "borda", "pagerank", "greedy_fas_topological")
"""Ordered tuple of method names used as keys throughout the script."""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reference_ranking(qrels_for_query: list) -> list[str]:
    """Derive a reference ranking from relevance grades.

    Documents are sorted by **descending** relevance.  When grades tie the
    relative order is preserved (stable sort).

    Parameters
    ----------
    qrels_for_query:
        ``QrelEntry`` objects for a single query.

    Returns
    -------
    list[str]
        Document ids ordered from most to least relevant.
    """
    sorted_entries = sorted(
        qrels_for_query, key=lambda e: e.relevance, reverse=True
    )
    # Deduplicate while preserving order (should not be needed in practice)
    seen: set[str] = set()
    ranking: list[str] = []
    for e in sorted_entries:
        if e.doc_id not in seen:
            seen.add(e.doc_id)
            ranking.append(e.doc_id)
    return ranking


def _backward_edge_weight(graph: nx.DiGraph, ranking: list[str]) -> float:
    """Sum of weights of edges that disagree with *ranking*.

    An edge u → v is *backward* if the ranking places v before u (v is
    ranked higher / preferred in the ranking).

    Parameters
    ----------
    graph:
        Directed preference graph.
    ranking:
        A proposed ordering of nodes (index 0 = best).

    Returns
    -------
    float

    Notes
    -----
    O(e) where e = number of edges in the graph.
    """
    pos = {node: i for i, node in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            total += data.get("weight", 1.0)
    return total


def _pairwise_inconsistency(graph: nx.DiGraph, ranking: list[str]) -> int:
    """Count graph edges whose direction disagrees with *ranking*.

    An edge u → v is inconsistent if the ranking places v before u.

    Parameters
    ----------
    graph:
        Directed preference graph.
    ranking:
        A proposed ordering of nodes (index 0 = best).

    Returns
    -------
    int

    Notes
    -----
    O(e) in the number of edges.
    """
    pos = {node: i for i, node in enumerate(ranking)}
    count = 0
    for u, v in graph.edges():
        u_pos = pos.get(u)
        v_pos = pos.get(v)
        if u_pos is not None and v_pos is not None and v_pos < u_pos:
            count += 1
    return count


def _kendall_tau(ranking: list[str], reference: list[str]) -> float | None:
    """Kendall τ between *ranking* and *reference*.

    Returns ``None`` if the node sets differ (e.g. ranking covers nodes
    not in the reference list).

    Parameters
    ----------
    ranking:
        Predicted ordering.
    reference:
        Ground-truth ordering.

    Returns
    -------
    float | None
        Kendall τ in [-1, +1], or ``None`` if node sets don't match.

    Notes
    -----
    O(n²) in the number of items due to the all-pairs comparison loop.
    This is a secondary bottleneck for large candidate sets (n > 200).

    # TODO: Replace with scipy.stats.kendalltau for O(n log n) performance
    #       using the merge-sort-based C implementation.
    """
    ranking_set = set(ranking)
    reference_set = set(reference)
    common = ranking_set & reference_set
    if len(common) < 2:
        return None

    # Restrict both lists to the common items
    ranking_common = [x for x in ranking if x in common]
    reference_common = [x for x in reference if x in common]

    pos_pred = {item: i for i, item in enumerate(ranking_common)}
    pos_ref = {item: i for i, item in enumerate(reference_common)}

    items = list(common)
    concordant = 0
    discordant = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            pred_order = pos_pred[a] < pos_pred[b]
            ref_order = pos_ref[a] < pos_ref[b]
            if pred_order == ref_order:
                concordant += 1
            else:
                discordant += 1

    total = concordant + discordant
    return (concordant - discordant) / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Plotting helper (optional dependency)
# ---------------------------------------------------------------------------


def _maybe_plot(
    per_query_rows: list[dict],
    dataset: str,
    output_dir: Path,
) -> None:
    """Generate simple timing plots if matplotlib is available.

    Parameters
    ----------
    per_query_rows:
        Rows produced by the per-query loop (one row per query × method).
    dataset:
        Dataset name (used in titles and filenames).
    output_dir:
        Root output directory; plots go to ``output_dir / "plots"``.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        log.info("matplotlib not available — skipping plots.")
        return

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Group by method
    methods_seen = sorted({r["method"] for r in per_query_rows})

    # 1. Average runtime by method
    avg_rt = {}
    for m in methods_seen:
        rts = [r["runtime_total_s"] for r in per_query_rows if r["method"] == m and r["runtime_total_s"] is not None]
        avg_rt[m] = sum(rts) / len(rts) if rts else 0.0

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(list(avg_rt.keys()), list(avg_rt.values()), color="#4C72B0")
    ax.set_ylabel("Avg per-query runtime (s)")
    ax.set_title(f"{dataset}: average runtime by method")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(plots_dir / f"{dataset}_runtime_by_method.png", dpi=150)
    plt.close(fig)

    # 2. Runtime vs number of nodes
    for m in methods_seen:
        subset = [r for r in per_query_rows if r["method"] == m and r["runtime_total_s"] is not None]
        if not subset:
            continue
        xs = [r["n_nodes"] for r in subset]
        ys = [r["runtime_total_s"] for r in subset]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.scatter(xs, ys, alpha=0.5, color="#DD8452")
        ax.set_xlabel("Number of nodes (candidates)")
        ax.set_ylabel("Per-query runtime (s)")
        ax.set_title(f"{dataset} [{m}]: runtime vs nodes")
        fig.tight_layout()
        fig.savefig(plots_dir / f"{dataset}_{m}_runtime_vs_nodes.png", dpi=150)
        plt.close(fig)

    # 3. Runtime vs number of edges
    for m in methods_seen:
        subset = [r for r in per_query_rows if r["method"] == m and r["runtime_total_s"] is not None]
        if not subset:
            continue
        xs = [r["n_edges"] for r in subset]
        ys = [r["runtime_total_s"] for r in subset]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.scatter(xs, ys, alpha=0.5, color="#55A868")
        ax.set_xlabel("Number of edges (preferences)")
        ax.set_ylabel("Per-query runtime (s)")
        ax.set_title(f"{dataset} [{m}]: runtime vs edges")
        fig.tight_layout()
        fig.savefig(plots_dir / f"{dataset}_{m}_runtime_vs_edges.png", dpi=150)
        plt.close(fig)

    log.info("Plots saved to %s", plots_dir)


# ---------------------------------------------------------------------------
# Per-query experiment
# ---------------------------------------------------------------------------


def run_query(
    *,
    query,
    qrels_for_query: list,
    dataset: str,
    top_k: int,
    weight_scheme: str,
    seed: int,
    global_acc: TimingAccumulator,
) -> tuple[list[dict], dict | None]:
    """Run the full pipeline for a single query.

    Parameters
    ----------
    query:
        The :class:`~consistency_ranker.data.schema.Query` object.
    qrels_for_query:
        ``QrelEntry`` objects for *query*.
    dataset:
        Short dataset name (for logging and output rows).
    top_k:
        Maximum number of candidate documents.
    weight_scheme:
        Preference weight scheme (``"grade_diff"`` or ``"binary"``).
    seed:
        Random seed for preference generation tie-breaking.
    global_acc:
        Shared ``TimingAccumulator`` that accumulates stage totals across
        all queries.  Stage names are prefixed with ``"query_"`` so that
        aggregate stage totals can be computed.

    Returns
    -------
    rows : list[dict]
        One row per method (to append to the per-query CSV).
    skip_info : dict | None
        If the query should be skipped, a dict with ``query_id`` and
        ``reason``; otherwise ``None``.
    """
    qid = query.query_id

    # ------------------------------------------------------------------
    # Safeguard: skip if too few distinct relevance-judged documents
    # ------------------------------------------------------------------
    unique_docs = {e.doc_id for e in qrels_for_query}
    n_distinct_grades = len({e.relevance for e in qrels_for_query})
    if len(unique_docs) < MIN_JUDGED_DOCS or n_distinct_grades < 2:
        return [], {
            "query_id": qid,
            "reason": f"only {len(unique_docs)} judged docs with {n_distinct_grades} distinct grade(s)",
        }

    query_acc = TimingAccumulator()
    query_acc.set_metadata(query_id=qid, dataset=dataset)

    # ------------------------------------------------------------------
    # 1. Generate pairwise preferences
    # ------------------------------------------------------------------
    with Timer("pairwise_preference_generation", accumulator=query_acc):
        schema_prefs = preferences_from_qrels(
            qrels_for_query,
            top_k=top_k,
            seed=seed,
            weight_scheme=weight_scheme,
        )

    if not schema_prefs:
        return [], {
            "query_id": qid,
            "reason": "no pairwise preferences generated (all candidates have same grade)",
        }

    # Convert PairwisePreference → pairwise_prefs.Preference for build_graph
    prefs = [
        Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
        for p in schema_prefs
    ]

    # ------------------------------------------------------------------
    # 2. Build graph
    # ------------------------------------------------------------------
    with Timer("graph_construction", accumulator=query_acc):
        graph = build_graph(prefs)

    summary = graph_summary(graph)
    n_nodes = summary["n_nodes"]
    n_edges = summary["n_edges"]
    density = nx.density(graph)
    sccs = list(nx.strongly_connected_components(graph))
    n_sccs = summary["n_sccs"]
    largest_scc = max(len(s) for s in sccs) if sccs else 0

    # Guard against extremely dense graphs (safety valve)
    # O(n²) edges can make FAS very slow; warn and skip FAS if needed.
    _fas_skipped = False
    if n_edges > 5_000:
        log.warning(
            "Query %s: graph has %d edges (> 5000). FAS solver will be slow.",
            qid,
            n_edges,
        )

    # ------------------------------------------------------------------
    # 3. Cycle detection (SCC-based proxy — avoids exponential enumeration)
    # ------------------------------------------------------------------
    with Timer("cycle_detection", accumulator=query_acc):
        is_cyclic = has_cycle(graph)
        n_non_trivial_sccs = sum(1 for s in sccs if len(s) > 1)
        scc_cycle_burden = sum(len(s) for s in sccs if len(s) > 1)

    # ------------------------------------------------------------------
    # 4. Reference ranking from qrels (label-derived)
    # ------------------------------------------------------------------
    ref_ranking = _reference_ranking(qrels_for_query[:top_k])

    # ------------------------------------------------------------------
    # 5. Greedy FAS (shared repair — used by topological method)
    # ------------------------------------------------------------------
    with Timer("greedy_fas_solver", accumulator=query_acc):
        dag, removed_edges = greedy_fas(graph)
        fas_weight = greedy_fas_total_weight(removed_edges)
        fas_n_removed = len(removed_edges)

    # ------------------------------------------------------------------
    # 6. Ranking methods
    # ------------------------------------------------------------------
    rankings: dict[str, list[str]] = {}

    with Timer("ranking_score_sum", accumulator=query_acc):
        rankings["score_sum"] = score_sum_ranking(graph)

    with Timer("ranking_borda", accumulator=query_acc):
        rankings["borda"] = borda_ranking(graph)

    with Timer("ranking_pagerank", accumulator=query_acc):
        rankings["pagerank"] = pagerank_ranking(graph)

    with Timer("ranking_topological", accumulator=query_acc):
        rankings["greedy_fas_topological"] = topological_ranking(dag)

    # ------------------------------------------------------------------
    # 7. Evaluation per method
    # ------------------------------------------------------------------
    with Timer("evaluation", accumulator=query_acc):
        method_metrics: dict[str, dict] = {}
        for method_name, ranking in rankings.items():
            bew = _backward_edge_weight(graph, ranking)
            pic = _pairwise_inconsistency(graph, ranking)
            tau = _kendall_tau(ranking, ref_ranking)
            method_metrics[method_name] = {
                "backward_edge_weight": bew,
                "pairwise_inconsistency": pic,
                "kendall_tau": tau,
            }

    # ------------------------------------------------------------------
    # 8. Accumulate timings into global accumulator
    # ------------------------------------------------------------------
    timing_rows = {r["stage"]: r for r in query_acc.summary_rows()}
    for stage, row in timing_rows.items():
        global_acc.record(stage, row["total_s"])

    # Retrieve per-stage runtimes for the output rows
    t_pref = timing_rows.get("pairwise_preference_generation", {}).get("total_s", 0.0)
    t_graph = timing_rows.get("graph_construction", {}).get("total_s", 0.0)
    t_cycle = timing_rows.get("cycle_detection", {}).get("total_s", 0.0)
    t_fas = timing_rows.get("greedy_fas_solver", {}).get("total_s", 0.0)
    t_eval = timing_rows.get("evaluation", {}).get("total_s", 0.0)
    t_total = sum(r["total_s"] for r in timing_rows.values())

    ranking_stage_times = {
        "score_sum": timing_rows.get("ranking_score_sum", {}).get("total_s", 0.0),
        "borda": timing_rows.get("ranking_borda", {}).get("total_s", 0.0),
        "pagerank": timing_rows.get("ranking_pagerank", {}).get("total_s", 0.0),
        "greedy_fas_topological": timing_rows.get("ranking_topological", {}).get("total_s", 0.0),
    }

    # ------------------------------------------------------------------
    # 9. Build output rows
    # ------------------------------------------------------------------
    rows = []
    for method_name in METHODS:
        m_metrics = method_metrics[method_name]
        rows.append({
            # Identity
            "dataset": dataset,
            "query_id": qid,
            "method": method_name,
            # Graph stats
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "graph_density": round(density, 6),
            "n_sccs": n_sccs,
            "largest_scc": largest_scc,
            "is_cyclic": is_cyclic,
            "n_non_trivial_sccs": n_non_trivial_sccs,
            "scc_cycle_burden": scc_cycle_burden,
            # FAS stats
            "fas_weight_removed": round(fas_weight, 6),
            "fas_n_edges_removed": fas_n_removed,
            # Evaluation
            "backward_edge_weight": round(m_metrics["backward_edge_weight"], 6),
            "pairwise_inconsistency": m_metrics["pairwise_inconsistency"],
            "kendall_tau": (
                round(m_metrics["kendall_tau"], 6)
                if m_metrics["kendall_tau"] is not None
                else None
            ),
            # Timings
            "runtime_pref_gen_s": round(t_pref, 6),
            "runtime_graph_build_s": round(t_graph, 6),
            "runtime_cycle_detect_s": round(t_cycle, 6),
            "runtime_fas_solver_s": round(t_fas, 6),
            "runtime_ranking_s": round(ranking_stage_times.get(method_name, 0.0), 6),
            "runtime_evaluation_s": round(t_eval, 6),
            "runtime_total_s": round(t_total, 6),
        })

    return rows, None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run real-data ranking experiment on a processed dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="scidocs",
        help="Dataset short name: scidocs | fiqa | hotpotqa | bright",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=50,
        help="Maximum number of queries to process.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Max candidate documents per query (preference graph size ≈ top_k² / 2).",
    )
    parser.add_argument(
        "--weight-scheme",
        type=str,
        default="grade_diff",
        choices=["grade_diff", "binary"],
        help="How to weight pairwise preferences.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Root directory for all outputs.",
    )
    parser.add_argument(
        "--save-timings",
        action="store_true",
        help="Save timing CSV and JSON to outputs/timings/.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print timing summary table to stdout at the end.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating plots even if matplotlib is available.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main experiment loop
# ---------------------------------------------------------------------------


def run_experiment(
    dataset: str,
    max_queries: int,
    top_k: int,
    weight_scheme: str,
    seed: int,
    output_dir: Path,
    save_timings: bool = False,
    profile: bool = False,
    generate_plots: bool = True,
) -> dict:
    """Run the full real-data experiment for *dataset*.

    Parameters
    ----------
    dataset:
        Short dataset name registered in the dataset registry.
    max_queries:
        Maximum number of queries to process.
    top_k:
        Maximum candidates per query.
    weight_scheme:
        Preference weight scheme.
    seed:
        Random seed.
    output_dir:
        Root output directory.
    save_timings:
        If ``True``, write timing CSV/JSON files.
    profile:
        If ``True``, print timing summary to stdout.
    generate_plots:
        If ``True``, generate timing and metric plots (requires matplotlib).

    Returns
    -------
    dict
        Experiment summary.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  Real-Data Ranking Experiment — {dataset.upper()}")
    print(f"{'='*65}")
    print(f"  dataset      : {dataset}")
    print(f"  max_queries  : {max_queries}")
    print(f"  top_k        : {top_k}")
    print(f"  weight_scheme: {weight_scheme}")
    print(f"  seed         : {seed}")
    print(f"  output_dir   : {output_dir}")
    print(f"  save_timings : {save_timings}\n")

    global_acc = TimingAccumulator()
    global_acc.set_metadata(dataset=dataset, max_queries=max_queries, top_k=top_k)

    # ------------------------------------------------------------------
    # 1. Load dataset
    # ------------------------------------------------------------------
    with Timer("dataset_loading", accumulator=global_acc):
        try:
            queries, _documents, qrels = load_dataset_splits(dataset)
        except FileNotFoundError as exc:
            log.error(
                "%s\n"
                "Run first: python scripts/prepare_datasets.py --dataset %s",
                exc,
                dataset,
            )
            sys.exit(1)
    print(f"[1] Loaded {len(queries)} queries, {len(qrels)} qrel entries")

    # ------------------------------------------------------------------
    # 2. Sample queries
    # ------------------------------------------------------------------
    with Timer("candidate_selection", accumulator=global_acc):
        # Build per-query qrel index
        qrels_by_query: dict[str, list] = defaultdict(list)
        for entry in qrels:
            qrels_by_query[entry.query_id].append(entry)

        # Restrict to queries that have at least MIN_JUDGED_DOCS entries
        eligible_qids = sorted(
            qid for qid, entries in qrels_by_query.items() if len(entries) >= MIN_JUDGED_DOCS
        )

        rng = random.Random(seed)
        rng.shuffle(eligible_qids)
        sampled_qids = eligible_qids[:max_queries]

        # Build a lookup from query_id → Query object
        query_by_id = {q.query_id: q for q in queries}

    print(f"[2] {len(eligible_qids)} eligible queries; sampled {len(sampled_qids)}")

    # ------------------------------------------------------------------
    # 3. Per-query pipeline
    # ------------------------------------------------------------------
    with Timer("total_pipeline", accumulator=global_acc):
        all_rows: list[dict] = []
        skipped: list[dict] = []

        for idx, qid in enumerate(sampled_qids):
            query = query_by_id.get(qid)
            if query is None:
                skipped.append({"query_id": qid, "reason": "query object not found"})
                continue

            query_qrels = qrels_by_query[qid]

            rows, skip_info = run_query(
                query=query,
                qrels_for_query=query_qrels,
                dataset=dataset,
                top_k=top_k,
                weight_scheme=weight_scheme,
                seed=seed,
                global_acc=global_acc,
            )

            if skip_info is not None:
                log.info("Skipping query %s: %s", skip_info["query_id"], skip_info["reason"])
                skipped.append(skip_info)
                continue

            all_rows.extend(rows)

            if (idx + 1) % 10 == 0 or (idx + 1) == len(sampled_qids):
                log.info(
                    "  Progress: %d / %d queries processed (%d skipped)",
                    idx + 1 - len(skipped),
                    len(sampled_qids),
                    len(skipped),
                )

    n_processed = len({r["query_id"] for r in all_rows})
    print(f"\n[3] Processed {n_processed} queries, skipped {len(skipped)}")

    if not all_rows:
        log.warning("No query results to save.")
        return {"n_processed": 0, "n_skipped": len(skipped)}

    # ------------------------------------------------------------------
    # 4. Save per-query CSV
    # ------------------------------------------------------------------
    pq_csv_path = output_dir / f"{dataset}_per_query.csv"
    _write_csv(all_rows, pq_csv_path)
    print(f"[4] Per-query CSV → {pq_csv_path}")

    # ------------------------------------------------------------------
    # 5. Build and save aggregate summary
    # ------------------------------------------------------------------
    summary_rows = _build_summary(all_rows)
    summary_csv_path = output_dir / f"{dataset}_summary.csv"
    _write_csv(summary_rows, summary_csv_path)
    print(f"[5] Aggregate summary CSV → {summary_csv_path}")

    # ------------------------------------------------------------------
    # 6. Timings
    # ------------------------------------------------------------------
    if profile:
        global_acc.print_summary()

    if save_timings:
        timings_dir = output_dir / "timings"
        csv_path = global_acc.save_csv(timings_dir / f"{dataset}_timings.csv")
        json_path = global_acc.save_json(timings_dir / f"{dataset}_timings.json")
        print(f"[6] Timings CSV  → {csv_path}")
        print(f"    Timings JSON → {json_path}")

    # ------------------------------------------------------------------
    # 7. Plots
    # ------------------------------------------------------------------
    if generate_plots:
        _maybe_plot(all_rows, dataset, output_dir)

    # ------------------------------------------------------------------
    # 8. Experiment summary
    # ------------------------------------------------------------------
    summary = _build_experiment_summary(all_rows, skipped, global_acc, dataset, top_k)
    _print_experiment_summary(summary, dataset)

    # Save summary JSON
    summary_json_path = output_dir / f"{dataset}_experiment_summary.json"
    with summary_json_path.open("w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n[8] Experiment summary JSON → {summary_json_path}")
    print(f"{'='*65}\n")

    return summary


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _build_summary(rows: list[dict]) -> list[dict]:
    """Build aggregate statistics per method.

    Parameters
    ----------
    rows:
        Per-query × per-method rows from the experiment loop.

    Returns
    -------
    list[dict]
        One dict per method with mean / median / max of key metrics.
    """
    by_method: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_method[r["method"]].append(r)

    summary_rows = []
    for method in METHODS:
        method_rows = by_method.get(method, [])
        if not method_rows:
            continue

        def _stats(key: str) -> dict[str, float]:
            vals = [r[key] for r in method_rows if r.get(key) is not None]
            if not vals:
                return {"mean": None, "median": None, "max": None, "min": None}
            vals_sorted = sorted(vals)
            n = len(vals_sorted)
            med = (vals_sorted[n // 2] if n % 2 else
                   (vals_sorted[n // 2 - 1] + vals_sorted[n // 2]) / 2)
            return {
                "mean": sum(vals) / n,
                "median": med,
                "max": max(vals),
                "min": min(vals),
            }

        bew = _stats("backward_edge_weight")
        pic = _stats("pairwise_inconsistency")
        tau = _stats("kendall_tau")
        rt = _stats("runtime_total_s")
        n_nodes = _stats("n_nodes")
        n_edges = _stats("n_edges")

        summary_rows.append({
            "method": method,
            "n_queries": len(method_rows),
            # Backward edge weight
            "bew_mean": bew["mean"],
            "bew_median": bew["median"],
            "bew_max": bew["max"],
            "bew_min": bew["min"],
            # Pairwise inconsistency
            "pic_mean": pic["mean"],
            "pic_median": pic["median"],
            "pic_max": pic["max"],
            # Kendall tau
            "tau_mean": tau["mean"],
            "tau_median": tau["median"],
            "tau_max": tau["max"],
            # Runtime
            "runtime_mean_s": rt["mean"],
            "runtime_median_s": rt["median"],
            "runtime_max_s": rt["max"],
            # Graph size
            "n_nodes_mean": n_nodes["mean"],
            "n_edges_mean": n_edges["mean"],
        })

    return summary_rows


def _build_experiment_summary(
    all_rows: list[dict],
    skipped: list[dict],
    global_acc: TimingAccumulator,
    dataset: str,
    top_k: int,
) -> dict:
    """Build a structured experiment summary dict.

    Parameters
    ----------
    all_rows:
        All per-query × per-method output rows.
    skipped:
        Queries that were skipped with their reasons.
    global_acc:
        The global ``TimingAccumulator``.
    dataset:
        Dataset short name.
    top_k:
        Candidate limit used.

    Returns
    -------
    dict
    """
    query_ids = list({r["query_id"] for r in all_rows})
    n_processed = len(query_ids)
    n_skipped = len(skipped)

    # Average graph size (from score_sum rows to avoid duplicating per method)
    ss_rows = [r for r in all_rows if r["method"] == "score_sum"]
    avg_n_nodes = sum(r["n_nodes"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_n_edges = sum(r["n_edges"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_scc = sum(r["largest_scc"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    pct_cyclic = (
        sum(1 for r in ss_rows if r["is_cyclic"]) / len(ss_rows) * 100
        if ss_rows else 0
    )

    # Average runtime by method
    by_method: dict[str, list[float]] = defaultdict(list)
    for r in all_rows:
        if r.get("runtime_total_s") is not None:
            by_method[r["method"]].append(r["runtime_total_s"])
    avg_rt_by_method = {
        m: sum(vs) / len(vs) for m, vs in by_method.items() if vs
    }

    # Best method by backward-edge-weight (lower is better)
    bew_by_method: dict[str, list[float]] = defaultdict(list)
    for r in all_rows:
        if r.get("backward_edge_weight") is not None:
            bew_by_method[r["method"]].append(r["backward_edge_weight"])
    avg_bew = {m: sum(vs) / len(vs) for m, vs in bew_by_method.items() if vs}
    best_method = min(avg_bew, key=avg_bew.get) if avg_bew else "n/a"

    # Global timing summary
    timing_summary = {row["stage"]: row for row in global_acc.summary_rows()}

    return {
        "dataset": dataset,
        "top_k": top_k,
        "n_processed": n_processed,
        "n_skipped": n_skipped,
        "skipped_reasons": [s["reason"] for s in skipped],
        "avg_n_nodes": round(avg_n_nodes, 2),
        "avg_n_edges": round(avg_n_edges, 2),
        "avg_largest_scc": round(avg_scc, 2),
        "pct_cyclic_graphs": round(pct_cyclic, 1),
        "avg_runtime_by_method_s": {m: round(v, 6) for m, v in avg_rt_by_method.items()},
        "avg_bew_by_method": {m: round(v, 6) for m, v in avg_bew.items()},
        "best_method_by_bew": best_method,
        "global_timings": {
            stage: {"total_s": row["total_s"], "mean_s": row["mean_s"]}
            for stage, row in timing_summary.items()
        },
    }


def _print_experiment_summary(summary: dict, dataset: str) -> None:
    print(f"\n{'='*65}")
    print(f"  Experiment Summary — {dataset.upper()}")
    print(f"{'='*65}")
    print(f"  Queries processed : {summary['n_processed']}")
    print(f"  Queries skipped   : {summary['n_skipped']}")
    print(f"  Avg graph nodes   : {summary['avg_n_nodes']:.1f}")
    print(f"  Avg graph edges   : {summary['avg_n_edges']:.1f}")
    print(f"  Avg largest SCC   : {summary['avg_largest_scc']:.1f}")
    print(f"  % cyclic graphs   : {summary['pct_cyclic_graphs']:.1f}%")
    print(f"\n  Average runtime by method (s):")
    for m, v in summary["avg_runtime_by_method_s"].items():
        print(f"    {m:<30} {v:.6f}")
    print(f"\n  Best method by backward-edge weight: {summary['best_method_by_bew']}")
    print(f"  Average BEW by method:")
    for m, v in summary["avg_bew_by_method"].items():
        print(f"    {m:<30} {v:.4f}")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _write_csv(rows: list[dict], path: Path) -> None:
    """Write a list of dicts to a CSV file.

    Parameters
    ----------
    rows:
        Data rows.
    path:
        Output path (parent directory created if needed).
    """
    if not rows:
        log.warning("No rows to write to %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = parse_args(argv)
    run_experiment(
        dataset=args.dataset,
        max_queries=args.max_queries,
        top_k=args.top_k,
        weight_scheme=args.weight_scheme,
        seed=args.seed,
        output_dir=args.output_dir,
        save_timings=args.save_timings,
        profile=args.profile,
        generate_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
