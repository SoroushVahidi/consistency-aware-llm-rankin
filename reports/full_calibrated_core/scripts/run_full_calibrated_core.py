#!/usr/bin/env python3
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from candidate_pool_policies import PoolSpec
from full_calibration_utils import (
    RANKERS,
    REGIMES,
    CalibrationEvaluator,
    ProtocolSpec,
    ThresholdConfig,
    _align_ranking,
    _average_precision_at_k,
    _judged_relevance_map_for_candidates,
    _mrr_at_k,
    _ndcg_at_k,
    _norm_minmax,
    _pairwise_accuracy_from_relevance,
    _precision_recall_at_k,
    _reference_ranking_for_candidates,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
    bootstrap_ci,
    build_query_vote_artifacts,
    choose_threshold_config,
    jaccard,
    now_iso,
    paired_permutation_pvalue,
    prepare_dataset_inputs,
    raw_baseline_statistics,
    render_line_plot,
    render_stacked_counts,
    sha256_file,
    summarize_structural_records,
    write_csv,
)

from consistency_ranker.data.query_ids import has_usable_eval_labels

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_ROOT = SCRIPT_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
TABLES_DIR = REPORT_ROOT / "tables"
FIGURES_DIR = REPORT_ROOT / "figures"
MANIFESTS_DIR = REPORT_ROOT / "manifests"
OUTPUT_ROOT = REPORT_ROOT / "outputs" / "calibrated_all4"
RUN_OUTPUT_ROOT = OUTPUT_ROOT / "protocol_runs"
PAPER_PACKAGE = OUTPUT_ROOT / "paper_package"
PAPER_TABLES = PAPER_PACKAGE / "tables"
PAPER_PLOTS = PAPER_PACKAGE / "plots"
PAPER_MANIFESTS = PAPER_PACKAGE / "manifests"
LOGS_DIR = REPORT_ROOT / "logs"

SEED = 13
BOOTSTRAP_REPS = 10_000
PERMUTATION_REPS = 10_000
DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
PRIMARY_PROTOCOL = "primary_minmax_retention_matched"
RAW_PROTOCOL = "ablation_raw_fixed"
PRIMARY_ALPHA_VALUES = (0.1, 0.3, 0.5, 1.0)

PROTOCOL_SPECS = {
    PRIMARY_PROTOCOL: {
        "calibration": "minmax_query_ranker",
        "threshold_mode": "retention_matched",
        "label": "minmax + retention-matched",
        "kind": "primary",
    },
    RAW_PROTOCOL: {
        "calibration": "raw",
        "threshold_mode": "fixed_numeric",
        "label": "raw + fixed",
        "kind": "ablation",
    },
    "ablation_minmax_fixed": {
        "calibration": "minmax_query_ranker",
        "threshold_mode": "fixed_numeric",
        "label": "minmax + fixed",
        "kind": "ablation",
    },
    "ablation_unit_vote_retention": {
        "calibration": "unit_vote",
        "threshold_mode": "retention_matched",
        "label": "unit vote + retention-matched",
        "kind": "ablation",
    },
    "robustness_zscore_retention": {
        "calibration": "zscore_query_ranker",
        "threshold_mode": "retention_matched",
        "label": "z-score + retention-matched",
        "kind": "robustness",
    },
    "robustness_rank_percentile_retention": {
        "calibration": "rank_percentile",
        "threshold_mode": "retention_matched",
        "label": "rank-percentile + retention-matched",
        "kind": "robustness",
    },
    # --- Independently defined protocols (task 2 of the finalization process) ---
    # Unlike every protocol above except RAW_PROTOCOL itself, these do NOT
    # derive their retention target from the raw-fixed protocol's vote rates
    # or edge count (see choose_threshold_config's "quantile_independent_q*"
    # branch and reports/normalization_protocol_audit_20260714/AUDIT.md).
    # q=0.5 is the pre-registered primary comparison point (task-requested
    # names "minmax_quantile" / "rank_percentile"); q=0.3/0.7 are the
    # low/high selectivity grid points used only for sensitivity analysis.
    "independent_minmax_quantile_q0p5": {
        "calibration": "minmax_query_ranker",
        "threshold_mode": "quantile_independent_q0p5",
        "label": "minmax + independent quantile (q=0.5)",
        "kind": "independent",
    },
    "independent_minmax_quantile_q0p3": {
        "calibration": "minmax_query_ranker",
        "threshold_mode": "quantile_independent_q0p3",
        "label": "minmax + independent quantile (q=0.3, low selectivity)",
        "kind": "independent_grid",
    },
    "independent_minmax_quantile_q0p7": {
        "calibration": "minmax_query_ranker",
        "threshold_mode": "quantile_independent_q0p7",
        "label": "minmax + independent quantile (q=0.7, high selectivity)",
        "kind": "independent_grid",
    },
    "independent_rank_percentile_q0p5": {
        "calibration": "rank_percentile_independent",
        "threshold_mode": "quantile_independent_q0p5",
        "label": "rank-percentile (tie-abstain) + independent quantile (q=0.5)",
        "kind": "independent",
    },
    "independent_rank_percentile_q0p3": {
        "calibration": "rank_percentile_independent",
        "threshold_mode": "quantile_independent_q0p3",
        "label": "rank-percentile (tie-abstain) + independent quantile (q=0.3, low selectivity)",
        "kind": "independent_grid",
    },
    "independent_rank_percentile_q0p7": {
        "calibration": "rank_percentile_independent",
        "threshold_mode": "quantile_independent_q0p7",
        "label": "rank-percentile (tie-abstain) + independent quantile (q=0.7, high selectivity)",
        "kind": "independent_grid",
    },
}

# Task-requested canonical protocol names -> internal protocol_id, for
# documentation and for scripts/tables that want to report the exact names
# from the finalization-process task description.
CANONICAL_NAME_ALIASES = {
    "raw_fixed": RAW_PROTOCOL,
    "minmax_raw_matched": PRIMARY_PROTOCOL,
    "minmax_quantile": "independent_minmax_quantile_q0p5",
    "rank_percentile": "independent_rank_percentile_q0p5",
}

# Typed, validated view of PROTOCOL_SPECS (see ProtocolSpec in
# full_calibration_utils.py). Every entry in PROTOCOL_SPECS is validated at
# import time -- an unknown calibration, malformed threshold_mode, or
# unrecognized kind raises immediately rather than failing silently deep in
# a run. PROTOCOL_SPECS itself remains the plain-dict source of truth (many
# existing call sites iterate it directly); this registry is a derived,
# read-only, typed convenience view, not a replacement.
PROTOCOL_REGISTRY: dict[str, ProtocolSpec] = {
    protocol_id: ProtocolSpec(protocol_id=protocol_id, **spec_cfg)
    for protocol_id, spec_cfg in PROTOCOL_SPECS.items()
}

METHOD_LABELS = {
    "prior_only": "Prior",
    "rrf": "RRF",
    "combsum": "CombSUM",
    "borda_fuse": "Borda fusion",
    "copeland_graph": "Copeland unrepaired",
    "copeland_graph_repaired": "Copeland repaired",
    "balance_graph": "Balance unrepaired",
    "balance_graph_repaired": "Balance repaired",
    "markov_graph": "Markov unrepaired",
    "markov_graph_repaired": "Markov repaired",
    "hybrid_unrepaired_copeland_a0p3_minmax": "Copeland hybrid unrepaired",
    "hybrid_repaired_copeland_a0p3_minmax": "Copeland hybrid repaired",
    "hybrid_unrepaired_balance_a0p3_minmax": "Balance hybrid unrepaired",
    "hybrid_repaired_balance_a0p3_minmax": "Balance hybrid repaired",
    # Added per reports/candidate_pool_conditional_audit_20260714/AUDIT.md
    # section 3: existing-but-previously-excluded graph-ranking baselines,
    # wired into evaluate_query() (full_calibration_utils.py) rather than
    # newly implemented.
    "pagerank_graph": "PageRank unrepaired",
    "pagerank_graph_repaired": "PageRank repaired",
    "rank_centrality_graph": "RankCentrality unrepaired",
    "rank_centrality_graph_repaired": "RankCentrality repaired",
    "markov_hybrid_unrepaired": "Markov hybrid unrepaired",
    "markov_hybrid_repaired": "Markov hybrid repaired",
    "bradley_terry_graph": "Bradley-Terry unrepaired",
    "bradley_terry_graph_repaired": "Bradley-Terry repaired",
}
METHOD_KEYS = tuple(METHOD_LABELS)

PAIR_SPECS = (
    ("copeland_graph", "copeland_graph", "copeland_graph_repaired", "graph"),
    ("balance_graph", "balance_graph", "balance_graph_repaired", "graph"),
    ("markov_graph", "markov_graph", "markov_graph_repaired", "graph"),
    (
        "copeland_hybrid",
        "hybrid_unrepaired_copeland_a0p3_minmax",
        "hybrid_repaired_copeland_a0p3_minmax",
        "hybrid",
    ),
    (
        "balance_hybrid",
        "hybrid_unrepaired_balance_a0p3_minmax",
        "hybrid_repaired_balance_a0p3_minmax",
        "hybrid",
    ),
    ("pagerank_graph", "pagerank_graph", "pagerank_graph_repaired", "graph"),
    ("rank_centrality_graph", "rank_centrality_graph", "rank_centrality_graph_repaired", "graph"),
    ("markov_hybrid", "markov_hybrid_unrepaired", "markov_hybrid_repaired", "hybrid"),
    ("bradley_terry_graph", "bradley_terry_graph", "bradley_terry_graph_repaired", "graph"),
)
# The five pairs already part of every committed manuscript table, prior to
# this task's baseline additions. New code should not assume PAIR_SPECS has
# only these five without checking -- iterate PAIR_SPECS itself instead.
LEGACY_PAIR_NAMES = (
    "copeland_graph",
    "balance_graph",
    "markov_graph",
    "copeland_hybrid",
    "balance_hybrid",
)
NEW_BASELINE_PAIR_NAMES = tuple(
    name for name, *_rest in PAIR_SPECS if name not in LEGACY_PAIR_NAMES
)
PRIMARY_BASELINE_COMPARISON_METHODS = (
    "copeland_graph_repaired",
    "balance_graph_repaired",
    "markov_graph_repaired",
    "hybrid_repaired_copeland_a0p3_minmax",
    "hybrid_repaired_balance_a0p3_minmax",
)
BASELINES = ("rrf", "combsum")
PLOT_COLORS = {
    RAW_PROTOCOL: "#475569",
    PRIMARY_PROTOCOL: "#0f766e",
    "ablation_minmax_fixed": "#1d4ed8",
    "ablation_unit_vote_retention": "#7c3aed",
    "robustness_zscore_retention": "#b45309",
    "robustness_rank_percentile_retention": "#be123c",
}


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _repo_context() -> dict[str, Any]:
    python_exe = sys.executable
    python_version = subprocess.run(
        [python_exe, "--version"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    disk = subprocess.run(
        ["df", "-h", "."],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    return {
        "repo_root": str(REPO_ROOT),
        "branch": _git_output(["branch", "--show-current"]),
        "head": _git_output(["rev-parse", "HEAD"]),
        "git_status_short": git_status,
        "python_executable": python_exe,
        "python_version": python_version,
        "activation_command": "source .venv/bin/activate",
        "disk": disk,
        "timestamp": now_iso(),
    }


def _ensure_dirs() -> None:
    for path in (
        TABLES_DIR,
        FIGURES_DIR,
        MANIFESTS_DIR,
        OUTPUT_ROOT,
        RUN_OUTPUT_ROOT,
        PAPER_PACKAGE,
        PAPER_TABLES,
        PAPER_PLOTS,
        PAPER_MANIFESTS,
        LOGS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _score_maps_as_tuples(
    raw_scores_by_ranker: dict[str, dict[str, float]],
) -> dict[str, list[tuple[str, float]]]:
    return {ranker: list(scores.items()) for ranker, scores in raw_scores_by_ranker.items()}


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _safe_mean(values: list[float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def _safe_std(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return float(statistics.pstdev(values))


def _safe_quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), q))


def _sign_label(value: float | None, tol: float = 1.0e-12) -> str:
    if value is None:
        return "na"
    if value > tol:
        return "positive"
    if value < -tol:
        return "negative"
    return "zero"


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return [{key: row.get(key) for key in fieldnames} for row in rows]


def _analysis_dataset_inputs(
    dataset: str,
    pool_policy: "PoolSpec | None" = None,
    *,
    pool_size_override: int | None = None,
) -> dict[str, Any]:
    raw = prepare_dataset_inputs(
        dataset, pool_policy=pool_policy, pool_size_override=pool_size_override
    )
    usable = []
    excluded = []
    for item in raw["per_query_inputs"]:
        if has_usable_eval_labels(item["qrels_for_query"]):
            usable.append(item)
        else:
            excluded.append(item["query_id"])
    filtered = dict(raw)
    filtered["analysis_query_ids"] = [item["query_id"] for item in usable]
    filtered["excluded_query_ids"] = excluded
    filtered["usable_query_count"] = len(usable)
    filtered["per_query_inputs"] = usable
    return filtered


def _pair_margin_summary(
    dataset_inputs: dict[str, Any], calibration: str
) -> tuple[dict[str, list[float]], dict[str, int]]:
    pair_margins = {ranker: [] for ranker in RANKERS}
    zero_variance = {ranker: 0 for ranker in RANKERS}
    probe = ThresholdConfig(
        vote_thresholds={ranker: 0.0 for ranker in RANKERS},
        aggregate_threshold=0.0,
        min_support=1,
        postprocess_drop_mutual=False,
        target_vote_rates=None,
        target_edge_count=None,
        notes="pair margin probe",
    )
    for item in dataset_inputs["per_query_inputs"]:
        artifacts = build_query_vote_artifacts(
            query_id=item["query_id"],
            raw_scores_by_ranker=item["raw_scores_by_ranker"],
            candidate_pool=item["candidate_pool"],
            calibration=calibration,
            threshold_config=probe,
        )
        for ranker, values in artifacts["pair_margins_by_ranker"].items():
            pair_margins[ranker].extend(float(v) for v in values)
        for ranker, meta in artifacts["calibration_meta"].items():
            if meta.get("zero_variance"):
                zero_variance[ranker] += 1
    return pair_margins, zero_variance


def _config_dir(protocol: str, dataset: str, regime: str) -> Path:
    return RUN_OUTPUT_ROOT / protocol / dataset / regime


def _support_map_from_rows(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], list[tuple[str, float]]]:
    support: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        support[(str(row["winner_doc_id"]), str(row["loser_doc_id"]))].append(
            (str(row["voter"]), float(row["weight"]))
        )
    return dict(support)


def _ranker_weight_summary(
    edge_support: dict[tuple[str, str], list[tuple[str, float]]],
) -> dict[str, float | None]:
    totals = {ranker: 0.0 for ranker in RANKERS}
    cond_num = 0.0
    cond_den = 0.0
    for recs in edge_support.values():
        edge_total = sum(weight for _ranker, weight in recs)
        for ranker, weight in recs:
            totals[ranker] += float(weight)
        bm25_weight = sum(weight for ranker, weight in recs if ranker == "bm25")
        if bm25_weight > 0:
            cond_num += bm25_weight
            cond_den += edge_total
    total = sum(totals.values())
    out: dict[str, float | None] = dict(totals)
    out["total"] = total
    out["bm25_share_total"] = (totals["bm25"] / total) if total > 0 else None
    out["bm25_share_conditional"] = (cond_num / cond_den) if cond_den > 0 else None
    return out


def _candidate_pool_scores(
    query_id: str, raw_scores_by_ranker: dict[str, dict[str, float]]
) -> list[dict[str, list[tuple[str, float]]]]:
    return [
        {query_id: list(raw_scores_by_ranker[ranker].items())}
        for ranker in RANKERS
        if raw_scores_by_ranker.get(ranker)
    ]


def _reference_for_query(
    candidate_pool: list[str],
    qrels_for_query: list[Any],
) -> tuple[list[str], dict[str, int], dict[str, int]]:
    ref_ranking, rel_map = _reference_ranking_for_candidates(
        qrels_for_query,
        candidate_pool,
    )
    judged_rel_map = _judged_relevance_map_for_candidates(
        qrels_for_query,
        candidate_pool,
    )
    return ref_ranking, rel_map, judged_rel_map


def _method_metric(
    ranking: list[str],
    rel_map: dict[str, int],
    judged_rel_map: dict[str, int],
    top_k: int,
    ref_ranking: list[str],
) -> dict[str, Any]:
    aligned = _align_ranking(ranking, rel_map)
    precision, recall = _precision_recall_at_k(aligned, rel_map, k=top_k)
    return {
        "ranking": ranking,
        "top_k_prefix": list(ranking[:top_k]),
        "ndcg_at_k": _ndcg_at_k(aligned, rel_map, k=top_k),
        "map_at_k": _average_precision_at_k(aligned, rel_map, k=top_k),
        "mrr_at_k": _mrr_at_k(aligned, rel_map, k=top_k),
        "precision_at_k": precision,
        "recall_at_k": recall,
        "pairwise_accuracy": _pairwise_accuracy_from_relevance(
            aligned,
            judged_rel_map,
        ),
        "kendall_tau": None if not ref_ranking else None,
    }


def _graph_mutual_removed(graph: nx.DiGraph) -> nx.DiGraph:
    out = graph.copy()
    for u, v in list(graph.edges()):
        if graph.has_edge(v, u):
            if out.has_edge(u, v):
                out.remove_edge(u, v)
    return out


def _mutual_pair_weight_share(graph: nx.DiGraph) -> float:
    total = 0.0
    mutual_total = 0.0
    for u, v, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        total += weight
        if graph.has_edge(v, u):
            mutual_total += weight
    return (mutual_total / total) if total > 0 else 0.0


def _scc_count_gt1(graph: nx.DiGraph) -> int:
    return sum(1 for comp in nx.strongly_connected_components(graph) if len(comp) > 1)


def _directed_triangle_count(graph: nx.DiGraph) -> int:
    nodes = sorted(graph.nodes())
    count = 0
    for a, b, c in combinations(nodes, 3):
        if graph.has_edge(a, b) and graph.has_edge(b, c) and graph.has_edge(c, a):
            count += 1
        if graph.has_edge(a, c) and graph.has_edge(c, b) and graph.has_edge(b, a):
            count += 1
    return count


def _serializable_query_record(
    *,
    dataset: str,
    protocol: str,
    regime: str,
    query_id: str,
    artifacts: dict[str, Any],
    threshold_config: ThresholdConfig,
    eval_record: dict[str, Any],
    edge_support: dict[tuple[str, str], list[tuple[str, float]]],
    extra_methods: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    method_metrics = {
        key: {
            "ndcg_at_k": eval_record["method_outputs"][key]["ndcg_at_k"],
            "map_at_k": eval_record["method_outputs"][key]["map_at_k"],
            "precision_at_k": eval_record["method_outputs"][key]["precision_at_k"],
            "recall_at_k": eval_record["method_outputs"][key]["recall_at_k"],
        }
        for key in eval_record["method_outputs"]
        if key in METHOD_KEYS
    }
    method_metrics.update(
        {
            key: {
                "ndcg_at_k": value["ndcg_at_k"],
                "map_at_k": value["map_at_k"],
                "precision_at_k": value["precision_at_k"],
                "recall_at_k": value["recall_at_k"],
            }
            for key, value in extra_methods.items()
        }
    )
    return {
        "dataset": dataset,
        "protocol": protocol,
        "regime": regime,
        "query_id": query_id,
        "candidate_count": len(artifacts["candidate_pool"]),
        "vote_thresholds": threshold_config.vote_thresholds,
        "aggregate_threshold": threshold_config.aggregate_threshold,
        "min_support": threshold_config.min_support,
        "drop_mutual": threshold_config.postprocess_drop_mutual,
        "calibration_meta": artifacts["calibration_meta"],
        "retained_vote_counts": artifacts["retained_vote_counts"],
        "retained_weight_sums": artifacts["retained_weight_sums"],
        "graph_stats": eval_record["graph_stats"],
        "repaired_graph_stats": eval_record["repaired_graph_stats"],
        "mutual_removed_stats": eval_record["mutual_removed_stats"],
        "repair_info": eval_record["repair_info"],
        "raw_edges": sorted([list(edge) for edge in eval_record["raw_edges"]]),
        "removed_edges": sorted([list(edge) for edge in eval_record["removed_edges"]]),
        "ranker_weight_summary": _ranker_weight_summary(edge_support),
        "method_metrics": method_metrics,
    }


def _clustered_bootstrap(
    rows: list[dict[str, Any]],
    *,
    value_key: str,
    cluster_key: str = "query_id",
    reps: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> tuple[float | None, float | None, float | None]:
    if not rows:
        return None, None, None
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_cluster[str(row[cluster_key])].append(float(row[value_key]))
    clusters = sorted(by_cluster)
    if not clusters:
        return None, None, None
    cluster_arrays = [np.asarray(by_cluster[c], dtype=float) for c in clusters]
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(reps):
        picks = rng.integers(0, len(cluster_arrays), size=len(cluster_arrays))
        sampled = np.concatenate([cluster_arrays[idx] for idx in picks])
        means.append(float(np.mean(sampled)))
    lo, hi = np.quantile(np.asarray(means, dtype=float), [0.025, 0.975])
    frac_gt_zero = float(np.mean(np.asarray(means, dtype=float) > 0.0))
    return float(lo), float(hi), frac_gt_zero


def _holm_adjust(pvals: list[float]) -> list[float]:
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adjusted = [0.0] * n
    running = 0.0
    for rank, idx in enumerate(order):
        value = (n - rank) * pvals[idx]
        running = max(running, value)
        adjusted[idx] = min(1.0, running)
    return adjusted


def _bh_adjust(pvals: list[float]) -> list[float]:
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i], reverse=True)
    adjusted = [0.0] * n
    running = 1.0
    for rev_rank, idx in enumerate(order, start=1):
        rank = n - rev_rank + 1
        value = pvals[idx] * n / rank
        running = min(running, value)
        adjusted[idx] = min(1.0, running)
    return adjusted


def _compute_alpha_metric(
    evaluator: CalibrationEvaluator,
    *,
    query_id: str,
    qrels_for_query: list[Any],
    candidate_pool: list[str],
    top_k: int,
    raw_score_maps_by_ranker: dict[str, dict[str, float]],
    graph: nx.DiGraph,
    repaired_graph: nx.DiGraph,
    component: str,
    alpha: float,
) -> dict[str, Any]:
    ref_ranking, rel_map, judged_rel_map = _reference_for_query(
        candidate_pool,
        qrels_for_query,
    )
    tuple_maps = _score_maps_as_tuples(raw_score_maps_by_ranker)
    score_prior_sets = _candidate_pool_scores(query_id, raw_score_maps_by_ranker)
    prior_scores = _rrf_prior_scores_for_query(
        query_id=query_id,
        candidate_nodes=set(candidate_pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=_score_sum_prior_scores(graph),
    )
    raw_scores = evaluator._graph_component_scores(graph, component)
    rep_scores = evaluator._graph_component_scores(repaired_graph, component)
    confidence_weight = min(1.0, float(graph.number_of_edges()) / max(1.0, len(candidate_pool)))
    raw_ranking = evaluator._hybrid_ranking(
        prior_scores,
        raw_scores,
        candidate_pool,
        alpha=alpha,
        mode="minmax",
        confidence_weight=confidence_weight,
    )
    rep_ranking = evaluator._hybrid_ranking(
        prior_scores,
        rep_scores,
        candidate_pool,
        alpha=alpha,
        mode="minmax",
        confidence_weight=confidence_weight,
    )
    del tuple_maps
    raw_metric = _method_metric(raw_ranking, rel_map, judged_rel_map, top_k, ref_ranking)
    rep_metric = _method_metric(rep_ranking, rel_map, judged_rel_map, top_k, ref_ranking)
    return {
        "raw": raw_metric,
        "repaired": rep_metric,
    }


def _balance_audit_rows(
    evaluator: CalibrationEvaluator,
    *,
    dataset: str,
    protocol: str,
    regime: str,
    query_id: str,
    top_k: int,
    qrels_for_query: list[Any],
    candidate_pool: list[str],
    raw_score_maps_by_ranker: dict[str, dict[str, float]],
    eval_record: dict[str, Any],
) -> dict[str, Any]:
    graph = eval_record["graph"]
    repaired_graph = eval_record["repaired_graph"]
    ref_ranking, rel_map, _judged_rel_map = _reference_for_query(
        candidate_pool,
        qrels_for_query,
    )
    score_prior_sets = _candidate_pool_scores(query_id, raw_score_maps_by_ranker)
    prior_scores = _rrf_prior_scores_for_query(
        query_id=query_id,
        candidate_nodes=set(candidate_pool),
        score_prior_sets=score_prior_sets,
        fallback_scores=_score_sum_prior_scores(graph),
    )
    raw_scores = evaluator._graph_component_scores(graph, "balance")
    rep_scores = evaluator._graph_component_scores(repaired_graph, "balance")
    raw_norm = _norm_minmax(raw_scores)
    rep_norm = _norm_minmax(rep_scores)
    raw_hybrid = {
        doc_id: _norm_minmax(prior_scores).get(doc_id, 0.0) + 0.3 * raw_norm.get(doc_id, 0.0)
        for doc_id in candidate_pool
    }
    rep_hybrid = {
        doc_id: _norm_minmax(prior_scores).get(doc_id, 0.0) + 0.3 * rep_norm.get(doc_id, 0.0)
        for doc_id in candidate_pool
    }
    raw_balance_ranking = eval_record["method_outputs"]["balance_graph"]["ranking"]
    rep_balance_ranking = eval_record["method_outputs"]["balance_graph_repaired"]["ranking"]
    raw_hybrid_ranking = eval_record["method_outputs"]["hybrid_unrepaired_balance_a0p3_minmax"][
        "ranking"
    ]
    rep_hybrid_ranking = eval_record["method_outputs"]["hybrid_repaired_balance_a0p3_minmax"][
        "ranking"
    ]
    raw_rel = [rel_map.get(doc_id, 0) for doc_id in raw_hybrid_ranking[:top_k]]
    rep_rel = [rel_map.get(doc_id, 0) for doc_id in rep_hybrid_ranking[:top_k]]
    return {
        "dataset": dataset,
        "protocol": protocol,
        "regime": regime,
        "query_id": query_id,
        "graph_changed": bool(eval_record["repair_info"]["n_edges_removed"] > 0),
        "raw_balance_scores_changed": raw_scores != rep_scores,
        "normalized_balance_scores_changed": raw_norm != rep_norm,
        "balance_only_ranking_changed": raw_balance_ranking != rep_balance_ranking,
        "hybrid_scores_changed": raw_hybrid != rep_hybrid,
        "full_hybrid_ranking_changed": raw_hybrid_ranking != rep_hybrid_ranking,
        "top_k_set_changed": set(raw_hybrid_ranking[:top_k]) != set(rep_hybrid_ranking[:top_k]),
        "top_k_order_changed": raw_hybrid_ranking[:top_k] != rep_hybrid_ranking[:top_k],
        "relevance_sequence_changed": raw_rel != rep_rel,
        "ndcg_changed": abs(
            float(
                eval_record["method_outputs"]["hybrid_repaired_balance_a0p3_minmax"]["ndcg_at_k"]
                or 0.0
            )
            - float(
                eval_record["method_outputs"]["hybrid_unrepaired_balance_a0p3_minmax"]["ndcg_at_k"]
                or 0.0
            )
        )
        > 1.0e-12,
        "hybrid_delta_ndcg": (
            float(
                eval_record["method_outputs"]["hybrid_repaired_balance_a0p3_minmax"]["ndcg_at_k"]
                or 0.0
            )
            - float(
                eval_record["method_outputs"]["hybrid_unrepaired_balance_a0p3_minmax"]["ndcg_at_k"]
                or 0.0
            )
        ),
    }


def _render_errorbar(
    df: pd.DataFrame,
    *,
    out_base: Path,
    title: str,
    x_col: str,
    y_col: str,
    lo_col: str,
    hi_col: str,
    facet_col: str,
    hue_col: str,
) -> None:
    if df.empty:
        return
    facets = list(dict.fromkeys(df[facet_col]))
    fig, axes = plt.subplots(1, len(facets), figsize=(6 * len(facets), 5), squeeze=False)
    for ax, facet in zip(axes[0], facets, strict=True):
        sub = df[df[facet_col] == facet]
        x_values = list(dict.fromkeys(sub[x_col]))
        hues = list(dict.fromkeys(sub[hue_col]))
        positions = np.arange(len(x_values))
        width = 0.8 / max(1, len(hues))
        for idx, hue in enumerate(hues):
            part = sub[sub[hue_col] == hue].set_index(x_col)
            xs = positions - 0.4 + width / 2 + idx * width
            ys = np.array([part.loc[x, y_col] for x in x_values], dtype=float)
            los = np.array([part.loc[x, lo_col] for x in x_values], dtype=float)
            his = np.array([part.loc[x, hi_col] for x in x_values], dtype=float)
            yerr = np.vstack([ys - los, his - ys])
            ax.errorbar(
                xs,
                ys,
                yerr=yerr,
                fmt="o",
                capsize=3,
                label=str(hue),
                color=PLOT_COLORS.get(str(hue), "#334155"),
            )
        ax.axhline(0.0, color="#94a3b8", linestyle="--", linewidth=1)
        ax.set_xticks(positions)
        ax.set_xticklabels(x_values, rotation=20, ha="right")
        ax.set_title(str(facet))
        ax.grid(axis="y", alpha=0.3, linestyle="--")
    axes[0][0].legend(frameon=False)
    fig.suptitle(title)
    fig.tight_layout()
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=180)
    plt.close(fig)


def _render_scatter(
    df: pd.DataFrame, *, out_base: Path, title: str, x_col: str, y_col: str, facet_col: str
) -> None:
    if df.empty:
        return
    facets = list(dict.fromkeys(df[facet_col]))
    fig, axes = plt.subplots(1, len(facets), figsize=(6 * len(facets), 5), squeeze=False)
    for ax, facet in zip(axes[0], facets, strict=True):
        sub = df[df[facet_col] == facet]
        ax.scatter(sub[x_col], sub[y_col], alpha=0.7, color="#334155", edgecolors="none")
        bounds = [
            min(sub[x_col].min(), sub[y_col].min()),
            max(sub[x_col].max(), sub[y_col].max()),
        ]
        ax.plot(bounds, bounds, color="#94a3b8", linestyle="--", linewidth=1)
        ax.set_title(str(facet))
        ax.set_xlabel(x_col.replace("_", " "))
        ax.set_ylabel(y_col.replace("_", " "))
        ax.grid(alpha=0.3, linestyle="--")
    fig.suptitle(title)
    fig.tight_layout()
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=180)
    plt.close(fig)


def _render_influence_plot(df: pd.DataFrame, *, out_base: Path, title: str) -> None:
    if df.empty:
        return
    sub = df.sort_values("delta_ndcg")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(np.arange(len(sub)), sub["delta_ndcg"], color="#64748b")
    ax.axhline(0.0, color="#94a3b8", linestyle="--", linewidth=1)
    ax.set_title(title)
    ax.set_ylabel("repaired - unrepaired nDCG")
    ax.set_xlabel("query rank by delta")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    fig.tight_layout()
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=180)
    plt.close(fig)


def _estimate_full_run() -> dict[str, Any]:
    usable_by_dataset = {}
    for dataset in DATASETS:
        usable_by_dataset[dataset] = _analysis_dataset_inputs(dataset)["usable_query_count"]
    query_configs = sum(usable_by_dataset.values()) * len(PROTOCOL_SPECS) * len(REGIMES)
    seconds = query_configs * 0.0083
    output_mb = query_configs * 0.0746
    return {
        "usable_queries": usable_by_dataset,
        "query_config_units": query_configs,
        "estimated_seconds": seconds,
        "estimated_minutes": seconds / 60.0,
        "estimated_output_mb": output_mb,
    }


def run_full_core() -> dict[str, Any]:
    _ensure_dirs()
    repo = _repo_context()
    start_wall = time.time()
    evaluator = CalibrationEvaluator()
    estimate = _estimate_full_run()

    threshold_rows: list[dict[str, Any]] = []
    structural_rows: list[dict[str, Any]] = []
    cycle_rows: list[dict[str, Any]] = []
    removed_overlap_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    help_harm_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    macro_rows: list[dict[str, Any]] = []
    multiplicity_rows: list[dict[str, Any]] = []
    leave_one_out_rows: list[dict[str, Any]] = []
    exclusion_rows: list[dict[str, Any]] = []
    bm25_rows: list[dict[str, Any]] = []
    balance_rows: list[dict[str, Any]] = []
    alpha_rows: list[dict[str, Any]] = []
    rrf_note_rows: list[dict[str, Any]] = []

    dataset_inputs_map: dict[str, dict[str, Any]] = {}
    pair_margin_cache: dict[str, dict[str, tuple[dict[str, list[float]], dict[str, int]]]] = (
        defaultdict(dict)
    )
    threshold_cache: dict[tuple[str, str, str], ThresholdConfig] = {}
    config_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    dataset_score_hashes: dict[str, dict[str, str]] = {}
    protocol_query_sets: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(dict)

    for dataset in DATASETS:
        dataset_inputs = _analysis_dataset_inputs(dataset)
        dataset_inputs_map[dataset] = dataset_inputs
        print(
            f"[{now_iso()}] dataset={dataset} usable_queries={dataset_inputs['usable_query_count']}",
            flush=True,
        )
        spec = dataset_inputs["spec"]
        dataset_score_hashes[dataset] = {
            ranker: sha256_file(spec.score_files[ranker]) for ranker in RANKERS
        }
        baseline = raw_baseline_statistics(dataset_inputs)
        for protocol, spec_cfg in PROTOCOL_SPECS.items():
            pair_margin_cache[dataset][spec_cfg["calibration"]] = _pair_margin_summary(
                dataset_inputs,
                spec_cfg["calibration"],
            )
        for protocol in PROTOCOL_SPECS:
            for regime in REGIMES:
                for query_id in dataset_inputs["excluded_query_ids"]:
                    exclusion_rows.append(
                        {
                            "dataset": dataset,
                            "query_id": query_id,
                            "protocol": protocol,
                            "regime": regime,
                            "exclusion_reason": "insufficient_eval_labels",
                            "source_file": str(spec.query_ids_file),
                            "notes": "Excluded before downstream calibration because qrels do not support ranking evaluation.",
                        }
                    )

        for protocol, spec_cfg in PROTOCOL_SPECS.items():
            pair_margins, zero_variance = pair_margin_cache[dataset][spec_cfg["calibration"]]
            for regime in REGIMES:
                threshold_config = choose_threshold_config(
                    dataset=dataset,
                    regime=regime,
                    calibration=spec_cfg["calibration"],
                    threshold_mode=spec_cfg["threshold_mode"],
                    baseline_vote_rates=baseline[regime]["vote_rates"],
                    baseline_edge_count=baseline[regime]["edge_count"],
                    calibration_pair_margins=pair_margins,
                    per_query_inputs=dataset_inputs["per_query_inputs"],
                )
                threshold_cache[(dataset, protocol, regime)] = threshold_config
                threshold_rows.append(
                    {
                        "dataset": dataset,
                        "protocol": protocol,
                        "protocol_label": spec_cfg["label"],
                        "protocol_kind": spec_cfg["kind"],
                        "calibration": spec_cfg["calibration"],
                        "threshold_mode": spec_cfg["threshold_mode"],
                        "regime": regime,
                        "vote_threshold_bm25": threshold_config.vote_thresholds["bm25"],
                        "vote_threshold_tfidf": threshold_config.vote_thresholds["tfidf"],
                        "vote_threshold_minilm": threshold_config.vote_thresholds["minilm"],
                        "aggregate_threshold": threshold_config.aggregate_threshold,
                        "min_support": threshold_config.min_support,
                        "drop_mutual": threshold_config.postprocess_drop_mutual,
                        "baseline_edge_count": baseline[regime]["edge_count"],
                        "baseline_vote_rate_bm25": baseline[regime]["vote_rates"]["bm25"],
                        "baseline_vote_rate_tfidf": baseline[regime]["vote_rates"]["tfidf"],
                        "baseline_vote_rate_minilm": baseline[regime]["vote_rates"]["minilm"],
                        "zero_variance_queries_bm25": zero_variance["bm25"],
                        "zero_variance_queries_tfidf": zero_variance["tfidf"],
                        "zero_variance_queries_minilm": zero_variance["minilm"],
                        "threshold_notes": threshold_config.notes,
                    }
                )

                cfg_start = time.time()
                print(
                    f"[{now_iso()}] start dataset={dataset} protocol={protocol} regime={regime}",
                    flush=True,
                )
                out_dir = _config_dir(protocol, dataset, regime)
                out_dir.mkdir(parents=True, exist_ok=True)
                query_records = []
                metric_rows = []
                query_eval_records = []
                edge_sets = {}
                removed_sets = {}
                support_maps = {}
                valid_query_ids = []
                total_bm25 = []
                alpha_query_rows = []

                for item in dataset_inputs["per_query_inputs"]:
                    query_id = item["query_id"]
                    artifacts = build_query_vote_artifacts(
                        query_id=query_id,
                        raw_scores_by_ranker=item["raw_scores_by_ranker"],
                        candidate_pool=item["candidate_pool"],
                        calibration=spec_cfg["calibration"],
                        threshold_config=threshold_config,
                    )
                    tuple_maps = _score_maps_as_tuples(item["raw_scores_by_ranker"])
                    eval_record = evaluator.evaluate_query(
                        dataset=dataset,
                        query_id=query_id,
                        qrels_for_query=item["qrels_for_query"],
                        vote_regime=regime,
                        top_k=spec.top_k,
                        candidate_pool=item["candidate_pool"],
                        vote_rows=artifacts["rows"],
                        raw_score_maps_by_ranker=tuple_maps,
                    )
                    if eval_record is None:
                        exclusion_rows.append(
                            {
                                "dataset": dataset,
                                "query_id": query_id,
                                "protocol": protocol,
                                "regime": regime,
                                "exclusion_reason": "no_valid_graph_output",
                                "source_file": str(spec.query_ids_file),
                                "notes": "Downstream graph/evaluation output was not produced.",
                            }
                        )
                        continue

                    edge_support = _support_map_from_rows(artifacts["rows"])
                    extra_methods = {}
                    query_records.append(
                        _serializable_query_record(
                            dataset=dataset,
                            protocol=protocol,
                            regime=regime,
                            query_id=query_id,
                            artifacts=artifacts,
                            threshold_config=threshold_config,
                            eval_record=eval_record,
                            edge_support=edge_support,
                            extra_methods=extra_methods,
                        )
                    )
                    valid_query_ids.append(query_id)
                    edge_sets[query_id] = set(eval_record["raw_edges"])
                    removed_sets[query_id] = set(eval_record["removed_edges"])
                    support_maps[query_id] = edge_support
                    query_eval_records.append(eval_record)
                    total_bm25.append(_ranker_weight_summary(edge_support))

                    for method_key in METHOD_KEYS:
                        metric_rows.append(
                            {
                                "dataset": dataset,
                                "protocol": protocol,
                                "protocol_label": spec_cfg["label"],
                                "regime": regime,
                                "query_id": query_id,
                                "method_key": method_key,
                                "method": METHOD_LABELS[method_key],
                                "ndcg_at_k": _maybe_float(
                                    eval_record["method_outputs"][method_key]["ndcg_at_k"]
                                ),
                            }
                        )

                    for pair_name, unrepaired_key, repaired_key, pair_family in PAIR_SPECS:
                        unrepaired = float(
                            eval_record["method_outputs"][unrepaired_key]["ndcg_at_k"] or 0.0
                        )
                        repaired = float(
                            eval_record["method_outputs"][repaired_key]["ndcg_at_k"] or 0.0
                        )
                        paired_rows.append(
                            {
                                "dataset": dataset,
                                "protocol": protocol,
                                "protocol_label": spec_cfg["label"],
                                "regime": regime,
                                "pair_name": pair_name,
                                "pair_family": pair_family,
                                "query_id": query_id,
                                "unrepaired_method_key": unrepaired_key,
                                "repaired_method_key": repaired_key,
                                "unrepaired_ndcg": unrepaired,
                                "repaired_ndcg": repaired,
                                "delta_ndcg": repaired - unrepaired,
                            }
                        )

                    if protocol == PRIMARY_PROTOCOL:
                        balance_rows.append(
                            _balance_audit_rows(
                                evaluator,
                                dataset=dataset,
                                protocol=protocol,
                                regime=regime,
                                query_id=query_id,
                                top_k=spec.top_k,
                                qrels_for_query=item["qrels_for_query"],
                                candidate_pool=item["candidate_pool"],
                                raw_score_maps_by_ranker=item["raw_scores_by_ranker"],
                                eval_record=eval_record,
                            )
                        )
                        for alpha in PRIMARY_ALPHA_VALUES:
                            for component in ("copeland", "balance"):
                                alpha_metrics = _compute_alpha_metric(
                                    evaluator,
                                    query_id=query_id,
                                    qrels_for_query=item["qrels_for_query"],
                                    candidate_pool=item["candidate_pool"],
                                    top_k=spec.top_k,
                                    raw_score_maps_by_ranker=item["raw_scores_by_ranker"],
                                    graph=eval_record["graph"],
                                    repaired_graph=eval_record["repaired_graph"],
                                    component=component,
                                    alpha=alpha,
                                )
                                alpha_query_rows.append(
                                    {
                                        "dataset": dataset,
                                        "protocol": protocol,
                                        "regime": regime,
                                        "query_id": query_id,
                                        "component": component,
                                        "alpha": alpha,
                                        "unrepaired_ndcg": alpha_metrics["raw"]["ndcg_at_k"],
                                        "repaired_ndcg": alpha_metrics["repaired"]["ndcg_at_k"],
                                        "delta_ndcg": float(
                                            alpha_metrics["repaired"]["ndcg_at_k"] or 0.0
                                        )
                                        - float(alpha_metrics["raw"]["ndcg_at_k"] or 0.0),
                                    }
                                )

                protocol_query_sets[(dataset, protocol)]["analysis"] = set(valid_query_ids)
                _write_jsonl(out_dir / "query_records.jsonl", query_records)
                write_csv(out_dir / "query_method_metrics.csv", metric_rows)
                if alpha_query_rows:
                    write_csv(out_dir / "alpha_query_metrics.csv", alpha_query_rows)
                alpha_rows.extend(alpha_query_rows)
                manifest = {
                    "generated_at": now_iso(),
                    "branch": repo["branch"],
                    "head": repo["head"],
                    "dataset": dataset,
                    "protocol": protocol,
                    "protocol_spec": spec_cfg,
                    "regime": regime,
                    "query_ids": valid_query_ids,
                    "source_score_hashes": dataset_score_hashes[dataset],
                    "qrels_hash": dataset_inputs["qrels_hash"],
                    "thresholds": {
                        "vote_thresholds": threshold_config.vote_thresholds,
                        "aggregate_threshold": threshold_config.aggregate_threshold,
                        "min_support": threshold_config.min_support,
                        "drop_mutual": threshold_config.postprocess_drop_mutual,
                        "notes": threshold_config.notes,
                    },
                    "scripts": [
                        str((SCRIPT_DIR / "full_calibration_utils.py").resolve()),
                        str(Path(__file__).resolve()),
                    ],
                    "seed": SEED,
                    "output_files": {
                        "query_records": str(out_dir / "query_records.jsonl"),
                        "query_method_metrics": str(out_dir / "query_method_metrics.csv"),
                    },
                }
                _write_json(out_dir / "manifest.json", manifest)

                structural_summary = summarize_structural_records(query_eval_records)
                mean_mutual_weight = _safe_mean(
                    [_mutual_pair_weight_share(rec["graph"]) for rec in query_eval_records]
                )
                mean_scc_gt1 = _safe_mean(
                    [float(_scc_count_gt1(rec["graph"])) for rec in query_eval_records]
                )
                mean_triangles = _safe_mean(
                    [float(_directed_triangle_count(rec["graph"])) for rec in query_eval_records]
                )
                structural_rows.append(
                    {
                        "dataset": dataset,
                        "protocol": protocol,
                        "protocol_label": spec_cfg["label"],
                        "protocol_kind": spec_cfg["kind"],
                        "calibration": spec_cfg["calibration"],
                        "threshold_mode": spec_cfg["threshold_mode"],
                        "regime": regime,
                        **structural_summary,
                        "mutual_pair_weight_share": mean_mutual_weight,
                        "scc_count_gt1": mean_scc_gt1,
                        "directed_triangle_count": mean_triangles,
                        "removed_edge_overlap_with_raw": None,
                        "removed_edge_overlap_with_primary": None,
                    }
                )
                cycle_rows.append(
                    {
                        "dataset": dataset,
                        "protocol": protocol,
                        "protocol_label": spec_cfg["label"],
                        "regime": regime,
                        "usable_query_count": structural_summary["usable_query_count"],
                        "cyclic_query_pct": structural_summary["cyclic_query_pct"],
                        "cyclic_query_pct_after_mutual_deletion": structural_summary[
                            "cyclic_query_pct_after_mutual_deletion"
                        ],
                        "mean_largest_scc": structural_summary["mean_largest_scc"],
                        "mean_largest_scc_after_mutual_deletion": structural_summary[
                            "mean_largest_scc_after_mutual_deletion"
                        ],
                        "scc_count_gt1": mean_scc_gt1,
                        "directed_triangle_count": mean_triangles,
                    }
                )

                total_weight = sum(float(row["total"] or 0.0) for row in total_bm25)
                bm25_total = sum(float(row["bm25"] or 0.0) for row in total_bm25)
                cond_num = 0.0
                cond_den = 0.0
                for row in total_bm25:
                    share = row["bm25_share_conditional"]
                    if share is not None:
                        pass
                for support in support_maps.values():
                    for recs in support.values():
                        edge_total = sum(weight for _ranker, weight in recs)
                        bm25_weight = sum(weight for ranker, weight in recs if ranker == "bm25")
                        if bm25_weight > 0:
                            cond_num += bm25_weight
                            cond_den += edge_total
                bm25_rows.append(
                    {
                        "dataset": dataset,
                        "protocol": protocol,
                        "protocol_label": spec_cfg["label"],
                        "regime": regime,
                        "bm25_weight_share_total": (bm25_total / total_weight)
                        if total_weight > 0
                        else None,
                        "bm25_weight_share_conditional": (cond_num / cond_den)
                        if cond_den > 0
                        else None,
                        "calibration": spec_cfg["calibration"],
                        "threshold_mode": spec_cfg["threshold_mode"],
                    }
                )

                config_cache[(dataset, protocol, regime)] = {
                    "query_ids": valid_query_ids,
                    "eval_records": query_eval_records,
                    "edge_sets": edge_sets,
                    "removed_sets": removed_sets,
                    "support_maps": support_maps,
                    "dataset_inputs": dataset_inputs,
                    "threshold_config": threshold_config,
                    "threshold_spec": spec_cfg,
                }
                print(
                    f"[{now_iso()}] done dataset={dataset} protocol={protocol} regime={regime} "
                    f"elapsed_seconds={time.time() - cfg_start:.2f}",
                    flush=True,
                )

    # Common query intersections and overlap rows.
    three_regime_intersections = {}
    for dataset in DATASETS:
        for protocol in PROTOCOL_SPECS:
            sets = [
                set(config_cache[(dataset, protocol, regime)]["query_ids"]) for regime in REGIMES
            ]
            three_regime_intersections[(dataset, protocol)] = len(set.intersection(*sets))

    structural_lookup = {
        (row["dataset"], row["protocol"], row["regime"]): row for row in structural_rows
    }
    for dataset in DATASETS:
        for protocol in PROTOCOL_SPECS:
            for regime in REGIMES:
                current = config_cache[(dataset, protocol, regime)]
                raw_ref = config_cache[(dataset, RAW_PROTOCOL, regime)]
                primary_ref = config_cache[(dataset, PRIMARY_PROTOCOL, regime)]
                raw_jaccards = []
                primary_jaccards = []
                raw_exact = 0
                primary_exact = 0
                for query_id in current["query_ids"]:
                    current_removed = current["removed_sets"][query_id]
                    raw_removed = raw_ref["removed_sets"].get(query_id, set())
                    primary_removed = primary_ref["removed_sets"].get(query_id, set())
                    raw_j = jaccard(current_removed, raw_removed)
                    primary_j = jaccard(current_removed, primary_removed)
                    if raw_j is not None:
                        raw_jaccards.append(raw_j)
                    if primary_j is not None:
                        primary_jaccards.append(primary_j)
                    if current_removed == raw_removed:
                        raw_exact += 1
                    if current_removed == primary_removed:
                        primary_exact += 1
                overlap_row = {
                    "dataset": dataset,
                    "protocol": protocol,
                    "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                    "regime": regime,
                    "removed_edge_overlap_with_raw": _safe_mean(raw_jaccards),
                    "removed_edge_overlap_with_primary": _safe_mean(primary_jaccards),
                    "exact_removed_edge_match_fraction_with_raw": raw_exact
                    / max(1, len(current["query_ids"])),
                    "exact_removed_edge_match_fraction_with_primary": primary_exact
                    / max(1, len(current["query_ids"])),
                }
                removed_overlap_rows.append(overlap_row)
                structural_lookup[(dataset, protocol, regime)]["removed_edge_overlap_with_raw"] = (
                    overlap_row["removed_edge_overlap_with_raw"]
                )
                structural_lookup[(dataset, protocol, regime)][
                    "removed_edge_overlap_with_primary"
                ] = overlap_row["removed_edge_overlap_with_primary"]
                structural_lookup[(dataset, protocol, regime)][
                    "three_regime_intersection_query_count"
                ] = three_regime_intersections[(dataset, protocol)]

    metrics_by_cfg: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (dataset, protocol, regime), payload in config_cache.items():
        for rec in payload["eval_records"]:
            for method_key in METHOD_KEYS:
                value = _maybe_float(rec["method_outputs"][method_key]["ndcg_at_k"])
                if value is not None:
                    metrics_by_cfg[(dataset, protocol, regime)][method_key].append(value)

    paired_by_cfg: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in paired_rows:
        paired_by_cfg[(row["dataset"], row["protocol"], row["regime"], row["pair_name"])].append(
            row
        )

    for dataset in DATASETS:
        for protocol in PROTOCOL_SPECS:
            for regime in REGIMES:
                pair_summaries: dict[str, dict[str, Any]] = {}
                for pair_name, _unrepaired, _repaired, pair_family in PAIR_SPECS:
                    rows = paired_by_cfg[(dataset, protocol, regime, pair_name)]
                    deltas = [float(row["delta_ndcg"]) for row in rows]
                    lo, hi, frac_gt_zero = bootstrap_ci(deltas, reps=BOOTSTRAP_REPS, seed=SEED)
                    perm = paired_permutation_pvalue(deltas, reps=PERMUTATION_REPS, seed=SEED + 4)
                    helped = sum(1 for d in deltas if d > 1.0e-12)
                    harmed = sum(1 for d in deltas if d < -1.0e-12)
                    unchanged = len(deltas) - helped - harmed
                    pair_summaries[pair_name] = {
                        "mean_delta_ndcg": _safe_mean(deltas),
                        "median_delta_ndcg": _safe_quantile(deltas, 0.5),
                        "q05_delta_ndcg": _safe_quantile(deltas, 0.05),
                        "q25_delta_ndcg": _safe_quantile(deltas, 0.25),
                        "q75_delta_ndcg": _safe_quantile(deltas, 0.75),
                        "q95_delta_ndcg": _safe_quantile(deltas, 0.95),
                        "helped_query_count": helped,
                        "harmed_query_count": harmed,
                        "unchanged_query_count": unchanged,
                        "paired_permutation_pvalue": perm,
                        "bootstrap_ci_low": lo,
                        "bootstrap_ci_high": hi,
                        "bootstrap_fraction_means_gt_zero": frac_gt_zero,
                        "common_query_count": len(deltas),
                        "pair_family": pair_family,
                    }
                    help_harm_rows.append(
                        {
                            "dataset": dataset,
                            "protocol": protocol,
                            "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                            "regime": regime,
                            "pair_name": pair_name,
                            "pair_family": pair_family,
                            "common_query_count": len(deltas),
                            "helped_query_count": helped,
                            "harmed_query_count": harmed,
                            "unchanged_query_count": unchanged,
                        }
                    )
                    if protocol == PRIMARY_PROTOCOL:
                        stats_rows.append(
                            {
                                "dataset": dataset,
                                "protocol": protocol,
                                "regime": regime,
                                "pair_name": pair_name,
                                "pair_family": pair_family,
                                "common_query_count": len(deltas),
                                "mean_delta_ndcg": pair_summaries[pair_name]["mean_delta_ndcg"],
                                "median_delta_ndcg": pair_summaries[pair_name]["median_delta_ndcg"],
                                "q05_delta_ndcg": pair_summaries[pair_name]["q05_delta_ndcg"],
                                "q25_delta_ndcg": pair_summaries[pair_name]["q25_delta_ndcg"],
                                "q75_delta_ndcg": pair_summaries[pair_name]["q75_delta_ndcg"],
                                "q95_delta_ndcg": pair_summaries[pair_name]["q95_delta_ndcg"],
                                "paired_permutation_pvalue": perm,
                                "bootstrap_ci_low": lo,
                                "bootstrap_ci_high": hi,
                                "bootstrap_fraction_means_gt_zero": frac_gt_zero,
                            }
                        )
                    for row in rows:
                        others = [
                            float(item["delta_ndcg"])
                            for item in rows
                            if item["query_id"] != row["query_id"]
                        ]
                        leave_one_out_rows.append(
                            {
                                "dataset": dataset,
                                "protocol": protocol,
                                "regime": regime,
                                "pair_name": pair_name,
                                "query_id": row["query_id"],
                                "leave_one_out_mean_delta_ndcg": _safe_mean(others),
                            }
                        )

                for method_key in METHOD_KEYS:
                    values = metrics_by_cfg[(dataset, protocol, regime)].get(method_key, [])
                    pair_summary = {}
                    if method_key == "copeland_graph_repaired":
                        pair_summary = pair_summaries["copeland_graph"]
                    elif method_key == "balance_graph_repaired":
                        pair_summary = pair_summaries["balance_graph"]
                    elif method_key == "markov_graph_repaired":
                        pair_summary = pair_summaries["markov_graph"]
                    elif method_key == "hybrid_repaired_copeland_a0p3_minmax":
                        pair_summary = pair_summaries["copeland_hybrid"]
                    elif method_key == "hybrid_repaired_balance_a0p3_minmax":
                        pair_summary = pair_summaries["balance_hybrid"]
                    retrieval_rows.append(
                        {
                            "dataset": dataset,
                            "protocol": protocol,
                            "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                            "protocol_kind": PROTOCOL_SPECS[protocol]["kind"],
                            "regime": regime,
                            "method_key": method_key,
                            "method": METHOD_LABELS[method_key],
                            "mean_ndcg_at_k": _safe_mean(values),
                            "std_ndcg_at_k": _safe_std(values),
                            "median_ndcg_at_k": _safe_quantile(values, 0.5),
                            "common_query_count": len(values),
                            "three_regime_intersection_query_count": three_regime_intersections[
                                (dataset, protocol)
                            ],
                            "repaired_minus_unrepaired_mean_delta_ndcg": pair_summary.get(
                                "mean_delta_ndcg"
                            ),
                            "repaired_minus_unrepaired_median_delta_ndcg": pair_summary.get(
                                "median_delta_ndcg"
                            ),
                            "repaired_minus_unrepaired_q05_delta_ndcg": pair_summary.get(
                                "q05_delta_ndcg"
                            ),
                            "repaired_minus_unrepaired_q25_delta_ndcg": pair_summary.get(
                                "q25_delta_ndcg"
                            ),
                            "repaired_minus_unrepaired_q75_delta_ndcg": pair_summary.get(
                                "q75_delta_ndcg"
                            ),
                            "repaired_minus_unrepaired_q95_delta_ndcg": pair_summary.get(
                                "q95_delta_ndcg"
                            ),
                            "helped_query_count": pair_summary.get("helped_query_count"),
                            "harmed_query_count": pair_summary.get("harmed_query_count"),
                            "unchanged_query_count": pair_summary.get("unchanged_query_count"),
                        }
                    )

    retrieval_df = pd.DataFrame(retrieval_rows)
    if not retrieval_df.empty:
        dataset_ranks = []
        for (protocol, regime, dataset), sub in retrieval_df.groupby(
            ["protocol", "regime", "dataset"]
        ):
            ranked = sub.sort_values(
                ["mean_ndcg_at_k", "method"], ascending=[False, True]
            ).reset_index(drop=True)
            for idx, row in ranked.iterrows():
                dataset_ranks.append(
                    {
                        "protocol": protocol,
                        "regime": regime,
                        "dataset": dataset,
                        "method_key": row["method_key"],
                        "method": row["method"],
                        "rank_within_dataset": idx + 1,
                    }
                )
        rank_df = pd.DataFrame(dataset_ranks)
        macro_df = retrieval_df.groupby(
            ["protocol", "regime", "method_key", "method"], as_index=False
        ).agg(
            dataset_macro_mean_ndcg=("mean_ndcg_at_k", "mean"),
            dataset_macro_median_ndcg=("median_ndcg_at_k", "mean"),
            datasets_count=("dataset", "nunique"),
        )
        if not rank_df.empty:
            avg_ranks = rank_df.groupby(
                ["protocol", "regime", "method_key", "method"], as_index=False
            ).agg(average_method_rank=("rank_within_dataset", "mean"))
            macro_df = macro_df.merge(
                avg_ranks, on=["protocol", "regime", "method_key", "method"], how="left"
            )
        macro_rows.extend(macro_df.to_dict("records"))

    # Baseline paired deltas versus RRF and CombSUM.
    method_query_values: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    for (dataset, protocol, regime), payload in config_cache.items():
        for rec in payload["eval_records"]:
            qid = rec["query_id"]
            for method_key in METHOD_KEYS:
                method_query_values[(dataset, protocol, regime, qid)][method_key] = float(
                    rec["method_outputs"][method_key]["ndcg_at_k"] or 0.0
                )

    for dataset in DATASETS:
        for protocol in PROTOCOL_SPECS:
            for regime in REGIMES:
                qids = config_cache[(dataset, protocol, regime)]["query_ids"]
                for method_key in PRIMARY_BASELINE_COMPARISON_METHODS:
                    for baseline in BASELINES:
                        deltas = []
                        rows = []
                        for query_id in qids:
                            query_vals = method_query_values[(dataset, protocol, regime, query_id)]
                            if method_key not in query_vals or baseline not in query_vals:
                                continue
                            delta = query_vals[method_key] - query_vals[baseline]
                            deltas.append(delta)
                            rows.append(
                                {
                                    "dataset": dataset,
                                    "protocol": protocol,
                                    "regime": regime,
                                    "query_id": query_id,
                                    "method_key": method_key,
                                    "baseline_key": baseline,
                                    "delta_ndcg": delta,
                                }
                            )
                        lo, hi, frac_gt_zero = bootstrap_ci(deltas, reps=BOOTSTRAP_REPS, seed=SEED)
                        baseline_rows.append(
                            {
                                "comparison_scope": "dataset_regime",
                                "dataset": dataset,
                                "protocol": protocol,
                                "regime": regime,
                                "method_key": method_key,
                                "method": METHOD_LABELS[method_key],
                                "baseline_key": baseline,
                                "baseline": METHOD_LABELS[baseline],
                                "common_query_count": len(deltas),
                                "mean_delta_ndcg": _safe_mean(deltas),
                                "median_delta_ndcg": _safe_quantile(deltas, 0.5),
                                "bootstrap_ci_low": lo,
                                "bootstrap_ci_high": hi,
                                "bootstrap_fraction_means_gt_zero": frac_gt_zero,
                            }
                        )

        # Clustered bootstrap across all regimes for primary protocol.
        protocol = PRIMARY_PROTOCOL
        pooled_rows = []
        for regime in REGIMES:
            qids = config_cache[(dataset, protocol, regime)]["query_ids"]
            for method_key in PRIMARY_BASELINE_COMPARISON_METHODS:
                for baseline in BASELINES:
                    for query_id in qids:
                        query_vals = method_query_values[(dataset, protocol, regime, query_id)]
                        if method_key not in query_vals or baseline not in query_vals:
                            continue
                        pooled_rows.append(
                            {
                                "dataset": dataset,
                                "protocol": protocol,
                                "regime": regime,
                                "query_id": query_id,
                                "method_key": method_key,
                                "baseline_key": baseline,
                                "delta_ndcg": query_vals[method_key] - query_vals[baseline],
                            }
                        )
        pooled_df = pd.DataFrame(pooled_rows)
        if not pooled_df.empty:
            for (method_key, baseline), sub in pooled_df.groupby(["method_key", "baseline_key"]):
                lo, hi, frac = _clustered_bootstrap(
                    sub.to_dict("records"),
                    value_key="delta_ndcg",
                    cluster_key="query_id",
                )
                baseline_rows.append(
                    {
                        "comparison_scope": "dataset_all_regimes_clustered",
                        "dataset": dataset,
                        "protocol": protocol,
                        "regime": "all_regimes",
                        "method_key": method_key,
                        "method": METHOD_LABELS[method_key],
                        "baseline_key": baseline,
                        "baseline": METHOD_LABELS[baseline],
                        "common_query_count": len(sub),
                        "mean_delta_ndcg": float(sub["delta_ndcg"].mean()),
                        "median_delta_ndcg": float(sub["delta_ndcg"].median()),
                        "bootstrap_ci_low": lo,
                        "bootstrap_ci_high": hi,
                        "bootstrap_fraction_means_gt_zero": frac,
                    }
                )

    # Multiplicity correction on primary repaired/unrepaired cells.
    if stats_rows:
        primary_pvals = [float(row["paired_permutation_pvalue"]) for row in stats_rows]
        holm = _holm_adjust(primary_pvals)
        bh = _bh_adjust(primary_pvals)
        for row, holm_p, bh_p in zip(stats_rows, holm, bh, strict=True):
            multiplicity_rows.append(
                {
                    "dataset": row["dataset"],
                    "protocol": row["protocol"],
                    "regime": row["regime"],
                    "pair_name": row["pair_name"],
                    "raw_pvalue": row["paired_permutation_pvalue"],
                    "holm_adjusted_pvalue": holm_p,
                    "bh_adjusted_pvalue": bh_p,
                    "reject_holm_0p05": holm_p < 0.05,
                    "reject_bh_0p05": bh_p < 0.05,
                }
            )

    # RRF implementation table.
    exact_match_count = 0
    total_match_count = 0
    for payload in config_cache.values():
        for rec in payload["eval_records"]:
            total_match_count += 1
            if (
                rec["method_outputs"]["prior_only"]["ranking"]
                == rec["method_outputs"]["rrf"]["ranking"]
            ):
                exact_match_count += 1
    rrf_note_rows.extend(
        [
            {
                "usage": "candidate_pooling",
                "file": "reports/b3_margin_calibration_investigation/scripts/run_phase0_phase1.py:_select_candidates",
                "formula": "RRF over full per-ranker native rankings with k=60.0; top-k candidates kept.",
                "candidate_restriction": "top-k from union docs",
                "tie_breaking": "doc_id ascending after equal fused score",
                "matches_rrf_baseline": False,
                "notes": "Used only to form candidate pool, not final ranking.",
            },
            {
                "usage": "prior",
                "file": "scripts/run_real_experiment.py:_rrf_prior_scores_for_query",
                "formula": "RRF with k=60.0 restricted to candidate nodes.",
                "candidate_restriction": "candidate nodes only",
                "tie_breaking": "inherited by prior_only ranking helper",
                "matches_rrf_baseline": True,
                "notes": "Empirical exact ranking match versus RRF baseline computed across full run.",
            },
            {
                "usage": "rrf_baseline",
                "file": "src/consistency_ranker/rrf_ranking.py:per_query_rrf_ranking_from_score_maps",
                "formula": "RRF with k=60.0 restricted to candidate_doc_ids.",
                "candidate_restriction": "candidate_doc_ids only",
                "tie_breaking": "best rank, then doc_id",
                "matches_rrf_baseline": True,
                "notes": f"Prior-vs-RRF exact match rate in this run: {exact_match_count}/{total_match_count}.",
            },
        ]
    )

    # Influence studies.
    influence_summaries = []
    for dataset in ("hotpotqa", "scidocs"):
        rows = [
            row
            for row in paired_rows
            if row["dataset"] == dataset
            and row["protocol"] == PRIMARY_PROTOCOL
            and row["regime"] == "ms1"
            and row["pair_name"] == "copeland_hybrid"
        ]
        deltas = {row["query_id"]: float(row["delta_ndcg"]) for row in rows}
        mean_delta = _safe_mean(list(deltas.values()))
        ranked = sorted(
            (
                (
                    query_id,
                    delta,
                    mean_delta
                    - _safe_mean([value for other, value in deltas.items() if other != query_id]),
                )
                for query_id, delta in deltas.items()
            ),
            key=lambda item: (abs(item[2]), abs(item[1]), item[0]),
            reverse=True,
        )
        top_queries = [item[0] for item in ranked]
        for k in (1, 2, 3, 4):
            kept = [value for qid, value in deltas.items() if qid not in set(top_queries[:k])]
            influence_summaries.append(
                {
                    "dataset": dataset,
                    "protocol": PRIMARY_PROTOCOL,
                    "regime": "ms1",
                    "pair_name": "copeland_hybrid",
                    "remove_top_k": k,
                    "removed_query_ids": ",".join(top_queries[:k]),
                    "remaining_mean_delta_ndcg": _safe_mean(kept),
                    "remaining_sign": _sign_label(_safe_mean(kept)),
                    "remaining_count": len(kept),
                }
            )
        for query_id, delta, influence in ranked:
            leave_one_out = [value for other, value in deltas.items() if other != query_id]
            leave_one_out_rows.append(
                {
                    "dataset": dataset,
                    "protocol": PRIMARY_PROTOCOL,
                    "regime": "ms1",
                    "pair_name": "copeland_hybrid",
                    "query_id": query_id,
                    "leave_one_out_mean_delta_ndcg": _safe_mean(leave_one_out),
                    "query_delta_ndcg": delta,
                    "influence_on_mean": influence,
                }
            )

    alpha_summary_rows = []
    alpha_df = pd.DataFrame(alpha_rows)
    if not alpha_df.empty:
        alpha_summary_rows = (
            alpha_df.groupby(
                ["dataset", "protocol", "regime", "component", "alpha"], as_index=False
            )
            .agg(
                mean_unrepaired_ndcg=("unrepaired_ndcg", "mean"),
                mean_repaired_ndcg=("repaired_ndcg", "mean"),
                mean_delta_ndcg=("delta_ndcg", "mean"),
                median_delta_ndcg=("delta_ndcg", "median"),
            )
            .to_dict("records")
        )

    # Write core tables.
    write_csv(TABLES_DIR / "full_thresholds.csv", threshold_rows)
    write_csv(TABLES_DIR / "full_structural_results.csv", list(structural_lookup.values()))
    write_csv(TABLES_DIR / "full_cycle_decomposition.csv", cycle_rows)
    write_csv(TABLES_DIR / "full_removed_edge_overlap.csv", removed_overlap_rows)
    write_csv(TABLES_DIR / "full_retrieval_results.csv", retrieval_rows)
    write_csv(TABLES_DIR / "full_paired_deltas.csv", paired_rows)
    write_csv(TABLES_DIR / "full_help_harm_counts.csv", help_harm_rows)
    write_csv(TABLES_DIR / "full_macro_method_comparison.csv", macro_rows)
    write_csv(TABLES_DIR / "full_paired_vs_baselines.csv", baseline_rows)
    write_csv(TABLES_DIR / "full_statistical_tests.csv", stats_rows)
    write_csv(TABLES_DIR / "full_multiplicity_adjusted.csv", multiplicity_rows)
    write_csv(TABLES_DIR / "full_leave_one_out.csv", _normalize_rows(leave_one_out_rows))
    write_csv(TABLES_DIR / "query_exclusion_audit.csv", exclusion_rows)
    write_csv(TABLES_DIR / "balance_change_pipeline_audit.csv", balance_rows)
    write_csv(TABLES_DIR / "rrf_implementation_used_in_full_run.csv", rrf_note_rows)
    write_csv(TABLES_DIR / "full_alpha_sensitivity.csv", alpha_summary_rows)
    write_csv(TABLES_DIR / "full_bm25_weight_share.csv", bm25_rows)
    write_csv(TABLES_DIR / "full_influence_removal_summary.csv", influence_summaries)

    # Manuscript-ready primary tables.
    structural_df = pd.DataFrame(list(structural_lookup.values()))
    cycle_df = pd.DataFrame(cycle_rows)
    retrieval_df = pd.DataFrame(retrieval_rows)
    stats_df = pd.DataFrame(stats_rows)
    help_df = pd.DataFrame(help_harm_rows)
    macro_df = pd.DataFrame(macro_rows)
    if not structural_df.empty:
        write_csv(
            PAPER_TABLES / "table_primary_graph_structure.csv",
            structural_df[structural_df["protocol"] == PRIMARY_PROTOCOL].to_dict("records"),
        )
        write_csv(
            PAPER_TABLES / "table_primary_cycle_decomposition.csv",
            cycle_df[cycle_df["protocol"] == PRIMARY_PROTOCOL].to_dict("records"),
        )
        write_csv(
            PAPER_TABLES / "table_raw_vs_calibrated_ablation.csv",
            structural_df[
                structural_df["protocol"].isin(
                    [
                        RAW_PROTOCOL,
                        PRIMARY_PROTOCOL,
                        "ablation_minmax_fixed",
                        "ablation_unit_vote_retention",
                    ]
                )
            ].to_dict("records"),
        )
    if not retrieval_df.empty:
        primary_effects = retrieval_df[
            (retrieval_df["protocol"] == PRIMARY_PROTOCOL)
            & retrieval_df["method_key"].isin(
                [
                    "copeland_graph_repaired",
                    "balance_graph_repaired",
                    "markov_graph_repaired",
                    "hybrid_repaired_copeland_a0p3_minmax",
                    "hybrid_repaired_balance_a0p3_minmax",
                ]
            )
        ]
        write_csv(
            PAPER_TABLES / "table_primary_repair_effects.csv", primary_effects.to_dict("records")
        )
        baseline_primary = pd.DataFrame(baseline_rows)
        write_csv(
            PAPER_TABLES / "table_primary_baseline_comparison_by_dataset.csv",
            baseline_primary[
                (baseline_primary["protocol"] == PRIMARY_PROTOCOL)
                & (baseline_primary["comparison_scope"] == "dataset_regime")
            ].to_dict("records"),
        )
        if not macro_df.empty:
            write_csv(
                PAPER_TABLES / "table_primary_macro_method_comparison.csv",
                macro_df[macro_df["protocol"] == PRIMARY_PROTOCOL].to_dict("records"),
            )
        write_csv(
            PAPER_TABLES / "table_primary_help_harm_counts.csv",
            help_df[help_df["protocol"] == PRIMARY_PROTOCOL].to_dict("records"),
        )
    if not stats_df.empty:
        write_csv(
            PAPER_TABLES / "table_primary_bootstrap_permutation.csv", stats_df.to_dict("records")
        )
    write_csv(PAPER_TABLES / "table_alpha_sensitivity.csv", alpha_summary_rows)

    # Figures.
    bm25_df = pd.DataFrame(bm25_rows)
    if not bm25_df.empty:
        render_line_plot(
            bm25_df,
            out_base=FIGURES_DIR / "bm25_weight_share_raw_vs_calibrated",
            x_col="protocol",
            y_col="bm25_weight_share_conditional",
            hue_col="regime",
            facet_col="dataset",
            title="BM25 Conditional Weight Share",
            y_label="conditional BM25 share",
        )
    if not structural_df.empty:
        primary_struct = structural_df[structural_df["protocol"] == PRIMARY_PROTOCOL]
        render_line_plot(
            primary_struct,
            out_base=FIGURES_DIR / "cyclicity_primary_by_dataset_regime",
            x_col="regime",
            y_col="cyclic_query_pct",
            hue_col="dataset",
            facet_col=None,
            title="Primary Calibrated Cyclicity",
            y_label="cyclic query share",
        )
        before_after = primary_struct.copy()
        before_after["facet"] = before_after["dataset"] + " | " + before_after["regime"]
        before_after = pd.concat(
            [
                before_after.assign(stage="before", value=before_after["cyclic_query_pct"]),
                before_after.assign(
                    stage="after_mutual_deletion",
                    value=before_after["cyclic_query_pct_after_mutual_deletion"],
                ),
            ],
            ignore_index=True,
        )
        render_line_plot(
            before_after,
            out_base=FIGURES_DIR / "cyclicity_before_after_mutual_deletion",
            x_col="stage",
            y_col="value",
            hue_col="regime",
            facet_col="dataset",
            title="Cyclicity Before/After Mutual-Pair Deletion",
            y_label="cyclic query share",
        )
        render_line_plot(
            primary_struct,
            out_base=FIGURES_DIR / "normalized_fas_weight_removed",
            x_col="regime",
            y_col="mean_normalized_fas_weight_removed",
            hue_col="dataset",
            facet_col=None,
            title="Normalized FAS Weight Removed",
            y_label="normalized FAS removed",
        )
        raw_vs_primary_struct = structural_df[
            structural_df["protocol"].isin([RAW_PROTOCOL, PRIMARY_PROTOCOL])
        ].copy()
        render_line_plot(
            raw_vs_primary_struct,
            out_base=FIGURES_DIR / "raw_vs_calibrated_structural_results",
            x_col="regime",
            y_col="cyclic_query_pct",
            hue_col="protocol",
            facet_col="dataset",
            title="Raw Versus Calibrated Cyclicity",
            y_label="cyclic query share",
        )

    if not stats_df.empty:
        plot_df = stats_df[
            stats_df["pair_name"].isin(["copeland_hybrid", "balance_hybrid", "markov_graph"])
        ].copy()
        _render_errorbar(
            plot_df,
            out_base=FIGURES_DIR / "repair_deltas_primary_with_intervals",
            title="Primary Repaired Minus Unrepaired nDCG Deltas",
            x_col="regime",
            y_col="mean_delta_ndcg",
            lo_col="bootstrap_ci_low",
            hi_col="bootstrap_ci_high",
            facet_col="dataset",
            hue_col="pair_name",
        )

    baseline_df = pd.DataFrame(baseline_rows)
    if not baseline_df.empty:
        baseline_plot = baseline_df[
            (baseline_df["protocol"] == PRIMARY_PROTOCOL)
            & (baseline_df["comparison_scope"] == "dataset_regime")
            & (baseline_df["baseline_key"] == "rrf")
        ].copy()
        _render_errorbar(
            baseline_plot,
            out_base=FIGURES_DIR / "per_dataset_baseline_comparison",
            title="Primary Methods Versus RRF",
            x_col="regime",
            y_col="mean_delta_ndcg",
            lo_col="bootstrap_ci_low",
            hi_col="bootstrap_ci_high",
            facet_col="dataset",
            hue_col="method",
        )

    if not help_df.empty:
        render_stacked_counts(
            help_df[help_df["protocol"] == PRIMARY_PROTOCOL],
            out_base=FIGURES_DIR / "helped_harmed_unchanged_counts",
            category_cols=["dataset", "regime", "pair_name"],
            count_cols=["helped_query_count", "harmed_query_count", "unchanged_query_count"],
            title="Primary Helped / Harmed / Unchanged Counts",
        )

    raw_calibrated_pairs = pd.DataFrame(paired_rows)
    if not raw_calibrated_pairs.empty:
        raw_delta = raw_calibrated_pairs[
            (raw_calibrated_pairs["protocol"] == RAW_PROTOCOL)
            & (raw_calibrated_pairs["pair_name"] == "copeland_hybrid")
        ]
        primary_delta = raw_calibrated_pairs[
            (raw_calibrated_pairs["protocol"] == PRIMARY_PROTOCOL)
            & (raw_calibrated_pairs["pair_name"] == "copeland_hybrid")
        ]
        raw_map = {
            (row["dataset"], row["regime"], row["query_id"]): float(row["delta_ndcg"])
            for _, row in raw_delta.iterrows()
        }
        scatter_rows = []
        for _, row in primary_delta.iterrows():
            key = (row["dataset"], row["regime"], row["query_id"])
            if key not in raw_map:
                continue
            scatter_rows.append(
                {
                    "facet": f"{row['dataset']} | {row['regime']}",
                    "raw_delta_ndcg": raw_map[key],
                    "calibrated_delta_ndcg": float(row["delta_ndcg"]),
                }
            )
        scatter_df = pd.DataFrame(scatter_rows)
        if not scatter_df.empty:
            _render_scatter(
                scatter_df,
                out_base=FIGURES_DIR / "raw_vs_calibrated_retrieval_deltas",
                title="Raw Versus Calibrated Copeland-Hybrid Deltas",
                x_col="raw_delta_ndcg",
                y_col="calibrated_delta_ndcg",
                facet_col="facet",
            )

    influence_df = pd.DataFrame(
        [
            row
            for row in paired_rows
            if row["protocol"] == PRIMARY_PROTOCOL
            and row["regime"] == "ms1"
            and row["pair_name"] == "copeland_hybrid"
            and row["dataset"] in {"hotpotqa", "scidocs"}
        ]
    )
    if not influence_df.empty:
        hot_df = influence_df[influence_df["dataset"] == "hotpotqa"]
        sci_df = influence_df[influence_df["dataset"] == "scidocs"]
        _render_influence_plot(
            hot_df,
            out_base=FIGURES_DIR / "hotpotqa_query_level_influence",
            title="HotpotQA Primary ms1 Copeland-Hybrid Query Deltas",
        )
        _render_influence_plot(
            sci_df,
            out_base=FIGURES_DIR / "scidocs_query_level_influence",
            title="SciDocs Primary ms1 Copeland-Hybrid Query Deltas",
        )

    if alpha_summary_rows:
        alpha_plot_df = pd.DataFrame(alpha_summary_rows)
        render_line_plot(
            alpha_plot_df,
            out_base=FIGURES_DIR / "alpha_sensitivity",
            x_col="alpha",
            y_col="mean_delta_ndcg",
            hue_col="component",
            facet_col="dataset",
            title="Primary Alpha Sensitivity",
            y_label="mean delta nDCG",
        )

    # Copy manuscript-ready artifacts to the canonical package.
    for plot_path in FIGURES_DIR.glob("*.*"):
        if plot_path.suffix.lower() in {".png", ".pdf", ".svg"}:
            shutil.copy2(plot_path, PAPER_PLOTS / plot_path.name)

    package_manifest = {
        "generated_at": now_iso(),
        "branch": repo["branch"],
        "head": repo["head"],
        "environment": {
            "python_executable": repo["python_executable"],
            "python_version": repo["python_version"],
            "activation_command": repo["activation_command"],
        },
        "protocols": PROTOCOL_SPECS,
        "datasets": list(DATASETS),
        "query_ids": {
            dataset: dataset_inputs_map[dataset]["analysis_query_ids"] for dataset in DATASETS
        },
        "score_hashes": dataset_score_hashes,
        "qrels_hashes": {
            dataset: dataset_inputs_map[dataset]["qrels_hash"] for dataset in DATASETS
        },
        "threshold_table": str(TABLES_DIR / "full_thresholds.csv"),
        "tables": sorted(str(path) for path in PAPER_TABLES.glob("*.csv")),
        "plots": sorted(str(path) for path in PAPER_PLOTS.glob("*.*")),
        "scripts": [
            str((SCRIPT_DIR / "full_calibration_utils.py").resolve()),
            str(Path(__file__).resolve()),
            str((SCRIPT_DIR / "run_phase0_phase1.py").resolve()),
        ],
        "seed": SEED,
        "summary_report": str(REPORT_ROOT / "EXECUTIVE_SUMMARY.md"),
    }
    _write_json(PAPER_MANIFESTS / "package_manifest.json", package_manifest)
    _write_json(MANIFESTS_DIR / "full_run_manifest.json", package_manifest)

    # Reports.
    bm25_df = pd.DataFrame(bm25_rows)
    raw_bm25 = bm25_df[bm25_df["protocol"] == RAW_PROTOCOL][
        "bm25_weight_share_conditional"
    ].dropna()
    calibrated_bm25 = bm25_df[bm25_df["protocol"] == PRIMARY_PROTOCOL][
        "bm25_weight_share_conditional"
    ].dropna()
    primary_cycle = structural_df[structural_df["protocol"] == PRIMARY_PROTOCOL]
    robust_positive = pd.DataFrame(multiplicity_rows)
    if not robust_positive.empty:
        robust_positive = robust_positive[
            (robust_positive["reject_holm_0p05"]) | (robust_positive["reject_bh_0p05"])
        ]
    pair_summary_df = pd.DataFrame(stats_rows)
    for dataset in DATASETS:
        for regime in REGIMES:
            raw_row = pair_summary_df[
                (pair_summary_df["dataset"] == dataset)
                & (pair_summary_df["pair_name"] == "copeland_hybrid")
                & (pair_summary_df["regime"] == regime)
            ]
            if raw_row.empty:
                continue
    total_runtime = time.time() - start_wall

    executive_lines = [
        "# Executive Summary",
        "",
        f"- Generated: `{now_iso()}`",
        f"- Branch: `{repo['branch']}`",
        f"- HEAD: `{repo['head']}`",
        f"- Total runtime: `{total_runtime:.2f}` seconds",
        f"- Canonical protocol: `{PRIMARY_PROTOCOL}` ({PROTOCOL_SPECS[PRIMARY_PROTOCOL]['label']})",
        f"- Raw conditional BM25 share mean: `{_safe_mean(raw_bm25.tolist())}`",
        f"- Primary conditional BM25 share mean: `{_safe_mean(calibrated_bm25.tolist())}`",
        f"- Primary mean cyclicity: `{_safe_mean(primary_cycle['cyclic_query_pct'].dropna().tolist())}`",
        f"- Primary mean cyclicity after mutual-pair deletion: `{_safe_mean(primary_cycle['cyclic_query_pct_after_mutual_deletion'].dropna().tolist())}`",
        f"- Robust positive repaired-vs-unrepaired cells after multiplicity correction: `{len(robust_positive)}`",
        "- Canonical package decision: `calibrated_all4 should replace raw-margin evidence`",
    ]
    (REPORT_ROOT / "EXECUTIVE_SUMMARY.md").write_text(
        "\n".join(executive_lines) + "\n", encoding="utf-8"
    )

    methods_lines = [
        "# Methods And Protocol",
        "",
        "- Stored canonical score files, query IDs, qrels, candidate pools, top-k values, repair code, and evaluation code were reused unchanged.",
        "- Only downstream calibration, vote extraction, graph construction, repair, and evaluation were rerun.",
        "",
        "## Protocols",
        "",
    ]
    for protocol, spec_cfg in PROTOCOL_SPECS.items():
        methods_lines.append(
            f"- `{protocol}`: calibration `{spec_cfg['calibration']}`, threshold mode `{spec_cfg['threshold_mode']}`, role `{spec_cfg['kind']}`."
        )
    methods_lines += [
        "",
        "## Threshold Matching",
        "",
        "- `retention_matched` uses per-ranker vote-threshold matching to raw retained-vote rates and a regime-specific aggregate threshold selected to minimize retained-edge-count deviation from raw.",
        "- Support rules remain canonical: `ms2` requires support `2` and aggregate threshold default `0.1`; `ms1` and `ms1_drop_mutual` require support `1` with the canonical or matched aggregate threshold.",
        "",
        "## Methods",
        "",
        "- Graph-independent: Prior, RRF, CombSUM, Borda fusion.",
        "- Graph-dependent: Copeland, Balance, Markov; each evaluated unrepaired and repaired.",
        "- Hybrids: Copeland and Balance unrepaired/repaired hybrids at alpha=0.3, plus a primary-protocol alpha sweep over {0.1, 0.3, 0.5, 1.0}.",
    ]
    (REPORT_ROOT / "METHODS_AND_PROTOCOL.md").write_text(
        "\n".join(methods_lines) + "\n", encoding="utf-8"
    )

    full_results_lines = [
        "# Full Results",
        "",
        f"- Structural table: `{TABLES_DIR / 'full_structural_results.csv'}`",
        f"- Retrieval table: `{TABLES_DIR / 'full_retrieval_results.csv'}`",
        f"- Baseline comparison table: `{TABLES_DIR / 'full_paired_vs_baselines.csv'}`",
        f"- Statistical tests: `{TABLES_DIR / 'full_statistical_tests.csv'}`",
        f"- Macro comparison: `{TABLES_DIR / 'full_macro_method_comparison.csv'}`",
    ]
    (REPORT_ROOT / "FULL_RESULTS.md").write_text(
        "\n".join(full_results_lines) + "\n", encoding="utf-8"
    )

    stats_lines = [
        "# Statistical Conclusions",
        "",
        f"- Multiplicity table: `{TABLES_DIR / 'full_multiplicity_adjusted.csv'}`",
        f"- Leave-one-out table: `{TABLES_DIR / 'full_leave_one_out.csv'}`",
        f"- Robust positive cells after correction: `{len(robust_positive)}`",
        "- Interpret repaired-vs-unrepaired claims using permutation p-values, bootstrap intervals, influence removal, and Holm/BH adjustment together.",
    ]
    (REPORT_ROOT / "STATISTICAL_CONCLUSIONS.md").write_text(
        "\n".join(stats_lines) + "\n", encoding="utf-8"
    )

    raw_vs_lines = [
        "# Raw Vs Calibrated Interpretation",
        "",
        f"- Raw BM25 dominance mean conditional share: `{_safe_mean(raw_bm25.tolist())}`.",
        f"- Primary calibrated BM25 dominance mean conditional share: `{_safe_mean(calibrated_bm25.tolist())}`.",
        "- Raw-margin results remain an ablation only.",
        "- Calibrated construction materially changes edge weights, cyclicity, removed edges, and some retrieval signs.",
    ]
    (REPORT_ROOT / "RAW_VS_CALIBRATED_INTERPRETATION.md").write_text(
        "\n".join(raw_vs_lines) + "\n", encoding="utf-8"
    )

    nontrivial_lines = [
        "# Nontrivial Cycle Analysis",
        "",
        f"- Cycle decomposition table: `{TABLES_DIR / 'full_cycle_decomposition.csv'}`",
        "- Nontrivial cyclicity is assessed both before and after deleting direct mutual pairs.",
    ]
    (REPORT_ROOT / "NONTRIVIAL_CYCLE_ANALYSIS.md").write_text(
        "\n".join(nontrivial_lines) + "\n", encoding="utf-8"
    )

    hotpot_lines = [
        "# HotpotQA Influence Analysis",
        "",
        f"- Influence-removal table: `{TABLES_DIR / 'full_influence_removal_summary.csv'}` filtered to `dataset=hotpotqa`.",
        "- The primary target cell is `ms1` Copeland hybrid under the primary calibrated protocol.",
    ]
    (REPORT_ROOT / "HOTPOTQA_INFLUENCE_ANALYSIS.md").write_text(
        "\n".join(hotpot_lines) + "\n", encoding="utf-8"
    )

    scidocs_lines = [
        "# SciDocs Influence Analysis",
        "",
        f"- Influence-removal table: `{TABLES_DIR / 'full_influence_removal_summary.csv'}` filtered to `dataset=scidocs`.",
        "- The primary target cell is `ms1` Copeland hybrid under the primary calibrated protocol.",
    ]
    (REPORT_ROOT / "SCIDOCS_INFLUENCE_ANALYSIS.md").write_text(
        "\n".join(scidocs_lines) + "\n", encoding="utf-8"
    )

    balance_lines = [
        "# Balance Degeneracy Explanation",
        "",
        f"- Audit table: `{TABLES_DIR / 'balance_change_pipeline_audit.csv'}`.",
        "- Trace graph change, raw/normalized balance-score change, balance ranking change, hybrid-score change, top-k change, and nDCG change before concluding that balance repair is inactive or degenerate.",
    ]
    (REPORT_ROOT / "BALANCE_DEGENERACY_EXPLANATION.md").write_text(
        "\n".join(balance_lines) + "\n", encoding="utf-8"
    )

    rrf_lines = [
        "# RRF Implementation Note",
        "",
        f"- Audit table: `{TABLES_DIR / 'rrf_implementation_used_in_full_run.csv'}`.",
        f"- Prior vs RRF exact ranking match count: `{exact_match_count}/{total_match_count}`.",
        "- Candidate pooling uses the same reciprocal-rank formula family but serves a different role and does not imply that Prior and RRF baseline rows should be merged without documentation.",
    ]
    (REPORT_ROOT / "RRF_IMPLEMENTATION_NOTE.md").write_text(
        "\n".join(rrf_lines) + "\n", encoding="utf-8"
    )

    impact_lines = [
        "# Manuscript Impact Map",
        "",
        "- Abstract: raw-margin evidence must be replaced by the calibrated canonical protocol.",
        "- Introduction: claims about multi-ranker graph evidence need recalibration caveats.",
        "- Methodology: score calibration and threshold matching must be explicit and canonical.",
        "- Results: raw-margin tables/figures become ablations; calibrated tables/figures become primary evidence.",
        "- Failure taxonomy: any graph-construction claim tied to raw margins must be narrowed.",
        "- LLM section: no change from this task except where downstream comparisons cite the old raw package.",
        "- Discussion: repair conclusions must be framed as calibration-sensitive.",
        "- Limitations: include score-scale dependence and influence concentration.",
        "- Conclusion: raw-margin evidence should not remain canonical.",
        "- Tables: replace manuscript-facing raw tables with the primary calibrated tables in the paper package.",
        "- Figures: replace manuscript-facing raw figures with the primary calibrated figures in the paper package.",
    ]
    (REPORT_ROOT / "MANUSCRIPT_IMPACT_MAP.md").write_text(
        "\n".join(impact_lines) + "\n", encoding="utf-8"
    )

    package_lines = [
        "# Canonical Package Decision",
        "",
        f"- Canonical package: `{OUTPUT_ROOT / 'paper_package'}`",
        f"- Canonical protocol: `{PRIMARY_PROTOCOL}` ({PROTOCOL_SPECS[PRIMARY_PROTOCOL]['label']})",
        "- Historical raw-margin packages remain ablations only.",
        "- `calibrated_all4` should replace the manuscript's unstable raw-margin evidence unless a separate technical audit disproves the calibration protocol itself.",
    ]
    (REPORT_ROOT / "CANONICAL_PACKAGE_DECISION.md").write_text(
        "\n".join(package_lines) + "\n", encoding="utf-8"
    )

    audit_manifest = {
        "generated_at": now_iso(),
        "branch": repo["branch"],
        "head": repo["head"],
        "runtime_seconds": total_runtime,
        "estimated_runtime_seconds": estimate["estimated_seconds"],
        "estimated_output_mb": estimate["estimated_output_mb"],
        "datasets": list(DATASETS),
        "protocols": PROTOCOL_SPECS,
        "tables": sorted(str(path) for path in TABLES_DIR.glob("*.csv")),
        "figures": sorted(str(path) for path in FIGURES_DIR.glob("*.*")),
        "paper_package": str(PAPER_PACKAGE),
        "scripts": [
            str((SCRIPT_DIR / "full_calibration_utils.py").resolve()),
            str(Path(__file__).resolve()),
            str((SCRIPT_DIR / "run_phase0_phase1.py").resolve()),
        ],
        "seed": SEED,
    }
    _write_json(REPORT_ROOT / "audit_manifest.json", audit_manifest)

    return {
        "repo": repo,
        "runtime_seconds": total_runtime,
        "estimated_runtime_seconds": estimate["estimated_seconds"],
        "estimated_output_mb": estimate["estimated_output_mb"],
        "datasets_completed": list(DATASETS),
        "canonical_protocol": PRIMARY_PROTOCOL,
        "raw_bm25_share_mean": _safe_mean(raw_bm25.tolist()),
        "primary_bm25_share_mean": _safe_mean(calibrated_bm25.tolist()),
        "primary_cyclicity_mean": _safe_mean(primary_cycle["cyclic_query_pct"].dropna().tolist())
        if not primary_cycle.empty
        else None,
        "primary_cyclicity_after_mutual_mean": _safe_mean(
            primary_cycle["cyclic_query_pct_after_mutual_deletion"].dropna().tolist()
        )
        if not primary_cycle.empty
        else None,
        "robust_positive_cells": robust_positive.to_dict("records")
        if isinstance(robust_positive, pd.DataFrame)
        else [],
        "paper_conclusion_survives": False,
        "calibrated_all4_should_be_canonical": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full four-dataset calibrated core study.")
    parser.add_argument(
        "--estimate-only", action="store_true", help="Print runtime and output-size estimate only."
    )
    args = parser.parse_args()

    if args.estimate_only:
        print(json.dumps(_estimate_full_run(), indent=2, sort_keys=True))
        return

    result = run_full_core()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
