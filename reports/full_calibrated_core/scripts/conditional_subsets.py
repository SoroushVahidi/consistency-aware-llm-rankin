"""Reusable per-query conditional-subset classification.

The manuscript's repaired-versus-unrepaired tables previously reported only
averages over all queries. This module classifies each (query, pair) into
the subsets needed to check whether that average conceals structure: most
queries have no cycle at all, and averaging a large inactive group together
with a small active group can hide or dilute a real effect in either
direction. Every classifier here is a pure function of one already-computed
``eval_record`` (the dict returned by
``CalibrationEvaluator.evaluate_query``) plus one ``(unrepaired_key,
repaired_key)`` method-pair, so it can be reused identically by the primary
protocol's canonical-pool analysis and by any pool-robustness or
protocol-robustness driver without duplicating classification logic.

Subset definitions (all mutually attachable to the same query -- a query
can be, e.g., both "has_cycle" and "ranking_changed" at once; these are
independent boolean flags, not a partition):

  has_cycle           -- eval_record["graph_stats"]["is_cyclic"] is True
                         before repair.
  repair_active       -- repair actually removed at least one edge
                         (len(eval_record["removed_edges"]) > 0). A query
                         can have a cycle that repair does not touch only
                         if repair failed to break it, which should not
                         happen given the repair guarantees a DAG; in
                         practice repair_active and has_cycle coincide
                         almost exactly, and any gap is itself diagnostic
                         (see run_failure_decomposition.py).
  ranking_changed     -- the repaired method's full output ranking differs
                         (as an ordered list) from the unrepaired method's,
                         for the given pair.
  topk_changed        -- the *set* of the top-k doc ids differs between
                         repaired and unrepaired, for the given pair and
                         the query's own top_k.
  relevance_order_changed -- pairwise_accuracy (agreement with the qrels-
                         derived reference ordering, already computed by
                         evaluate_query) differs between repaired and
                         unrepaired -- i.e. repair changed the ordering of
                         at least one pair of documents with different
                         relevance labels, not just unlabeled documents.
  metric_changed      -- ndcg_at_k differs (repaired != unrepaired) beyond
                         floating-point tolerance.
"""

from __future__ import annotations

from typing import Any

_FLOAT_TOL = 1.0e-12


def classify_query_pair(
    eval_record: dict[str, Any],
    *,
    unrepaired_key: str,
    repaired_key: str,
    top_k: int,
) -> dict[str, bool]:
    outputs = eval_record["method_outputs"]
    unrepaired = outputs[unrepaired_key]
    repaired = outputs[repaired_key]

    has_cycle = bool(eval_record["graph_stats"].get("is_cyclic", False))
    repair_active = len(eval_record["removed_edges"]) > 0

    unrepaired_ranking = list(unrepaired["ranking"])
    repaired_ranking = list(repaired["ranking"])
    ranking_changed = unrepaired_ranking != repaired_ranking
    topk_changed = set(unrepaired_ranking[:top_k]) != set(repaired_ranking[:top_k])

    unrepaired_pw = unrepaired.get("pairwise_accuracy")
    repaired_pw = repaired.get("pairwise_accuracy")
    if unrepaired_pw is None or repaired_pw is None:
        relevance_order_changed = False
    else:
        relevance_order_changed = abs(float(unrepaired_pw) - float(repaired_pw)) > _FLOAT_TOL

    unrepaired_ndcg = unrepaired.get("ndcg_at_k")
    repaired_ndcg = repaired.get("ndcg_at_k")
    if unrepaired_ndcg is None or repaired_ndcg is None:
        metric_changed = False
    else:
        metric_changed = abs(float(unrepaired_ndcg) - float(repaired_ndcg)) > _FLOAT_TOL

    return {
        "has_cycle": has_cycle,
        "repair_active": repair_active,
        "ranking_changed": ranking_changed,
        "topk_changed": topk_changed,
        "relevance_order_changed": relevance_order_changed,
        "metric_changed": metric_changed,
    }


# Ordered so each named subset in the task's requirement (B..F) maps to one
# boolean flag above, plus "all" (A) which every query satisfies trivially.
SUBSET_DEFINITIONS: dict[str, str] = {
    "all": "every evaluated query (no filter)",
    "has_cycle": "queries whose unrepaired graph contains at least one directed cycle",
    "repair_active": "queries where repair actually removed at least one edge",
    "ranking_changed": "queries where the repaired method's full ranking differs from unrepaired",
    "topk_changed": "queries where the top-k document set differs between repaired and unrepaired",
    "relevance_order_changed": (
        "queries where pairwise agreement with the qrels-derived reference ordering "
        "changed between repaired and unrepaired"
    ),
}


def failure_decomposition_counts(flags_by_query: list[dict[str, bool]]) -> dict[str, Any]:
    """Descriptive accounting of *why* repair had no visible effect, built
    directly from observed classify_query_pair() outputs -- not the
    obsolete six-way rule-based taxonomy. Categories are mutually exclusive
    and exhaustive over the query set for one method pair:

      no_cycle                 -- has_cycle is False (repair was never
                                   relevant; there was nothing to fix).
      cycle_but_repair_inactive -- has_cycle True but repair_active False
                                   (should not occur in practice; flagged
                                   as a diagnostic if it does).
      repair_inactive_on_ranking -- repair_active True but ranking_changed
                                   False (edges were removed but the
                                   specific ranking method's output was
                                   unaffected).
      ranking_changed_metric_stable -- ranking_changed True but
                                   metric_changed False (the ranking
                                   moved, but not in a way nDCG@k detects).
      metric_changed            -- metric_changed True (repair produced a
                                   measurable retrieval-metric difference,
                                   in either direction).
    """
    n = len(flags_by_query)
    counts = {
        "n_queries": n,
        "no_cycle": 0,
        "cycle_but_repair_inactive": 0,
        "repair_inactive_on_ranking": 0,
        "ranking_changed_metric_stable": 0,
        "metric_changed": 0,
    }
    for flags in flags_by_query:
        if not flags["has_cycle"]:
            counts["no_cycle"] += 1
        elif not flags["repair_active"]:
            counts["cycle_but_repair_inactive"] += 1
        elif not flags["ranking_changed"]:
            counts["repair_inactive_on_ranking"] += 1
        elif not flags["metric_changed"]:
            counts["ranking_changed_metric_stable"] += 1
        else:
            counts["metric_changed"] += 1
    if n > 0:
        for key in (
            "no_cycle",
            "cycle_but_repair_inactive",
            "repair_inactive_on_ranking",
            "ranking_changed_metric_stable",
            "metric_changed",
        ):
            counts[f"{key}_fraction"] = counts[key] / n
    return counts
