"""Reinsert repaired per-SCC local orderings into an unchanged global ranking.

Non-member slots are never written, so their identity is positionally
exact -- strictly stronger than "relative order preserved," and avoids
re-running a whole-graph ranking extraction (which would not guarantee
this, since scores for untouched nodes can shift/tie once other nodes'
edges change).
"""

from __future__ import annotations


def reinsert_scc_orderings(
    incumbent_ranking: list[str],
    local_orders: dict[frozenset[str], list[str]],
) -> list[str]:
    """Splice per-SCC local orderings back into *incumbent_ranking*.

    Parameters
    ----------
    incumbent_ranking:
        The full-graph incumbent ranking (e.g. ``copeland_ranking`` on the
        original, unrepaired graph), computed once per query and shared
        across every SCC-local candidate for that query so all candidates
        are comparable slot-substitutions of the same base sequence.
    local_orders:
        ``{frozenset(scc_members): new_local_order}`` for every repaired
        nontrivial SCC. SCCs are disjoint node sets by construction
        (``nx.strongly_connected_components``), so index sets never collide.

    Returns
    -------
    list[str]
        A permutation of *incumbent_ranking* where only the index
        positions occupied by SCC members have been overwritten.
    """
    result = list(incumbent_ranking)
    for members, new_order in local_orders.items():
        if set(new_order) != set(members):
            raise ValueError(
                f"local order {new_order!r} is not a permutation of SCC members {members!r}"
            )
        positions = sorted(i for i, n in enumerate(incumbent_ranking) if n in members)
        if len(positions) != len(new_order):
            raise ValueError(
                f"SCC {members!r} occupies {len(positions)} slots in the incumbent "
                f"ranking but local order has {len(new_order)} members"
            )
        for slot, node in zip(positions, new_order):
            result[slot] = node
    return result


__all__ = ["reinsert_scc_orderings"]
