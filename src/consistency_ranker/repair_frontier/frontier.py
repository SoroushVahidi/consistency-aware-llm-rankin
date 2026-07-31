"""Build a repair frontier: many candidate global rankings per query.

Assembles, per query graph: the unrepaired incumbent; whole-graph greedy and
exact repair; every SCC-local candidate family (applied uniformly across
all nontrivial SCCs and reinserted into the incumbent's slots); protected
SCC-local repair evaluated under each of the three acceptance modes (the
Part-1 deployable method, with abstain semantics); and label-free
alternative extraction methods on the untouched original graph. Identical
rankings are deduplicated, keeping the first (generation-order) occurrence.
"""

from __future__ import annotations

import time

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    copeland_ranking,
    pagerank_ranking,
    rank_centrality_ranking,
)
from consistency_ranker.failure_mining.graph_features import extended_graph_stats
from consistency_ranker.mwfas_solver import is_scip_available
from consistency_ranker.mwfas_solver import solve as mwfas_solve

from .acceptance import accept_candidate
from .disposition import classify_edge_dispositions
from .local_candidates import generate_local_candidates
from .protection_rules import EdgeProtectionRule
from .reinsertion import reinsert_scc_orderings
from .types import EdgeConfidence, FrontierCandidate


def _nontrivial_sccs(graph: nx.DiGraph) -> list[frozenset[str]]:
    return [frozenset(s) for s in nx.strongly_connected_components(graph) if len(s) > 1]


def _topk_membership_changes(
    candidate_ranking: list[str], incumbent_ranking: list[str], k: int
) -> int:
    a, b = set(candidate_ranking[:k]), set(incumbent_ranking[:k])
    return len(a ^ b)


def build_repair_frontier(
    graph: nx.DiGraph,
    dataset: str,
    query_id: str,
    *,
    relevance_map: dict[str, int] | None = None,
    confidences: dict[tuple[str, str], EdgeConfidence] | None = None,
    protection_rules: list[EdgeProtectionRule] = (),
    acceptance_modes: tuple[str, ...] = ("objective_only", "conservative", "oracle_analysis_only"),
    conservative_margin: float = 0.05,
    weak_edge_tau: float = 0.5,
    topk: int = 10,
    exact_max_n: int = 12,
    exact_time_limit_s: float = 300.0,
) -> list[FrontierCandidate]:
    confidences = confidences or {}
    incumbent_ranking = copeland_ranking(graph)
    graph_features = extended_graph_stats(graph)
    nontrivial_sccs = _nontrivial_sccs(graph)
    usable_modes = [
        m for m in acceptance_modes if m != "oracle_analysis_only" or relevance_map is not None
    ]

    # Each raw entry is a dict with keys: ranking, method, modified, fas_obj,
    # n_changed, weight_changed, violations, dispositions, runtime_s.
    raw: list[dict] = []
    # method_name -> {acceptance_mode: accepted} for protected candidates only.
    acceptance_by_method: dict[str, dict[str, bool]] = {}

    def _record(ranking, method, modified, fas_obj, n_changed, w_changed, viol, disps, runtime_s):
        raw.append(
            dict(
                ranking=ranking, method=method, modified=modified, fas_obj=fas_obj,
                n_changed=n_changed, weight_changed=w_changed, violations=viol,
                dispositions=disps, runtime_s=runtime_s,
            )
        )

    # 1. Unrepaired incumbent.
    t0 = time.time()
    _record(incumbent_ranking, "incumbent", [], 0.0, 0, 0.0, 0, {}, time.time() - t0)

    # 2. Whole-graph greedy / exact.
    t0 = time.time()
    dag, removed = mwfas_solve(graph, method="greedy")
    ranking = copeland_ranking(dag)
    dispositions = classify_edge_dispositions(graph, dag)
    removed_weight = sum(w for _, _, w in removed)
    _record(ranking, "whole_graph_greedy", nontrivial_sccs, removed_weight,
            len(removed), removed_weight, 0, dispositions, time.time() - t0)

    if len(graph) <= exact_max_n and is_scip_available():
        t0 = time.time()
        try:
            dag_e, removed_e, status = mwfas_solve(
                graph, method="scip", return_status=True, time_limit_s=exact_time_limit_s
            )
            ranking_e = copeland_ranking(dag_e)
            dispositions_e = classify_edge_dispositions(graph, dag_e)
            removed_weight_e = sum(w for _, _, w in removed_e)
            _record(ranking_e, "whole_graph_exact", nontrivial_sccs, status.objective,
                    len(removed_e), removed_weight_e, 0, dispositions_e, time.time() - t0)
        except RuntimeError:
            pass

    # 3. SCC-local candidate families: apply the SAME method uniformly across
    # every nontrivial SCC, reinsert all of them at once (one frontier
    # candidate per method, not a per-SCC cross-product).
    per_scc_candidates = {}
    for members in nontrivial_sccs:
        sub = graph.subgraph(members).copy()
        per_scc_candidates[members] = generate_local_candidates(
            sub, members, incumbent_ranking, confidences=confidences,
            protection_rules=list(protection_rules), weak_edge_tau=weak_edge_tau,
            exact_max_n=exact_max_n, exact_time_limit_s=exact_time_limit_s,
        )

    method_names: set[str] = set()
    for cands in per_scc_candidates.values():
        method_names.update(c.method for c in cands)
    method_names.discard("original")  # identical to "incumbent"; would only add dedup noise

    for method_name in sorted(method_names):
        t0 = time.time()
        local_orders, modified = {}, []
        fas_objective, n_changed, weight_changed, violations = 0.0, 0, 0.0, 0
        dispositions: dict[tuple[str, str], str] = {}
        for members, cands in per_scc_candidates.items():
            match = next((c for c in cands if c.method == method_name), None)
            if match is None:
                continue
            local_orders[members] = match.local_order
            modified.append(members)
            fas_objective += match.objective
            n_changed += len(match.removed_edges)
            weight_changed += sum(w for _, _, w in match.removed_edges)
            violations += match.protected_edge_violations
            sub = graph.subgraph(members).copy()
            dispositions.update(classify_edge_dispositions(sub, match.local_dag))
        if not local_orders:
            continue
        candidate_ranking = reinsert_scc_orderings(incumbent_ranking, local_orders)
        full_method_name = f"scc_local_{method_name}"
        _record(candidate_ranking, full_method_name, modified, fas_objective, n_changed,
                weight_changed, violations, dispositions, time.time() - t0)

        # Protected-repair candidates are Part 1's deployable method: record,
        # per acceptance mode, whether this candidate would be deployed (vs.
        # abstaining to the incumbent) -- as a property of this ONE candidate,
        # not separate rows (a mode's deployed ranking is always either this
        # candidate's own ranking or the incumbent's, both already present in
        # the frontier, so per-mode rows would always be dropped by
        # ranking-based deduplication).
        if method_name.startswith("protected_"):
            acceptance_by_method[full_method_name] = {
                mode: accept_candidate(
                    graph, incumbent_ranking, candidate_ranking, mode=mode,
                    margin=conservative_margin, relevance_map=relevance_map, ndcg_k=topk,
                )
                for mode in usable_modes
            }

    # 4. Alternative extraction methods on the untouched original graph.
    alt_extractors = (
        ("borda", borda_ranking),
        ("pagerank", pagerank_ranking),
        ("rank_centrality", rank_centrality_ranking),
    )
    for name, fn in alt_extractors:
        t0 = time.time()
        alt_ranking = fn(graph)
        _record(alt_ranking, f"alt_extraction_{name}", [], 0.0, 0, 0.0, 0, {}, time.time() - t0)

    candidates: list[FrontierCandidate] = []
    for r in raw:
        method = r["method"]
        ranking = r["ranking"]
        candidates.append(
            FrontierCandidate(
                candidate_id=method,
                dataset=dataset,
                query_id=query_id,
                global_ranking=ranking,
                modified_sccs=r["modified"],
                fas_objective=r["fas_obj"],
                n_reversed_or_removed=r["n_changed"],
                weight_reversed_or_removed=r["weight_changed"],
                protected_edge_violations=r["violations"],
                topk_membership_changes=_topk_membership_changes(ranking, incumbent_ranking, topk),
                graph_features=graph_features,
                runtime_s=r["runtime_s"],
                identical_to_incumbent=(ranking == incumbent_ranking),
                acceptance_mode="n/a",
                accepted=True,
                edge_dispositions=r["dispositions"],
                acceptance_by_mode=acceptance_by_method.get(method, {}),
            )
        )

    return _deduplicate(candidates)


def _deduplicate(candidates: list[FrontierCandidate]) -> list[FrontierCandidate]:
    """Keep the first (generation-order) candidate for each distinct ranking."""
    seen: set[tuple[str, ...]] = set()
    out: list[FrontierCandidate] = []
    for c in candidates:
        key = tuple(c.global_ranking)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


__all__ = ["build_repair_frontier"]
