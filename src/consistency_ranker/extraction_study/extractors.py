"""Registry of preference-graph extraction methods for the bounded
extraction-vs-repair study.

Every entry is a pure function of the graph AS-IS -- none of these repair
cycles first. Isolating extraction from repair is the whole point of this
study: the repair-frontier program found that most observed frontier
benefit came from alternative extraction methods (Borda/PageRank/rank-
centrality), not from SCC-local or protected repair, so this study checks
that finding directly and systematically.

Prior-fusion variants use the graph's OWN score-sum as the "prior", matching
this repository's established convention (see `_score_sum_prior_scores` in
scripts/run_real_experiment.py, identical to
:func:`consistency_ranker.baseline_ranking.score_sum_scores`) -- there is no
external classical-retriever score available for these already-materialized
graphs, and this is how the existing hybrid rankers are invoked elsewhere in
the repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import networkx as nx

from consistency_ranker.baseline_ranking import (
    borda_ranking,
    copeland_ranking,
    fas_balance_score_prior_alpha_ranking,
    hodge_rank_ranking,
    hybrid_rrf_fas_regularized_ranking,
    pagerank_ranking,
    rank_centrality_ranking,
    score_sum_scores,
    weighted_out_minus_in_ranking,
)

ExtractorFamily = Literal["graph_only", "prior_fusion"]


@dataclass(frozen=True)
class Extractor:
    name: str
    family: ExtractorFamily
    fn: Callable[[nx.DiGraph], list[str]]


def _fas_balance_prior_fusion(graph: nx.DiGraph) -> list[str]:
    prior = score_sum_scores(graph)
    return fas_balance_score_prior_alpha_ranking(graph, prior, alpha=0.5)


def _hybrid_rrf_prior_fusion(graph: nx.DiGraph) -> list[str]:
    prior = score_sum_scores(graph)
    return hybrid_rrf_fas_regularized_ranking(graph, prior, fas_regularization=0.2)


# "incumbent" and "copeland" are deliberately the SAME function: the
# repair-frontier program's incumbent extraction method IS Copeland. Keeping
# both names makes that identity visible in the output (their delta is
# always exactly 0) rather than silently assuming it.
EXTRACTORS: dict[str, Extractor] = {
    "incumbent": Extractor("incumbent", "graph_only", copeland_ranking),
    "copeland": Extractor("copeland", "graph_only", copeland_ranking),
    "borda": Extractor("borda", "graph_only", borda_ranking),
    "pagerank": Extractor("pagerank", "graph_only", pagerank_ranking),
    "rank_centrality": Extractor("rank_centrality", "graph_only", rank_centrality_ranking),
    "balance_score": Extractor("balance_score", "graph_only", weighted_out_minus_in_ranking),
    "hodge_rank": Extractor("hodge_rank", "graph_only", hodge_rank_ranking),
    "fas_balance_prior_fusion": Extractor(
        "fas_balance_prior_fusion", "prior_fusion", _fas_balance_prior_fusion
    ),
    "hybrid_rrf_prior_fusion": Extractor(
        "hybrid_rrf_prior_fusion", "prior_fusion", _hybrid_rrf_prior_fusion
    ),
}

INCUMBENT_NAME = "incumbent"


def extract_all(graph: nx.DiGraph) -> dict[str, list[str]]:
    """Run every registered extractor on *graph* as-is (no repair).
    Extractors that raise on a degenerate graph are omitted, not silently
    substituted -- callers should check which names are present."""
    out: dict[str, list[str]] = {}
    for name, extractor in EXTRACTORS.items():
        try:
            out[name] = extractor.fn(graph)
        except Exception:  # noqa: BLE001 - degenerate-graph edge cases are skipped, not fatal
            continue
    return out


__all__ = ["Extractor", "ExtractorFamily", "EXTRACTORS", "INCUMBENT_NAME", "extract_all"]
