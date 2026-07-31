"""Classify each original edge's fate after a repair candidate is applied.

Four mutually exclusive categories, computed via ``nx.condensation`` (always
a DAG, even when the repaired subgraph still contains a residual cycle) plus
a topological rank of its supernodes:

- ``preserved``: edge still present in the repaired subgraph.
- ``removed``: edge deleted by repair, but the final rank order still
  happens to place *u* before *v*.
- ``reversed``: edge deleted and the final rank order places *v* before *u*
  (the common case).
- ``unresolved``: edge lies inside a residual nontrivial SCC of the repaired
  subgraph -- the candidate didn't fully resolve this part of the cycle
  (e.g. the deliberately-unrepaired "original ordering" candidate, or a
  weak-edge-deletion variant that allows a residual cycle).
"""

from __future__ import annotations

from typing import Literal

import networkx as nx

Disposition = Literal["preserved", "removed", "reversed", "unresolved"]


def classify_edge_dispositions(
    original_subgraph: nx.DiGraph,
    repaired_subgraph: nx.DiGraph,
) -> dict[tuple[str, str], Disposition]:
    """Classify every edge of *original_subgraph* against *repaired_subgraph*.

    Both graphs must share the same node set; *repaired_subgraph* must be
    edge-subset of *original_subgraph* (repair only removes edges, never
    adds or reverses them in-place -- "reversal" is a downstream ranking
    artifact, tracked here, not a graph mutation).
    """
    if set(original_subgraph.nodes()) != set(repaired_subgraph.nodes()):
        raise ValueError("original_subgraph and repaired_subgraph must share the same node set")

    residual_sccs = [s for s in nx.strongly_connected_components(repaired_subgraph) if len(s) > 1]
    residual_member: dict[str, int] = {}
    for idx, scc in enumerate(residual_sccs):
        for node in scc:
            residual_member[node] = idx

    condensation = nx.condensation(repaired_subgraph)
    topo_rank = {
        supernode: rank for rank, supernode in enumerate(nx.topological_sort(condensation))
    }
    mapping = condensation.graph["mapping"]
    node_rank = {n: topo_rank[mapping[n]] for n in repaired_subgraph.nodes()}

    out: dict[tuple[str, str], Disposition] = {}
    for u, v in original_subgraph.edges():
        same_residual_scc = (
            u in residual_member
            and v in residual_member
            and residual_member[u] == residual_member[v]
        )
        if same_residual_scc:
            out[(u, v)] = "unresolved"
        elif repaired_subgraph.has_edge(u, v):
            out[(u, v)] = "preserved"
        elif node_rank[u] < node_rank[v]:
            out[(u, v)] = "removed"
        else:
            out[(u, v)] = "reversed"
    return out


__all__ = ["Disposition", "classify_edge_dispositions"]
