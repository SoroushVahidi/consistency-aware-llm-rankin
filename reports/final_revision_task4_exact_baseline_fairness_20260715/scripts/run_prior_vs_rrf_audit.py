#!/usr/bin/env python3
"""JDIQ Task 4, section 6: line-by-line Prior vs RRF discrepancy audit.

Root-cause candidates checked directly (not assumed):
  - rank universe: Prior computes each doc's rank AMONG CANDIDATE-POOL
    documents only (restrict-then-rank); the standalone RRF baseline
    computes rank among the ranker's ENTIRE stored list, then restricts
    the final ranking to candidates (rank-then-restrict). This is a
    genuine scoring difference, not merely a tie-break difference.
  - missing-document fallback: Prior falls back to the score-sum-of-graph
    prior for candidates unscored by every ranker; standalone RRF gives
    such docs a fused score of exactly 0.0.
  - tie-breaking: Prior breaks ties by doc_id only; standalone RRF breaks
    ties by best observed rank, then doc_id.

Uses the same canonical-pool, ms1-regime graph construction as the
manuscript pipeline (so the score-sum fallback matches production exactly).
"""

# ruff: noqa: I001 -- import order below is semantically constrained (see comment)
from __future__ import annotations

import json
import time
from typing import Any

from scipy.stats import kendalltau, spearmanr

# task4_common must import before full_calibration_utils: it puts the
# latter's directory on sys.path (see task4_common's sys.path bootstrap).
import task4_common as t4
import full_calibration_utils as fcu
from consistency_ranker.rrf_ranking import (
    DEFAULT_RRF_K,
    per_query_rrf_ranking_from_score_maps,
    ranked_list_from_score_entries,
    rrf_scores_and_best_ranks,
)
from scripts.run_real_experiment import (
    _prior_only_ranking,
    _rrf_prior_scores_for_query,
    _score_sum_prior_scores,
)

REGIME = "ms1"


def _tie_groups(score_map: dict[str, float]) -> list[list[str]]:
    by_score: dict[float, list[str]] = {}
    for doc_id, score in score_map.items():
        by_score.setdefault(round(float(score), 12), []).append(doc_id)
    return [docs for docs in by_score.values() if len(docs) > 1]


def audit_dataset(dataset: str) -> dict[str, Any]:
    dataset_inputs = t4.rfc._analysis_dataset_inputs(
        dataset, pool_size_override=t4.CANONICAL_POOL[dataset]
    )
    baseline = fcu.raw_baseline_statistics(dataset_inputs)
    pair_margins, _zero_var = t4.rfc._pair_margin_summary(dataset_inputs, "minmax_query_ranker")
    threshold_config = fcu.choose_threshold_config(
        dataset=dataset,
        regime=REGIME,
        calibration="minmax_query_ranker",
        threshold_mode="retention_matched",
        baseline_vote_rates=baseline[REGIME]["vote_rates"],
        baseline_edge_count=baseline[REGIME]["edge_count"],
        calibration_pair_margins=pair_margins,
        per_query_inputs=dataset_inputs["per_query_inputs"],
    )

    rows: list[dict[str, Any]] = []
    worked_example: dict[str, Any] | None = None
    for item in dataset_inputs["per_query_inputs"]:
        qid = item["query_id"]
        pool = item["candidate_pool"]
        raw_scores_by_ranker = item["raw_scores_by_ranker"]

        artifacts = fcu.build_query_vote_artifacts(
            query_id=qid,
            raw_scores_by_ranker=raw_scores_by_ranker,
            candidate_pool=pool,
            calibration="minmax_query_ranker",
            threshold_config=threshold_config,
        )
        prefs = [
            fcu.Preference(
                winner=str(r["winner_doc_id"]),
                loser=str(r["loser_doc_id"]),
                weight=float(r["weight"]),
            )
            for r in artifacts["rows"]
        ]
        graph = fcu.build_graph(prefs)
        graph.add_nodes_from(pool)

        score_prior_sets = [
            {qid: list(raw_scores_by_ranker[r].items())}
            for r in t4.RANKERS
            if raw_scores_by_ranker.get(r)
        ]
        prior_scores = _rrf_prior_scores_for_query(
            query_id=qid,
            candidate_nodes=set(pool),
            score_prior_sets=score_prior_sets,
            fallback_scores=_score_sum_prior_scores(graph),
        )
        prior_ranking = _prior_only_ranking(pool, prior_scores)

        per_system_full_lists = [
            ranked_list_from_score_entries(sm.get(qid, [])) for sm in score_prior_sets
        ]
        rrf_full_scores, rrf_best_rank = rrf_scores_and_best_ranks(
            per_system_full_lists, k=DEFAULT_RRF_K
        )
        rrf_ranking = per_query_rrf_ranking_from_score_maps(
            qid, score_prior_sets, pool, k=DEFAULT_RRF_K
        )

        # Candidate sets are identical by construction (both methods are
        # restricted to the same `pool` at output time) -- verified, not assumed.
        identical_candidate_sets = set(prior_ranking) == set(rrf_ranking) == set(pool)

        # Compare the two methods' FUSED SCORE per candidate doc (before any
        # tie-break is applied).
        prior_score_map = {d: prior_scores.get(d, 0.0) for d in pool}
        rrf_score_map = {d: rrf_full_scores.get(d, 0.0) for d in pool}
        identical_fused_scores = all(
            abs(prior_score_map[d] - rrf_score_map[d]) < 1e-12 for d in pool
        )
        # missing from every ranker -> Prior uses graph fallback, RRF uses 0.0
        unscored_by_any_ranker = [
            d for d in pool if all(d not in raw_scores_by_ranker.get(r, {}) for r in t4.RANKERS)
        ]

        rrf_tie_groups = _tie_groups(rrf_score_map)
        prior_tie_groups = _tie_groups(prior_score_map)

        # Does the RANK ORDER induced by fused scores alone (ignoring exact
        # tie-break rule) already differ, or would resolving ties identically
        # make the rankings match? Build the "order ignoring ties" partition:
        # two methods agree on order-modulo-ties iff every pair of docs with
        # DIFFERENT scores under BOTH methods is ordered the same way.
        order_modulo_ties_agrees = True
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                a, b = pool[i], pool[j]
                pa, pb = prior_score_map[a], prior_score_map[b]
                ra, rb = rrf_score_map[a], rrf_score_map[b]
                if abs(pa - pb) < 1e-12 or abs(ra - rb) < 1e-12:
                    continue  # tie in at least one method -- not informative for this check
                if (pa > pb) != (ra > rb):
                    order_modulo_ties_agrees = False
                    break
            if not order_modulo_ties_agrees:
                break

        exact_ranking_match = prior_ranking == rrf_ranking
        tau, _p = kendalltau(
            [prior_ranking.index(d) for d in pool], [rrf_ranking.index(d) for d in pool]
        )
        rho, _p2 = spearmanr(
            [prior_ranking.index(d) for d in pool], [rrf_ranking.index(d) for d in pool]
        )

        row = {
            "dataset": dataset,
            "query_id": qid,
            "pool_size": len(pool),
            "identical_candidate_sets": identical_candidate_sets,
            "identical_fused_scores": identical_fused_scores,
            "n_unscored_by_any_ranker": len(unscored_by_any_ranker),
            "n_rrf_tie_groups": len(rrf_tie_groups),
            "largest_rrf_tie_group_size": max((len(g) for g in rrf_tie_groups), default=0),
            "n_prior_tie_groups": len(prior_tie_groups),
            "largest_prior_tie_group_size": max((len(g) for g in prior_tie_groups), default=0),
            "order_modulo_ties_agrees": order_modulo_ties_agrees,
            "exact_ranking_match": exact_ranking_match,
            "kendall_tau_b": float(tau) if tau is not None else None,
            "spearman_rho": float(rho) if rho is not None else None,
        }
        rows.append(row)

        if worked_example is None and not exact_ranking_match and not identical_fused_scores:
            worked_example = {
                "dataset": dataset,
                "query_id": qid,
                "candidate_pool": pool,
                "prior_score_map": prior_score_map,
                "rrf_fused_score_map": rrf_score_map,
                "prior_ranking": prior_ranking,
                "rrf_ranking": rrf_ranking,
                "order_modulo_ties_agrees": order_modulo_ties_agrees,
                "explanation": (
                    "order_modulo_ties_agrees=False means the two methods' underlying fused "
                    "scores induce a genuinely different order for at least one pair of "
                    "non-tied documents -- i.e. the divergence is NOT explainable by "
                    "tie-breaking rule alone. This happens because Prior ranks each ranker's "
                    "candidate documents only among themselves (rank 1..|candidates scored by "
                    "that ranker|), while the standalone RRF baseline ranks them among that "
                    "ranker's ENTIRE stored list before restricting to the pool -- a candidate "
                    "document can have a very different reciprocal-rank contribution under the "
                    "two schemes even when its raw ranker score is identical."
                    if not order_modulo_ties_agrees
                    else "the two methods agree on the pairwise order of every non-tied pair; "
                    "any ranking difference here is attributable to tie-breaking alone."
                ),
            }

    return {"rows": rows, "worked_example": worked_example}


def main() -> int:
    t0 = time.time()
    all_rows: list[dict[str, Any]] = []
    worked_examples: dict[str, Any] = {}
    for dataset in t4.DATASETS:
        print(f"[prior-vs-rrf] {dataset}", flush=True)
        result = audit_dataset(dataset)
        all_rows.extend(result["rows"])
        if result["worked_example"]:
            worked_examples[dataset] = result["worked_example"]

    t4.write_csv(t4.TABLES_DIR / "prior_vs_rrf_per_query.csv", all_rows)
    t4.write_json(t4.OUTPUTS_DIR / "prior_vs_rrf_worked_examples.json", worked_examples)

    summary_rows = []
    for dataset in t4.DATASETS:
        rows = [r for r in all_rows if r["dataset"] == dataset]
        n = len(rows)
        if n == 0:
            continue
        summary_rows.append(
            {
                "dataset": dataset,
                "n_queries": n,
                "fraction_identical_candidate_sets": sum(
                    r["identical_candidate_sets"] for r in rows
                )
                / n,
                "fraction_identical_fused_scores": sum(r["identical_fused_scores"] for r in rows)
                / n,
                "mean_n_rrf_tie_groups": sum(r["n_rrf_tie_groups"] for r in rows) / n,
                "mean_largest_rrf_tie_group_size": sum(
                    r["largest_rrf_tie_group_size"] for r in rows
                )
                / n,
                "fraction_order_modulo_ties_agrees": sum(
                    r["order_modulo_ties_agrees"] for r in rows
                )
                / n,
                "fraction_ranking_differs_only_by_tiebreak": sum(
                    r["order_modulo_ties_agrees"] and not r["exact_ranking_match"] for r in rows
                )
                / n,
                "fraction_underlying_scores_differ": sum(
                    not r["order_modulo_ties_agrees"] for r in rows
                )
                / n,
                "fraction_exact_ranking_match": sum(r["exact_ranking_match"] for r in rows) / n,
                "mean_kendall_tau_b": sum(
                    r["kendall_tau_b"] for r in rows if r["kendall_tau_b"] is not None
                )
                / max(1, sum(1 for r in rows if r["kendall_tau_b"] is not None)),
                "mean_spearman_rho": sum(
                    r["spearman_rho"] for r in rows if r["spearman_rho"] is not None
                )
                / max(1, sum(1 for r in rows if r["spearman_rho"] is not None)),
                "mean_n_unscored_by_any_ranker": sum(r["n_unscored_by_any_ranker"] for r in rows)
                / n,
            }
        )
    t4.write_csv(t4.TABLES_DIR / "prior_vs_rrf_summary.csv", summary_rows)

    total_n = len(all_rows)
    total_exact_match = sum(r["exact_ranking_match"] for r in all_rows)
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "regime": REGIME,
        "pool": "canonical",
        "total_queries": total_n,
        "total_exact_ranking_matches": total_exact_match,
        "overall_exact_match_fraction": total_exact_match / total_n if total_n else None,
        "manuscript_claim_under_test": (
            "main.tex lines ~887-891,1095-1108 state Prior and RRF 'differ only in "
            "tie-breaking' and report 216/6156 exact matches across the full study "
            "(342 queries x 3 regimes x 6 protocols). This script computes the analogous "
            "figure restricted to canonical-pool ms1 only (342 queries, 1 regime, 1 protocol) "
            "and additionally decomposes mismatches into tie-break-only vs genuine "
            "score-order differences."
        ),
        "elapsed_seconds": time.time() - t0,
    }
    t4.write_json(t4.MANIFESTS_DIR / "prior_vs_rrf_audit_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
