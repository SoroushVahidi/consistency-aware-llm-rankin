"""Per-edge multi-provider confidence/unanimity table.

Generalizes the inline ``provider_disagreement`` computation in
``scripts/run_reviewer_concerns_program.py`` (a single scalar per query)
into a reusable per-edge table, so individual edges -- not just whole
queries -- can be flagged as unanimous, disputed, high/low margin, etc.
"""

from __future__ import annotations

from collections import defaultdict

from consistency_ranker.pairwise_prefs import Preference

from .types import EdgeConfidence


def compute_edge_confidence(
    provider_prefs: dict[str, list[Preference]],
) -> dict[tuple[str, str], EdgeConfidence]:
    """Build an :class:`EdgeConfidence` for every directed edge implied by
    *provider_prefs* (one entry per direction that at least one provider
    voted for -- a genuine mutual pair gets two independent entries, one
    per direction, matching how :func:`build_graph` would materialize both
    directed edges).

    Parameters
    ----------
    provider_prefs:
        ``{provider_name: [Preference, ...]}`` -- the same per-provider
        preference lists used to build per-provider and aggregate graphs.
    """
    # canonical unordered pair -> {provider: (winner, weight)}
    pair_votes: dict[frozenset[str], dict[str, tuple[str, float]]] = defaultdict(dict)
    for provider, prefs in provider_prefs.items():
        for p in prefs:
            key = frozenset((p.winner, p.loser))
            pair_votes[key][provider] = (p.winner, float(p.weight))

    result: dict[tuple[str, str], EdgeConfidence] = {}
    for key, votes in pair_votes.items():
        if len(key) != 2:
            continue
        directions = {w for w, _ in votes.values()}
        for winner in directions:
            (loser,) = [x for x in key if x != winner]
            agree = [(prov, wt) for prov, (w, wt) in votes.items() if w == winner]
            disagree = [(prov, wt) for prov, (w, wt) in votes.items() if w != winner]
            n_total = len(votes)
            n_agree = len(agree)
            agree_weight = sum(wt for _, wt in agree)
            disagree_weight = sum(wt for _, wt in disagree)
            result[(winner, loser)] = EdgeConfidence(
                winner=winner,
                loser=loser,
                n_providers_total=n_total,
                n_providers_agree=n_agree,
                unanimous=(n_agree == n_total),
                margin=agree_weight - disagree_weight,
                aggregate_weight=agree_weight,
            )
    return result


__all__ = ["compute_edge_confidence"]
