#!/usr/bin/env python
"""
run_regularized_aggregation_pilot.py
=====================================
CLI driver for the regularized partial-information rank aggregation pilot
(the "safe integration of sparse pairwise LLM judgments" pivot).

Uses the same frozen, pre-existing, exhaustive real OpenAI (gpt-4o-mini)
pairwise SciDocs judgments as the prior offline active-acquisition pilot
(``outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl``). No live
provider or API calls; no new judgments collected; qrels are used only for
post-hoc evaluation, never for aggregation decisions.

Two modes:

``fragility``
    Phase 1 mechanism analysis. Replays the *existing* sparse
    Copeland-over-BM25 extraction rule under random-order acquisition,
    checkpointing at *every single revealed edge* (not just the coarse
    budget grid) for the first 21 edges (0-20% budget), and quantifies how
    often one edge changes top-10 membership, ejects a relevant document, or
    both -- and how often an ejected document later returns once evidence is
    exhaustive.

``evaluate``
    Phase 3/6 comparison. Fixes acquisition order to random (the strongest
    policy from the prior pilot) and compares five *aggregation* rules that
    all consume the same revealed-edge sequence at each budget checkpoint:
    initial BM25, existing sparse Copeland, pure (unregularized) Bradley-
    Terry, a fixed BM25/Copeland blend, and the proposed coverage-adaptive
    prior-regularized Bradley-Terry aggregator -- plus the exhaustive
    reference. Uses a frozen 15/35 dev/test query split (Phase 4) and a
    frozen severe-harm threshold (Phase 7) to avoid any test-set snooping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.active_acquisition.evaluate import (  # noqa: E402
    auc_over_budget,
    evaluate_ranking,
    topk_overlap,
)
from consistency_ranker.active_acquisition.oracle import (  # noqa: E402
    QueryOracle,
    load_scidocs_pairwise_oracle,
)
from consistency_ranker.active_acquisition.regularized_aggregation import (  # noqa: E402
    SCHEDULES,
    fixed_blend_ranking,
    pure_bt_ranking,
    regularized_bt_ranking,
)
from consistency_ranker.active_acquisition.scoring import (  # noqa: E402
    normalize_bm25,
    rank_from_copeland,
)
from consistency_ranker.active_acquisition.simulate import (  # noqa: E402
    _static_order,
    reference_rankings,
)
from consistency_ranker.active_acquisition.stats import paired_comparison  # noqa: E402
from consistency_ranker.evaluation import ndcg_at_k  # noqa: E402
from consistency_ranker.statistical_inference import (  # noqa: E402
    bootstrap_mean_interval,
    holm_adjust,
    proportion_interval,
)

STATISTICAL_ANALYSIS_SCHEMA_VERSION = 2
# v2: per-method severe-harm rates (result["severe_harm"][budget][method]) now
# carry a Wilson binomial-proportion CI, added where none previously existed.
# The paired severe_harm_rate_reduction_vs_sparse_copeland statistic is a
# mean of a *paired difference* of two correlated binary indicators, not a
# single-group proportion -- proportion_interval() does not apply to it, so
# it intentionally remains bootstrap-based, as before.

SEVERE_HARM_THRESHOLD = -0.05  # frozen before test-set inspection, Phase 7


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _all_pairs(candidates: tuple[str, ...]) -> list[frozenset]:
    return [
        frozenset((candidates[a], candidates[b]))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
    ]


def _random_order_walk(
    oe: QueryOracle, seed: int, max_step: int
) -> list[tuple[int, dict[str, float], list[tuple[str, str]]]]:
    """Replay the *existing* random-order acquisition exactly as
    ``simulate.simulate_trajectory`` does it for ``algorithm="random"``
    (identical RNG consumption pattern -- ``pick_next_pair`` for "random"
    never touches ``ctx``), but checkpoint after *every* revealed edge and
    also return the running Copeland tally and the revealed-pairs list so
    far, which the coarse-grained pilot runner does not expose.

    Returns a list of ``(step, copeland_tally_copy, revealed_so_far_copy)``.
    """
    candidates = oe.candidates
    all_pairs = _all_pairs(candidates)
    rng = random.Random(seed)
    remaining = list(all_pairs)
    copeland = {d: 0.0 for d in candidates}
    revealed: list[tuple[str, str]] = []
    out = []
    for step in range(1, min(max_step, len(all_pairs)) + 1):
        pair = remaining[rng.randrange(len(remaining))]
        i, j = sorted(pair)
        winner, loser = oe.reveal(i, j)
        copeland[winner] += 1.0
        copeland[loser] -= 1.0
        revealed.append((winner, loser))
        remaining.remove(pair)
        out.append((step, dict(copeland), list(revealed)))
    return out


# ---------------------------------------------------------------------------
# Mode: fragility (Phase 1)
# ---------------------------------------------------------------------------


def run_fragility_analysis(output_dir: Path, max_step: int = 21, seed: int = 42) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    oracles = load_scidocs_pairwise_oracle()
    query_ids = sorted(oracles)

    per_step_rows: list[dict] = []
    ejection_examples: list[dict] = []

    for qid in query_ids:
        oe = oracles[qid]
        candidates = oe.candidates
        bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
        initial_ranking, exhaustive_ranking = reference_rankings(oe, seed=seed)
        exhaustive_top10 = set(exhaustive_ranking[:10])
        relevance = oe.relevance

        prev_topk = set(initial_ranking[:10])
        prev_ndcg = ndcg_at_k(initial_ranking, relevance, k=10)

        walk = _random_order_walk(oe, seed=seed, max_step=max_step)
        for step, copeland, revealed in walk:
            ranking = rank_from_copeland(candidates, copeland, bm25_norm)
            topk = set(ranking[:10])
            ndcg = ndcg_at_k(ranking, relevance, k=10)
            n_nonzero = sum(1 for d in candidates if copeland[d] != 0.0)

            entered = topk - prev_topk
            left = prev_topk - topk
            ejected_relevant = [d for d in left if relevance.get(d, 0) > 0]
            ndcg_delta = ndcg - prev_ndcg

            row = dict(
                query_id=qid,
                step=step,
                n_revealed_edges=step,
                n_docs_nonzero_copeland=n_nonzero,
                topk_changed_docs=len(entered) + len(left),
                topk_docs_entered=len(entered),
                topk_docs_left=len(left),
                n_relevant_docs_ejected_this_step=len(ejected_relevant),
                ndcg=ndcg,
                ndcg_delta_this_step=ndcg_delta,
                topk_overlap_vs_initial_bm25=topk_overlap(ranking, initial_ranking, 10),
                topk_overlap_vs_exhaustive=topk_overlap(ranking, exhaustive_ranking, 10),
            )
            per_step_rows.append(row)

            for d in ejected_relevant:
                returns_in_exhaustive = d in exhaustive_top10
                example = dict(
                    query_id=qid,
                    step=step,
                    ejected_doc=d,
                    ejected_doc_relevance=relevance[d],
                    ejected_doc_bm25_rank=initial_ranking.index(d) + 1,
                    winner_of_triggering_edge=revealed[-1][0],
                    loser_of_triggering_edge=revealed[-1][1],
                    ndcg_before=prev_ndcg,
                    ndcg_after=ndcg,
                    returns_in_exhaustive_top10=returns_in_exhaustive,
                )
                ejection_examples.append(example)

            prev_topk = topk
            prev_ndcg = ndcg

    _write_csv(output_dir / "fragility_per_step.csv", per_step_rows)
    _write_csv(output_dir / "fragility_ejection_events.csv", ejection_examples)

    # Aggregate summary.
    n_total_steps = len(per_step_rows)
    n_churn_steps = sum(1 for r in per_step_rows if r["topk_changed_docs"] > 0)
    n_ejection_steps = sum(1 for r in per_step_rows if r["n_relevant_docs_ejected_this_step"] > 0)
    step1_rows = [r for r in per_step_rows if r["step"] == 1]
    n_step1_churn = sum(1 for r in step1_rows if r["topk_changed_docs"] > 0)
    n_step1_ejection = sum(1 for r in step1_rows if r["n_relevant_docs_ejected_this_step"] > 0)
    n_returns = sum(1 for e in ejection_examples if e["returns_in_exhaustive_top10"])

    within_budget = [r for r in per_step_rows if r["step"] <= 11]  # <=10% budget
    ndcg_deltas_all = [r["ndcg_delta_this_step"] for r in within_budget]
    ndcg_deltas_churn = [
        r["ndcg_delta_this_step"] for r in within_budget if r["topk_changed_docs"] > 0
    ]
    ndcg_deltas_nochurn = [
        r["ndcg_delta_this_step"] for r in within_budget if r["topk_changed_docs"] == 0
    ]

    summary = dict(
        n_queries=len(query_ids),
        max_step_analyzed=max_step,
        n_query_step_observations=n_total_steps,
        n_steps_with_topk_churn=n_churn_steps,
        frac_steps_with_topk_churn=n_churn_steps / n_total_steps,
        n_steps_ejecting_a_relevant_doc=n_ejection_steps,
        frac_steps_ejecting_a_relevant_doc=n_ejection_steps / n_total_steps,
        n_queries_step1=len(step1_rows),
        n_step1_topk_churn=n_step1_churn,
        frac_step1_topk_churn=n_step1_churn / len(step1_rows),
        n_step1_ejects_relevant_doc=n_step1_ejection,
        frac_step1_ejects_relevant_doc=n_step1_ejection / len(step1_rows),
        n_ejection_events_le_10pct_budget=len(
            [e for e in ejection_examples if e["step"] <= 11]
        ),
        n_ejection_events_total_le_20pct=len(ejection_examples),
        n_ejected_docs_that_return_in_exhaustive=n_returns,
        frac_ejected_docs_that_return_in_exhaustive=(
            n_returns / len(ejection_examples) if ejection_examples else None
        ),
        mean_abs_ndcg_delta_le10pct_budget_churn_steps=(
            sum(abs(x) for x in ndcg_deltas_churn) / len(ndcg_deltas_churn)
            if ndcg_deltas_churn
            else None
        ),
        mean_abs_ndcg_delta_le10pct_budget_nochurn_steps=(
            sum(abs(x) for x in ndcg_deltas_nochurn) / len(ndcg_deltas_nochurn)
            if ndcg_deltas_nochurn
            else None
        ),
        mean_ndcg_delta_le10pct_budget_all_steps=(
            sum(ndcg_deltas_all) / len(ndcg_deltas_all) if ndcg_deltas_all else None
        ),
    )
    with (output_dir / "fragility_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"Wrote fragility outputs to {output_dir}")


# ---------------------------------------------------------------------------
# Mode: evaluate (Phase 3/4/6/7/8)
# ---------------------------------------------------------------------------

METHODS = (
    "initial_bm25",
    "sparse_copeland",
    "pure_bt_no_prior",
    "fixed_blend",
    "regularized_bt",
    "exhaustive",
)

BASELINE_METHODS_FOR_STRONGEST = ("sparse_copeland", "pure_bt_no_prior", "fixed_blend")


def _dev_test_split(query_ids: list[str], n_dev: int, seed: int) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    shuffled = sorted(query_ids)
    rng.shuffle(shuffled)
    dev = sorted(shuffled[:n_dev])
    test = sorted(shuffled[n_dev:])
    return dev, test


def _rank_for_method(
    method: str,
    candidates: tuple[str, ...],
    revealed: list[tuple[str, str]],
    bm25_norm: dict[str, float],
    initial_ranking: list[str],
    exhaustive_ranking: list[str],
    n_total_pairs: int,
    schedule_name: str,
) -> list[str]:
    if method == "initial_bm25":
        return initial_ranking
    if method == "exhaustive":
        return exhaustive_ranking
    if method == "sparse_copeland":
        copeland = {d: 0.0 for d in candidates}
        for w, loser in revealed:
            copeland[w] += 1.0
            copeland[loser] -= 1.0
        return rank_from_copeland(candidates, copeland, bm25_norm)
    if method == "pure_bt_no_prior":
        return pure_bt_ranking(candidates, revealed, bm25_norm)
    if method == "fixed_blend":
        return fixed_blend_ranking(candidates, revealed, bm25_norm)
    if method == "regularized_bt":
        return regularized_bt_ranking(
            candidates, revealed, bm25_norm, n_total_pairs, SCHEDULES[schedule_name]
        )
    raise ValueError(f"Unknown method {method!r}")


def _walk_for_order(
    oe: QueryOracle, order: str, seed: int
) -> list[tuple[int, list[tuple[str, str]]]]:
    """Return [(step, revealed_so_far)] for every step 1..n_pairs, for the
    requested acquisition-order protocol ("random" primary, "static_adjacent"
    secondary robustness check)."""
    candidates = oe.candidates
    all_pairs = _all_pairs(candidates)
    if order == "random":
        pair_sequence = list(all_pairs)
        random.Random(seed).shuffle(pair_sequence)
    elif order == "static_adjacent":
        pair_sequence = _static_order(candidates, oe.bm25_scores)
    else:
        raise ValueError(order)
    revealed: list[tuple[str, str]] = []
    out = []
    for step, pair in enumerate(pair_sequence, start=1):
        i, j = sorted(pair)
        winner, loser = oe.reveal(i, j)
        revealed.append((winner, loser))
        out.append((step, list(revealed)))
    return out


def run_evaluation(
    output_dir: Path,
    config: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = _REPO_ROOT / config["judgments_path"]
    input_hash = _sha256_file(judgments_path)
    oracles = load_scidocs_pairwise_oracle(judgments_path)
    query_ids = sorted(oracles)
    assert len(query_ids) == config["n_queries_expected"]

    n_pairs = (
        config["candidate_pool_size_expected"] * (config["candidate_pool_size_expected"] - 1) // 2
    )
    k = config["primary_cutoff_k"]
    seed = config["seed"]

    budgets = sorted({round(f * n_pairs) for f in config["budget_fractions"]} | {1})
    dev_ids, test_ids = _dev_test_split(
        query_ids, config["n_dev_queries"], config["dev_split_seed"]
    )

    schedule_name = config["frozen_schedule"]

    all_rows: list[dict] = []
    runtime_by_method: dict[str, list[float]] = defaultdict(list)

    for order in ("random", "static_adjacent"):
        for qid in query_ids:
            oe = oracles[qid]
            candidates = oe.candidates
            bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
            initial_ranking, exhaustive_ranking = reference_rankings(oe, seed=seed)
            relevance = oe.relevance
            walk = dict(_walk_for_order(oe, order, seed))

            for budget in budgets:
                if budget == 0:
                    revealed: list[tuple[str, str]] = []
                elif budget >= n_pairs:
                    revealed = walk[n_pairs]
                else:
                    revealed = walk[budget]

                for method in METHODS:
                    t0 = time.perf_counter()
                    ranking = _rank_for_method(
                        method,
                        candidates,
                        revealed,
                        bm25_norm,
                        initial_ranking,
                        exhaustive_ranking,
                        n_pairs,
                        schedule_name,
                    )
                    dt = time.perf_counter() - t0
                    runtime_by_method[method].append(dt)
                    ndcg, overlap_exh, tau_exh = evaluate_ranking(
                        ranking, relevance, exhaustive_ranking, k=k
                    )
                    overlap_bm25 = topk_overlap(ranking, initial_ranking, k)
                    all_rows.append(
                        dict(
                            order=order,
                            query_id=qid,
                            split="dev" if qid in dev_ids else "test",
                            method=method,
                            budget=budget,
                            budget_frac=budget / n_pairs,
                            ndcg=ndcg,
                            delta_vs_bm25=ndcg
                            - evaluate_ranking(
                                initial_ranking, relevance, exhaustive_ranking, k=k
                            )[0],
                            topk_overlap_vs_exhaustive=overlap_exh,
                            topk_overlap_vs_bm25=overlap_bm25,
                            kendall_tau_vs_exhaustive=tau_exh,
                        )
                    )

    _write_csv(output_dir / "aggregation_trajectories.csv", all_rows)

    # AUC per (order, method, query, split)
    auc_rows = []
    by_key: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
    for r in all_rows:
        by_key[(r["order"], r["method"], r["query_id"])].append((r["budget_frac"], r["ndcg"]))
    for (order, method, qid), pts in by_key.items():
        pts.sort()
        fracs = [p[0] for p in pts]
        ndcgs = [p[1] for p in pts]
        auc = auc_over_budget(fracs, ndcgs)
        split = "dev" if qid in dev_ids else "test"
        auc_rows.append(dict(order=order, method=method, query_id=qid, split=split, auc_ndcg=auc))
    _write_csv(output_dir / "aggregation_auc.csv", auc_rows)

    runtime_summary = {
        m: dict(
            n=len(v),
            mean_s=sum(v) / len(v) if v else None,
            max_s=max(v) if v else None,
        )
        for m, v in runtime_by_method.items()
    }

    manifest = dict(
        protocol=config["protocol"],
        input_judgments_path=config["judgments_path"],
        input_judgments_sha256=input_hash,
        n_queries=len(query_ids),
        n_pairs_per_query=n_pairs,
        budgets=budgets,
        dev_query_ids=dev_ids,
        test_query_ids=test_ids,
        frozen_schedule=schedule_name,
        severe_harm_threshold=SEVERE_HARM_THRESHOLD,
        seed=seed,
    )
    with (output_dir / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    with (output_dir / "runtime_summary.json").open("w") as f:
        json.dump(runtime_summary, f, indent=2)

    stats_result = _statistical_analysis(all_rows, auc_rows, test_ids, budgets, n_pairs)
    with (output_dir / "statistical_analysis.json").open("w") as f:
        json.dump(stats_result, f, indent=2, default=str)

    print(f"Wrote evaluation outputs to {output_dir}")


def _metric_map(
    rows: list[dict], order: str, method: str, budget: int, ids: set[str], key: str
) -> dict[str, float]:
    return {
        r["query_id"]: r[key]
        for r in rows
        if r["order"] == order
        and r["method"] == method
        and r["budget"] == budget
        and r["query_id"] in ids
    }


def _statistical_analysis(
    rows: list[dict], auc_rows: list[dict], test_ids: list[str], budgets: list[int], n_pairs: int
) -> dict:
    test_id_set = set(test_ids)
    order = "random"
    b05 = round(0.05 * n_pairs)
    b10 = round(0.10 * n_pairs)
    b20 = round(0.20 * n_pairs)

    result: dict = {
        "schema_version": STATISTICAL_ANALYSIS_SCHEMA_VERSION,
        "primary_comparisons": [],
        "severe_harm": {},
        "auc_comparisons": [],
    }
    pvals = []
    records = []

    def add_comparison(label, a_map, b_map):
        common = sorted(set(a_map) & set(b_map))
        deltas = [a_map[q] - b_map[q] for q in common]
        comp = paired_comparison(label, deltas)
        records.append((label, comp))
        pvals.append(comp.pvalue)

    reg_05 = _metric_map(rows, order, "regularized_bt", b05, test_id_set, "ndcg")
    reg_10 = _metric_map(rows, order, "regularized_bt", b10, test_id_set, "ndcg")
    reg_20 = _metric_map(rows, order, "regularized_bt", b20, test_id_set, "ndcg")
    sc_05 = _metric_map(rows, order, "sparse_copeland", b05, test_id_set, "ndcg")
    sc_10 = _metric_map(rows, order, "sparse_copeland", b10, test_id_set, "ndcg")
    bm25_10 = _metric_map(rows, order, "initial_bm25", b10, test_id_set, "ndcg")
    bm25_20 = _metric_map(rows, order, "initial_bm25", b20, test_id_set, "ndcg")

    add_comparison("proposed_vs_sparse_copeland_5pct", reg_05, sc_05)
    add_comparison("proposed_vs_sparse_copeland_10pct", reg_10, sc_10)
    add_comparison("proposed_vs_bm25_10pct", reg_10, bm25_10)
    add_comparison("proposed_vs_bm25_20pct", reg_20, bm25_20)

    holm_ps = holm_adjust(pvals + [None])  # placeholder slot for AUC comparison appended below
    # AUC: proposed vs strongest non-oracle baseline, selected on the DEV set only.
    dev_ids_all = set(r["query_id"] for r in auc_rows) - test_id_set
    strongest = None
    best_mean = float("-inf")
    strongest_means = {}
    for m in BASELINE_METHODS_FOR_STRONGEST:
        vals = [
            r["auc_ndcg"]
            for r in auc_rows
            if r["order"] == order and r["method"] == m and r["query_id"] in dev_ids_all
        ]
        mean_v = sum(vals) / len(vals) if vals else float("-inf")
        strongest_means[m] = mean_v
        if mean_v > best_mean:
            best_mean, strongest = mean_v, m
    result["strongest_baseline_selected_on_dev"] = strongest
    result["dev_auc_means_by_baseline"] = strongest_means

    reg_auc = {
        r["query_id"]: r["auc_ndcg"]
        for r in auc_rows
        if r["order"] == order
        and r["method"] == "regularized_bt"
        and r["query_id"] in test_id_set
    }
    base_auc = {
        r["query_id"]: r["auc_ndcg"]
        for r in auc_rows
        if r["order"] == order and r["method"] == strongest and r["query_id"] in test_id_set
    }
    common = sorted(set(reg_auc) & set(base_auc))
    auc_deltas = [reg_auc[q] - base_auc[q] for q in common]
    auc_comp = paired_comparison(f"auc_proposed_vs_{strongest}", auc_deltas)
    records.append((f"auc_proposed_vs_{strongest}", auc_comp))
    pvals.append(auc_comp.pvalue)

    holm_ps = holm_adjust(pvals)
    for (label, comp), holm_p in zip(records, holm_ps):
        result["primary_comparisons"].append(
            dict(
                label=label,
                n=comp.n,
                mean_delta=comp.mean_delta,
                cohen_d=comp.cohen_d,
                ci95_lower=comp.ci_lower,
                ci95_upper=comp.ci_upper,
                sign_flip_pvalue=comp.pvalue,
                holm_pvalue=holm_p,
                wins=comp.wins,
                ties=comp.ties,
                losses=comp.losses,
            )
        )

    # Severe-harm tail: per-query delta vs BM25 <= -0.05, at 5%/10%/20%, test set.
    for budget, label in ((b05, "5pct"), (b10, "10pct"), (b20, "20pct")):
        harm = {}
        for method in ("sparse_copeland", "regularized_bt", "pure_bt_no_prior", "fixed_blend"):
            deltas = list(
                _metric_map(rows, order, method, budget, test_id_set, "delta_vs_bm25").values()
            )
            n_severe = sum(1 for d in deltas if d <= SEVERE_HARM_THRESHOLD)
            worst = min(deltas) if deltas else None
            p05 = sorted(deltas)[max(0, int(0.05 * len(deltas)) - 1)] if deltas else None
            severe_ci = (
                proportion_interval(n_severe, len(deltas)) if deltas else proportion_interval(0, 0)
            )
            harm[method] = dict(
                n=len(deltas),
                n_severe_harm=n_severe,
                frac_severe_harm=n_severe / len(deltas) if deltas else None,
                frac_severe_harm_ci_method=severe_ci.method,
                frac_severe_harm_ci95_lower=severe_ci.lower,
                frac_severe_harm_ci95_upper=severe_ci.upper,
                worst_query_delta=worst,
                p05_delta=p05,
            )
        result["severe_harm"][label] = harm

        # Paired bootstrap CI for the severe-harm-rate reduction (regularized_bt
        # vs sparse_copeland), over the 35 test queries (Phase 8 requirement).
        reg_map = _metric_map(rows, order, "regularized_bt", budget, test_id_set, "delta_vs_bm25")
        sc_map = _metric_map(rows, order, "sparse_copeland", budget, test_id_set, "delta_vs_bm25")
        common_q = sorted(set(reg_map) & set(sc_map))
        paired_indicator_deltas = [
            (1.0 if sc_map[q] <= SEVERE_HARM_THRESHOLD else 0.0)
            - (1.0 if reg_map[q] <= SEVERE_HARM_THRESHOLD else 0.0)
            for q in common_q
        ]
        ci = bootstrap_mean_interval(paired_indicator_deltas, reps=10_000, seed=13)
        result["severe_harm"][label]["severe_harm_rate_reduction_vs_sparse_copeland"] = dict(
            n=len(common_q),
            mean_reduction=sum(paired_indicator_deltas) / len(paired_indicator_deltas),
            ci95_lower=ci.lower,
            ci95_upper=ci.upper,
        )

    result["severe_harm_threshold"] = SEVERE_HARM_THRESHOLD
    return result


def _write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fragility", "evaluate"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=_REPO_ROOT / "configs/regularized_aggregation_pilot_v1.json",
    )
    args = parser.parse_args()

    if args.mode == "fragility":
        run_fragility_analysis(args.output_dir)
    else:
        with args.config.open() as f:
            config = json.load(f)
        run_evaluation(args.output_dir, config)


if __name__ == "__main__":
    main()
