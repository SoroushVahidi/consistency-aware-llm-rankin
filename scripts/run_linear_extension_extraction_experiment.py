# ruff: noqa: E501
#!/usr/bin/env python3
"""
Linear-extension extraction experiment (DAG ranking stage only).

Compares hard-constraint topological methods and soft score baselines on:
  * synthetic noisy preference graphs (original + repaired DAG)
  * optional precomputed real pairwise preference files (no LLM API calls)

Outputs a timestamped report directory with CSV/JSON artifacts and FINAL_REPORT.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    copeland_ranking,
    score_sum_ranking,
    score_sum_scores,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.dag_ambiguity import dag_ambiguity_features
from consistency_ranker.dag_linear_extensions import (
    HARD_CONSTRAINT_METHODS,
    assert_valid_topological_order,
    closest_valid_extension_exact,
    dag_backward_edge_weight,
    farthest_valid_extension_exact,
    is_valid_topological_order,
    linear_extension_metric_dispersion,
    method_metadata,
    pairwise_accuracy_vs_graph,
    run_hard_constraint_method,
    sample_linear_extensions,
)
from consistency_ranker.evaluation import kendall_tau, ndcg_at_k
from consistency_ranker.experiment_cli import (
    ensure_output_dir,
    file_sha256,
    utc_stamp,
    write_run_manifest,
)
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.pairwise_prefs import Preference, generate_preferences
from consistency_ranker.soft_score_ranking import (
    normalized_weighted_balance_ranking,
    serialrank_ranking,
    soft_method_metadata,
    springrank_ranking,
)
from consistency_ranker.statistical_inference import (
    bootstrap_mean_interval,
    delta_summary,
    holm_adjust,
    sign_flip_pvalue,
)
from consistency_ranker.synthetic_data import generate_items, ground_truth_ranking

REPO_ROOT = Path(__file__).resolve().parents[1]

HARD_METHODS_CORE = [
    "lexicographic_topo",
    "prior_priority_topo",
    "balance_priority_topo_static",
    "balance_priority_topo_dynamic",
    "norm_balance_priority_topo_static",
    "norm_balance_priority_topo_dynamic",
    "degree_ratio_priority_topo_static",
    "degree_ratio_priority_topo_dynamic",
    "log_degree_ratio_priority_topo_static",
    "log_degree_ratio_priority_topo_dynamic",
    "source_sink_peeling",
    "closest_valid_extension_greedy",
]

SOFT_METHODS = [
    "soft_score_sum",
    "soft_borda",
    "soft_balance",
    "soft_norm_balance",
    "soft_copeland",
    "soft_springrank",
    "soft_serialrank",
]


def _utc_stamp() -> str:
    return utc_stamp()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _soft_ranking(name: str, graph: nx.DiGraph) -> list[str]:
    if name == "soft_score_sum":
        return score_sum_ranking(graph)
    if name == "soft_borda":
        return borda_ranking(graph)
    if name == "soft_balance":
        return weighted_out_minus_in_ranking(graph)
    if name == "soft_norm_balance":
        return normalized_weighted_balance_ranking(graph)
    if name == "soft_copeland":
        return copeland_ranking(graph)
    if name == "soft_springrank":
        return springrank_ranking(graph)
    if name == "soft_serialrank":
        return serialrank_ranking(graph)
    raise ValueError(name)


def _eval_ranking(
    *,
    ranking: list[str],
    reference: list[str],
    original_graph: nx.DiGraph,
    dag: nx.DiGraph,
    relevance_map: dict[str, int] | None,
    top_k: int,
) -> dict[str, Any]:
    ref_nodes = [x for x in reference if x in dag]
    for n in dag.nodes():
        if n not in ref_nodes:
            ref_nodes.append(n)
    aligned = [x for x in ranking if x in ref_nodes]
    for n in ref_nodes:
        if n not in aligned:
            aligned.append(n)
    out: dict[str, Any] = {
        "kendall_tau_vs_reference": float(kendall_tau(aligned, ref_nodes)),
        "pairwise_accuracy_vs_dag": float(pairwise_accuracy_vs_graph(dag, ranking)),
        "bew_vs_original_graph": float(dag_backward_edge_weight(original_graph, ranking)),
        "bew_vs_dag": float(dag_backward_edge_weight(dag, ranking)),
        "is_valid_topo_on_dag": bool(is_valid_topological_order(dag, ranking)),
    }
    if relevance_map is not None:
        out["ndcg"] = float(ndcg_at_k(ranking, relevance_map, k=top_k))
    else:
        out["ndcg"] = None
    return out


def _run_one_instance(
    *,
    instance_id: str,
    source: str,
    graph: nx.DiGraph,
    reference: list[str],
    prior_scores: dict[str, float],
    prior_ranking: list[str],
    relevance_map: dict[str, int] | None,
    top_k: int,
    seed: int,
    n_random_samples: int,
    exact_oracle_max_nodes: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    was_dag = nx.is_directed_acyclic_graph(graph)
    if was_dag:
        dag = graph.copy()
        removed = []
        fas_weight = 0.0
    else:
        dag, removed = greedy_fas(graph)
        fas_weight = greedy_fas_total_weight(removed)

    amb = dag_ambiguity_features(dag)
    rows: list[dict[str, Any]] = []
    base_meta = {
        "instance_id": instance_id,
        "source": source,
        "originally_acyclic": was_dag,
        "n_nodes": graph.number_of_nodes(),
        "n_edges_original": graph.number_of_edges(),
        "n_edges_dag": dag.number_of_edges(),
        "fas_removed_edges": len(removed),
        "fas_removed_weight": fas_weight,
        **{f"amb_{k}": v for k, v in amb.items()},
    }

    # Hard-constraint methods
    for method in HARD_METHODS_CORE:
        t0 = time.perf_counter()
        ranking = run_hard_constraint_method(
            method,
            dag,
            prior_scores=prior_scores,
            prior_ranking=prior_ranking,
            seed=seed,
        )
        runtime = time.perf_counter() - t0
        assert_valid_topological_order(dag, ranking)
        metrics = _eval_ranking(
            ranking=ranking,
            reference=reference,
            original_graph=graph,
            dag=dag,
            relevance_map=relevance_map,
            top_k=top_k,
        )
        rows.append(
            {
                **base_meta,
                "method": method,
                "family": "hard_constraint",
                "guarantees_topo": True,
                "runtime_seconds": runtime,
                "seed": seed,
                **metrics,
            }
        )

    # Soft methods on repaired DAG (and noted as soft)
    for method in SOFT_METHODS:
        t0 = time.perf_counter()
        ranking = _soft_ranking(method, dag)
        runtime = time.perf_counter() - t0
        metrics = _eval_ranking(
            ranking=ranking,
            reference=reference,
            original_graph=graph,
            dag=dag,
            relevance_map=relevance_map,
            top_k=top_k,
        )
        rows.append(
            {
                **base_meta,
                "method": method,
                "family": "soft_score",
                "guarantees_topo": False,
                "runtime_seconds": runtime,
                "seed": seed,
                **metrics,
            }
        )

    # Random extension dispersion (diagnostic)
    samples = sample_linear_extensions(dag, n_samples=n_random_samples, seed=seed)
    disp = linear_extension_metric_dispersion(samples, reference, metric="kendall_tau")
    dispersion_record = {
        **base_meta,
        "n_random_samples": n_random_samples,
        "seed": seed,
        **{f"tau_{k}": v for k, v in disp.items()},
    }

    # Small-instance oracles (enumeration + ILP cross-check on tiny DAGs)
    if dag.number_of_nodes() <= exact_oracle_max_nodes:
        best = closest_valid_extension_exact(dag, prior_ranking)
        worst = farthest_valid_extension_exact(dag, prior_ranking)
        oracle_specs: list[tuple[str, list[str]]] = [
            ("best_extension_oracle", best),
            ("worst_extension_oracle", worst),
        ]
        if dag.number_of_nodes() <= 8:
            from consistency_ranker.dag_linear_extensions import (
                closest_valid_extension_ilp,
            )

            ilp = closest_valid_extension_ilp(dag, prior_ranking)
            oracle_specs.append(("closest_valid_extension_ilp", ilp))
        for label, ranking in oracle_specs:
            metrics = _eval_ranking(
                ranking=ranking,
                reference=reference,
                original_graph=graph,
                dag=dag,
                relevance_map=relevance_map,
                top_k=top_k,
            )
            rows.append(
                {
                    **base_meta,
                    "method": label,
                    "family": (
                        "hard_constraint_oracle"
                        if label == "closest_valid_extension_ilp"
                        else "diagnostic_oracle"
                    ),
                    "guarantees_topo": True,
                    "runtime_seconds": None,
                    "seed": seed,
                    **metrics,
                }
            )

    return rows, dispersion_record


def _synthetic_instances(
    *,
    n_items: int,
    noises: list[float],
    seeds: list[int],
    small_n_items: list[int] | None = None,
) -> list[dict[str, Any]]:
    instances = []
    sizes = [n_items]
    if small_n_items:
        sizes = list(dict.fromkeys([*small_n_items, n_items]))
    for n in sizes:
        # Fewer seeds for tiny oracle graphs; full seed grid for primary size.
        use_seeds = seeds if n == n_items else seeds[: min(5, len(seeds))]
        use_noises = noises if n == n_items else [0.1, 0.3]
        for noise in use_noises:
            for seed in use_seeds:
                items = generate_items(n, seed=seed)
                gt = ground_truth_ranking(items)
                quality = {it.item_id: it.quality for it in items}
                prefs = generate_preferences(quality, noise=noise, seed=seed)
                graph = build_graph(prefs)
                prior_scores = score_sum_scores(graph)
                prior_ranking = sorted(prior_scores, key=lambda d: (-prior_scores[d], d))
                rel = {doc: n - i for i, doc in enumerate(gt)}
                instances.append(
                    {
                        "instance_id": f"synth_n{n}_noise{noise:.2f}_seed{seed}",
                        "source": "synthetic" if n == n_items else "synthetic_small",
                        "graph": graph,
                        "reference": gt,
                        "prior_scores": prior_scores,
                        "prior_ranking": prior_ranking,
                        "relevance_map": rel,
                    }
                )
    return instances


def _load_real_preference_instances(
    preferences_path: Path,
    qrels_path: Path | None,
    *,
    max_queries: int,
    max_nodes: int,
    source_label: str | None = None,
    winner_key: str = "winner_doc_id",
    loser_key: str = "loser_doc_id",
) -> list[dict[str, Any]]:
    by_query: dict[str, list[Preference]] = defaultdict(list)
    with preferences_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            qid = str(rec["query_id"])
            winner = rec.get(winner_key, rec.get("winner"))
            loser = rec.get(loser_key, rec.get("loser"))
            if winner is None or loser is None:
                continue
            by_query[qid].append(
                Preference(
                    winner=str(winner),
                    loser=str(loser),
                    weight=float(rec.get("weight", 1.0)),
                )
            )

    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    if qrels_path is not None and qrels_path.exists():
        with qrels_path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                qrels[str(rec["query_id"])][str(rec["doc_id"])] = int(rec["relevance"])

    label = source_label or f"real:{preferences_path}"
    instances: list[dict[str, Any]] = []
    for qid in sorted(by_query.keys()):
        if len(instances) >= max_queries:
            break
        prefs = by_query[qid]
        graph = build_graph(prefs)
        if graph.number_of_nodes() == 0 or graph.number_of_nodes() > max_nodes:
            continue
        prior_scores = score_sum_scores(graph)
        prior_ranking = sorted(prior_scores, key=lambda n: (-prior_scores[n], n))
        rel_map = qrels.get(qid, {})
        # Judgment-free Kendall reference = prior ranking (not qrels).
        # Retrieval metrics use qrels only when the query has labels; do not
        # fabricate all-zero relevance maps (that would coerce missing → 0 nDCG).
        reference = list(prior_ranking)
        eval_rel: dict[str, int] | None
        if rel_map:
            eval_rel = {d: int(rel_map.get(d, 0)) for d in graph.nodes()}
        else:
            eval_rel = None
        instances.append(
            {
                "instance_id": f"{label}_{qid[:12]}",
                "source": label,
                "graph": graph,
                "reference": reference,
                "prior_scores": prior_scores,
                "prior_ranking": prior_ranking,
                "relevance_map": eval_rel,
            }
        )
    return instances


def _aggregate_method_rows(
    rows: list[dict[str, Any]],
    *,
    source_filter: str | None = None,
) -> list[dict[str, Any]]:
    filtered = rows
    if source_filter == "synthetic":
        filtered = [r for r in rows if r["source"] == "synthetic"]
    elif source_filter == "real":
        filtered = [r for r in rows if r["source"] != "synthetic"]
    elif source_filter is not None:
        filtered = [r for r in rows if r["source"] == source_filter]
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in filtered:
        by_method[r["method"]].append(r)
    out = []
    for method, group in sorted(by_method.items()):
        taus = [float(r["kendall_tau_vs_reference"]) for r in group]
        bews = [float(r["bew_vs_original_graph"]) for r in group]
        ndcgs = [float(r["ndcg"]) for r in group if r.get("ndcg") is not None]
        topo_ok = [bool(r["is_valid_topo_on_dag"]) for r in group]
        runtimes = [
            float(r["runtime_seconds"])
            for r in group
            if r.get("runtime_seconds") is not None
        ]
        out.append(
            {
                "slice": source_filter or "all",
                "method": method,
                "family": group[0]["family"],
                "guarantees_topo": group[0]["guarantees_topo"],
                "n": len(group),
                "mean_kendall_tau": float(np.mean(taus)),
                "std_kendall_tau": float(np.std(taus)),
                "mean_bew_original": float(np.mean(bews)),
                "mean_ndcg": float(np.mean(ndcgs)) if ndcgs else None,
                "frac_valid_topo": float(np.mean(topo_ok)),
                "mean_runtime_seconds": float(np.mean(runtimes)) if runtimes else None,
            }
        )
    return out


def _paired_comparisons(
    rows: list[dict[str, Any]],
    *,
    baseline: str,
    metric: str,
    seed: int,
) -> list[dict[str, Any]]:
    by_inst: dict[str, dict[str, float]] = defaultdict(dict)
    family: dict[str, str] = {}
    for r in rows:
        if r.get(metric) is None:
            continue
        by_inst[r["instance_id"]][r["method"]] = float(r[metric])
        family[r["method"]] = r["family"]
    methods = sorted({m for vals in by_inst.values() for m in vals})
    raw_p: list[tuple[str, float | None]] = []
    results: list[dict[str, Any]] = []
    for method in methods:
        if method == baseline:
            continue
        deltas = []
        for _iid, vals in by_inst.items():
            if baseline in vals and method in vals:
                deltas.append(vals[method] - vals[baseline])
        if not deltas:
            continue
        summary = delta_summary(deltas)
        sf = sign_flip_pvalue(deltas, reps=5000, seed=seed)
        boot = bootstrap_mean_interval(deltas, reps=2000, seed=seed)
        raw_p.append((method, sf.pvalue))
        results.append(
            {
                "baseline": baseline,
                "method": method,
                "family": family.get(method),
                "metric": metric,
                "n_paired": summary["n"],
                "mean_delta": summary["mean"],
                "median_delta": summary["median"],
                "sign_flip_pvalue": sf.pvalue,
                "bootstrap_ci_low": boot.lower,
                "bootstrap_ci_high": boot.upper,
            }
        )
    # Holm correction across methods for this metric.
    pvals = [p for _, p in raw_p if p is not None]
    labels = [m for m, p in raw_p if p is not None]
    if pvals:
        adjusted = holm_adjust(pvals)
        adj_map = dict(zip(labels, adjusted))
        for row in results:
            row["holm_adjusted_pvalue"] = adj_map.get(row["method"])
    else:
        for row in results:
            row["holm_adjusted_pvalue"] = None
    return results


def _ambiguity_stratified(
    rows: list[dict[str, Any]],
    *,
    baseline: str,
    focus_methods: list[str],
) -> list[dict[str, Any]]:
    out = []
    buckets = sorted({r["amb_ambiguity_bucket"] for r in rows})
    for bucket in buckets:
        sub = [r for r in rows if r["amb_ambiguity_bucket"] == bucket]
        by_inst: dict[str, dict[str, float]] = defaultdict(dict)
        for r in sub:
            by_inst[r["instance_id"]][r["method"]] = float(r["kendall_tau_vs_reference"])
        for method in focus_methods:
            deltas = []
            for vals in by_inst.values():
                if baseline in vals and method in vals:
                    deltas.append(vals[method] - vals[baseline])
            if not deltas:
                continue
            out.append(
                {
                    "ambiguity_bucket": bucket,
                    "baseline": baseline,
                    "method": method,
                    "n": len(deltas),
                    "mean_delta_tau": float(np.mean(deltas)),
                    "std_delta_tau": float(np.std(deltas)),
                    "frac_strict_improve": float(np.mean([d > 1e-12 for d in deltas])),
                }
            )
    return out


def _sensitivity_vs_ambiguity(dispersion_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in dispersion_rows:
        tau_std = r.get("tau_std")
        frac_inc = r.get("amb_fraction_incomparable_pairs")
        if tau_std is None or frac_inc is None:
            continue
        out.append(
            {
                "instance_id": r["instance_id"],
                "ambiguity_bucket": r["amb_ambiguity_bucket"],
                "fraction_incomparable_pairs": frac_inc,
                "max_frontier_size": r["amb_max_frontier_size"],
                "n_linear_extensions": r.get("amb_n_linear_extensions"),
                "tau_std_across_extensions": tau_std,
                "tau_range": (
                    None
                    if r.get("tau_max") is None or r.get("tau_min") is None
                    else float(r["tau_max"]) - float(r["tau_min"])
                ),
            }
        )
    return out


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    if np.std(x) < 1e-15 or np.std(y) < 1e-15:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _fmt_ndcg(val):
    return "n/a" if val is None else f"{val:.4f}"


def _build_report(
    *,
    out_dir: Path,
    config: dict[str, Any],
    method_summary: list[dict[str, Any]],
    paired: list[dict[str, Any]],
    stratified: list[dict[str, Any]],
    sensitivity: list[dict[str, Any]],
    audit: dict[str, Any],
) -> str:
    # Rank hard methods by mean Kendall tau
    hard = [r for r in method_summary if r["family"] == "hard_constraint"]
    hard_sorted = sorted(hard, key=lambda r: (-(r["mean_kendall_tau"] or -999), r["method"]))
    soft = [r for r in method_summary if r["family"] == "soft_score"]
    soft_sorted = sorted(soft, key=lambda r: (-(r["mean_kendall_tau"] or -999), r["method"]))

    best_hard = hard_sorted[0] if hard_sorted else None
    lex = next((r for r in hard if r["method"] == "lexicographic_topo"), None)
    norm_dyn = next(
        (r for r in hard if r["method"] == "norm_balance_priority_topo_dynamic"), None
    )
    prior = next((r for r in hard if r["method"] == "prior_priority_topo"), None)

    sens_corr = _pearson(
        [float(r["fraction_incomparable_pairs"]) for r in sensitivity],
        [float(r["tau_std_across_extensions"]) for r in sensitivity],
    )

    # Headline change recommendation: only if a hard method beats prior_priority
    # and lexicographic with Holm-adjusted significance on tau.
    sig_wins = [
        r
        for r in paired
        if r["baseline"] == "prior_priority_topo"
        and r["metric"] == "kendall_tau_vs_reference"
        and r["family"] == "hard_constraint"
        and r.get("holm_adjusted_pvalue") is not None
        and r["holm_adjusted_pvalue"] < 0.05
        and (r.get("mean_delta") or 0) > 0
    ]

    lines = [
        "# Linear-extension extraction experiment — FINAL REPORT",
        "",
        f"Generated: `{config['timestamp_utc']}`",
        "",
        "## 1. Audit summary (existing vs missing)",
        "",
        "### Already present before this work",
        "",
        "- **Hard (partial):** `topological_ranking` (NetworkX default), `priority_topological_ranking` (prior among sources).",
        "- **Soft (active pipeline):** score-sum, Borda, Copeland, weighted balance, PageRank, RankCentrality, Markov, hybrid RRF/balance mixes.",
        "- **Priors (judgment-free):** RRF / CombSUM / Borda-fuse / score-sum helpers.",
        "- **Older related repos:** `minimum-weighted-fas-heuristics` EXP11 (min-id / max-id / static weighted-net Kahn); `ranking-by-feedback-arc-set` SpringRank + SerialRank.",
        "",
        "### Missing / incomplete before this work",
        "",
        "- Explicit lexicographic Kahn, static vs dynamic balance / normalized-balance / ratio topo tie-breakers,",
        "  source/sink peeling, closest-valid-extension, random extension sampling, ambiguity features,",
        "  soft SpringRank/SerialRank/normalized-balance soft baselines in the active package,",
        "  and a dedicated linear-extension sensitivity experiment with multiplicity-corrected paired tests.",
        "",
        "### Implemented now",
        "",
        "- Hard-constraint family in `src/consistency_ranker/dag_linear_extensions.py`.",
        "- Ambiguity features in `src/consistency_ranker/dag_ambiguity.py`.",
        "- Soft baselines in `src/consistency_ranker/soft_score_ranking.py`.",
        "",
        "## 2. Experimental configuration",
        "",
        "```json",
        json.dumps(config, indent=2),
        "```",
        "",
        "## 3. Method performance (mean Kendall τ vs reference)",
        "",
        "### Hard-constraint methods (guaranteed valid topological orders)",
        "",
        "| Method | Mean τ | Std | Mean BEW(original) | Mean nDCG | Frac valid topo |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in hard_sorted:
        lines.append(
            f"| `{r['method']}` | {r['mean_kendall_tau']:.4f} | {r['std_kendall_tau']:.4f} | "
            f"{r['mean_bew_original']:.4f} | "
            f"{_fmt_ndcg(r['mean_ndcg'])} | "
            f"{r['frac_valid_topo']:.3f} |"
        )
    lines += [
        "",
        "### Soft score methods (may violate individual DAG edges)",
        "",
        "| Method | Mean τ | Std | Mean BEW(original) | Mean nDCG | Frac valid topo |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in soft_sorted:
        lines.append(
            f"| `{r['method']}` | {r['mean_kendall_tau']:.4f} | {r['std_kendall_tau']:.4f} | "
            f"{r['mean_bew_original']:.4f} | "
            f"{_fmt_ndcg(r['mean_ndcg'])} | "
            f"{r['frac_valid_topo']:.3f} |"
        )

    lines += [
        "",
        "## 4. Does linear-extension choice matter?",
        "",
    ]
    if sensitivity:
        mean_std = float(np.mean([r["tau_std_across_extensions"] for r in sensitivity]))
        mean_range = float(
            np.mean([r["tau_range"] for r in sensitivity if r["tau_range"] is not None])
        )
        lines.append(
            f"- Across instances, mean τ std over random valid extensions = **{mean_std:.4f}**; "
            f"mean τ range = **{mean_range:.4f}**."
        )
        lines.append(
            f"- Pearson correlation between fraction of incomparable pairs and τ std = "
            f"**{sens_corr if sens_corr is not None else 'n/a'}**."
        )
    else:
        lines.append("- Insufficient dispersion rows to summarize sensitivity.")

    lines += [
        "",
        "## 5. Benefit vs ambiguity",
        "",
        "| Bucket | Method vs baseline | N | Mean Δτ | Frac improve |",
        "|---|---|---:|---:|---:|",
    ]
    for r in stratified:
        lines.append(
            f"| {r['ambiguity_bucket']} | `{r['method']}` vs `{r['baseline']}` | "
            f"{r['n']} | {r['mean_delta_tau']:.4f} | {r['frac_strict_improve']:.3f} |"
        )

    lines += [
        "",
        "## 6. Normalized degree heuristic usefulness",
        "",
    ]
    if lex and norm_dyn:
        lines.append(
            f"- Lexicographic mean τ = {lex['mean_kendall_tau']:.4f}; "
            f"dynamic normalized-balance topo mean τ = {norm_dyn['mean_kendall_tau']:.4f}."
        )
        delta = norm_dyn["mean_kendall_tau"] - lex["mean_kendall_tau"]
        lines.append(
            f"- Raw mean Δτ (norm-balance-dynamic − lex) = {delta:.4f}. "
            "See paired Holm-adjusted tests in `paired_comparisons.csv` before claiming significance."
        )
    if prior and best_hard:
        lines.append(
            f"- Best hard method by mean τ: `{best_hard['method']}` "
            f"({best_hard['mean_kendall_tau']:.4f}); "
            f"current prior-priority topo: {prior['mean_kendall_tau']:.4f}."
        )

    lines += [
        "",
        "## 7. Should the headline method change?",
        "",
    ]
    if sig_wins:
        lines.append(
            "Holm-adjusted paired sign-flip tests found hard methods that significantly beat "
            "`prior_priority_topo` on Kendall τ: "
            + ", ".join(f"`{r['method']}` (adj p={r['holm_adjusted_pvalue']:.4g})" for r in sig_wins)
            + "."
        )
        lines.append(
            "A manuscript change is supported only for those methods, and only as an extraction-stage "
            "ablation — not as a claim that repair itself improved retrieval."
        )
    else:
        lines.append(
            "No hard-constraint method significantly outperformed `prior_priority_topo` after Holm "
            "correction on Kendall τ in this run. **Do not change the headline extraction method** "
            "based on this experiment alone; keep prior-priority topological ranking as the default "
            "deployable hard method, and report the new family as a calibrated ablation."
        )

    lines += [
        "",
        "## 8. Precise manuscript-facing wording supported by this evidence",
        "",
        "1. After cycle repair, the active preference graph is a DAG; any linear extension is a valid "
        "hard ranking that respects every retained edge.",
        "2. When the DAG is ambiguous (large source frontier / many incomparable pairs), different "
        "valid extensions can change agreement with an external reference; random-extension dispersion "
        "quantifies that sensitivity.",
        "3. Soft score rankings (balance, SpringRank, SerialRank, normalized balance) remain useful "
        "baselines but must be labeled as **not** guaranteeing edge fidelity on the repaired DAG.",
        "4. The older normalized degree score is useful as a **topological tie-breaker** among available "
        "sources (hard) and as a soft score; these two uses must not be conflated.",
        "",
        "## 9. Artifacts",
        "",
        "- `per_instance_method_metrics.csv`",
        "- `method_summary.csv`",
        "- `paired_comparisons.csv`",
        "- `ambiguity_stratified_deltas.csv`",
        "- `extension_dispersion.csv`",
        "- `sensitivity_vs_ambiguity.csv`",
        "- `method_catalog.json`",
        "- `config.json`",
        "- `AUDIT.md`",
        "",
        "## 10. Reproduce",
        "",
        "```bash",
        "source .venv/bin/activate",
        "python scripts/run_linear_extension_extraction_experiment.py \\",
        f"  --output-dir {out_dir}",
        "```",
        "",
        "See also `REPRODUCE.sh` in this directory.",
        "",
    ]
    return "\n".join(lines)


def _audit_markdown() -> str:
    audit_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "historical"
        / "linear_extension_method_audit.md"
    )
    if not audit_path.exists():
        return (
            "# Method audit unavailable\n\n"
            f"Expected historical audit at `{audit_path.as_posix()}`.\n"
        )
    return audit_path.read_text()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report directory (default: reports/linear_extension_extraction_<UTC>).",
    )
    parser.add_argument("--n-items", type=int, default=12)
    parser.add_argument(
        "--noises",
        type=float,
        nargs="+",
        default=[0.0, 0.1, 0.2, 0.3],
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--n-random-samples", type=int, default=32)
    parser.add_argument("--exact-oracle-max-nodes", type=int, default=8)
    parser.add_argument(
        "--small-n-items",
        type=int,
        nargs="+",
        default=[6, 8],
        help="Extra synthetic sizes for exact/ILP oracle diagnostics.",
    )
    parser.add_argument(
        "--real-preferences",
        type=Path,
        default=REPO_ROOT / "data/processed/beir/scidocs/pairwise/preferences.jsonl",
    )
    parser.add_argument(
        "--real-qrels",
        type=Path,
        default=REPO_ROOT / "data/processed/beir/scidocs/qrels.jsonl",
    )
    parser.add_argument(
        "--llm-judgments",
        type=Path,
        default=(
            REPO_ROOT
            / "outputs/openai_scidocs_real_pairwise_q50_k15/judgment_cache"
            / "llm_pairwise_judgments.jsonl"
        ),
        help="Cached LLM pairwise judgments (no API calls).",
    )
    parser.add_argument("--max-real-queries", type=int, default=50)
    parser.add_argument("--max-real-nodes", type=int, default=30)
    parser.add_argument("--skip-real", action="store_true")
    parser.add_argument("--skip-proxy-prefs", action="store_true")
    parser.add_argument("--baseline", type=str, default="prior_priority_topo")
    parser.add_argument("--stats-seed", type=int, default=42)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Tiny offline smoke: synthetic only, 1 seed, small n.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into a non-empty --output-dir.",
    )
    args = parser.parse_args()

    stamp = utc_stamp()
    n_items = args.n_items
    noises = list(args.noises)
    seeds = list(args.seeds)
    top_k = args.top_k
    n_random_samples = args.n_random_samples
    exact_oracle_max_nodes = args.exact_oracle_max_nodes
    small_n_items = list(args.small_n_items)
    skip_real = bool(args.skip_real)
    skip_proxy = bool(args.skip_proxy_prefs)
    if args.quick:
        n_items = 6
        noises = [0.1]
        seeds = [0]
        top_k = 5
        n_random_samples = 4
        exact_oracle_max_nodes = 6
        small_n_items = [6]
        skip_real = True
        skip_proxy = True

    out_dir = ensure_output_dir(
        (
            args.output_dir
            or (REPO_ROOT / "reports" / f"linear_extension_extraction_{stamp}")
        ).resolve(),
        overwrite=args.overwrite,
    )

    config = {
        "timestamp_utc": stamp,
        "n_items": n_items,
        "noises": noises,
        "seeds": seeds,
        "top_k": top_k,
        "n_random_samples": n_random_samples,
        "exact_oracle_max_nodes": exact_oracle_max_nodes,
        "small_n_items": small_n_items,
        "skip_real": skip_real,
        "skip_proxy_prefs": skip_proxy,
        "real_preferences": str(args.real_preferences),
        "real_qrels": str(args.real_qrels),
        "llm_judgments": str(args.llm_judgments),
        "max_real_queries": args.max_real_queries,
        "max_real_nodes": args.max_real_nodes,
        "baseline": args.baseline,
        "stats_seed": args.stats_seed,
        "quick": bool(args.quick),
        "offline": True,
        "paid_api_calls": 0,
        "hard_methods": HARD_METHODS_CORE,
        "soft_methods": SOFT_METHODS,
        "hard_constraint_catalog": list(HARD_CONSTRAINT_METHODS),
        "notes": (
            "Proxy SciDocs preferences separate relevant/non-relevant perfectly "
            "under any DAG linear extension (nDCG saturated). Primary real "
            "evaluation uses cached LLM pairwise judgments. Qrels are used only "
            "for post-hoc nDCG; they never guide extraction."
        ),
    }
    write_run_manifest(
        out_dir,
        script="scripts/run_linear_extension_extraction_experiment.py",
        config=config,
        repo_root=REPO_ROOT,
        input_hashes={
            "real_preferences": file_sha256(args.real_preferences),
            "real_qrels": file_sha256(args.real_qrels),
            "llm_judgments": file_sha256(args.llm_judgments),
        },
    )

    instances = _synthetic_instances(
        n_items=n_items,
        noises=noises,
        seeds=seeds,
        small_n_items=small_n_items,
    )
    if not skip_real:
        if args.llm_judgments.exists():
            instances.extend(
                _load_real_preference_instances(
                    args.llm_judgments,
                    args.real_qrels if args.real_qrels.exists() else None,
                    max_queries=args.max_real_queries,
                    max_nodes=args.max_real_nodes,
                    source_label="llm_cached_scidocs",
                    winner_key="winner",
                    loser_key="loser",
                )
            )
        if not skip_proxy and args.real_preferences.exists():
            instances.extend(
                _load_real_preference_instances(
                    args.real_preferences,
                    args.real_qrels if args.real_qrels.exists() else None,
                    max_queries=min(20, args.max_real_queries),
                    max_nodes=args.max_real_nodes,
                    source_label="proxy_scidocs_prefs",
                )
            )

    all_rows: list[dict[str, Any]] = []
    dispersion_rows: list[dict[str, Any]] = []
    for inst in instances:
        rows, disp = _run_one_instance(
            instance_id=inst["instance_id"],
            source=inst["source"],
            graph=inst["graph"],
            reference=inst["reference"],
            prior_scores=inst["prior_scores"],
            prior_ranking=inst["prior_ranking"],
            relevance_map=inst["relevance_map"],
            top_k=top_k,
            seed=args.stats_seed,
            n_random_samples=n_random_samples,
            exact_oracle_max_nodes=exact_oracle_max_nodes,
        )
        all_rows.extend(rows)
        dispersion_rows.append(disp)

    method_summary = _aggregate_method_rows(all_rows)
    method_summary_synth = _aggregate_method_rows(all_rows, source_filter="synthetic")
    method_summary_synth_small = _aggregate_method_rows(
        all_rows, source_filter="synthetic_small"
    )
    method_summary_llm = _aggregate_method_rows(
        all_rows, source_filter="llm_cached_scidocs"
    )
    method_summary_proxy = _aggregate_method_rows(
        all_rows, source_filter="proxy_scidocs_prefs"
    )
    paired = []
    # Primary paired tests on synthetic + LLM cached (exclude saturated proxy).
    paired_rows = [
        r
        for r in all_rows
        if r["source"] in {"synthetic", "llm_cached_scidocs", "synthetic_small"}
    ]
    for metric in ("kendall_tau_vs_reference", "ndcg", "bew_vs_original_graph"):
        paired.extend(
            _paired_comparisons(
                paired_rows,
                baseline=args.baseline,
                metric=metric,
                seed=args.stats_seed,
            )
        )
    stratified = _ambiguity_stratified(
        paired_rows,
        baseline=args.baseline,
        focus_methods=[
            "lexicographic_topo",
            "norm_balance_priority_topo_dynamic",
            "balance_priority_topo_dynamic",
            "balance_priority_topo_static",
            "source_sink_peeling",
            "closest_valid_extension_greedy",
            "soft_norm_balance",
            "soft_springrank",
        ],
    )
    sensitivity = _sensitivity_vs_ambiguity(dispersion_rows)

    _write_csv(out_dir / "per_instance_method_metrics.csv", all_rows)
    _write_csv(out_dir / "method_summary.csv", method_summary)
    _write_csv(out_dir / "method_summary_synthetic.csv", method_summary_synth)
    _write_csv(out_dir / "method_summary_synthetic_small.csv", method_summary_synth_small)
    _write_csv(out_dir / "method_summary_llm_cached.csv", method_summary_llm)
    _write_csv(out_dir / "method_summary_proxy_prefs.csv", method_summary_proxy)
    _write_csv(out_dir / "paired_comparisons.csv", paired)
    _write_csv(out_dir / "ambiguity_stratified_deltas.csv", stratified)
    _write_csv(out_dir / "extension_dispersion.csv", dispersion_rows)
    _write_csv(out_dir / "sensitivity_vs_ambiguity.csv", sensitivity)
    _write_json(
        out_dir / "method_catalog.json",
        {
            "hard": method_metadata(),
            "soft_new": soft_method_metadata(),
        },
    )
    _write_json(out_dir / "config.json", config)
    (out_dir / "AUDIT.md").write_text(_audit_markdown())

    # Build report from synthetic for hard-method ranking clarity;
    # append LLM section below.
    report = _build_report(
        out_dir=out_dir,
        config=config,
        method_summary=method_summary_synth if method_summary_synth else method_summary,
        paired=paired,
        stratified=stratified,
        sensitivity=sensitivity,
        audit={},
    )
    # Append LLM slice table.
    if method_summary_llm:
        extra = [
            "",
            "## Appendix: LLM-cached SciDocs slice (primary real-data eval)",
            "",
            "Kendall τ reference is the judgment-free score-sum prior; "
            "nDCG uses qrels.",
            "",
            "| Method | Family | Mean τ | Mean nDCG | Frac valid topo |",
            "|---|---|---:|---:|---:|",
        ]
        for r in sorted(
            method_summary_llm,
            key=lambda x: (-(x["mean_ndcg"] or -1), -(x["mean_kendall_tau"] or -1)),
        ):
            extra.append(
                f"| `{r['method']}` | {r['family']} | "
                f"{r['mean_kendall_tau']:.4f} | {_fmt_ndcg(r['mean_ndcg'])} | "
                f"{r['frac_valid_topo']:.3f} |"
            )
        report = report + "\n".join(extra) + "\n"

    if method_summary_synth_small:
        extra = [
            "",
            "## Appendix: Small synthetic graphs (exact / ILP oracles)",
            "",
            "Used to cross-check greedy closest-extension against enumeration and HiGHS ILP.",
            "",
            "| Method | Family | Mean τ | Mean nDCG | Frac valid topo |",
            "|---|---|---:|---:|---:|",
        ]
        for r in sorted(
            method_summary_synth_small,
            key=lambda x: (-(x["mean_kendall_tau"] or -1), x["method"]),
        ):
            extra.append(
                f"| `{r['method']}` | {r['family']} | "
                f"{r['mean_kendall_tau']:.4f} | {_fmt_ndcg(r['mean_ndcg'])} | "
                f"{r['frac_valid_topo']:.3f} |"
            )
        report = report + "\n".join(extra) + "\n"

    incomplete = [
        "",
        "## 11. What remains incomplete (honest)",
        "",
        "1. **No new LLM API experiments** were launched; real-data evaluation uses "
        "cached OpenAI SciDocs pairwise judgments only.",
        "2. **Proxy SciDocs preferences** make every DAG linear extension achieve "
        "nDCG=1.0 when relevant docs dominate; they are diagnostic for ambiguity "
        "structure, not retrieval ranking differences.",
        "3. **Manuscript text was not edited**; only evidence-backed wording is "
        "proposed above.",
        "4. **SerialRank** transfers cleanly but performs poorly here; treat as a "
        "soft baseline, not a contender.",
        "5. Ambiguity-stratified `highly_ambiguous` counts remain modest on the "
        "synthetic+LLM mix; sensitivity conclusions rely mainly on the continuous "
        "correlation between incomparable-pair fraction and extension τ dispersion.",
        "6. Closest-extension ILP (HiGHS) is implemented and exercised on the small "
        "synthetic slice; very large DAGs still use the greedy deployable method.",
        "",
    ]
    report = report + "\n".join(incomplete)
    (out_dir / "FINAL_REPORT.md").write_text(report)
    (out_dir / "INCOMPLETE.md").write_text("\n".join(incomplete).lstrip() + "\n")

    repro = f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv/bin/activate
PYTHONPATH=src python scripts/run_linear_extension_extraction_experiment.py \\
  --output-dir "$(dirname "$0")" \\
  --n-items {n_items} \\
  --small-n-items {' '.join(str(x) for x in small_n_items)} \\
  --noises {' '.join(str(x) for x in noises)} \\
  --seeds {' '.join(str(x) for x in seeds)} \\
  --top-k {top_k} \\
  --n-random-samples {n_random_samples} \\
  --exact-oracle-max-nodes {exact_oracle_max_nodes} \\
  --max-real-queries {args.max_real_queries} \\
  --max-real-nodes {args.max_real_nodes} \\
  --stats-seed {args.stats_seed} \\
  {"--skip-real" if skip_real else ""} \\
  {"--skip-proxy-prefs" if skip_proxy else ""} \\
  --overwrite
"""
    repro_path = out_dir / "REPRODUCE.sh"
    repro_path.write_text(repro)
    repro_path.chmod(0o755)

    print(f"Wrote report to {out_dir}")
    print(f"Instances: {len(instances)}; method-rows: {len(all_rows)}")
    hard = [r for r in method_summary_synth if r["family"] == "hard_constraint"]
    hard_sorted = sorted(hard, key=lambda r: (-r["mean_kendall_tau"], r["method"]))
    print("Top hard methods on synthetic by mean Kendall τ:")
    for r in hard_sorted[:5]:
        print(f"  {r['method']}: {r['mean_kendall_tau']:.4f}")
    if method_summary_llm:
        hard_llm = [r for r in method_summary_llm if r["family"] == "hard_constraint"]
        hard_llm_sorted = sorted(
            hard_llm, key=lambda r: (-(r["mean_ndcg"] or -1), r["method"])
        )
        print("Top hard methods on LLM-cached SciDocs by mean nDCG:")
        for r in hard_llm_sorted[:5]:
            print(
                f"  {r['method']}: ndcg={r['mean_ndcg']:.4f} "
                f"tau={r['mean_kendall_tau']:.4f}"
            )


if __name__ == "__main__":
    main()
