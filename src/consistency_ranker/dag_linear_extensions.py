"""
Hard-constraint linear-extension ranking for DAGs.

Every public ranking method in this module returns a **valid topological
ordering** of the input DAG: every retained edge ``u → v`` has ``u`` before
``v`` in the output.  Soft score-based methods that may violate edges live in
:mod:`consistency_ranker.baseline_ranking` and
:mod:`consistency_ranker.soft_score_ranking`.

Method family
-------------
* Lexicographic Kahn (min document id among available sources).
* Prior-priority Kahn (external prior scores among available sources).
* Weighted-balance / normalized-balance / degree-ratio priorities, each in
  **static** (computed once on the original DAG) and **dynamic** (recomputed
  on the residual graph) variants.
* Source/sink peeling (build from both ends).
* Closest-valid-extension-to-prior (greedy + exact small-instance solvers).
* Random / sampled linear extensions (seed-reproducible).
* Diagnostic best/worst extensions relative to a prior (oracle; not deployable).
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Literal

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_scores,
    score_sum_scores,
    weighted_out_minus_in_scores,
)
from consistency_ranker.evaluation import kendall_tau, n_violations

PriorityMode = Literal["static", "dynamic"]
DEFAULT_EPS = 1.0e-12

HARD_CONSTRAINT_METHODS: tuple[str, ...] = (
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
    "closest_valid_extension_exact",
    "closest_valid_extension_ilp",
    "random_topo",
)


def require_dag(dag: nx.DiGraph, method_name: str) -> None:
    """Raise NetworkXUnfeasible if *dag* is not a DAG."""
    if not nx.is_directed_acyclic_graph(dag):
        raise nx.NetworkXUnfeasible(
            f"{method_name} requires a DAG. "
            "Use greedy_fas or mwfas_solver to remove cycles first."
        )


def is_valid_topological_order(dag: nx.DiGraph, ranking: Sequence[str]) -> bool:
    """Return True iff *ranking* is a permutation of nodes that respects every edge."""
    nodes = list(dag.nodes())
    if len(ranking) != len(nodes) or set(ranking) != set(nodes):
        return False
    pos = {n: i for i, n in enumerate(ranking)}
    return all(pos[u] < pos[v] for u, v in dag.edges())


def assert_valid_topological_order(dag: nx.DiGraph, ranking: Sequence[str]) -> None:
    """Raise AssertionError if *ranking* is not a valid linear extension."""
    if not is_valid_topological_order(dag, ranking):
        raise AssertionError(
            "Ranking is not a valid topological ordering of the DAG "
            f"(n={dag.number_of_nodes()}, m={dag.number_of_edges()})."
        )


def weighted_in_out_degrees(
    graph: nx.DiGraph,
    *,
    nodes: Iterable[str] | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Return (weighted in-degree, weighted out-degree) maps."""
    node_list = list(nodes) if nodes is not None else list(graph.nodes())
    in_w = {n: 0.0 for n in node_list}
    out_w = {n: 0.0 for n in node_list}
    node_set = set(node_list)
    for u, v, data in graph.edges(data=True):
        if u not in node_set or v not in node_set:
            continue
        w = float(data.get("weight", 1.0))
        out_w[u] += w
        in_w[v] += w
    return in_w, out_w


def balance_priority_scores(graph: nx.DiGraph, *, eps: float = DEFAULT_EPS) -> dict[str, float]:
    """``W_out(v) - W_in(v)`` (eps unused; kept for API symmetry)."""
    del eps
    return weighted_out_minus_in_scores(graph)


def normalized_balance_priority_scores(
    graph: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> dict[str, float]:
    """``(W_out - W_in) / (W_out + W_in + eps)`` per node."""
    in_w, out_w = weighted_in_out_degrees(graph)
    return {
        n: (out_w[n] - in_w[n]) / (out_w[n] + in_w[n] + eps)
        for n in graph.nodes()
    }


def degree_ratio_priority_scores(
    graph: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> dict[str, float]:
    """``(W_out + eps) / (W_in + eps)`` per node."""
    in_w, out_w = weighted_in_out_degrees(graph)
    return {n: (out_w[n] + eps) / (in_w[n] + eps) for n in graph.nodes()}


def log_degree_ratio_priority_scores(
    graph: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> dict[str, float]:
    """``log((W_out + eps) / (W_in + eps))`` per node."""
    ratios = degree_ratio_priority_scores(graph, eps=eps)
    return {n: math.log(r) for n, r in ratios.items()}


def _kahn_priority_ranking(
    dag: nx.DiGraph,
    *,
    priority_fn: Callable[[nx.DiGraph, set[str]], dict[str, float]],
    mode: PriorityMode,
    method_name: str,
) -> list[str]:
    """Kahn topological sort choosing max priority among available sources.

    Document-id tie-breaking is used only as the final deterministic fallback.
    """
    require_dag(dag, method_name)
    remaining = set(dag.nodes())
    if not remaining:
        return []

    in_deg = {n: 0 for n in remaining}
    for u, v in dag.edges():
        if u in remaining and v in remaining:
            in_deg[v] += 1

    static_scores: dict[str, float] | None = None
    if mode == "static":
        static_scores = priority_fn(dag, remaining)

    ranking: list[str] = []
    available = [n for n in remaining if in_deg[n] == 0]
    while available:
        if mode == "static":
            assert static_scores is not None
            scores = static_scores
        else:
            # Induce residual subgraph on remaining nodes for dynamic scores.
            residual = dag.subgraph(remaining)
            scores = priority_fn(residual, remaining)
        best = max(available, key=lambda n: (scores.get(n, 0.0), n))
        available.remove(best)
        ranking.append(best)
        remaining.remove(best)
        for child in dag.successors(best):
            if child not in remaining:
                continue
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)

    if len(ranking) != dag.number_of_nodes():
        raise nx.NetworkXUnfeasible(f"{method_name} failed: graph is not a DAG.")
    return ranking


def lexicographic_topological_ranking(dag: nx.DiGraph) -> list[str]:
    """Deterministic Kahn ordering: smallest document id among available sources."""
    require_dag(dag, "lexicographic_topological_ranking")
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = sorted(n for n, d in in_deg.items() if d == 0)
    ranking: list[str] = []
    while available:
        best = available.pop(0)  # already sorted; smallest id
        ranking.append(best)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                # Insert while keeping sorted order.
                inserted = False
                for i, node in enumerate(available):
                    if child < node:
                        available.insert(i, child)
                        inserted = True
                        break
                if not inserted:
                    available.append(child)
    if len(ranking) != dag.number_of_nodes():
        raise nx.NetworkXUnfeasible("lexicographic_topological_ranking failed: not a DAG.")
    return ranking


def prior_priority_topological_ranking(
    dag: nx.DiGraph,
    priority_scores: dict[str, float],
) -> list[str]:
    """Among available sources, pick highest prior score (id fallback)."""
    require_dag(dag, "prior_priority_topological_ranking")
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = [n for n, d in in_deg.items() if d == 0]
    ranking: list[str] = []
    while available:
        best = max(available, key=lambda n: (float(priority_scores.get(n, 0.0)), n))
        available.remove(best)
        ranking.append(best)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    if len(ranking) != dag.number_of_nodes():
        raise nx.NetworkXUnfeasible("prior_priority_topological_ranking failed: not a DAG.")
    return ranking


def balance_priority_topological_ranking(
    dag: nx.DiGraph,
    *,
    mode: PriorityMode = "dynamic",
) -> list[str]:
    """Priority ``W_out - W_in`` among available sources (static or dynamic)."""

    def _scores(g: nx.DiGraph, _nodes: set[str]) -> dict[str, float]:
        return balance_priority_scores(g)

    return _kahn_priority_ranking(
        dag,
        priority_fn=_scores,
        mode=mode,
        method_name=f"balance_priority_topological_ranking[{mode}]",
    )


def normalized_balance_priority_topological_ranking(
    dag: nx.DiGraph,
    *,
    mode: PriorityMode = "dynamic",
    eps: float = DEFAULT_EPS,
) -> list[str]:
    """Priority ``(W_out-W_in)/(W_out+W_in+eps)`` among available sources."""

    def _scores(g: nx.DiGraph, _nodes: set[str]) -> dict[str, float]:
        return normalized_balance_priority_scores(g, eps=eps)

    return _kahn_priority_ranking(
        dag,
        priority_fn=_scores,
        mode=mode,
        method_name=f"normalized_balance_priority_topological_ranking[{mode}]",
    )


def degree_ratio_priority_topological_ranking(
    dag: nx.DiGraph,
    *,
    mode: PriorityMode = "dynamic",
    eps: float = DEFAULT_EPS,
    log: bool = False,
) -> list[str]:
    """Degree-ratio priority among available sources only (hard constraint)."""

    def _scores(g: nx.DiGraph, _nodes: set[str]) -> dict[str, float]:
        if log:
            return log_degree_ratio_priority_scores(g, eps=eps)
        return degree_ratio_priority_scores(g, eps=eps)

    label = "log_degree_ratio" if log else "degree_ratio"
    return _kahn_priority_ranking(
        dag,
        priority_fn=_scores,
        mode=mode,
        method_name=f"{label}_priority_topological_ranking[{mode}]",
    )


def source_sink_peeling_ranking(
    dag: nx.DiGraph,
    *,
    eps: float = DEFAULT_EPS,
) -> list[str]:
    """Build a ranking from both ends using weighted degree evidence.

    At each step, among remaining **sources** pick the strongest source for the
    front (high residual out-weight, then high balance, then id), and among
    remaining **sinks** pick the strongest sink for the back (high residual
    in-weight, then low balance, then reverse id).  Isolated nodes (both source
    and sink) are placed at the front under the source rule.

    The construction only ever places zero-in-degree nodes at the front and
    zero-out-degree nodes at the back of the residual DAG, so every retained
    edge remains forward.
    """
    require_dag(dag, "source_sink_peeling_ranking")
    remaining = set(dag.nodes())
    if not remaining:
        return []

    in_deg = {n: 0 for n in remaining}
    out_deg = {n: 0 for n in remaining}
    in_w = {n: 0.0 for n in remaining}
    out_w = {n: 0.0 for n in remaining}
    for u, v, data in dag.edges(data=True):
        w = float(data.get("weight", 1.0))
        out_deg[u] += 1
        in_deg[v] += 1
        out_w[u] += w
        in_w[v] += w

    front: list[str] = []
    back: list[str] = []

    def _remove(node: str) -> None:
        remaining.remove(node)
        for succ in dag.successors(node):
            if succ not in remaining:
                continue
            w = float(dag[node][succ].get("weight", 1.0))
            in_deg[succ] -= 1
            in_w[succ] -= w
        for pred in dag.predecessors(node):
            if pred not in remaining:
                continue
            w = float(dag[pred][node].get("weight", 1.0))
            out_deg[pred] -= 1
            out_w[pred] -= w

    while remaining:
        sources = [n for n in remaining if in_deg[n] == 0]
        sinks = [n for n in remaining if out_deg[n] == 0]
        if not sources or not sinks:
            raise nx.NetworkXUnfeasible("source_sink_peeling_ranking failed: not a DAG.")

        if len(remaining) == 1:
            only = next(iter(remaining))
            front.append(only)
            remaining.clear()
            break

        # Prefer placing a strong source when possible; if a node is both a
        # source and a sink (isolated in residual), treat it as a source.
        source_candidates = sources
        sink_candidates = [n for n in sinks if n not in sources or len(remaining) == 1]

        best_source = max(
            source_candidates,
            key=lambda n: (out_w[n], out_w[n] - in_w[n], n),
        )
        # Strength as sink: high in-weight, then low balance (more "losing").
        best_sink = max(
            sink_candidates if sink_candidates else sinks,
            key=lambda n: (in_w[n], in_w[n] - out_w[n], n),
        )

        if best_source == best_sink:
            front.append(best_source)
            _remove(best_source)
            continue

        # Compare source strength vs sink strength; place the stronger end first
        # this iteration, then the other if still present.
        source_strength = out_w[best_source] + abs(out_w[best_source] - in_w[best_source])
        sink_strength = in_w[best_sink] + abs(in_w[best_sink] - out_w[best_sink])
        if source_strength > sink_strength + eps or (
            abs(source_strength - sink_strength) <= eps and best_source <= best_sink
        ):
            front.append(best_source)
            _remove(best_source)
            if best_sink in remaining:
                back.append(best_sink)
                _remove(best_sink)
        else:
            back.append(best_sink)
            _remove(best_sink)
            if best_source in remaining:
                front.append(best_source)
                _remove(best_source)

    ranking = front + list(reversed(back))
    if len(ranking) != dag.number_of_nodes() or set(ranking) != set(dag.nodes()):
        raise RuntimeError("source_sink_peeling_ranking produced an incomplete permutation.")
    assert_valid_topological_order(dag, ranking)
    return ranking


def closest_valid_extension_greedy(
    dag: nx.DiGraph,
    prior_ranking: Sequence[str],
) -> list[str]:
    """Greedy Kahn: among available sources prefer nodes earlier in *prior_ranking*.

    Priority is ``-position_in_prior`` so higher prior positions win.  Nodes
    missing from the prior receive a large positive position (lowest priority).
    """
    require_dag(dag, "closest_valid_extension_greedy")
    prior_pos = {n: i for i, n in enumerate(prior_ranking)}
    missing_pos = len(prior_ranking) + dag.number_of_nodes()
    priority = {n: -float(prior_pos.get(n, missing_pos)) for n in dag.nodes()}
    return prior_priority_topological_ranking(dag, priority)


def enumerate_linear_extensions(
    dag: nx.DiGraph,
    *,
    max_extensions: int | None = None,
) -> list[list[str]]:
    """Enumerate (up to *max_extensions*) linear extensions via recursive Kahn."""
    require_dag(dag, "enumerate_linear_extensions")
    nodes = list(dag.nodes())
    n = len(nodes)
    if n == 0:
        return [[]]
    in_deg0 = {v: dag.in_degree(v) for v in nodes}
    results: list[list[str]] = []

    def _rec(available: list[str], in_deg: dict[str, int], prefix: list[str]) -> None:
        if max_extensions is not None and len(results) >= max_extensions:
            return
        if len(prefix) == n:
            results.append(list(prefix))
            return
        # Deterministic exploration order for reproducibility.
        for node in sorted(available):
            if max_extensions is not None and len(results) >= max_extensions:
                return
            new_available = [x for x in available if x != node]
            new_in = dict(in_deg)
            for child in dag.successors(node):
                new_in[child] -= 1
                if new_in[child] == 0:
                    new_available.append(child)
            prefix.append(node)
            _rec(new_available, new_in, prefix)
            prefix.pop()

    start = [v for v, d in in_deg0.items() if d == 0]
    _rec(start, in_deg0, [])
    return results


def count_linear_extensions(
    dag: nx.DiGraph,
    *,
    max_count: int | None = 100_000,
) -> int | None:
    """Exact count of linear extensions, or None if truncated at *max_count*."""
    require_dag(dag, "count_linear_extensions")
    nodes = list(dag.nodes())
    n = len(nodes)
    if n == 0:
        return 0
    in_deg0 = {v: dag.in_degree(v) for v in nodes}
    total = 0

    def _rec(available: list[str], in_deg: dict[str, int], depth: int) -> bool:
        nonlocal total
        if max_count is not None and total >= max_count:
            return False
        if depth == n:
            total += 1
            return True
        for node in available:
            new_available = [x for x in available if x != node]
            new_in = dict(in_deg)
            for child in dag.successors(node):
                new_in[child] -= 1
                if new_in[child] == 0:
                    new_available.append(child)
            if not _rec(new_available, new_in, depth + 1):
                return False
        return True

    start = [v for v, d in in_deg0.items() if d == 0]
    finished = _rec(start, in_deg0, 0)
    if not finished:
        return None
    return total


def _restrict_prior_to_dag(dag: nx.DiGraph, prior_ranking: Sequence[str]) -> list[str]:
    """Restrict *prior_ranking* to DAG nodes, appending any missing nodes by id."""
    prior_restricted = [x for x in prior_ranking if x in dag]
    missing = sorted(n for n in dag.nodes() if n not in prior_restricted)
    prior_restricted.extend(missing)
    return prior_restricted


def closest_valid_extension_exact(
    dag: nx.DiGraph,
    prior_ranking: Sequence[str],
    *,
    objective: Literal["kendall", "displacement"] = "kendall",
    max_nodes: int = 10,
) -> list[str]:
    """Exact closest linear extension to *prior_ranking* on small DAGs.

    Minimizes Kendall-tau discordant pairs (``objective='kendall'``) or sum of
    absolute position displacements (``objective='displacement'``) by enumerating
    linear extensions.  Raises ValueError if the DAG has more than *max_nodes*
    nodes.  For medium graphs prefer :func:`closest_valid_extension_ilp`.
    """
    require_dag(dag, "closest_valid_extension_exact")
    n = dag.number_of_nodes()
    if n > max_nodes:
        raise ValueError(
            f"closest_valid_extension_exact supports n<={max_nodes}; got n={n}. "
            "Use closest_valid_extension_ilp or closest_valid_extension_greedy."
        )
    extensions = enumerate_linear_extensions(dag)
    if not extensions:
        return []
    prior_restricted = _restrict_prior_to_dag(dag, prior_ranking)

    def _cost(ext: list[str]) -> tuple[float, list[str]]:
        if objective == "kendall":
            return (float(n_violations(ext, prior_restricted)), ext)
        pos_prior = {x: i for i, x in enumerate(prior_restricted)}
        disp = sum(abs(i - pos_prior[x]) for i, x in enumerate(ext))
        return (float(disp), ext)

    best = min(extensions, key=_cost)
    return best


def closest_valid_extension_ilp(
    dag: nx.DiGraph,
    prior_ranking: Sequence[str],
    *,
    objective: Literal["kendall", "displacement"] = "kendall",
    max_nodes: int = 40,
    time_limit_s: float = 30.0,
) -> list[str]:
    """Exact closest linear extension via a linear-ordering MILP (HiGHS).

    Formulation (pairwise binaries ``x[u,v] = 1`` iff ``u`` precedes ``v``):
    * tournament: ``x[u,v] + x[v,u] = 1``;
    * transitivity: ``x[u,v] + x[v,w] <= 1 + x[u,w]``;
    * DAG hard constraints: ``x[u,v] = 1`` for every retained edge ``u → v``;
    * Kendall objective: minimize discordant pairs vs the (judgment-free) prior;
    * displacement objective: minimize ``sum_i |pos(i) - prior_pos(i)|`` using
      position variables derived from the pairwise order.

    Uses ``scipy.optimize.milp`` (HiGHS).  Never consults qrels.
    """
    require_dag(dag, "closest_valid_extension_ilp")
    nodes = sorted(dag.nodes())
    n = len(nodes)
    if n == 0:
        return []
    if n > max_nodes:
        raise ValueError(
            f"closest_valid_extension_ilp supports n<={max_nodes}; got n={n}. "
            "Use closest_valid_extension_greedy for larger DAGs."
        )
    if n == 1:
        return list(nodes)

    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    prior_restricted = _restrict_prior_to_dag(dag, prior_ranking)
    prior_pos = {x: i for i, x in enumerate(prior_restricted)}
    idx = {u: i for i, u in enumerate(nodes)}

    # Variable layout: for i < j, two binaries? Better: x[i,j] for all i!=j
    # Pack as offset = i*(n-1) + (j if j < i else j-1) → n*(n-1) binaries.
    def _var(i: int, j: int) -> int:
        assert i != j
        return i * (n - 1) + (j if j < i else j - 1)

    n_pair = n * (n - 1)
    # Optional position vars p[i] in [0, n-1] for displacement.
    use_pos = objective == "displacement"
    n_pos = n if use_pos else 0
    # Displacement absolute-value auxiliaries d[i] >= |p[i] - prior_pos|.
    n_disp = n if use_pos else 0
    n_vars = n_pair + n_pos + n_disp

    c = np.zeros(n_vars, dtype=float)
    if objective == "kendall":
        for a, b in itertools.combinations(nodes, 2):
            ia, ib = idx[a], idx[b]
            if prior_pos[a] < prior_pos[b]:
                # Cost 1 if b before a (discordant).
                c[_var(ib, ia)] = 1.0
            else:
                c[_var(ia, ib)] = 1.0
    else:
        # Minimize sum d[i]; c on displacement auxiliaries.
        for i in range(n):
            c[n_pair + n_pos + i] = 1.0

    constraints: list[LinearConstraint] = []
    # Tournament constraints.
    for i, j in itertools.combinations(range(n), 2):
        row = np.zeros(n_vars)
        row[_var(i, j)] = 1.0
        row[_var(j, i)] = 1.0
        constraints.append(LinearConstraint(row, 1.0, 1.0))

    # Transitivity (for all distinct triples).
    for i, j, k in itertools.permutations(range(n), 3):
        if not (i < j < k):
            # Emit each unordered triple once with oriented inequalities.
            continue
        for a, b, c_ in ((i, j, k), (i, k, j), (j, i, k), (j, k, i), (k, i, j), (k, j, i)):
            row = np.zeros(n_vars)
            row[_var(a, b)] = 1.0
            row[_var(b, c_)] = 1.0
            row[_var(a, c_)] = -1.0
            constraints.append(LinearConstraint(row, -np.inf, 1.0))

    # DAG edges must be forward.
    for u, v in dag.edges():
        row = np.zeros(n_vars)
        row[_var(idx[u], idx[v])] = 1.0
        constraints.append(LinearConstraint(row, 1.0, 1.0))

    if use_pos:
        # p[i] = sum_j x[j,i]  (number of nodes before i) ∈ {0,...,n-1}
        for i in range(n):
            row = np.zeros(n_vars)
            row[n_pair + i] = 1.0
            for j in range(n):
                if j == i:
                    continue
                row[_var(j, i)] = -1.0
            constraints.append(LinearConstraint(row, 0.0, 0.0))
            # d[i] >= p[i] - prior; d[i] >= prior - p[i]
            pref = float(prior_pos[nodes[i]])
            row_hi = np.zeros(n_vars)
            row_hi[n_pair + n_pos + i] = 1.0
            row_hi[n_pair + i] = -1.0
            constraints.append(LinearConstraint(row_hi, -pref, np.inf))
            row_lo = np.zeros(n_vars)
            row_lo[n_pair + n_pos + i] = 1.0
            row_lo[n_pair + i] = 1.0
            constraints.append(LinearConstraint(row_lo, pref, np.inf))

    integrality = np.ones(n_vars, dtype=int)
    ub = np.ones(n_vars, dtype=float)
    if use_pos:
        # Position and displacement can be continuous (integral at optimum).
        integrality[n_pair:] = 0
        for i in range(n):
            ub[n_pair + i] = float(n - 1)
            ub[n_pair + n_pos + i] = float(n - 1)
    bounds = Bounds(lb=np.zeros(n_vars, dtype=float), ub=ub)

    result = milp(
        c=c,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={"time_limit": float(time_limit_s), "disp": False},
    )
    if result.x is None or not np.isfinite(result.fun):
        raise RuntimeError(
            f"closest_valid_extension_ilp failed (status={result.status}: {result.message}). "
            "Fall back to closest_valid_extension_greedy."
        )

    # Recover order: for each node, count how many others precede it.
    precede_count = {u: 0 for u in nodes}
    x = result.x
    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes):
            if i == j:
                continue
            if x[_var(i, j)] >= 0.5:
                precede_count[v] += 1
    ranking = sorted(nodes, key=lambda u: (precede_count[u], u))
    assert_valid_topological_order(dag, ranking)
    return ranking


def farthest_valid_extension_exact(
    dag: nx.DiGraph,
    prior_ranking: Sequence[str],
    *,
    objective: Literal["kendall", "displacement"] = "kendall",
    max_nodes: int = 10,
) -> list[str]:
    """Exact farthest linear extension from *prior_ranking* (diagnostic oracle)."""
    require_dag(dag, "farthest_valid_extension_exact")
    n = dag.number_of_nodes()
    if n > max_nodes:
        raise ValueError(
            f"farthest_valid_extension_exact supports n<={max_nodes}; got n={n}."
        )
    extensions = enumerate_linear_extensions(dag)
    prior_restricted = _restrict_prior_to_dag(dag, prior_ranking)

    def _score(ext: list[str]) -> float:
        if objective == "kendall":
            return float(n_violations(ext, prior_restricted))
        pos_prior = {x: i for i, x in enumerate(prior_restricted)}
        return float(sum(abs(i - pos_prior[x]) for i, x in enumerate(ext)))

    return max(extensions, key=_score)


def random_topological_ranking(
    dag: nx.DiGraph,
    *,
    seed: int,
) -> list[str]:
    """Sample one linear extension by random choice among available sources."""
    require_dag(dag, "random_topological_ranking")
    rng = random.Random(seed)
    in_deg = {n: dag.in_degree(n) for n in dag.nodes()}
    available = [n for n, d in in_deg.items() if d == 0]
    ranking: list[str] = []
    while available:
        # Sort before choice so the RNG sees a deterministic candidate order.
        available_sorted = sorted(available)
        best = rng.choice(available_sorted)
        available = [x for x in available if x != best]
        ranking.append(best)
        for child in dag.successors(best):
            in_deg[child] -= 1
            if in_deg[child] == 0:
                available.append(child)
    if len(ranking) != dag.number_of_nodes():
        raise nx.NetworkXUnfeasible("random_topological_ranking failed: not a DAG.")
    return ranking


def sample_linear_extensions(
    dag: nx.DiGraph,
    *,
    n_samples: int,
    seed: int,
) -> list[list[str]]:
    """Draw *n_samples* seed-reproducible random linear extensions."""
    return [
        random_topological_ranking(dag, seed=seed + i)
        for i in range(int(n_samples))
    ]


def linear_extension_metric_dispersion(
    rankings: Sequence[Sequence[str]],
    reference: Sequence[str],
    *,
    metric: Literal["kendall_tau", "n_violations"] = "kendall_tau",
) -> dict[str, float | int | None]:
    """Summarize metric variation across sampled linear extensions."""
    if not rankings:
        return {
            "n_samples": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "q25": None,
            "q50": None,
            "q75": None,
        }
    values: list[float] = []
    for ranking in rankings:
        if metric == "kendall_tau":
            values.append(float(kendall_tau(list(ranking), list(reference))))
        else:
            values.append(float(n_violations(list(ranking), list(reference))))
    values_sorted = sorted(values)
    n = len(values_sorted)

    def _quantile(q: float) -> float:
        if n == 1:
            return values_sorted[0]
        idx = q * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return values_sorted[lo]
        w = idx - lo
        return (1.0 - w) * values_sorted[lo] + w * values_sorted[hi]

    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return {
        "n_samples": n,
        "mean": mean,
        "std": math.sqrt(var),
        "min": values_sorted[0],
        "max": values_sorted[-1],
        "q25": _quantile(0.25),
        "q50": _quantile(0.50),
        "q75": _quantile(0.75),
    }


def dag_backward_edge_weight(graph: nx.DiGraph, ranking: Sequence[str]) -> float:
    """Sum of edge weights violated by *ranking* (edge u→v with v before u)."""
    pos = {n: i for i, n in enumerate(ranking)}
    total = 0.0
    for u, v, data in graph.edges(data=True):
        if u not in pos or v not in pos:
            continue
        if pos[v] < pos[u]:
            total += float(data.get("weight", 1.0))
    return total


def pairwise_accuracy_vs_graph(graph: nx.DiGraph, ranking: Sequence[str]) -> float:
    """Fraction of graph edges that agree with *ranking* (forward edges)."""
    edges = list(graph.edges())
    if not edges:
        return 1.0
    pos = {n: i for i, n in enumerate(ranking)}
    agree = 0
    considered = 0
    for u, v in edges:
        if u not in pos or v not in pos:
            continue
        considered += 1
        if pos[u] < pos[v]:
            agree += 1
    return agree / considered if considered else 1.0


def build_prior_scores_from_ranking(ranking: Sequence[str]) -> dict[str, float]:
    """Convert a total order into descending prior scores (n-1, n-2, ...)."""
    n = len(ranking)
    return {doc: float(n - i) for i, doc in enumerate(ranking)}


def score_sum_prior_from_graph(graph: nx.DiGraph) -> dict[str, float]:
    """Judgment-free score-sum prior from (possibly cyclic) original graph."""
    return score_sum_scores(graph)


def borda_prior_from_graph(graph: nx.DiGraph) -> dict[str, float]:
    """Judgment-free tournament-Borda prior from the preference graph."""
    return borda_scores(graph)


def rrf_prior_from_ranked_lists(
    per_system_ranked_lists: Sequence[Sequence[str]],
    candidate_doc_ids: Iterable[str] | None = None,
    *,
    k: float = 60.0,
) -> dict[str, float]:
    """Judgment-free RRF prior scores from multi-system ranked lists."""
    from consistency_ranker.rrf_ranking import rrf_scores_and_best_ranks

    lists = [list(lst) for lst in per_system_ranked_lists]
    scores, _ = rrf_scores_and_best_ranks(lists, k=k)
    if candidate_doc_ids is None:
        return dict(scores)
    return {str(d): float(scores.get(str(d), 0.0)) for d in candidate_doc_ids}


def combsum_prior_from_score_maps(
    per_system_scores: Sequence[dict[str, float]],
    candidate_doc_ids: Iterable[str] | None = None,
) -> dict[str, float]:
    """Judgment-free CombSUM prior: sum of per-system scores per document.

    Each map should already be normalized the same way as the retrieval
    pipeline (e.g. min-max per ranker).  Missing docs contribute 0.
    """
    if candidate_doc_ids is None:
        keys: set[str] = set()
        for m in per_system_scores:
            keys.update(str(d) for d in m)
        candidates = sorted(keys)
    else:
        candidates = [str(d) for d in candidate_doc_ids]
    out: dict[str, float] = {d: 0.0 for d in candidates}
    for m in per_system_scores:
        for d in candidates:
            out[d] += float(m.get(d, 0.0))
    return out


def borda_fuse_prior_from_ranked_lists(
    per_system_ranked_lists: Sequence[Sequence[str]],
    candidate_doc_ids: Iterable[str] | None = None,
) -> dict[str, float]:
    """Judgment-free Borda-fusion prior over multi-system ranked lists."""
    from consistency_ranker.borda_fuse_ranking import borda_fuse_scores

    lists = [list(lst) for lst in per_system_ranked_lists]
    if candidate_doc_ids is None:
        universe: set[str] = set()
        for lst in lists:
            universe.update(str(x) for x in lst)
        candidates = sorted(universe)
    else:
        candidates = [str(d) for d in candidate_doc_ids]
    return borda_fuse_scores(lists, n_q=len(candidates))


def run_hard_constraint_method(
    method: str,
    dag: nx.DiGraph,
    *,
    prior_scores: dict[str, float] | None = None,
    prior_ranking: Sequence[str] | None = None,
    seed: int = 0,
    eps: float = DEFAULT_EPS,
) -> list[str]:
    """Dispatch a named hard-constraint method. Never uses qrels."""
    if method == "lexicographic_topo":
        return lexicographic_topological_ranking(dag)
    if method == "prior_priority_topo":
        if prior_scores is None:
            raise ValueError("prior_priority_topo requires prior_scores.")
        return prior_priority_topological_ranking(dag, prior_scores)
    if method == "balance_priority_topo_static":
        return balance_priority_topological_ranking(dag, mode="static")
    if method == "balance_priority_topo_dynamic":
        return balance_priority_topological_ranking(dag, mode="dynamic")
    if method == "norm_balance_priority_topo_static":
        return normalized_balance_priority_topological_ranking(dag, mode="static", eps=eps)
    if method == "norm_balance_priority_topo_dynamic":
        return normalized_balance_priority_topological_ranking(dag, mode="dynamic", eps=eps)
    if method == "degree_ratio_priority_topo_static":
        return degree_ratio_priority_topological_ranking(dag, mode="static", eps=eps, log=False)
    if method == "degree_ratio_priority_topo_dynamic":
        return degree_ratio_priority_topological_ranking(dag, mode="dynamic", eps=eps, log=False)
    if method == "log_degree_ratio_priority_topo_static":
        return degree_ratio_priority_topological_ranking(dag, mode="static", eps=eps, log=True)
    if method == "log_degree_ratio_priority_topo_dynamic":
        return degree_ratio_priority_topological_ranking(dag, mode="dynamic", eps=eps, log=True)
    if method == "source_sink_peeling":
        return source_sink_peeling_ranking(dag, eps=eps)
    if method == "closest_valid_extension_greedy":
        if prior_ranking is None:
            raise ValueError("closest_valid_extension_greedy requires prior_ranking.")
        return closest_valid_extension_greedy(dag, prior_ranking)
    if method == "closest_valid_extension_exact":
        if prior_ranking is None:
            raise ValueError("closest_valid_extension_exact requires prior_ranking.")
        return closest_valid_extension_exact(dag, prior_ranking)
    if method == "closest_valid_extension_ilp":
        if prior_ranking is None:
            raise ValueError("closest_valid_extension_ilp requires prior_ranking.")
        return closest_valid_extension_ilp(dag, prior_ranking)
    if method == "random_topo":
        return random_topological_ranking(dag, seed=seed)
    raise ValueError(f"Unknown hard-constraint method: {method!r}")


def method_metadata() -> list[dict[str, Any]]:
    """Machine-readable catalog of hard-constraint methods and guarantees."""
    return [
        {
            "method": "lexicographic_topo",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Kahn; min document id among available sources.",
        },
        {
            "method": "prior_priority_topo",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Kahn; highest prior among available sources.",
        },
        {
            "method": "balance_priority_topo_static",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Static W_out-W_in priorities.",
        },
        {
            "method": "balance_priority_topo_dynamic",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Dynamic W_out-W_in on residual DAG.",
        },
        {
            "method": "norm_balance_priority_topo_static",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Static normalized balance from older MWFAS work.",
        },
        {
            "method": "norm_balance_priority_topo_dynamic",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Dynamic normalized balance.",
        },
        {
            "method": "degree_ratio_priority_topo_static",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Static (W_out+eps)/(W_in+eps) among sources only.",
        },
        {
            "method": "degree_ratio_priority_topo_dynamic",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Dynamic degree ratio among sources only.",
        },
        {
            "method": "log_degree_ratio_priority_topo_static",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Static log degree ratio among sources only.",
        },
        {
            "method": "log_degree_ratio_priority_topo_dynamic",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Dynamic log degree ratio among sources only.",
        },
        {
            "method": "source_sink_peeling",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Build from both ends using residual weighted degrees.",
        },
        {
            "method": "closest_valid_extension_greedy",
            "family": "hard_constraint",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Greedy closest linear extension to an external prior.",
        },
        {
            "method": "closest_valid_extension_exact",
            "family": "hard_constraint_oracle",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Exact closest extension via enumeration; small DAGs only.",
        },
        {
            "method": "closest_valid_extension_ilp",
            "family": "hard_constraint_oracle",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Exact closest extension via HiGHS MILP; medium DAGs.",
        },
        {
            "method": "random_topo",
            "family": "hard_constraint_stochastic",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": False,
            "notes": "Seed-reproducible random linear extension.",
        },
        {
            "method": "best_extension_oracle",
            "family": "diagnostic_oracle",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Closest extension; evaluation may use qrels afterward.",
        },
        {
            "method": "worst_extension_oracle",
            "family": "diagnostic_oracle",
            "guarantees_topo": True,
            "uses_qrels": False,
            "deterministic": True,
            "notes": "Farthest extension; diagnostic only.",
        },
    ]


# Back-compat alias used by older priority_topological_ranking call sites.
def priority_topological_ranking_from_scores(
    dag: nx.DiGraph,
    priority_scores: dict[str, float],
) -> list[str]:
    return prior_priority_topological_ranking(dag, priority_scores)


def all_pairs_reachable_incomparable_fraction(dag: nx.DiGraph) -> float:
    """Fraction of unordered pairs with no directed path either way."""
    nodes = list(dag.nodes())
    n = len(nodes)
    if n < 2:
        return 0.0
    reachable = {u: set(nx.descendants(dag, u)) for u in nodes}
    incomparable = 0
    total = 0
    for a, b in itertools.combinations(nodes, 2):
        total += 1
        if b not in reachable[a] and a not in reachable[b]:
            incomparable += 1
    return incomparable / total if total else 0.0
