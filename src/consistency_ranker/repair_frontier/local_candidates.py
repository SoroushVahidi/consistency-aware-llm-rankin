"""Per-SCC candidate generators for incumbent-protected SCC-local repair.

Each generator takes one nontrivial SCC's induced subgraph and returns a
:class:`~.types.LocalCandidate` with a full local ordering of that SCC's
members. All solver-driven candidates route through the scalable
``mwfas_solver.solve`` backend (SCIP-based exact, proven at n<=10 in
production runs) rather than the slow brute-force
``reliability_weighted_repair.exact_fas_with_costs`` (max_n=9,
``itertools.permutations``) -- confidence-weighted variants apply their
cost scheme via a shadow graph (``weight`` temporarily overwritten by a
removal cost, original preserved as ``orig_weight``) and then reuse the
same scalable path.
"""

from __future__ import annotations

import copy
from dataclasses import asdict

import networkx as nx

from consistency_ranker.baseline_ranking import copeland_ranking, topological_ranking
from consistency_ranker.mwfas_solver import is_scip_available
from consistency_ranker.mwfas_solver import solve as mwfas_solve
from consistency_ranker.reliability_repair.reliability_weighted_repair import greedy_fas_with_costs

from .protection_rules import EdgeProtectionRule, annotate_removal_costs
from .types import EdgeConfidence, LocalCandidate


def _restrict_to_members(ranking: list[str], members: frozenset[str]) -> list[str]:
    return [n for n in ranking if n in members]


def _remap_to_original_weights(
    sub: nx.DiGraph, removed: list[tuple[str, str, float]]
) -> list[tuple[str, str, float]]:
    return [(u, v, float(sub[u][v]["weight"])) for u, v, _cost in removed]


def generate_original_candidate(
    sub: nx.DiGraph, incumbent_ranking: list[str], members: frozenset[str]
) -> LocalCandidate:
    """The incumbent's own relative order restricted to this SCC's members,
    deliberately unrepaired (objective=0). Since `sub` is still cyclic,
    every edge inside it will classify as "unresolved" downstream."""
    local_order = _restrict_to_members(incumbent_ranking, members)
    return LocalCandidate(
        scc_key=members,
        method="original",
        local_order=local_order,
        local_dag=sub.copy(),
        objective=0.0,
        removed_edges=[],
        feasible=True,
    )


def generate_greedy_candidate(sub: nx.DiGraph, members: frozenset[str]) -> LocalCandidate:
    dag, removed = mwfas_solve(sub, method="greedy")
    order = topological_ranking(dag)
    return LocalCandidate(
        scc_key=members,
        method="greedy",
        local_order=order,
        local_dag=dag,
        objective=sum(w for _, _, w in removed),
        removed_edges=removed,
        feasible=True,
    )


def generate_exact_candidate(
    sub: nx.DiGraph, members: frozenset[str], *, time_limit_s: float = 300.0
) -> LocalCandidate | None:
    """Returns None (candidate omitted, not silently substituted) if SCIP is
    unavailable or the exact solve does not reach proven optimality."""
    if not is_scip_available():
        return None
    try:
        dag, removed, status = mwfas_solve(
            sub, method="scip", return_status=True, time_limit_s=time_limit_s
        )
    except RuntimeError:
        return None
    order = topological_ranking(dag)
    return LocalCandidate(
        scc_key=members,
        method="exact",
        local_order=order,
        local_dag=dag,
        objective=status.objective,
        removed_edges=removed,
        solver_status=asdict(status),
        feasible=True,
    )


def generate_confidence_weighted_candidate(
    sub: nx.DiGraph,
    members: frozenset[str],
    confidences: dict[tuple[str, str], EdgeConfidence],
    *,
    method: str = "greedy",
    exact_time_limit_s: float = 300.0,
) -> LocalCandidate | None:
    """High-confidence edges are expensive to remove (soft, cost-based --
    distinct from the hard `protected_*` candidates)."""
    shadow = copy.deepcopy(sub)
    for u, v, data in shadow.edges(data=True):
        orig_w = float(data.get("weight", 1.0))
        conf = confidences.get((u, v))
        reliability = conf.reliability if conf is not None else 0.5
        data["weight"] = orig_w * (1.0 + 5.0 * reliability)

    solver_status = None
    if method == "exact":
        if not is_scip_available():
            return None
        try:
            dag, removed, status = mwfas_solve(
                shadow, method="scip", return_status=True, time_limit_s=exact_time_limit_s
            )
        except RuntimeError:
            return None
        solver_status = asdict(status)
    else:
        dag, removed = mwfas_solve(shadow, method="greedy")

    orig_removed = _remap_to_original_weights(sub, removed)
    real_dag = sub.copy()
    real_dag.remove_edges_from([(u, v) for u, v, _ in removed])
    order = topological_ranking(real_dag)
    return LocalCandidate(
        scc_key=members,
        method=f"confidence_weighted_{method}",
        local_order=order,
        local_dag=real_dag,
        objective=sum(w for _, _, w in orig_removed),
        removed_edges=orig_removed,
        solver_status=solver_status,
        feasible=True,
    )


def generate_reliability_greedy_candidate(
    sub: nx.DiGraph,
    members: frozenset[str],
    confidences: dict[tuple[str, str], EdgeConfidence],
) -> LocalCandidate:
    """Uses `reliability_weighted_repair.greedy_fas_with_costs` directly
    (named explicitly as reusable in the spec), with `removal_cost` set
    from confidence rather than `weight`, so the graph's own `weight`
    (used for objective bookkeeping) is left untouched."""
    shadow = copy.deepcopy(sub)
    for u, v, data in shadow.edges(data=True):
        orig_w = float(data.get("weight", 1.0))
        conf = confidences.get((u, v))
        reliability = conf.reliability if conf is not None else 0.5
        data["removal_cost"] = orig_w * (1.0 + 5.0 * reliability)
    dag, removed, _meta = greedy_fas_with_costs(shadow, cost_attr="removal_cost")
    orig_removed = _remap_to_original_weights(sub, removed)
    order = topological_ranking(dag)
    return LocalCandidate(
        scc_key=members,
        method="reliability_weighted_greedy",
        local_order=order,
        local_dag=dag,
        objective=sum(w for _, _, w in orig_removed),
        removed_edges=orig_removed,
        feasible=True,
    )


def generate_protected_candidate(
    sub: nx.DiGraph,
    members: frozenset[str],
    confidences: dict[tuple[str, str], EdgeConfidence],
    rule: EdgeProtectionRule,
    *,
    incumbent_rank: dict[str, int] | None = None,
    method: str = "greedy",
    exact_time_limit_s: float = 300.0,
) -> LocalCandidate:
    """Hard-protected repair: protected edges get an inflated removal cost
    (see `protection_rules.annotate_removal_costs`) so the solver only ever
    touches one as an absolute last resort. `protected_edge_violations`
    counts how often that happened -- diagnostic, not a silent failure."""
    shadow, protected = annotate_removal_costs(
        sub, confidences, rule, incumbent_rank=incumbent_rank
    )
    solver_status = None
    if method == "exact" and is_scip_available():
        try:
            dag, removed, status = mwfas_solve(
                shadow, method="scip", return_status=True, time_limit_s=exact_time_limit_s
            )
            solver_status = asdict(status)
        except RuntimeError:
            dag, removed = mwfas_solve(shadow, method="greedy")
    else:
        dag, removed = mwfas_solve(shadow, method="greedy")

    removed_set = {(u, v) for u, v, _ in removed}
    violations = len(removed_set & protected)
    orig_removed = _remap_to_original_weights(sub, removed)
    real_dag = sub.copy()
    real_dag.remove_edges_from([(u, v) for u, v, _ in removed])
    order = topological_ranking(real_dag)
    return LocalCandidate(
        scc_key=members,
        method=f"protected_{rule.kind}_{method}",
        local_order=order,
        local_dag=real_dag,
        objective=sum(w for _, _, w in orig_removed),
        removed_edges=orig_removed,
        solver_status=solver_status,
        feasible=True,
        protected_edge_violations=violations,
    )


def generate_weak_edge_deletion_candidate(
    sub: nx.DiGraph,
    members: frozenset[str],
    confidences: dict[tuple[str, str], EdgeConfidence],
    *,
    tau: float,
    allow_residual: bool,
) -> LocalCandidate:
    """Hard-delete edges below confidence *tau* regardless of cycle
    membership. If `allow_residual`, a leftover cycle is tolerated (ranked
    anyway via `copeland_ranking`, which is well-defined on cyclic graphs;
    residual-cycle edges are classified "unresolved" downstream). Otherwise
    falls back to cost-based greedy on the remainder to guarantee a total
    order -- both variants are exposed as separate frontier candidates."""
    filtered = sub.copy()
    weak_edges: list[tuple[str, str, float]] = []
    for u, v in list(sub.edges()):
        conf = confidences.get((u, v))
        reliability = conf.reliability if conf is not None else 1.0
        if reliability < tau:
            weak_edges.append((u, v, float(sub[u][v]["weight"])))
            filtered.remove_edge(u, v)

    method_name = f"weak_edge_deletion_residual={allow_residual}_tau={tau}"
    if nx.is_directed_acyclic_graph(filtered):
        order = topological_ranking(filtered)
        return LocalCandidate(
            scc_key=members, method=method_name, local_order=order, local_dag=filtered,
            objective=sum(w for _, _, w in weak_edges), removed_edges=weak_edges, feasible=True,
        )
    if allow_residual:
        order = copeland_ranking(filtered)
        return LocalCandidate(
            scc_key=members, method=method_name, local_order=order, local_dag=filtered,
            objective=sum(w for _, _, w in weak_edges), removed_edges=weak_edges, feasible=True,
        )

    for _u, _v, data in filtered.edges(data=True):
        data["removal_cost"] = float(data.get("weight", 1.0))
    dag2, removed2, _meta = greedy_fas_with_costs(filtered, cost_attr="removal_cost")
    order = topological_ranking(dag2)
    total_removed = weak_edges + [(u, v, w) for u, v, w in removed2]
    return LocalCandidate(
        scc_key=members, method=method_name, local_order=order, local_dag=dag2,
        objective=sum(w for _, _, w in total_removed), removed_edges=total_removed, feasible=True,
    )


def generate_local_candidates(
    sub: nx.DiGraph,
    members: frozenset[str],
    incumbent_ranking: list[str],
    *,
    confidences: dict[tuple[str, str], EdgeConfidence] | None = None,
    protection_rules: list[EdgeProtectionRule] = (),
    weak_edge_tau: float = 0.5,
    exact_max_n: int = 12,
    exact_time_limit_s: float = 300.0,
) -> list[LocalCandidate]:
    """Assemble every local candidate family for one nontrivial SCC."""
    confidences = confidences or {}
    incumbent_rank = {n: i for i, n in enumerate(incumbent_ranking)}
    can_exact = len(sub) <= exact_max_n and is_scip_available()

    candidates: list[LocalCandidate] = [
        generate_original_candidate(sub, incumbent_ranking, members),
        generate_greedy_candidate(sub, members),
    ]
    if can_exact:
        exact = generate_exact_candidate(sub, members, time_limit_s=exact_time_limit_s)
        if exact is not None:
            candidates.append(exact)

    cw_greedy = generate_confidence_weighted_candidate(sub, members, confidences, method="greedy")
    if cw_greedy is not None:
        candidates.append(cw_greedy)
    if can_exact:
        cw_exact = generate_confidence_weighted_candidate(
            sub, members, confidences, method="exact", exact_time_limit_s=exact_time_limit_s
        )
        if cw_exact is not None:
            candidates.append(cw_exact)

    candidates.append(generate_reliability_greedy_candidate(sub, members, confidences))

    for allow_residual in (True, False):
        candidates.append(
            generate_weak_edge_deletion_candidate(
                sub, members, confidences, tau=weak_edge_tau, allow_residual=allow_residual
            )
        )

    for rule in protection_rules:
        if rule.kind == "none":
            continue
        candidates.append(
            generate_protected_candidate(
                sub, members, confidences, rule, incumbent_rank=incumbent_rank, method="greedy"
            )
        )
        if can_exact:
            candidates.append(
                generate_protected_candidate(
                    sub, members, confidences, rule, incumbent_rank=incumbent_rank,
                    method="exact", exact_time_limit_s=exact_time_limit_s,
                )
            )

    return candidates


__all__ = [
    "generate_original_candidate",
    "generate_greedy_candidate",
    "generate_exact_candidate",
    "generate_confidence_weighted_candidate",
    "generate_reliability_greedy_candidate",
    "generate_protected_candidate",
    "generate_weak_edge_deletion_candidate",
    "generate_local_candidates",
]
