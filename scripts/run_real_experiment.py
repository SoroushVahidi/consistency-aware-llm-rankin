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

    # Synthetic conflict stress-test (qrels-derived + flips)
    python scripts/run_real_experiment.py --dataset scidocs \\
        --preference-source qrels_flip --flip-prob 0.15 --max-queries 50 --top-k 20

    # External score-derived preferences
    python scripts/run_real_experiment.py --dataset scidocs \\
        --preference-source score_file --score-file path/to/scores.jsonl

    # External pairwise preferences (LLM or multi-ranker votes)
    python scripts/run_real_experiment.py --dataset scidocs \\
        --preference-source llm_pairwise_file --pairwise-file path/to/pairs.jsonl


Outputs (under ``--output-dir``, default ``outputs/real_full``):
- ``<dataset>/<preference_source>/<dataset>_per_query.csv``      per-query × per-method results
- ``<dataset>/<preference_source>/<dataset>_summary.csv``        aggregate statistics per method
- ``<dataset>/<preference_source>/timings/<dataset>_timings.csv``  timing data (CSV)
- ``<dataset>/<preference_source>/timings/<dataset>_timings.json`` timing data (JSON)
- ``<dataset>/<preference_source>/plots/``                       timing plots (if matplotlib available)


from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Allow running as `python scripts/run_real_experiment.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    fas_balance_score_prior_alpha_beta_ranking,
    pagerank_ranking,
    score_sum_ranking,
    score_sum_scores,
    topological_ranking,
)
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.data.unified_loader import (
    load_dataset_splits,
    preferences_from_qrels,
)
from consistency_ranker.data.query_ids import (
    eligible_query_ids,
    has_usable_eval_labels,
    load_query_ids_file,
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

NON_HYBRID_METHODS = (
    "score_sum",
    "borda",
    "pagerank",
    "greedy_fas_topological",
    "greedy_fas_weighted_balance",
    "greedy_fas_copeland",
    "greedy_fas_score_augmented_topological",
    "fas_balance_score_prior_alpha_beta",
)
"""Core baseline/FAS methods always evaluated."""


@dataclass(frozen=True)
class HybridMethodSpec:
    """Configuration for one hybrid ranking method."""

    name: str
    component: str
    alpha: float
    use_repaired_graph: bool
    mode: str = "score_component"  # score_component | priority_topological | prior_only


DEFAULT_HYBRID_SPECS = (
    HybridMethodSpec(
        name="hybrid_rrf_fas_regularized",
        component="balance",
        alpha=0.2,
        use_repaired_graph=True,
    ),
    HybridMethodSpec(
        name="hybrid_rrf_balance_a05",
        component="balance",
        alpha=0.5,
        use_repaired_graph=True,
    ),
    HybridMethodSpec(
        name="hybrid_rrf_copeland_a03",
        component="copeland",
        alpha=0.3,
        use_repaired_graph=True,
    ),
    HybridMethodSpec(
        name="hybrid_rrf_priority_topo_a03",
        component="balance",
        alpha=0.3,
        use_repaired_graph=True,
        mode="priority_topological",
    ),
)
"""Default hybrid methods for standard runs."""

PRIMARY_QUALITY_METRIC = "ndcg_at_k"
"""Primary ranking-quality metric for real-data evaluation."""

PREFERENCE_SOURCES = (
    "qrels",
    "qrels_flip",
    "score_file",
    "llm_pairwise_file",
    "votes_file",
)
"""Supported pairwise-preference sources for real-data experiments."""

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


def _reference_ranking_for_candidates(
    qrels_for_query: list,
    candidates: set[str] | list[str],
) -> tuple[list[str], dict[str, int]]:
    """Build candidate-aligned qrels reference ranking.

    Returns
    -------
    tuple[list[str], dict[str, int]]
        (reference ranking over all candidate docs, relevance map)
    """
    rel_map: dict[str, int] = {}
    for e in qrels_for_query:
        # Keep the highest grade if duplicates exist
        rel_map[e.doc_id] = max(rel_map.get(e.doc_id, e.relevance), e.relevance)
    candidate_list = sorted(set(candidates))
    for doc_id in candidate_list:
        rel_map.setdefault(doc_id, 0)
    candidate_list.sort(key=lambda d: (-rel_map[d], d))
    return candidate_list, rel_map


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


def _ndcg_at_k(
    ranking: list[str],
    rel_map: dict[str, int],
    k: int,
) -> float | None:
    """Compute nDCG@k for a ranked list and relevance map."""
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return None

    def _dcg(items: list[str]) -> float:
        total = 0.0
        for i, doc_id in enumerate(items[:k_eff]):
            rel = rel_map.get(doc_id, 0)
            gain = (2.0 ** rel - 1.0) / math.log2(i + 2.0)
            total += gain
        return total

    dcg = _dcg(ranking)
    ideal = sorted(ranking, key=lambda d: rel_map.get(d, 0), reverse=True)
    idcg = _dcg(ideal)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def _precision_recall_at_k(
    ranking: list[str],
    rel_map: dict[str, int],
    k: int,
) -> tuple[float | None, float | None]:
    """Compute precision@k and recall@k for binary relevance rel>0."""
    if not ranking:
        return None, None
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return None, None
    top = ranking[:k_eff]
    hits = sum(1 for d in top if rel_map.get(d, 0) > 0)
    precision = hits / k_eff
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    recall = (hits / total_relevant) if total_relevant > 0 else None
    return precision, recall


def _average_precision_at_k(
    ranking: list[str],
    rel_map: dict[str, int],
    k: int,
) -> float | None:
    """Compute AP@k (binary relevance rel>0)."""
    if not ranking:
        return None
    k_eff = min(k, len(ranking))
    if k_eff <= 0:
        return None
    total_relevant = sum(1 for d in ranking if rel_map.get(d, 0) > 0)
    if total_relevant == 0:
        return None
    hit_count = 0
    ap_sum = 0.0
    for i, d in enumerate(ranking[:k_eff], start=1):
        if rel_map.get(d, 0) > 0:
            hit_count += 1
            ap_sum += hit_count / i
    denom = min(total_relevant, k_eff)
    return ap_sum / denom if denom > 0 else None


def _pairwise_accuracy_from_relevance(
    ranking: list[str],
    rel_map: dict[str, int],
) -> float | None:
    """Pairwise accuracy on judged candidate pairs with different grades."""
    if len(ranking) < 2:
        return None
    pos = {d: i for i, d in enumerate(ranking)}
    docs = list(ranking)
    correct = 0
    total = 0
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            a, b = docs[i], docs[j]
            ra = rel_map.get(a)
            rb = rel_map.get(b)
            if ra is None or rb is None or ra == rb:
                continue
            total += 1
            if (ra > rb and pos[a] < pos[b]) or (rb > ra and pos[b] < pos[a]):
                correct += 1
    return (correct / total) if total > 0 else None


def _weighted_out_minus_in_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank nodes by (weighted out-degree - weighted in-degree)."""
    scores: dict[str, float] = {n: 0.0 for n in graph.nodes()}
    for u, v, data in graph.edges(data=True):
        w = data.get("weight", 1.0)
        scores[u] += w
        scores[v] -= w
    return sorted(scores, key=lambda n: (-scores[n], n))


def _copeland_ranking(graph: nx.DiGraph) -> list[str]:
    """Rank by Copeland wins-losses score on a graph."""
    scores: dict[str, int] = {n: 0 for n in graph.nodes()}
    for n in graph.nodes():
        scores[n] = graph.out_degree(n) - graph.in_degree(n)
    return sorted(scores, key=lambda n: (-scores[n], n))


def _priority_topological_ranking(
    dag: nx.DiGraph,
    priority_scores: dict[str, float],
) -> list[str]:
    """Topological ranking with deterministic priority tie-breaking."""
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = [n for n, d in in_deg.items() if d == 0]
    ranking: list[str] = []
    while available:
        best = max(available, key=lambda n: (priority_scores.get(n, 0.0), n))
        available.remove(best)
        ranking.append(best)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    return ranking


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo <= 1e-12:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _hybrid_rrf_fas_regularized_ranking(
    dag: nx.DiGraph,
    prior_scores: dict[str, float],
    fas_regularization: float = 0.2,
) -> list[str]:
    """Hybrid ranking: score prior + repaired-graph consistency regularizer."""
    if not dag.nodes():
        return []
    balance: dict[str, float] = {n: 0.0 for n in dag.nodes()}
    for u, v, data in dag.edges(data=True):
        w = data.get("weight", 1.0)
        balance[u] += w
        balance[v] -= w
    prior_n = _normalize_scores({n: prior_scores.get(n, 0.0) for n in dag.nodes()})
    bal_n = _normalize_scores(balance)
    combo = {
        n: prior_n.get(n, 0.0) + fas_regularization * bal_n.get(n, 0.0)
        for n in dag.nodes()
    }
    return sorted(combo, key=lambda n: (-combo[n], n))


def _hybrid_rrf_component_ranking(
    dag: nx.DiGraph,
    prior_scores: dict[str, float],
    *,
    component: str = "balance",
    alpha: float = 0.2,
) -> list[str]:
    """Hybrid score ranking from score prior + repaired-graph component."""
    if not dag.nodes():
        return []
    if component == "balance":
        comp_raw: dict[str, float] = {n: 0.0 for n in dag.nodes()}
        for u, v, data in dag.edges(data=True):
            w = data.get("weight", 1.0)
            comp_raw[u] += w
            comp_raw[v] -= w
    elif component == "copeland":
        comp_raw = {n: float(dag.out_degree(n) - dag.in_degree(n)) for n in dag.nodes()}
    else:
        raise ValueError(f"Unknown component: {component!r}")

    prior_n = _normalize_scores({n: prior_scores.get(n, 0.0) for n in dag.nodes()})
    comp_n = _normalize_scores(comp_raw)
    combo = {n: prior_n.get(n, 0.0) + alpha * comp_n.get(n, 0.0) for n in dag.nodes()}
    return sorted(combo, key=lambda n: (-combo[n], n))


def _hybrid_rrf_priority_topological_ranking(
    dag: nx.DiGraph,
    prior_scores: dict[str, float],
    *,
    component: str = "balance",
    alpha: float = 0.3,
) -> list[str]:
    """Hybrid priority topological ranking using prior + repaired component."""
    if component == "balance":
        comp_raw: dict[str, float] = {n: 0.0 for n in dag.nodes()}
        for u, v, data in dag.edges(data=True):
            w = data.get("weight", 1.0)
            comp_raw[u] += w
            comp_raw[v] -= w
    elif component == "copeland":
        comp_raw = {n: float(dag.out_degree(n) - dag.in_degree(n)) for n in dag.nodes()}
    else:
        raise ValueError(f"Unknown component: {component!r}")

    prior_n = _normalize_scores({n: prior_scores.get(n, 0.0) for n in dag.nodes()})
    comp_n = _normalize_scores(comp_raw)
    pri = {n: prior_n.get(n, 0.0) + alpha * comp_n.get(n, 0.0) for n in dag.nodes()}
    return _priority_topological_ranking(dag, pri)


def _prior_only_ranking(
    candidate_nodes: Iterable[str],
    prior_scores: dict[str, float],
) -> list[str]:
    """Rank by score prior only."""
    return sorted(candidate_nodes, key=lambda n: (-prior_scores.get(n, 0.0), n))


def _alpha_token(alpha: float) -> str:
    s = f"{alpha:.3f}".rstrip("0").rstrip(".")
    if "." not in s:
        s = f"{s}.0"
    return s.replace(".", "p")


def _parse_alpha_values(raw: str) -> list[float]:
    vals: list[float] = []
    for part in raw.split(","):
        tok = part.strip()
        if not tok:
            continue
        try:
            val = float(tok)
        except ValueError as exc:
            raise ValueError(f"Invalid alpha value: {tok!r}") from exc
        if val < 0.0:
            raise ValueError(f"Alpha must be non-negative. Got {val}.")
        vals.append(val)
    if not vals:
        raise ValueError("No alpha values parsed from --hybrid-alpha-values.")
    return vals


def _build_hybrid_specs(
    *,
    include_ablation: bool,
    alpha_sweep_components: list[str] | None,
    alpha_values: list[float],
) -> list[HybridMethodSpec]:
    """Build dynamic hybrid specs for defaults + optional ablations/sweeps."""
    specs: list[HybridMethodSpec] = list(DEFAULT_HYBRID_SPECS)

    if include_ablation:
        specs.extend(
            [
                HybridMethodSpec(
                    name="hybrid_rrf_prior_only",
                    component="prior",
                    alpha=0.0,
                    use_repaired_graph=True,
                    mode="prior_only",
                ),
                HybridMethodSpec(
                    name="hybrid_rrf_unrepaired_copeland_a03",
                    component="copeland",
                    alpha=0.3,
                    use_repaired_graph=False,
                ),
                HybridMethodSpec(
                    name="hybrid_rrf_repaired_copeland_a03",
                    component="copeland",
                    alpha=0.3,
                    use_repaired_graph=True,
                ),
                HybridMethodSpec(
                    name="hybrid_rrf_unrepaired_balance_a03",
                    component="balance",
                    alpha=0.3,
                    use_repaired_graph=False,
                ),
                HybridMethodSpec(
                    name="hybrid_rrf_repaired_balance_a03",
                    component="balance",
                    alpha=0.3,
                    use_repaired_graph=True,
                ),
            ]
        )

    if alpha_sweep_components:
        for component in alpha_sweep_components:
            for alpha in alpha_values:
                token = _alpha_token(alpha)
                specs.append(
                    HybridMethodSpec(
                        name=f"hybrid_rrf_repaired_{component}_a{token}",
                        component=component,
                        alpha=alpha,
                        use_repaired_graph=True,
                    )
                )

    # Deterministic dedupe by method name (first occurrence wins).
    dedup: dict[str, HybridMethodSpec] = {}
    for spec in specs:
        if spec.name not in dedup:
            dedup[spec.name] = spec
    return list(dedup.values())


def _method_plan(
    *,
    include_hybrid_ablation: bool,
    alpha_sweep_components: list[str] | None,
    alpha_values: list[float],
    selected_methods: list[str] | None = None,
) -> tuple[list[str], dict[str, HybridMethodSpec]]:
    specs = _build_hybrid_specs(
        include_ablation=include_hybrid_ablation,
        alpha_sweep_components=alpha_sweep_components,
        alpha_values=alpha_values,
    )
    hybrid_by_name = {s.name: s for s in specs}
    methods = list(NON_HYBRID_METHODS) + [s.name for s in specs]
    if selected_methods:
        selected_set = set(selected_methods)
        unknown = [m for m in selected_methods if m not in methods]
        if unknown:
            raise ValueError(
                "Unknown method(s) requested via --methods: "
                f"{', '.join(unknown)}. Available methods: {', '.join(methods)}"
            )
        methods = [m for m in methods if m in selected_set]
        hybrid_by_name = {
            name: spec for name, spec in hybrid_by_name.items() if name in selected_set
        }
    return methods, hybrid_by_name


def _filter_methods(
    methods: list[str],
    hybrid_specs: dict[str, HybridMethodSpec],
    selected_methods: list[str] | None,
) -> tuple[list[str], dict[str, HybridMethodSpec]]:
    """Restrict the method plan to an explicit shortlist when requested."""
    if not selected_methods:
        return methods, hybrid_specs

    missing = sorted(set(selected_methods) - set(methods))
    if missing:
        raise ValueError(
            f"Unknown method(s) requested via --methods: {missing}. "
            f"Available methods: {sorted(methods)}"
        )

    filtered_methods = [m for m in methods if m in selected_methods]
    filtered_hybrid_specs = {name: spec for name, spec in hybrid_specs.items() if name in filtered_methods}
    return filtered_methods, filtered_hybrid_specs


def _resolve_output_dir(
    output_dir: Path,
    dataset: str,
    preference_source: str,
) -> Path:
    """Normalize output_dir to a source-specific real-data directory.

    Accepted inputs include:
    - a root like ``outputs/real_full``
    - a dataset directory like ``outputs/real_full/scidocs``
    - a fully resolved directory like ``outputs/real_full/scidocs/qrels``
    """
    output_dir = Path(output_dir)
    if len(output_dir.parts) >= 2 and output_dir.parts[-2:] == (dataset, preference_source):
        return output_dir
    if output_dir.name == dataset:
        return output_dir / preference_source
    return output_dir / dataset / preference_source


def _load_score_prior_files(
    score_prior_files: list[Path] | None,
) -> list[dict[str, list[tuple[str, float]]]]:
    """Load score prior files for hybrid post-repair ranking methods."""
    if not score_prior_files:
        return []
    return [_load_score_file(path) for path in score_prior_files]


def _resolve_output_dir(
    base_output_dir: Path,
    preference_source: str,
) -> Path:
    """Return a preference-source-specific output directory.

    This prevents `qrels`, `qrels_flip`, `score_file`, and `votes_file`
    runs from writing into the same directory tree. If the supplied path
    already contains the preference source, it is left unchanged. If the
    final path component looks like `seed_*`, the preference source is
    inserted before that seed directory.
    """
    if preference_source in base_output_dir.parts:
        return base_output_dir
    if base_output_dir.name.startswith("seed_"):
        return base_output_dir.parent / preference_source / base_output_dir.name
    return base_output_dir / preference_source


def _rrf_prior_scores_for_query(
    query_id: str,
    candidate_nodes: set[str],
    score_prior_sets: list[dict[str, list[tuple[str, float]]]],
    fallback_scores: dict[str, float] | None = None,
) -> dict[str, float]:
    """Aggregate score priors with reciprocal-rank fusion over files."""
    if not score_prior_sets:
        if fallback_scores is None:
            return {doc_id: 0.0 for doc_id in candidate_nodes}
        return {doc_id: fallback_scores.get(doc_id, 0.0) for doc_id in candidate_nodes}

    rrf_k = 60.0
    scores: dict[str, float] = defaultdict(float)
    for score_map in score_prior_sets:
        entries = score_map.get(query_id, [])
        if not entries:
            continue
        best: dict[str, float] = {}
        for doc_id, score in entries:
            if doc_id in candidate_nodes:
                best[doc_id] = max(best.get(doc_id, score), score)
        ranked = sorted(best.items(), key=lambda x: (-x[1], x[0]))
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (rrf_k + rank)
    for doc_id in candidate_nodes:
        scores.setdefault(
            doc_id,
            0.0 if fallback_scores is None else fallback_scores.get(doc_id, 0.0),
        )
    return scores


def _score_sum_prior_scores(graph: nx.DiGraph) -> dict[str, float]:
    """Return score-sum scores from the original graph for hybrid priors."""
    scores: dict[str, float] = {n: 0.0 for n in graph.nodes()}
    for u, _v, data in graph.edges(data=True):
        scores[u] += data.get("weight", 1.0)
    return scores


def _has_usable_eval_labels(qrels_for_query: list) -> bool:
    """Return True when qrels support evaluation ranking comparisons."""
    return has_usable_eval_labels(qrels_for_query)


def _load_pairwise_preference_file(path: Path) -> dict[str, list[Preference]]:
    """Load query-level pairwise preferences from a JSONL file.

    Expected keys per line:
    - query_id
    - winner_doc_id / winner
    - loser_doc_id / loser
    - optional weight (default 1.0)
    """
    if not path.exists():
        raise FileNotFoundError(f"Pairwise preference file not found: {path}")

    result: dict[str, list[Preference]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            query_id = row.get("query_id")
            winner = row.get("winner_doc_id", row.get("winner"))
            loser = row.get("loser_doc_id", row.get("loser"))
            weight = row.get("weight", 1.0)
            if query_id is None or winner is None or loser is None:
                raise ValueError(
                    f"{path}:{lineno} missing required keys "
                    "(query_id, winner_doc_id/winner, loser_doc_id/loser)."
                )
            result[str(query_id)].append(
                Preference(
                    winner=str(winner),
                    loser=str(loser),
                    weight=float(weight),
                )
            )
    return result


def _load_score_file(path: Path) -> dict[str, list[tuple[str, float]]]:
    """Load query-document scores from JSONL.

    Expected keys per line:
    - query_id
    - doc_id
    - score
    """
    if not path.exists():
        raise FileNotFoundError(f"Score file not found: {path}")

    by_query: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "query_id" not in row or "doc_id" not in row or "score" not in row:
                raise ValueError(
                    f"{path}:{lineno} missing required keys (query_id, doc_id, score)."
                )
            by_query[str(row["query_id"])].append(
                (str(row["doc_id"]), float(row["score"]))
            )
    return by_query


def _score_entries_to_preferences(
    score_entries: list[tuple[str, float]],
    top_k: int,
    seed: int,
) -> list[Preference]:
    """Convert document scores to pairwise preferences (higher score wins)."""
    if not score_entries:
        return []
    rng = random.Random(seed)
    rng.shuffle(score_entries)
    # Deduplicate docs by max score
    best_score: dict[str, float] = {}
    for doc_id, score in score_entries:
        best_score[doc_id] = max(best_score.get(doc_id, score), score)
    ranked = sorted(best_score.items(), key=lambda x: x[1], reverse=True)[:top_k]

    prefs: list[Preference] = []
    for i in range(len(ranked)):
        for j in range(i + 1, len(ranked)):
            winner, w_score = ranked[i]
            loser, l_score = ranked[j]
            margin = abs(w_score - l_score)
            prefs.append(
                Preference(
                    winner=winner,
                    loser=loser,
                    weight=max(margin, 1e-6),
                )
            )
    return prefs


def _restrict_preferences_top_k(
    prefs: list[Preference],
    top_k: int,
) -> list[Preference]:
    """Restrict pairwise preferences to a top-k document subset."""
    if not prefs:
        return []
    doc_strength: dict[str, float] = defaultdict(float)
    for p in prefs:
        doc_strength[p.winner] += p.weight
        doc_strength[p.loser] += p.weight
    keep_docs = {
        doc for doc, _ in sorted(doc_strength.items(), key=lambda x: x[1], reverse=True)[:top_k]
    }
    return [p for p in prefs if p.winner in keep_docs and p.loser in keep_docs]


def _flip_preference_directions(
    prefs: list[Preference],
    flip_prob: float,
    seed: int,
    query_id: str,
) -> list[Preference]:
    """Randomly flip preference directions for stress-testing cycles."""
    if not (0.0 <= flip_prob <= 1.0):
        raise ValueError(f"flip_prob must be in [0, 1], got {flip_prob}")
    if flip_prob == 0.0:
        return prefs

    rng = random.Random(f"{seed}:{query_id}")
    flipped: list[Preference] = []
    for p in prefs:
        if rng.random() < flip_prob:
            flipped.append(Preference(winner=p.loser, loser=p.winner, weight=p.weight))
        else:
            flipped.append(p)
    return flipped


def _build_query_preferences(
    *,
    query_id: str,
    qrels_for_query: list,
    top_k: int,
    weight_scheme: str,
    seed: int,
    preference_source: str,
    flip_prob: float,
    pairwise_index: dict[str, list[Preference]] | None,
    score_index: dict[str, list[tuple[str, float]]] | None,
) -> tuple[list[Preference], str]:
    """Build preferences for a query from the selected source."""
    if preference_source == "qrels":
        schema_prefs = preferences_from_qrels(
            qrels_for_query,
            top_k=top_k,
            seed=seed,
            weight_scheme=weight_scheme,
        )
        prefs = [
            Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
            for p in schema_prefs
        ]
        return prefs, "label-derived pairwise preferences from qrels"

    if preference_source == "qrels_flip":
        schema_prefs = preferences_from_qrels(
            qrels_for_query,
            top_k=top_k,
            seed=seed,
            weight_scheme=weight_scheme,
        )
        base = [
            Preference(winner=p.winner_doc_id, loser=p.loser_doc_id, weight=p.weight)
            for p in schema_prefs
        ]
        flipped = _flip_preference_directions(
            base,
            flip_prob=flip_prob,
            seed=seed,
            query_id=query_id,
        )
        return (
            flipped,
            f"synthetic corruption: qrels-derived edges with flip_prob={flip_prob}",
        )

    if preference_source in {"llm_pairwise_file", "votes_file"}:
        if pairwise_index is None:
            raise ValueError("pairwise_index is required for pairwise file sources.")
        prefs = _restrict_preferences_top_k(pairwise_index.get(query_id, []), top_k=top_k)
        note = (
            "external pairwise preferences from llm comparisons file"
            if preference_source == "llm_pairwise_file"
            else "external pairwise preferences from ranker votes file"
        )
        return prefs, note

    if preference_source == "score_file":
        if score_index is None:
            raise ValueError("score_index is required for score_file source.")
        prefs = _score_entries_to_preferences(
            score_index.get(query_id, []),
            top_k=top_k,
            seed=seed,
        )
        return prefs, "external pairwise preferences induced from score file"

    raise ValueError(f"Unknown preference_source: {preference_source!r}")


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
    preference_source: str,
    flip_prob: float,
    pairwise_index: dict[str, list[Preference]] | None,
    score_index: dict[str, list[tuple[str, float]]] | None,
    score_prior_sets: list[dict[str, list[tuple[str, float]]]],
    methods: list[str],
    hybrid_specs: dict[str, HybridMethodSpec],
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
    # Safeguard: skip if evaluation labels are insufficient
    # ------------------------------------------------------------------
    unique_docs = {e.doc_id for e in qrels_for_query}
    n_distinct_grades = len({e.relevance for e in qrels_for_query})
    if not _has_usable_eval_labels(qrels_for_query):
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
        prefs, pref_note = _build_query_preferences(
            query_id=qid,
            qrels_for_query=qrels_for_query,
            top_k=top_k,
            weight_scheme=weight_scheme,
            seed=seed,
            preference_source=preference_source,
            flip_prob=flip_prob,
            pairwise_index=pairwise_index,
            score_index=score_index,
        )

    if not prefs:
        return [], {
            "query_id": qid,
            "reason": f"no preferences generated from source={preference_source!r}",
        }

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
    # 4. Candidate-aligned reference ranking from qrels
    # ------------------------------------------------------------------
    legacy_ref_ranking = _reference_ranking(qrels_for_query)[:top_k]
    candidate_nodes = set(graph.nodes())
    ref_ranking, rel_map = _reference_ranking_for_candidates(
        qrels_for_query=qrels_for_query,
        candidates=candidate_nodes,
    )
    candidate_set = set(ref_ranking)

    # Graph-vs-qrels inconsistency before/after repair
    graph_bew_pre = _backward_edge_weight(graph, ref_ranking)
    graph_pic_pre = _pairwise_inconsistency(graph, ref_ranking)

    # ------------------------------------------------------------------
    # 5. Greedy FAS (shared repair — used by topological method)
    # ------------------------------------------------------------------
    with Timer("greedy_fas_solver", accumulator=query_acc):
        dag, removed_edges = greedy_fas(graph)
        fas_weight = greedy_fas_total_weight(removed_edges)
        fas_n_removed = len(removed_edges)
    graph_bew_post = _backward_edge_weight(dag, ref_ranking)
    graph_pic_post = _pairwise_inconsistency(dag, ref_ranking)

    # ------------------------------------------------------------------
    # 6. Ranking methods
    # ------------------------------------------------------------------
    rankings: dict[str, list[str]] = {}
    ranking_stage_by_method: dict[str, str] = {}

    with Timer("ranking_score_sum", accumulator=query_acc):
        rankings["score_sum"] = score_sum_ranking(graph)
    ranking_stage_by_method["score_sum"] = "ranking_score_sum"

    with Timer("ranking_borda", accumulator=query_acc):
        rankings["borda"] = borda_ranking(graph)
    ranking_stage_by_method["borda"] = "ranking_borda"

    with Timer("ranking_pagerank", accumulator=query_acc):
        rankings["pagerank"] = pagerank_ranking(graph)
    ranking_stage_by_method["pagerank"] = "ranking_pagerank"

    with Timer("ranking_topological", accumulator=query_acc):
        rankings["greedy_fas_topological"] = topological_ranking(dag)
    ranking_stage_by_method["greedy_fas_topological"] = "ranking_topological"

    with Timer("ranking_fas_weighted_balance", accumulator=query_acc):
        rankings["greedy_fas_weighted_balance"] = _weighted_out_minus_in_ranking(dag)
    ranking_stage_by_method["greedy_fas_weighted_balance"] = "ranking_fas_weighted_balance"

    with Timer("ranking_fas_copeland", accumulator=query_acc):
        rankings["greedy_fas_copeland"] = _copeland_ranking(dag)
    ranking_stage_by_method["greedy_fas_copeland"] = "ranking_fas_copeland"

    # Score-sum prior from the original (pre-repair) graph: used by
    # fas_balance_score_prior_alpha_beta and score-augmented topological.
    _score_sum_prior: dict[str, float] = score_sum_scores(graph)

    with Timer("ranking_fas_balance_score_prior_alpha_beta", accumulator=query_acc):
        rankings["fas_balance_score_prior_alpha_beta"] = (
            fas_balance_score_prior_alpha_beta_ranking(dag, _score_sum_prior)
        )
    ranking_stage_by_method["fas_balance_score_prior_alpha_beta"] = (
        "ranking_fas_balance_score_prior_alpha_beta"
    )

    prior_scores = _rrf_prior_scores_for_query(
        query_id=qid,
        candidate_nodes=set(graph.nodes()),
        score_prior_sets=score_prior_sets,
        fallback_scores=_score_sum_prior_scores(graph),
    )
    with Timer("ranking_fas_score_augmented_topological", accumulator=query_acc):
        rankings["greedy_fas_score_augmented_topological"] = _priority_topological_ranking(
            dag,
            priority_scores=prior_scores,
        )
    ranking_stage_by_method["greedy_fas_score_augmented_topological"] = (
        "ranking_fas_score_augmented_topological"
    )

    for method_name, spec in hybrid_specs.items():
        stage_name = f"ranking_{method_name}"
        ranking_stage_by_method[method_name] = stage_name
        source_graph = dag if spec.use_repaired_graph else graph
        with Timer(stage_name, accumulator=query_acc):
            if spec.mode == "prior_only":
                rankings[method_name] = _prior_only_ranking(
                    source_graph.nodes(),
                    prior_scores=prior_scores,
                )
            elif spec.mode == "priority_topological":
                rankings[method_name] = _hybrid_rrf_priority_topological_ranking(
                    source_graph,
                    prior_scores=prior_scores,
                    component=spec.component,
                    alpha=spec.alpha,
                )
            else:
                rankings[method_name] = _hybrid_rrf_component_ranking(
                    source_graph,
                    prior_scores=prior_scores,
                    component=spec.component,
                    alpha=spec.alpha,
                )

    # ------------------------------------------------------------------
    # 7. Evaluation per method
    # ------------------------------------------------------------------
    with Timer("evaluation", accumulator=query_acc):
        method_metrics: dict[str, dict] = {}
        for method_name, ranking in rankings.items():
            bew = _backward_edge_weight(graph, ranking)
            pic = _pairwise_inconsistency(graph, ranking)
            # Candidate-aligned ranking for primary quality metrics
            ranking_aligned = [d for d in ranking if d in candidate_set]
            tau = _kendall_tau(ranking_aligned, ref_ranking)
            tau_legacy = _kendall_tau(ranking, legacy_ref_ranking)
            ndcg = _ndcg_at_k(ranking_aligned, rel_map, k=top_k)
            map_k = _average_precision_at_k(ranking_aligned, rel_map, k=top_k)
            precision_k, recall_k = _precision_recall_at_k(ranking_aligned, rel_map, k=top_k)
            pair_acc = _pairwise_accuracy_from_relevance(ranking_aligned, rel_map)
            method_metrics[method_name] = {
                "backward_edge_weight": bew,
                "pairwise_inconsistency": pic,
                "kendall_tau": tau,
                "kendall_tau_legacy": tau_legacy,
                "ndcg_at_k": ndcg,
                "map_at_k": map_k,
                "precision_at_k": precision_k,
                "recall_at_k": recall_k,
                "pairwise_accuracy": pair_acc,
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
        method_name: timing_rows.get(stage_name, {}).get("total_s", 0.0)
        for method_name, stage_name in ranking_stage_by_method.items()
    }

    # ------------------------------------------------------------------
    # 9. Build output rows
    # ------------------------------------------------------------------
    rows = []
    for method_name in methods:
        m_metrics = method_metrics[method_name]
        rows.append({
            # Identity
            "dataset": dataset,
            "query_id": qid,
            "method": method_name,
            "preference_source": preference_source,
            "preference_source_note": pref_note,
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
            # Graph-vs-qrels inconsistency (pre/post FAS)
            "graph_ref_bew_pre": round(graph_bew_pre, 6),
            "graph_ref_bew_post": round(graph_bew_post, 6),
            "graph_ref_pic_pre": graph_pic_pre,
            "graph_ref_pic_post": graph_pic_post,
            # Evaluation context
            "n_eval_candidates": len(ref_ranking),
            "primary_metric": PRIMARY_QUALITY_METRIC,
            # Evaluation
            "backward_edge_weight": round(m_metrics["backward_edge_weight"], 6),
            "pairwise_inconsistency": m_metrics["pairwise_inconsistency"],
            "kendall_tau": (
                round(m_metrics["kendall_tau"], 6)
                if m_metrics["kendall_tau"] is not None
                else None
            ),
            "kendall_tau_legacy": (
                round(m_metrics["kendall_tau_legacy"], 6)
                if m_metrics["kendall_tau_legacy"] is not None
                else None
            ),
            "ndcg_at_k": (
                round(m_metrics["ndcg_at_k"], 6)
                if m_metrics["ndcg_at_k"] is not None
                else None
            ),
            "map_at_k": (
                round(m_metrics["map_at_k"], 6)
                if m_metrics["map_at_k"] is not None
                else None
            ),
            "precision_at_k": (
                round(m_metrics["precision_at_k"], 6)
                if m_metrics["precision_at_k"] is not None
                else None
            ),
            "recall_at_k": (
                round(m_metrics["recall_at_k"], 6)
                if m_metrics["recall_at_k"] is not None
                else None
            ),
            "pairwise_accuracy": (
                round(m_metrics["pairwise_accuracy"], 6)
                if m_metrics["pairwise_accuracy"] is not None
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
        "--preference-source",
        type=str,
        default="qrels",
        choices=list(PREFERENCE_SOURCES),
        help=(
            "Source used to build preference graph: qrels (baseline), "
            "qrels_flip (synthetic corruption), score_file (reranker scores), "
            "llm_pairwise_file, or votes_file."
        ),
    )
    parser.add_argument(
        "--flip-prob",
        type=float,
        default=0.15,
        help="Edge-flip probability used only when --preference-source qrels_flip.",
    )
    parser.add_argument(
        "--pairwise-file",
        type=Path,
        default=None,
        help=(
            "JSONL pairwise file for llm_pairwise_file or votes_file modes "
            "(query_id, winner_doc_id/winner, loser_doc_id/loser, weight?)."
        ),
    )
    parser.add_argument(
        "--score-file",
        type=Path,
        default=None,
        help="JSONL score file for score_file mode (query_id, doc_id, score).",
    )
    parser.add_argument(
        "--score-prior-files",
        type=Path,
        nargs="*",
        default=None,
        help=(
            "Optional score JSONL files used as prior signals for hybrid "
            "post-repair ranking extractors."
        ),
    )
    parser.add_argument(
        "--query-id-file",
        type=Path,
        default=None,
        help=(
            "Optional TXT/JSONL file specifying exact query ids to use. "
            "When provided, sampling uses this file (filtered to eligible qrels)."
        ),
    )
    parser.add_argument(
        "--include-hybrid-ablation",
        action="store_true",
        help=(
            "Include repaired-vs-unrepaired hybrid ablation methods "
            "(prior only, unrepaired/repaired balance+copeland)."
        ),
    )
    parser.add_argument(
        "--hybrid-alpha-sweep-components",
        type=str,
        nargs="*",
        default=None,
        choices=["balance", "copeland"],
        help=(
            "Optional repaired-hybrid component(s) to sweep over "
            "--hybrid-alpha-values."
        ),
    )
    parser.add_argument(
        "--hybrid-alpha-values",
        type=str,
        default="0.0,0.1,0.2,0.3,0.5,0.7,1.0",
        help="Comma-separated alpha values for optional hybrid alpha sweep.",
    )
    parser.add_argument(
        "--methods",

            nargs="*",
    default=None,
    help=(
        "Optional explicit shortlist of methods to run. "
        "If omitted, all standard baselines/FAS/hybrid defaults are run. "
        "Useful for low-cost validation packages."
    ),

        ),
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
        default=Path("outputs/real_full"),
        help="Root or fully resolved directory for real-data outputs.",
    )
    parser.add_argument(
        "--save-timings",
        action="store_true",
        help="Save timing CSV and JSON under <output-dir>/<preference_source>/timings/.",
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
    preference_source: str,
    flip_prob: float,
    pairwise_file: Path | None,
    score_file: Path | None,
    score_prior_files: list[Path] | None,
    seed: int,
    output_dir: Path,
    methods_filter: list[str] | None = None,
    save_timings: bool = False,
    profile: bool = False,
    generate_plots: bool = True,
    query_id_file: Path | None = None,
    include_hybrid_ablation: bool = False,
    hybrid_alpha_sweep_components: list[str] | None = None,
    hybrid_alpha_values: str = "0.0,0.1,0.2,0.3,0.5,0.7,1.0",
    methods_filter: list[str] | None = None,
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

      output_dir = _resolve_output_dir(Path(output_dir), dataset=dataset, preference_source=preference_source)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  Real-Data Ranking Experiment — {dataset.upper()}")
    print(f"{'='*65}")
    print(f"  dataset      : {dataset}")
    print(f"  max_queries  : {max_queries}")
    print(f"  top_k        : {top_k}")
    print(f"  weight_scheme: {weight_scheme}")
    print(f"  pref_source  : {preference_source}")
    if preference_source == "qrels_flip":
        print(f"  flip_prob    : {flip_prob}")
    if pairwise_file is not None:
        print(f"  pairwise_file: {pairwise_file}")
    if score_file is not None:
        print(f"  score_file   : {score_file}")
    if score_prior_files:
        print(f"  score_priors : {', '.join(str(p) for p in score_prior_files)}")
    if query_id_file is not None:
        print(f"  query_id_file: {query_id_file}")
    alpha_values = _parse_alpha_values(hybrid_alpha_values)
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=include_hybrid_ablation,
        alpha_sweep_components=hybrid_alpha_sweep_components,
        alpha_values=alpha_values,
        selected_methods=methods_filter,
    )
    methods, hybrid_specs = _filter_methods(
        methods,
        hybrid_specs,
        selected_methods=methods_filter,
    )
    print(f"  hybrid_ablation: {include_hybrid_ablation}")
    if hybrid_alpha_sweep_components:
        print(
            "  hybrid_alpha_sweep: "
            f"components={','.join(hybrid_alpha_sweep_components)} "
            f"alphas={','.join(str(a) for a in alpha_values)}"
        )
    print(f"  methods      : {', '.join(methods)}")
    print(f"  seed         : {seed}")
    print(f"  output_dir   : {output_dir}")
    print(f"  save_timings : {save_timings}\n")

    global_acc = TimingAccumulator()
    global_acc.set_metadata(
        dataset=dataset,
        max_queries=max_queries,
        top_k=top_k,
        preference_source=preference_source,
        flip_prob=flip_prob if preference_source == "qrels_flip" else None,
    )

    pairwise_index: dict[str, list[Preference]] | None = None
    score_index: dict[str, list[tuple[str, float]]] | None = None
    score_prior_sets: list[dict[str, list[tuple[str, float]]]] = []
    with Timer("preference_source_loading", accumulator=global_acc):
        if preference_source in {"llm_pairwise_file", "votes_file"}:
            if pairwise_file is None:
                raise ValueError(
                    "--pairwise-file is required for llm_pairwise_file/votes_file modes."
                )
            pairwise_index = _load_pairwise_preference_file(pairwise_file)
            print(f"[0] Loaded pairwise preferences for {len(pairwise_index)} queries")
        elif preference_source == "score_file":
            if score_file is None:
                raise ValueError("--score-file is required for score_file mode.")
            score_index = _load_score_file(score_file)
            print(f"[0] Loaded score entries for {len(score_index)} queries")
        score_prior_sets = _load_score_prior_files(score_prior_files)
        if score_prior_sets:
            print(f"[0] Loaded {len(score_prior_sets)} score prior file(s) for hybrid methods")

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

        # Restrict to queries that have usable evaluation labels
        eligible_qids = eligible_query_ids(qrels)
        eligible_set = set(eligible_qids)

        if query_id_file is not None:
            requested_qids = load_query_ids_file(query_id_file)
            sampled_qids = [qid for qid in requested_qids if qid in eligible_set][:max_queries]
        else:
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
                preference_source=preference_source,
                flip_prob=flip_prob,
                pairwise_index=pairwise_index,
                score_index=score_index,
                score_prior_sets=score_prior_sets,
                methods=methods,
                hybrid_specs=hybrid_specs,
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
        source_note = {
            "qrels": "Real preference edges derived directly from qrels (label-order DAG baseline).",
            "qrels_flip": (
                "Synthetic corruption: qrels-derived edges with random direction flips to induce conflicts."
            ),
            "score_file": "Real preference edges induced from external score file (reranker-style).",
            "llm_pairwise_file": "Real preference edges loaded from external LLM pairwise judgments.",
            "votes_file": "Real preference edges loaded from external multi-ranker vote pairs.",
        }.get(preference_source, "Unknown preference source.")
        return {
            "dataset": dataset,
            "preference_source": preference_source,
            "preference_source_note": source_note,
            "flip_prob": flip_prob if preference_source == "qrels_flip" else None,
            "primary_metric": PRIMARY_QUALITY_METRIC,
            "n_processed": 0,
            "n_skipped": len(skipped),
            "skipped_reasons": [s["reason"] for s in skipped],
        }

    # ------------------------------------------------------------------
    # 4. Save per-query CSV
    # ------------------------------------------------------------------
    pq_csv_path = output_dir / f"{dataset}_per_query.csv"
    _write_csv(all_rows, pq_csv_path)
    print(f"[4] Per-query CSV → {pq_csv_path}")

    # ------------------------------------------------------------------
    # 5. Build and save aggregate summary
    # ------------------------------------------------------------------
    summary_rows = _build_summary(all_rows, methods=methods)
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
    summary = _build_experiment_summary(
        all_rows,
        skipped,
        global_acc,
        dataset,
        top_k,
        preference_source=preference_source,
        flip_prob=flip_prob,
    )
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


def _build_summary(rows: list[dict], methods: list[str]) -> list[dict]:
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
    for method in methods:
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
        tau_legacy = _stats("kendall_tau_legacy")
        ndcg = _stats("ndcg_at_k")
        map_k = _stats("map_at_k")
        p_k = _stats("precision_at_k")
        r_k = _stats("recall_at_k")
        pair_acc = _stats("pairwise_accuracy")
        rt = _stats("runtime_total_s")
        n_nodes = _stats("n_nodes")
        n_edges = _stats("n_edges")
        fas_w = _stats("fas_weight_removed")
        cyc = _stats("is_cyclic")
        pre_bew = _stats("graph_ref_bew_pre")
        post_bew = _stats("graph_ref_bew_post")
        pre_pic = _stats("graph_ref_pic_pre")
        post_pic = _stats("graph_ref_pic_post")

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
            "tau_legacy_mean": tau_legacy["mean"],
            # Primary ranking quality metrics (candidate-aligned)
            "ndcg_mean": ndcg["mean"],
            "map_mean": map_k["mean"],
            "precision_at_k_mean": p_k["mean"],
            "recall_at_k_mean": r_k["mean"],
            "pairwise_accuracy_mean": pair_acc["mean"],
            # Runtime
            "runtime_mean_s": rt["mean"],
            "runtime_median_s": rt["median"],
            "runtime_max_s": rt["max"],
            # Graph size
            "n_nodes_mean": n_nodes["mean"],
            "n_edges_mean": n_edges["mean"],
            # Cycle / FAS / pre-post consistency
            "cyclic_pct": cyc["mean"] * 100 if cyc["mean"] is not None else None,
            "fas_removed_weight_mean": fas_w["mean"],
            "graph_ref_bew_pre_mean": pre_bew["mean"],
            "graph_ref_bew_post_mean": post_bew["mean"],
            "graph_ref_pic_pre_mean": pre_pic["mean"],
            "graph_ref_pic_post_mean": post_pic["mean"],
        })

    return summary_rows


def _build_experiment_summary(
    all_rows: list[dict],
    skipped: list[dict],
    global_acc: TimingAccumulator,
    dataset: str,
    top_k: int,
    preference_source: str,
    flip_prob: float,
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

    # Primary metric: candidate-aligned nDCG@k (higher is better)
    ndcg_by_method: dict[str, list[float]] = defaultdict(list)
    for r in all_rows:
        if r.get("ndcg_at_k") is not None:
            ndcg_by_method[r["method"]].append(r["ndcg_at_k"])
    avg_ndcg = {m: sum(vs) / len(vs) for m, vs in ndcg_by_method.items() if vs}
    best_method_by_primary = max(avg_ndcg, key=avg_ndcg.get) if avg_ndcg else "n/a"

    # Pre/post inconsistency of graph edges w.r.t. qrels reference
    avg_pre_pic = sum(r["graph_ref_pic_pre"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_post_pic = sum(r["graph_ref_pic_post"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_pre_bew = sum(r["graph_ref_bew_pre"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_post_bew = sum(r["graph_ref_bew_post"] for r in ss_rows) / len(ss_rows) if ss_rows else 0
    avg_fas_weight = sum(r["fas_weight_removed"] for r in ss_rows) / len(ss_rows) if ss_rows else 0

    # Global timing summary
    timing_summary = {row["stage"]: row for row in global_acc.summary_rows()}

    source_note = {
        "qrels": "Real preference edges derived directly from qrels (label-order DAG baseline).",
        "qrels_flip": (
            "Synthetic corruption: qrels-derived edges with random direction flips to induce conflicts."
        ),
        "score_file": "Real preference edges induced from external score file (reranker-style).",
        "llm_pairwise_file": "Real preference edges loaded from external LLM pairwise judgments.",
        "votes_file": "Real preference edges loaded from external multi-ranker vote pairs.",
    }.get(preference_source, "Unknown preference source.")

    return {
        "dataset": dataset,
        "top_k": top_k,
        "preference_source": preference_source,
        "preference_source_note": source_note,
        "flip_prob": flip_prob if preference_source == "qrels_flip" else None,
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
        "primary_metric": PRIMARY_QUALITY_METRIC,
        "avg_primary_by_method": {m: round(v, 6) for m, v in avg_ndcg.items()},
        "best_method_by_primary": best_method_by_primary,
        "avg_graph_ref_pic_pre": round(avg_pre_pic, 6),
        "avg_graph_ref_pic_post": round(avg_post_pic, 6),
        "avg_graph_ref_bew_pre": round(avg_pre_bew, 6),
        "avg_graph_ref_bew_post": round(avg_post_bew, 6),
        "avg_fas_removed_weight": round(avg_fas_weight, 6),
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
    print(f"  Preference source : {summary['preference_source']}")
    print(f"  Avg graph nodes   : {summary['avg_n_nodes']:.1f}")
    print(f"  Avg graph edges   : {summary['avg_n_edges']:.1f}")
    print(f"  Avg largest SCC   : {summary['avg_largest_scc']:.1f}")
    print(f"  % cyclic graphs   : {summary['pct_cyclic_graphs']:.1f}%")
    print(f"  Primary metric    : {summary['primary_metric']}")
    print(f"  Avg FAS weight    : {summary['avg_fas_removed_weight']:.4f}")
    print(
        f"  Graph inconsistency pre/post (edges): "
        f"{summary['avg_graph_ref_pic_pre']:.4f} -> {summary['avg_graph_ref_pic_post']:.4f}"
    )
    print(
        f"  Graph inconsistency pre/post (weight): "
        f"{summary['avg_graph_ref_bew_pre']:.4f} -> {summary['avg_graph_ref_bew_post']:.4f}"
    )
    print(f"\n  Average runtime by method (s):")
    for m, v in summary["avg_runtime_by_method_s"].items():
        print(f"    {m:<30} {v:.6f}")
    print(f"\n  Best method by backward-edge weight: {summary['best_method_by_bew']}")
    print(f"  Average BEW by method:")
    for m, v in summary["avg_bew_by_method"].items():
        print(f"    {m:<30} {v:.4f}")
    print(f"\n  Best method by primary metric: {summary['best_method_by_primary']}")
    print(f"  Average primary metric by method:")
    for m, v in summary["avg_primary_by_method"].items():
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
        preference_source=args.preference_source,
        flip_prob=args.flip_prob,
        pairwise_file=args.pairwise_file,
        score_file=args.score_file,
        score_prior_files=args.score_prior_files,
        query_id_file=args.query_id_file,
        include_hybrid_ablation=args.include_hybrid_ablation,
        hybrid_alpha_sweep_components=args.hybrid_alpha_sweep_components,
        hybrid_alpha_values=args.hybrid_alpha_values,
        methods_filter=args.methods,
        seed=args.seed,
        output_dir=args.output_dir,
        methods_filter=args.methods,
        save_timings=args.save_timings,
        profile=args.profile,
        generate_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()
