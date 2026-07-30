#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_ROOT = SCRIPT_DIR.parent
REPO_ROOT = REPORT_ROOT.parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_phase0_phase1 import _dataset_specs, _load_manifest, _load_score_file, _select_candidates  # noqa: E402
from consistency_ranker.baseline_ranking import (  # noqa: E402
    borda_ranking,
    borda_scores,
    copeland_ranking,
    pagerank_ranking,
    priority_topological_ranking,
    rank_centrality_ranking,
    rank_centrality_scores,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
    weighted_out_minus_in_ranking,
    weighted_out_minus_in_scores,
)
from consistency_ranker.data.dataset_registry import get_config  # noqa: E402
from consistency_ranker.data.unified_loader import load_dataset_splits  # noqa: E402
from consistency_ranker.failure_mining.graph_features import extended_graph_stats  # noqa: E402
from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight  # noqa: E402
from consistency_ranker.markov_graph_ranking import (  # noqa: E402
    DEFAULT_MARKOV_DAMPING,
    markov_graph_ranking,
    markov_graph_scores,
)
from consistency_ranker.metric_aware_repair import reweight_graph_for_metric_aware_fas  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402
from consistency_ranker.rrf_ranking import DEFAULT_RRF_K, per_query_rrf_ranking_from_score_maps  # noqa: E402
from consistency_ranker.combsum_ranking import COMBSUM_NORM_MINMAX, per_query_combsum_ranking_from_score_maps  # noqa: E402
from consistency_ranker.borda_fuse_ranking import per_query_borda_fuse_ranking_from_score_maps  # noqa: E402
from scripts.run_real_experiment import (  # noqa: E402
    _alpha_token,
    _average_precision_at_k,
    _backward_edge_weight,
    _kendall_tau,
    _ndcg_at_k,
    _pairwise_accuracy_from_relevance,
    _pairwise_inconsistency,
    _precision_recall_at_k,
    _prior_only_ranking,
    _reference_ranking_for_candidates,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
)


CALIBRATIONS = (
    "raw",
    "minmax_query_ranker",
    "zscore_query_ranker",
    "rank_percentile",
    "unit_vote",
)
THRESHOLD_MODES = ("fixed_numeric", "retention_matched")
REGIMES = ("ms2", "ms1", "ms1_drop_mutual")
PILOT_DATASETS = ("hotpotqa", "scidocs")
RANKERS = ("bm25", "tfidf", "minilm")
METHOD_KEYS = (
    "hybrid_unrepaired_copeland_a0p3_minmax",
    "hybrid_repaired_copeland_a0p3_minmax",
    "hybrid_unrepaired_balance_a0p3_minmax",
    "hybrid_repaired_balance_a0p3_minmax",
    "rrf",
    "combsum",
)
METHOD_LABELS = {
    "hybrid_unrepaired_copeland_a0p3_minmax": "copeland_unrepaired",
    "hybrid_repaired_copeland_a0p3_minmax": "copeland_repaired",
    "hybrid_unrepaired_balance_a0p3_minmax": "balance_unrepaired",
    "hybrid_repaired_balance_a0p3_minmax": "balance_repaired",
    "rrf": "rrf",
    "combsum": "combsum",
}
PAIR_METHODS = (
    ("copeland", "hybrid_unrepaired_copeland_a0p3_minmax", "hybrid_repaired_copeland_a0p3_minmax"),
    ("balance", "hybrid_unrepaired_balance_a0p3_minmax", "hybrid_repaired_balance_a0p3_minmax"),
)
PLOT_COLORS = {
    "raw": "#334155",
    "minmax_query_ranker": "#1d4ed8",
    "zscore_query_ranker": "#0f766e",
    "rank_percentile": "#b45309",
    "unit_vote": "#7c3aed",
}


def _load_method_audit_module():
    path = REPO_ROOT / "experiments" / "method_improvement_audit_20260711_205733" / "run_method_improvement_audit.py"
    spec = importlib.util.spec_from_file_location("b3_method_audit_module", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


METHOD_AUDIT_MOD = _load_method_audit_module()


@dataclass(frozen=True)
class ThresholdConfig:
    vote_thresholds: dict[str, float]
    aggregate_threshold: float
    min_support: int
    postprocess_drop_mutual: bool
    target_vote_rates: dict[str, float] | None
    target_edge_count: int | None
    notes: str


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(type(obj).__name__)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _norm_minmax(scores: dict[str, float]) -> dict[str, float]:
    return METHOD_AUDIT_MOD._norm_minmax(scores)


def _norm_zscore(scores: dict[str, float]) -> dict[str, float]:
    return METHOD_AUDIT_MOD._norm_zscore(scores)


def _rank_scores(scores: dict[str, float]) -> dict[str, float]:
    return METHOD_AUDIT_MOD._rank_scores(scores)


def _align_ranking(ranking: list[str], rel_map: dict[str, int]) -> list[str]:
    return METHOD_AUDIT_MOD._align_ranking(ranking, rel_map)


def bootstrap_ci(values: list[float], reps: int = 10_000, seed: int = 13) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    samples = rng.choice(arr, size=(reps, arr.size), replace=True).mean(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    frac_gt_zero = float(np.mean(samples > 0.0))
    return float(lo), float(hi), frac_gt_zero


def paired_permutation_pvalue(deltas: list[float], reps: int = 10_000, seed: int = 17) -> float | None:
    if not deltas:
        return None
    arr = np.asarray(deltas, dtype=float)
    observed = abs(float(arr.mean()))
    rng = np.random.default_rng(seed)
    flips = rng.choice(np.array([-1.0, 1.0]), size=(reps, arr.size), replace=True)
    perm_means = np.abs((flips * arr).mean(axis=1))
    return float((np.sum(perm_means >= observed) + 1) / (reps + 1))


def delta_summary(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {
            "mean_delta": None,
            "median_delta": None,
            "q05_delta": None,
            "q25_delta": None,
            "q75_delta": None,
            "q95_delta": None,
        }
    arr = np.asarray(deltas, dtype=float)
    q05, q25, q75, q95 = np.quantile(arr, [0.05, 0.25, 0.75, 0.95])
    return {
        "mean_delta": float(arr.mean()),
        "median_delta": float(np.median(arr)),
        "q05_delta": float(q05),
        "q25_delta": float(q25),
        "q75_delta": float(q75),
        "q95_delta": float(q95),
    }


def jaccard(a: set[tuple[str, str]], b: set[tuple[str, str]]) -> float | None:
    if not a and not b:
        return 1.0
    if not a and b:
        return 0.0
    if a and not b:
        return 0.0
    return float(len(a & b) / len(a | b))


def _rank_percentile_scores(scores: dict[str, float]) -> dict[str, float]:
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    n = len(ranked)
    if n == 0:
        return {}
    if n == 1:
        return {ranked[0][0]: 1.0}
    out: dict[str, float] = {}
    for idx, (doc_id, _score) in enumerate(ranked):
        out[doc_id] = 1.0 - (idx / (n - 1))
    return out


def _robust_iqr_scores(scores: dict[str, float]) -> tuple[dict[str, float], bool]:
    if not scores:
        return {}, False
    vals = np.asarray(list(scores.values()), dtype=float)
    median = float(np.median(vals))
    q1, q3 = np.quantile(vals, [0.25, 0.75])
    iqr = float(q3 - q1)
    if iqr <= 1.0e-12:
        return ({doc_id: 0.0 for doc_id in scores}, True)
    return ({doc_id: (float(score) - median) / iqr for doc_id, score in scores.items()}, False)


def calibrate_query_ranker_scores(
    scores: dict[str, float],
    *,
    calibration: str,
) -> tuple[dict[str, float], dict[str, Any]]:
    if calibration == "raw":
        return dict(scores), {"zero_variance": False, "tie_rule": "native"}
    if calibration == "minmax_query_ranker":
        vals = list(scores.values())
        zero_var = bool(vals) and (max(vals) - min(vals) <= 1.0e-12)
        return _norm_minmax(scores), {"zero_variance": zero_var, "tie_rule": "native"}
    if calibration == "zscore_query_ranker":
        vals = list(scores.values())
        zero_var = bool(vals) and (statistics.pstdev(vals) <= 1.0e-12)
        return _norm_zscore(scores), {"zero_variance": zero_var, "tie_rule": "native"}
    if calibration == "rank_percentile":
        return _rank_percentile_scores(scores), {
            "zero_variance": False,
            "tie_rule": "sort by (-score, doc_id) then assign descending unique percentiles",
        }
    if calibration == "unit_vote":
        return dict(scores), {"zero_variance": False, "tie_rule": "native"}
    raise ValueError(f"Unknown calibration: {calibration}")


def apply_calibration_to_score_maps(
    raw_scores_by_ranker: dict[str, dict[str, float]],
    candidate_pool: list[str],
    *,
    calibration: str,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, Any]]]:
    calibrated: dict[str, dict[str, float]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for ranker in RANKERS:
        score_map = raw_scores_by_ranker.get(ranker, {})
        restricted = {doc_id: score_map[doc_id] for doc_id in candidate_pool if doc_id in score_map}
        calibrated_scores, meta = calibrate_query_ranker_scores(restricted, calibration=calibration)
        calibrated[ranker] = calibrated_scores
        metadata[ranker] = meta
    return calibrated, metadata


def base_variant_parameters(regime: str) -> tuple[int, float, bool]:
    if regime == "ms2":
        return 2, 0.1, False
    if regime == "ms1":
        return 1, 0.0, False
    if regime == "ms1_drop_mutual":
        return 1, 0.0, True
    raise ValueError(regime)


def _vote_rows_from_direction_maps(
    query_id: str,
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]],
    *,
    min_support: int,
    aggregate_threshold: float,
    drop_mutual: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair_key in sorted(direction_maps):
        dir_votes = direction_maps[pair_key]
        kept: dict[tuple[str, str], list[tuple[str, float]]] = {}
        for direction, recs in dir_votes.items():
            support = len(recs)
            agg_weight = sum(weight for _ranker, weight in recs)
            if support < min_support:
                continue
            if agg_weight < aggregate_threshold:
                continue
            kept[direction] = recs
        if drop_mutual and len(kept) > 1:
            continue
        for (winner, loser), recs in sorted(kept.items()):
            for ranker, weight in recs:
                rows.append(
                    {
                        "query_id": query_id,
                        "winner_doc_id": winner,
                        "loser_doc_id": loser,
                        "weight": float(weight),
                        "voter": ranker,
                    }
                )
    return rows


def build_query_vote_artifacts(
    *,
    query_id: str,
    raw_scores_by_ranker: dict[str, dict[str, float]],
    candidate_pool: list[str],
    calibration: str,
    threshold_config: ThresholdConfig,
) -> dict[str, Any]:
    calibrated_scores, calibration_meta = apply_calibration_to_score_maps(
        raw_scores_by_ranker,
        candidate_pool,
        calibration=calibration,
    )
    pair_margins_by_ranker: dict[str, list[float]] = {ranker: [] for ranker in RANKERS}
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
    retained_vote_counts: dict[str, int] = defaultdict(int)
    retained_weight_sums: dict[str, float] = defaultdict(float)

    for ranker in RANKERS:
        score_map = calibrated_scores.get(ranker, {})
        if calibration == "unit_vote":
            raw_direction_map = {doc_id: raw_scores_by_ranker.get(ranker, {}).get(doc_id) for doc_id in candidate_pool if doc_id in raw_scores_by_ranker.get(ranker, {})}
        else:
            raw_direction_map = score_map
        threshold = float(threshold_config.vote_thresholds.get(ranker, 0.0))
        for a, b in combinations(candidate_pool, 2):
            if a not in raw_direction_map or b not in raw_direction_map:
                continue
            direction_a = raw_direction_map[a]
            direction_b = raw_direction_map[b]
            if direction_a == direction_b:
                continue
            if calibration == "unit_vote":
                raw_margin_map = raw_scores_by_ranker.get(ranker, {})
                margin = abs(float(raw_margin_map[a]) - float(raw_margin_map[b]))
            else:
                margin = abs(float(score_map[a]) - float(score_map[b]))
            pair_margins_by_ranker[ranker].append(float(margin))
            if margin < threshold:
                continue
            if direction_a > direction_b:
                winner, loser = a, b
            else:
                winner, loser = b, a
            pair_key = (a, b) if a < b else (b, a)
            vote_weight = 1.0 if calibration == "unit_vote" else float(margin)
            direction_maps[pair_key][(winner, loser)].append((ranker, vote_weight))
            retained_vote_counts[ranker] += 1
            retained_weight_sums[ranker] += vote_weight

    rows = _vote_rows_from_direction_maps(
        query_id,
        direction_maps,
        min_support=threshold_config.min_support,
        aggregate_threshold=threshold_config.aggregate_threshold,
        drop_mutual=threshold_config.postprocess_drop_mutual,
    )

    return {
        "query_id": query_id,
        "candidate_pool": list(candidate_pool),
        "calibrated_scores": calibrated_scores,
        "calibration_meta": calibration_meta,
        "pair_margins_by_ranker": pair_margins_by_ranker,
        "retained_vote_counts": dict(retained_vote_counts),
        "retained_weight_sums": dict(retained_weight_sums),
        "rows": rows,
    }


def direction_maps_for_query(
    *,
    raw_scores_by_ranker: dict[str, dict[str, float]],
    candidate_pool: list[str],
    calibration: str,
    vote_thresholds: dict[str, float],
) -> dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]]:
    artifacts = build_query_vote_artifacts(
        query_id="__threshold_probe__",
        raw_scores_by_ranker=raw_scores_by_ranker,
        candidate_pool=candidate_pool,
        calibration=calibration,
        threshold_config=ThresholdConfig(
            vote_thresholds=vote_thresholds,
            aggregate_threshold=0.0,
            min_support=1,
            postprocess_drop_mutual=False,
            target_vote_rates=None,
            target_edge_count=None,
            notes="threshold probe",
        ),
    )
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))
    for ranker in RANKERS:
        score_map = artifacts["calibrated_scores"].get(ranker, {})
        if calibration == "unit_vote":
            raw_direction_map = {doc_id: raw_scores_by_ranker.get(ranker, {}).get(doc_id) for doc_id in candidate_pool if doc_id in raw_scores_by_ranker.get(ranker, {})}
        else:
            raw_direction_map = score_map
        threshold = float(vote_thresholds.get(ranker, 0.0))
        for a, b in combinations(candidate_pool, 2):
            if a not in raw_direction_map or b not in raw_direction_map:
                continue
            da = raw_direction_map[a]
            db = raw_direction_map[b]
            if da == db:
                continue
            if calibration == "unit_vote":
                raw_margin_map = raw_scores_by_ranker.get(ranker, {})
                margin = abs(float(raw_margin_map[a]) - float(raw_margin_map[b]))
            else:
                margin = abs(float(score_map[a]) - float(score_map[b]))
            if margin < threshold:
                continue
            if da > db:
                winner, loser = a, b
            else:
                winner, loser = b, a
            pair_key = (a, b) if a < b else (b, a)
            vote_weight = 1.0 if calibration == "unit_vote" else float(margin)
            direction_maps[pair_key][(winner, loser)].append((ranker, vote_weight))
    return direction_maps


def count_edges_from_direction_maps(
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]],
    *,
    regime: str,
    aggregate_threshold: float,
) -> int:
    min_support, _default_threshold, drop_mutual = base_variant_parameters(regime)
    rows = _vote_rows_from_direction_maps(
        "__count__",
        direction_maps,
        min_support=min_support,
        aggregate_threshold=aggregate_threshold,
        drop_mutual=drop_mutual,
    )
    return len({(row["winner_doc_id"], row["loser_doc_id"]) for row in rows})


def _edge_candidates_for_threshold_search(
    direction_maps: dict[tuple[str, str], dict[tuple[str, str], list[tuple[str, float]]]],
    *,
    min_support: int,
) -> list[list[float]]:
    pair_candidates: list[list[float]] = []
    for dir_votes in direction_maps.values():
        weights: list[float] = []
        for recs in dir_votes.values():
            if len(recs) < min_support:
                continue
            weights.append(sum(weight for _ranker, weight in recs))
        if weights:
            pair_candidates.append(weights)
    return pair_candidates


def _best_aggregate_threshold_from_candidates(
    per_query_candidates: list[list[list[float]]],
    *,
    drop_mutual: bool,
    baseline_edge_count: int,
) -> float:
    events: dict[float, list[int]] = defaultdict(list)
    active_counts: list[int] = []

    def _contribution(active: int) -> int:
        if drop_mutual:
            return active if active <= 1 else 0
        return active

    pair_id = 0
    for query_candidates in per_query_candidates:
        for pair_weights in query_candidates:
            active_counts.append(0)
            for weight in pair_weights:
                events[float(weight)].append(pair_id)
            pair_id += 1

    if not events:
        return 0.0

    best_threshold = 0.0
    best_gap = abs(0 - baseline_edge_count)
    current_total_edges = 0
    for threshold in sorted(events, reverse=True):
        for current_pair_id in events[threshold]:
            before = active_counts[current_pair_id]
            after = before + 1
            current_total_edges += _contribution(after) - _contribution(before)
            active_counts[current_pair_id] = after
        gap = abs(current_total_edges - baseline_edge_count)
        if best_gap is None or gap < best_gap or (gap == best_gap and threshold < best_threshold):
            best_gap = gap
            best_threshold = float(threshold)

    gap_zero = abs(current_total_edges - baseline_edge_count)
    if gap_zero < best_gap or (gap_zero == best_gap and 0.0 < best_threshold):
        return 0.0
    return best_threshold


def choose_threshold_config(
    *,
    dataset: str,
    regime: str,
    calibration: str,
    threshold_mode: str,
    baseline_vote_rates: dict[str, float],
    baseline_edge_count: int,
    calibration_pair_margins: dict[str, list[float]],
    per_query_inputs: list[dict[str, Any]],
) -> ThresholdConfig:
    min_support, default_agg, drop_mutual = base_variant_parameters(regime)
    if threshold_mode == "fixed_numeric":
        return ThresholdConfig(
            vote_thresholds={ranker: 0.05 for ranker in RANKERS},
            aggregate_threshold=default_agg,
            min_support=min_support,
            postprocess_drop_mutual=drop_mutual,
            target_vote_rates=None,
            target_edge_count=None,
            notes="fixed canonical numeric thresholds",
        )

    if calibration == "raw":
        return ThresholdConfig(
            vote_thresholds={ranker: 0.05 for ranker in RANKERS},
            aggregate_threshold=default_agg,
            min_support=min_support,
            postprocess_drop_mutual=drop_mutual,
            target_vote_rates=baseline_vote_rates,
            target_edge_count=baseline_edge_count,
            notes="retention target is the raw baseline; thresholds unchanged",
        )

    vote_thresholds: dict[str, float] = {}
    for ranker in RANKERS:
        vals = calibration_pair_margins.get(ranker, [])
        target_rate = baseline_vote_rates.get(ranker, 0.0)
        if not vals:
            vote_thresholds[ranker] = 0.0
            continue
        if calibration == "unit_vote":
            vote_thresholds[ranker] = 0.05
            continue
        q = max(0.0, min(1.0, 1.0 - target_rate))
        vote_thresholds[ranker] = float(np.quantile(np.asarray(vals, dtype=float), q))

    if calibration == "unit_vote":
        candidate_thresholds = [0.0, 1.0, 2.0, 3.0]
    else:
        per_query_candidates: list[list[list[float]]] = []
        for item in per_query_inputs:
            direction_maps = direction_maps_for_query(
                raw_scores_by_ranker=item["raw_scores_by_ranker"],
                candidate_pool=item["candidate_pool"],
                calibration=calibration,
                vote_thresholds=vote_thresholds,
            )
            per_query_candidates.append(
                _edge_candidates_for_threshold_search(
                    direction_maps,
                    min_support=min_support,
                )
            )
        best_threshold = _best_aggregate_threshold_from_candidates(
            per_query_candidates,
            drop_mutual=drop_mutual,
            baseline_edge_count=baseline_edge_count,
        )
        return ThresholdConfig(
            vote_thresholds=vote_thresholds,
            aggregate_threshold=best_threshold,
            min_support=min_support,
            postprocess_drop_mutual=drop_mutual,
            target_vote_rates=baseline_vote_rates,
            target_edge_count=baseline_edge_count,
            notes=(
                "vote thresholds matched to raw per-ranker retained-vote rates across the dataset; "
                "aggregate threshold chosen to minimize absolute retained-edge-count gap versus raw for this regime"
            ),
        )

    best_threshold = 0.0
    best_gap = None
    for agg_threshold in candidate_thresholds:
        total_edges = 0
        for item in per_query_inputs:
            direction_maps = direction_maps_for_query(
                raw_scores_by_ranker=item["raw_scores_by_ranker"],
                candidate_pool=item["candidate_pool"],
                calibration=calibration,
                vote_thresholds=vote_thresholds,
            )
            total_edges += count_edges_from_direction_maps(
                direction_maps,
                regime=regime,
                aggregate_threshold=float(agg_threshold),
            )
        gap = abs(total_edges - baseline_edge_count)
        if best_gap is None or gap < best_gap or (gap == best_gap and agg_threshold < best_threshold):
            best_gap = gap
            best_threshold = float(agg_threshold)

    return ThresholdConfig(
        vote_thresholds=vote_thresholds,
        aggregate_threshold=best_threshold,
        min_support=min_support,
        postprocess_drop_mutual=drop_mutual,
        target_vote_rates=baseline_vote_rates,
        target_edge_count=baseline_edge_count,
        notes=(
            "vote thresholds matched to raw per-ranker retained-vote rates across the dataset; "
            "aggregate threshold chosen to minimize absolute retained-edge-count gap versus raw for this regime"
        ),
    )


class CalibrationEvaluator:
    def __init__(self) -> None:
        self.audit_runner = METHOD_AUDIT_MOD.AuditRunner()

    def _graph_component_scores(self, graph: nx.DiGraph, method: str) -> dict[str, float]:
        return self.audit_runner._graph_component_scores(graph, method)

    def _hybrid_ranking(
        self,
        prior_scores: dict[str, float],
        component_scores: dict[str, float],
        candidate_nodes: Iterable[str],
        *,
        alpha: float,
        mode: str,
        confidence_weight: float | None = None,
    ) -> list[str]:
        return self.audit_runner._hybrid_ranking(
            prior_scores,
            component_scores,
            candidate_nodes,
            alpha=alpha,
            mode=mode,
            confidence_weight=confidence_weight,
        )

    def _apply_repair(
        self,
        graph: nx.DiGraph,
        prior_scores: dict[str, float],
        *,
        top_k: int,
    ) -> tuple[nx.DiGraph, dict[str, Any]]:
        return self.audit_runner._apply_repair(graph, prior_scores, top_k=top_k, mode="greedy")

    def evaluate_query(
        self,
        *,
        dataset: str,
        query_id: str,
        qrels_for_query: list[Any],
        vote_regime: str,
        top_k: int,
        candidate_pool: list[str],
        vote_rows: list[dict[str, Any]],
        raw_score_maps_by_ranker: dict[str, list[tuple[str, float]]],
    ) -> dict[str, Any] | None:
        prefs = [
            Preference(
                winner=str(row["winner_doc_id"]),
                loser=str(row["loser_doc_id"]),
                weight=float(row["weight"]),
            )
            for row in vote_rows
        ]
        graph = build_graph(prefs)
        graph.add_nodes_from(candidate_pool)
        if graph.number_of_nodes() < 2:
            return None

        candidate_nodes = list(candidate_pool)
        ref_ranking, rel_map = _reference_ranking_for_candidates(qrels_for_query, candidate_nodes)
        score_prior_sets = [{query_id: raw_score_maps_by_ranker[r]} for r in RANKERS if raw_score_maps_by_ranker.get(r)]
        prior_scores = _rrf_prior_scores_for_query(
            query_id=query_id,
            candidate_nodes=set(candidate_nodes),
            score_prior_sets=score_prior_sets,
            fallback_scores=_score_sum_prior_scores(graph),
        )
        repaired_graph, repair_info = self._apply_repair(graph, prior_scores, top_k=top_k)
        repaired_graph.add_nodes_from(candidate_pool)

        graph_stats = extended_graph_stats(graph, prior_scores=prior_scores, ref_ranking=ref_ranking)
        repaired_stats = extended_graph_stats(repaired_graph, prior_scores=prior_scores, ref_ranking=ref_ranking)
        confidence_weight = min(1.0, float(graph_stats.get("edge_weight_mean", 0.0)) / 5.0 if graph.number_of_edges() else 0.0)
        raw_edges = {(u, v) for u, v in graph.edges()}
        repaired_edges = {(u, v) for u, v in repaired_graph.edges()}
        removed_edges = raw_edges - repaired_edges
        mutual_removed_graph = graph.copy()
        for u, v in list(graph.edges()):
            if graph.has_edge(v, u):
                mutual_removed_graph.remove_edge(u, v)
        mutual_removed_stats = extended_graph_stats(mutual_removed_graph, prior_scores=prior_scores, ref_ranking=ref_ranking)

        method_outputs: dict[str, dict[str, Any]] = {}

        def add_method(name: str, ranking: list[str], scores: dict[str, float] | None = None) -> None:
            aligned = _align_ranking(ranking, rel_map)
            ndcg = _ndcg_at_k(aligned, rel_map, k=top_k)
            mapk = _average_precision_at_k(aligned, rel_map, k=top_k)
            pk, rk = _precision_recall_at_k(aligned, rel_map, k=top_k)
            method_outputs[name] = {
                "ranking": ranking,
                "scores": scores or _rank_scores({d: float(len(ranking) - i) for i, d in enumerate(ranking)}),
                "ndcg_at_k": ndcg,
                "map_at_k": mapk,
                "precision_at_k": pk,
                "recall_at_k": rk,
                "pairwise_accuracy": _pairwise_accuracy_from_relevance(aligned, rel_map),
                "kendall_tau": _kendall_tau(aligned, ref_ranking),
            }

        score_sum_raw = score_sum_scores(graph)
        score_sum_rep = score_sum_scores(repaired_graph)
        copeland_raw = self._graph_component_scores(graph, "copeland")
        copeland_rep = self._graph_component_scores(repaired_graph, "copeland")
        balance_raw = self._graph_component_scores(graph, "balance")
        balance_rep = self._graph_component_scores(repaired_graph, "balance")

        add_method("prior_only", _prior_only_ranking(candidate_nodes, prior_scores), prior_scores)
        add_method("rrf", per_query_rrf_ranking_from_score_maps(query_id, score_prior_sets, candidate_nodes, k=DEFAULT_RRF_K))
        add_method("combsum", per_query_combsum_ranking_from_score_maps(query_id, score_prior_sets, candidate_nodes, normalization=COMBSUM_NORM_MINMAX))
        add_method("borda_fuse", per_query_borda_fuse_ranking_from_score_maps(query_id, score_prior_sets, candidate_nodes))
        add_method("score_sum", score_sum_ranking(graph), score_sum_raw)
        add_method("borda", borda_ranking(graph), borda_scores(graph))
        add_method("copeland_graph", copeland_ranking(graph), copeland_raw)
        add_method("copeland_graph_repaired", copeland_ranking(repaired_graph), copeland_rep)
        add_method("balance_graph", weighted_out_minus_in_ranking(graph), balance_raw)
        add_method("balance_graph_repaired", weighted_out_minus_in_ranking(repaired_graph), balance_rep)
        add_method("markov_graph", markov_graph_ranking(graph), markov_graph_scores(graph, damping=DEFAULT_MARKOV_DAMPING))
        add_method("markov_graph_repaired", markov_graph_ranking(repaired_graph), markov_graph_scores(repaired_graph, damping=DEFAULT_MARKOV_DAMPING))
        add_method("topological_repaired", topological_ranking(repaired_graph))
        add_method("priority_topological_repaired", priority_topological_ranking(repaired_graph, prior_scores))
        add_method("hybrid_unrepaired_copeland_a0p3_minmax", self._hybrid_ranking(prior_scores, copeland_raw, candidate_nodes, alpha=0.3, mode="minmax", confidence_weight=confidence_weight))
        add_method("hybrid_repaired_copeland_a0p3_minmax", self._hybrid_ranking(prior_scores, copeland_rep, candidate_nodes, alpha=0.3, mode="minmax", confidence_weight=confidence_weight))
        add_method("hybrid_unrepaired_balance_a0p3_minmax", self._hybrid_ranking(prior_scores, balance_raw, candidate_nodes, alpha=0.3, mode="minmax", confidence_weight=confidence_weight))
        add_method("hybrid_repaired_balance_a0p3_minmax", self._hybrid_ranking(prior_scores, balance_rep, candidate_nodes, alpha=0.3, mode="minmax", confidence_weight=confidence_weight))

        return {
            "dataset": dataset,
            "query_id": query_id,
            "vote_regime": vote_regime,
            "candidate_pool": candidate_pool,
            "graph": graph,
            "repaired_graph": repaired_graph,
            "graph_stats": graph_stats,
            "repaired_graph_stats": repaired_stats,
            "mutual_removed_stats": mutual_removed_stats,
            "prior_scores": prior_scores,
            "ref_ranking": ref_ranking,
            "rel_map": rel_map,
            "method_outputs": method_outputs,
            "repair_info": repair_info,
            "raw_edges": raw_edges,
            "removed_edges": removed_edges,
            "graph_bew_pre": _backward_edge_weight(graph, ref_ranking),
            "graph_bew_post": _backward_edge_weight(repaired_graph, ref_ranking),
            "graph_pic_pre": _pairwise_inconsistency(graph, ref_ranking),
            "graph_pic_post": _pairwise_inconsistency(repaired_graph, ref_ranking),
        }


def prepare_dataset_inputs(dataset: str) -> dict[str, Any]:
    manifest_path = REPO_ROOT / "experiments" / "method_improvement_audit_20260711_205733" / "phase_reports" / "canonical_rerun_manifest.json"
    manifest = _load_manifest(manifest_path)
    specs = _dataset_specs(manifest)
    spec = specs[dataset]
    query_ids = [line.strip() for line in spec.query_ids_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw_score_maps_by_ranker = {ranker: _load_score_file(spec.score_files[ranker]) for ranker in RANKERS}
    queries, documents, qrels = load_dataset_splits(dataset)
    qrels_by_query: dict[str, list[Any]] = defaultdict(list)
    for entry in qrels:
        qrels_by_query[entry.query_id].append(entry)
    candidate_pools: dict[str, list[str]] = {}
    per_query_inputs: list[dict[str, Any]] = []
    for qid in query_ids:
        ranker_scores = {ranker: raw_score_maps_by_ranker[ranker].get(qid, {}) for ranker in RANKERS}
        candidate_pool = _select_candidates(ranker_scores, spec.top_k)
        candidate_pools[qid] = candidate_pool
        per_query_inputs.append(
            {
                "query_id": qid,
                "candidate_pool": candidate_pool,
                "raw_scores_by_ranker": ranker_scores,
                "qrels_for_query": qrels_by_query.get(qid, []),
            }
        )
    return {
        "dataset": dataset,
        "spec": spec,
        "query_ids": query_ids,
        "raw_score_maps_by_ranker": raw_score_maps_by_ranker,
        "qrels_by_query": qrels_by_query,
        "candidate_pools": candidate_pools,
        "per_query_inputs": per_query_inputs,
        "qrels_hash": sha256_file(get_config(dataset).processed_path / "qrels.jsonl"),
    }


def raw_baseline_statistics(dataset_inputs: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    per_query_inputs = dataset_inputs["per_query_inputs"]
    dataset = dataset_inputs["dataset"]
    for regime in REGIMES:
        min_support, agg_threshold, drop_mutual = base_variant_parameters(regime)
        total_edges = 0
        vote_rate_counts: dict[str, dict[str, int]] = {
            ranker: {"possible": 0, "retained": 0} for ranker in RANKERS
        }
        for item in per_query_inputs:
            artifacts = build_query_vote_artifacts(
                query_id=item["query_id"],
                raw_scores_by_ranker=item["raw_scores_by_ranker"],
                candidate_pool=item["candidate_pool"],
                calibration="raw",
                threshold_config=ThresholdConfig(
                    vote_thresholds={ranker: 0.05 for ranker in RANKERS},
                    aggregate_threshold=agg_threshold,
                    min_support=min_support,
                    postprocess_drop_mutual=drop_mutual,
                    target_vote_rates=None,
                    target_edge_count=None,
                    notes="raw baseline",
                ),
            )
            total_edges += len({(row["winner_doc_id"], row["loser_doc_id"]) for row in artifacts["rows"]})
            for ranker in RANKERS:
                possible = 0
                score_map = item["raw_scores_by_ranker"].get(ranker, {})
                for a, b in combinations(item["candidate_pool"], 2):
                    if a in score_map and b in score_map and score_map[a] != score_map[b]:
                        possible += 1
                vote_rate_counts[ranker]["possible"] += possible
                vote_rate_counts[ranker]["retained"] += int(artifacts["retained_vote_counts"].get(ranker, 0))
        results[regime] = {
            "edge_count": total_edges,
            "vote_rates": {
                ranker: (
                    vote_rate_counts[ranker]["retained"] / vote_rate_counts[ranker]["possible"]
                    if vote_rate_counts[ranker]["possible"] else 0.0
                )
                for ranker in RANKERS
            },
        }
    return results


def summarize_structural_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    usable = len(records)
    if usable == 0:
        return {
            "usable_query_count": 0,
            "mean_candidate_count": None,
            "mean_edge_count": None,
            "graph_density": None,
            "mutual_pair_count": None,
            "pct_queries_with_mutual_pair": None,
            "cyclic_query_pct": None,
            "cyclic_query_pct_after_mutual_deletion": None,
            "mean_largest_scc": None,
            "mean_largest_scc_after_mutual_deletion": None,
            "mean_total_graph_weight": None,
            "mean_normalized_graph_weight": None,
            "mean_fas_edges_removed": None,
            "mean_fas_weight_removed": None,
            "mean_normalized_fas_weight_removed": None,
        }
    def _mean(xs: list[float]) -> float:
        return float(sum(xs) / len(xs)) if xs else 0.0

    candidate_counts = [len(rec["candidate_pool"]) for rec in records]
    edge_counts = [rec["graph"].number_of_edges() for rec in records]
    densities = [nx.density(rec["graph"]) if rec["graph"].number_of_nodes() > 1 else 0.0 for rec in records]
    mutual_pairs = [int(rec["graph_stats"].get("n_mutual_pairs", 0)) for rec in records]
    cyclic = [bool(rec["graph_stats"].get("is_cyclic")) for rec in records]
    cyclic_after_mutual = [bool(rec["mutual_removed_stats"].get("is_cyclic")) for rec in records]
    largest_scc = [int(rec["graph_stats"].get("largest_scc_size", 0)) for rec in records]
    largest_scc_after = [int(rec["mutual_removed_stats"].get("largest_scc_size", 0)) for rec in records]
    total_weight = [float(rec["graph_stats"].get("total_edge_weight", 0.0)) for rec in records]
    normalized_weight = [
        float(rec["graph_stats"].get("total_edge_weight", 0.0)) / max(1, rec["graph"].number_of_edges())
        for rec in records
    ]
    fas_edges_removed = [int(rec["repair_info"].get("n_edges_removed", 0)) for rec in records]
    fas_weight_removed = [float(rec["repair_info"].get("removed_weight", 0.0)) for rec in records]
    normalized_fas = [
        (float(rec["repair_info"].get("removed_weight", 0.0)) / float(rec["graph_stats"].get("total_edge_weight", 0.0)))
        if float(rec["graph_stats"].get("total_edge_weight", 0.0)) > 0 else 0.0
        for rec in records
    ]
    return {
        "usable_query_count": usable,
        "mean_candidate_count": _mean(candidate_counts),
        "mean_edge_count": _mean(edge_counts),
        "graph_density": _mean(densities),
        "mutual_pair_count": _mean(mutual_pairs),
        "pct_queries_with_mutual_pair": float(sum(1 for x in mutual_pairs if x > 0) / usable),
        "cyclic_query_pct": float(sum(1 for x in cyclic if x) / usable),
        "cyclic_query_pct_after_mutual_deletion": float(sum(1 for x in cyclic_after_mutual if x) / usable),
        "mean_largest_scc": _mean(largest_scc),
        "mean_largest_scc_after_mutual_deletion": _mean(largest_scc_after),
        "mean_total_graph_weight": _mean(total_weight),
        "mean_normalized_graph_weight": _mean(normalized_weight),
        "mean_fas_edges_removed": _mean(fas_edges_removed),
        "mean_fas_weight_removed": _mean(fas_weight_removed),
        "mean_normalized_fas_weight_removed": _mean(normalized_fas),
    }


def render_line_plot(
    df: pd.DataFrame,
    *,
    out_base: Path,
    x_col: str,
    y_col: str,
    hue_col: str,
    facet_col: str | None,
    title: str,
    y_label: str,
) -> None:
    if df.empty:
        return
    if facet_col:
        facets = list(dict.fromkeys(df[facet_col]))
        fig, axes = plt.subplots(1, len(facets), figsize=(6 * len(facets), 4.8), squeeze=False)
        axes_list = axes[0]
    else:
        fig, ax = plt.subplots(figsize=(6.5, 4.8))
        facets = [None]
        axes_list = [ax]
    for ax, facet in zip(axes_list, facets):
        subset = df if facet is None else df[df[facet_col] == facet]
        for hue in dict.fromkeys(subset[hue_col]):
            lines = subset[subset[hue_col] == hue]
            ax.plot(
                lines[x_col],
                lines[y_col],
                marker="o",
                linewidth=2,
                color=PLOT_COLORS.get(str(hue), "#334155"),
                label=str(hue),
            )
        if facet is not None:
            ax.set_title(str(facet))
        ax.set_ylabel(y_label)
        ax.set_xlabel(x_col.replace("_", " "))
        ax.grid(alpha=0.3, linestyle="--")
    axes_list[0].legend(frameon=False, fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=180)
    plt.close(fig)


def render_stacked_counts(
    df: pd.DataFrame,
    *,
    out_base: Path,
    category_cols: list[str],
    count_cols: list[str],
    title: str,
) -> None:
    if df.empty:
        return
    labels = [" | ".join(str(row[col]) for col in category_cols) for _, row in df.iterrows()]
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    colors = {"helped_query_count": "#0f766e", "harmed_query_count": "#b91c1c", "unchanged_query_count": "#64748b"}
    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.55), 5))
    for col in count_cols:
        vals = df[col].to_numpy(dtype=float)
        ax.bar(x, vals, bottom=bottom, label=col.replace("_query_count", ""), color=colors.get(col, "#334155"))
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("query count")
    ax.set_title(title)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    fig.tight_layout()
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=180)
    plt.close(fig)
