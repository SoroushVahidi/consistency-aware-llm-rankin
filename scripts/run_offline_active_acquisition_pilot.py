#!/usr/bin/env python
"""
run_offline_active_acquisition_pilot.py
========================================
CLI driver for the offline active-acquisition pilot (consistency-aware active
preference acquisition for budgeted reranking).

Uses the pre-existing, exhaustive real OpenAI pairwise SciDocs judgments
(``outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl``) as an
offline oracle. No live provider or API calls; no new judgments collected;
qrels are used only for post-hoc evaluation, never for acquisition decisions.

Usage
-----
::

    python scripts/run_offline_active_acquisition_pilot.py \\
        --config configs/offline_active_acquisition_pilot_v1.json \\
        --output-dir reports/offline_active_acquisition_pilot_<timestamp>

Resumable: per-query raw results are appended to ``raw_trajectories.jsonl``;
re-running with the same ``--output-dir`` skips queries already present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.active_acquisition.evaluate import (  # noqa: E402
    auc_over_budget,
    budget_to_fraction_of_improvement,
    evaluate_ranking,
    topk_stabilization_budget,
)
from consistency_ranker.active_acquisition.oracle import load_scidocs_pairwise_oracle  # noqa: E402
from consistency_ranker.active_acquisition.simulate import (  # noqa: E402
    reference_rankings,
    simulate_trajectory,
)
from consistency_ranker.active_acquisition.stats import paired_comparison  # noqa: E402
from consistency_ranker.active_acquisition.strategies import (  # noqa: E402
    ALGORITHMS,
    PHASE7_ABLATIONS,
    REQUIRED_PHASE3_STRATEGIES,
    STRATEGY_TO_ALGORITHM,
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _budgets_from_fractions(fractions: list[float], n_pairs: int) -> list[int]:
    return sorted({round(f * n_pairs) for f in fractions})


def run_pilot(config: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = _REPO_ROOT / config["judgments_path"]
    input_hash = _sha256_file(judgments_path)

    oracles = load_scidocs_pairwise_oracle(judgments_path)
    if len(oracles) != config["n_queries_expected"]:
        raise ValueError(f"Expected {config['n_queries_expected']} queries, found {len(oracles)}")
    for qid, oe in oracles.items():
        if len(oe.candidates) != config["candidate_pool_size_expected"]:
            raise ValueError(
                f"query {qid}: expected pool size "
                f"{config['candidate_pool_size_expected']}, found {len(oe.candidates)}"
            )

    k_primary = config["primary_cutoff_k"]
    k_secondary = config["secondary_cutoff_k_for_continuity"]
    seed = config["seed"]

    raw_path = output_dir / "raw_trajectories.jsonl"
    done_queries: set[str] = set()
    if raw_path.exists():
        with raw_path.open() as f:
            for line in f:
                if line.strip():
                    done_queries.add(json.loads(line)["query_id"])
        print(f"[resume] {len(done_queries)} queries already computed, skipping them")

    n_pairs = (
        config["candidate_pool_size_expected"] * (config["candidate_pool_size_expected"] - 1) // 2
    )
    budgets = _budgets_from_fractions(config["budget_fractions"], n_pairs)
    interior_budgets = [b for b in budgets if 0 < b < n_pairs]

    query_ids = sorted(oracles)
    t_start = time.time()
    with raw_path.open("a") as out:
        for qi, qid in enumerate(query_ids):
            if qid in done_queries:
                continue
            oe = oracles[qid]
            initial_ranking, exhaustive_ranking = reference_rankings(oe, seed=seed)
            record: dict = {
                "query_id": qid,
                "n_candidates": len(oe.candidates),
                "initial_ranking": initial_ranking,
                "exhaustive_ranking": exhaustive_ranking,
                "relevance": oe.relevance,
                "algorithms": {},
            }
            for algo in ALGORITHMS:
                cps = simulate_trajectory(oe, algo, interior_budgets, k_primary, seed)
                record["algorithms"][algo] = [
                    {
                        "budget": c.budget,
                        "ranking": c.ranking,
                        "decision_runtime_s": c.decision_runtime_s,
                    }
                    for c in cps
                ]
            out.write(json.dumps(record) + "\n")
            out.flush()
            if (qi + 1) % 10 == 0 or qi + 1 == len(query_ids):
                print(
                    f"[{qi + 1}/{len(query_ids)}] {qid} done ({time.time() - t_start:.1f}s elapsed)"
                )

    _postprocess(config, output_dir, raw_path, k_primary, k_secondary, n_pairs, input_hash)


def _postprocess(
    config: dict,
    output_dir: Path,
    raw_path: Path,
    k_primary: int,
    k_secondary: int,
    n_pairs: int,
    input_hash: str,
) -> None:
    rows: list[dict] = []
    per_query_curves: dict[tuple[str, str], dict[int, dict]] = defaultdict(dict)

    all_labels = (
        list(REQUIRED_PHASE3_STRATEGIES) + ["exhaustive", "initial"] + list(PHASE7_ABLATIONS)
    )

    with raw_path.open() as f:
        for line in f:
            rec = json.loads(line)
            qid = rec["query_id"]
            relevance = rec["relevance"]
            initial_ranking = rec["initial_ranking"]
            exhaustive_ranking = rec["exhaustive_ranking"]

            ndcg_init, overlap_init, tau_init = evaluate_ranking(
                initial_ranking, relevance, exhaustive_ranking, k=k_primary
            )
            ndcg_init15, _, _ = evaluate_ranking(
                initial_ranking, relevance, exhaustive_ranking, k=k_secondary
            )
            ndcg_exh, overlap_exh, tau_exh = evaluate_ranking(
                exhaustive_ranking, relevance, exhaustive_ranking, k=k_primary
            )
            ndcg_exh15, _, _ = evaluate_ranking(
                exhaustive_ranking, relevance, exhaustive_ranking, k=k_secondary
            )

            for label in all_labels:
                if label == "initial":
                    rows.append(
                        dict(
                            query_id=qid,
                            strategy=label,
                            budget=0,
                            budget_frac=0.0,
                            ndcg=ndcg_init,
                            ndcg15=ndcg_init15,
                            topk_overlap=overlap_init,
                            kendall_tau=tau_init,
                            decision_runtime_s=0.0,
                        )
                    )
                    per_query_curves[(qid, label)][0] = {
                        "ranking": initial_ranking,
                        "ndcg": ndcg_init,
                    }
                    continue
                if label == "exhaustive":
                    rows.append(
                        dict(
                            query_id=qid,
                            strategy=label,
                            budget=n_pairs,
                            budget_frac=1.0,
                            ndcg=ndcg_exh,
                            ndcg15=ndcg_exh15,
                            topk_overlap=overlap_exh,
                            kendall_tau=tau_exh,
                            decision_runtime_s=0.0,
                        )
                    )
                    per_query_curves[(qid, label)][n_pairs] = {
                        "ranking": exhaustive_ranking,
                        "ndcg": ndcg_exh,
                    }
                    continue

                algo = STRATEGY_TO_ALGORITHM[label]
                checkpoints = rec["algorithms"][algo]
                # every labeled strategy's curve includes the shared 0%/100% endpoints
                rows.append(
                    dict(
                        query_id=qid,
                        strategy=label,
                        budget=0,
                        budget_frac=0.0,
                        ndcg=ndcg_init,
                        ndcg15=ndcg_init15,
                        topk_overlap=overlap_init,
                        kendall_tau=tau_init,
                        decision_runtime_s=0.0,
                    )
                )
                per_query_curves[(qid, label)][0] = {"ranking": initial_ranking, "ndcg": ndcg_init}
                for cp in checkpoints:
                    ranking = cp["ranking"]
                    ndcg, overlap, tau = evaluate_ranking(
                        ranking, relevance, exhaustive_ranking, k=k_primary
                    )
                    ndcg15, _, _ = evaluate_ranking(
                        ranking, relevance, exhaustive_ranking, k=k_secondary
                    )
                    rows.append(
                        dict(
                            query_id=qid,
                            strategy=label,
                            budget=cp["budget"],
                            budget_frac=cp["budget"] / n_pairs,
                            ndcg=ndcg,
                            ndcg15=ndcg15,
                            topk_overlap=overlap,
                            kendall_tau=tau,
                            decision_runtime_s=cp["decision_runtime_s"],
                        )
                    )
                    per_query_curves[(qid, label)][cp["budget"]] = {
                        "ranking": ranking,
                        "ndcg": ndcg,
                    }
                rows.append(
                    dict(
                        query_id=qid,
                        strategy=label,
                        budget=n_pairs,
                        budget_frac=1.0,
                        ndcg=ndcg_exh,
                        ndcg15=ndcg_exh15,
                        topk_overlap=overlap_exh,
                        kendall_tau=tau_exh,
                        decision_runtime_s=0.0,
                    )
                )
                per_query_curves[(qid, label)][n_pairs] = {
                    "ranking": exhaustive_ranking,
                    "ndcg": ndcg_exh,
                }

    _write_csv(output_dir / "trajectories.csv", rows)

    # Per (query, strategy) aggregate metrics.
    # "initial" and "exhaustive" are single-point reference conditions, not
    # progressions — AUC / budget-to-X% / stabilization only apply to the
    # adaptive strategies that actually acquire a growing set of judgments.
    reference_only_labels = {"initial", "exhaustive"}
    agg_rows = []
    for (qid, label), by_budget in per_query_curves.items():
        if label in reference_only_labels:
            continue
        budgets_sorted = sorted(by_budget)
        ndcgs = [by_budget[b]["ndcg"] for b in budgets_sorted]
        rankings = [by_budget[b]["ranking"] for b in budgets_sorted]
        fracs = [b / n_pairs for b in budgets_sorted]
        ndcg_initial = by_budget[0]["ndcg"]
        ndcg_exhaustive = by_budget[n_pairs]["ndcg"]
        auc = auc_over_budget(fracs, ndcgs)
        b90 = budget_to_fraction_of_improvement(
            budgets_sorted, ndcgs, ndcg_initial, ndcg_exhaustive, fraction=0.90
        )
        b95 = budget_to_fraction_of_improvement(
            budgets_sorted, ndcgs, ndcg_initial, ndcg_exhaustive, fraction=0.95
        )
        stab = topk_stabilization_budget(budgets_sorted, rankings, k=10)
        agg_rows.append(
            dict(
                query_id=qid,
                strategy=label,
                auc_ndcg=auc,
                ndcg_initial=ndcg_initial,
                ndcg_exhaustive=ndcg_exhaustive,
                improves_over_initial=bool(ndcg_exhaustive > ndcg_initial + 1e-12),
                budget_to_90pct=b90,
                budget_to_95pct=b95,
                topk_stabilization_budget=stab,
            )
        )
    _write_csv(output_dir / "per_query_summary.csv", agg_rows)

    # Budget-curve summary (mean nDCG per strategy per budget).
    curve_means: dict[tuple[str, int], list[float]] = defaultdict(list)
    for r in rows:
        curve_means[(r["strategy"], r["budget"])].append(r["ndcg"])
    curve_summary = [
        dict(strategy=s, budget=b, budget_frac=b / n_pairs, n=len(v), mean_ndcg=sum(v) / len(v))
        for (s, b), v in sorted(curve_means.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    ]
    _write_csv(output_dir / "budget_curve_summary.csv", curve_summary)

    # Statistical analysis (Phase 6).
    stats_result = _statistical_analysis(config, rows, agg_rows, n_pairs)
    with (output_dir / "statistical_analysis.json").open("w") as f:
        json.dump(stats_result, f, indent=2, default=str)

    manifest = {
        "protocol": config["protocol"],
        "input_judgments_path": config["judgments_path"],
        "input_judgments_sha256": input_hash,
        "n_queries": len(set(r["query_id"] for r in rows)),
        "n_pairs_per_query": n_pairs,
        "budgets": sorted(set(r["budget"] for r in rows)),
        "seed": config["seed"],
    }
    with (output_dir / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote outputs to {output_dir}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _strategy_ndcg_by_query(rows: list[dict], strategy: str, budget: int) -> dict[str, float]:
    return {
        r["query_id"]: r["ndcg"]
        for r in rows
        if r["strategy"] == strategy and r["budget"] == budget
    }


def _statistical_analysis(
    config: dict, rows: list[dict], agg_rows: list[dict], n_pairs: int
) -> dict:
    budget_fracs_primary = config["pre_registered_primary_comparison"]["budgets_tested"]
    budgets_primary = [round(f * n_pairs) for f in budget_fracs_primary]
    baseline_candidates = [
        "random_unobserved",
        "static_adjacent",
        "uncertainty_only",
        "cycle_scc",
        "existing_uht",
    ]

    # Pre-registered rule: strongest baseline by mean nDCG@10 at the 20% checkpoint.
    b20 = budgets_primary[-1]
    means_at_b20 = {}
    for b in baseline_candidates:
        vals = list(_strategy_ndcg_by_query(rows, b, b20).values())
        means_at_b20[b] = sum(vals) / len(vals) if vals else float("-inf")
    strongest_baseline = max(means_at_b20, key=lambda k: means_at_b20[k])

    result: dict = {
        "strongest_baseline_selected": strongest_baseline,
        "mean_ndcg_at_20pct_by_baseline": means_at_b20,
        "primary_comparisons": [],
        "all_baseline_comparisons": [],
        "auc_comparisons": [],
    }

    all_pvals_for_holm = []
    comparison_records = []
    for budget in budgets_primary:
        proposed_map = _strategy_ndcg_by_query(rows, "proposed", budget)
        for baseline in baseline_candidates:
            baseline_map = _strategy_ndcg_by_query(rows, baseline, budget)
            common = sorted(set(proposed_map) & set(baseline_map))
            deltas = [proposed_map[q] - baseline_map[q] for q in common]
            label = f"proposed_vs_{baseline}_budget_{budget}"
            comp = paired_comparison(label, deltas)
            comparison_records.append((budget, baseline, comp))
            all_pvals_for_holm.append(comp.pvalue)

    from consistency_ranker.statistical_inference import holm_adjust

    holm_ps = holm_adjust(all_pvals_for_holm)
    for (budget, baseline, comp), holm_p in zip(comparison_records, holm_ps):
        row = {
            "budget": budget,
            "budget_frac": budget / n_pairs,
            "baseline": baseline,
            "n": comp.n,
            "mean_delta_ndcg": comp.mean_delta,
            "cohen_d": comp.cohen_d,
            "ci95_lower": comp.ci_lower,
            "ci95_upper": comp.ci_upper,
            "sign_flip_pvalue": comp.pvalue,
            "holm_pvalue": holm_p,
            "wins": comp.wins,
            "ties": comp.ties,
            "losses": comp.losses,
            "is_strongest_baseline": baseline == strongest_baseline,
        }
        result["all_baseline_comparisons"].append(row)
        if baseline == strongest_baseline:
            result["primary_comparisons"].append(row)

    # AUC comparisons: proposed vs each baseline (and vs strongest specifically).
    auc_by_strategy_query: dict[str, dict[str, float]] = defaultdict(dict)
    for r in agg_rows:
        auc_by_strategy_query[r["strategy"]][r["query_id"]] = r["auc_ndcg"]
    auc_pvals = []
    auc_records = []
    proposed_auc = auc_by_strategy_query["proposed"]
    for baseline in baseline_candidates:
        baseline_auc = auc_by_strategy_query[baseline]
        common = sorted(set(proposed_auc) & set(baseline_auc))
        deltas = [proposed_auc[q] - baseline_auc[q] for q in common]
        comp = paired_comparison(f"auc_proposed_vs_{baseline}", deltas)
        auc_records.append((baseline, comp))
        auc_pvals.append(comp.pvalue)
    auc_holm = holm_adjust(auc_pvals)
    for (baseline, comp), holm_p in zip(auc_records, auc_holm):
        result["auc_comparisons"].append(
            {
                "baseline": baseline,
                "n": comp.n,
                "mean_delta_auc": comp.mean_delta,
                "cohen_d": comp.cohen_d,
                "ci95_lower": comp.ci_lower,
                "ci95_upper": comp.ci_upper,
                "sign_flip_pvalue": comp.pvalue,
                "holm_pvalue": holm_p,
                "wins": comp.wins,
                "ties": comp.ties,
                "losses": comp.losses,
            }
        )

    # Ablation comparisons: does each added term help vs the previous ablation, at 10%/20%.
    ablation_chain = [
        ("ablation_impact_only", "ablation_impact_x_uncertainty"),
        ("ablation_impact_x_uncertainty", "ablation_full"),
        ("ablation_uncertainty_only", "ablation_impact_only"),
    ]
    result["ablation_comparisons"] = []
    for budget in budgets_primary:
        for a, b in ablation_chain:
            a_map = _strategy_ndcg_by_query(rows, a, budget)
            b_map = _strategy_ndcg_by_query(rows, b, budget)
            common = sorted(set(a_map) & set(b_map))
            deltas = [b_map[q] - a_map[q] for q in common]
            comp = paired_comparison(f"{b}_vs_{a}_budget_{budget}", deltas)
            result["ablation_comparisons"].append(
                {
                    "budget": budget,
                    "budget_frac": budget / n_pairs,
                    "from": a,
                    "to": b,
                    "mean_delta_ndcg": comp.mean_delta,
                    "cohen_d": comp.cohen_d,
                    "ci95_lower": comp.ci_lower,
                    "ci95_upper": comp.ci_upper,
                    "sign_flip_pvalue": comp.pvalue,
                    "wins": comp.wins,
                    "ties": comp.ties,
                    "losses": comp.losses,
                }
            )

    # Runtime summary.
    runtimes = [r["decision_runtime_s"] for r in rows if r["decision_runtime_s"] > 0]
    result["runtime_summary"] = {
        "n_decisions_timed": len(runtimes),
        "mean_decision_runtime_s": (sum(runtimes) / len(runtimes)) if runtimes else None,
        "max_decision_runtime_s": max(runtimes) if runtimes else None,
    }

    # Outcome-D check: does exhaustive improve over initial at all, in aggregate?
    n_improve = sum(
        1 for r in agg_rows if r["strategy"] == "proposed" and r["improves_over_initial"]
    )
    n_total = sum(1 for r in agg_rows if r["strategy"] == "proposed")
    mean_ndcg_initial = (
        sum(r["ndcg_initial"] for r in agg_rows if r["strategy"] == "proposed") / n_total
    )
    mean_ndcg_exhaustive = (
        sum(r["ndcg_exhaustive"] for r in agg_rows if r["strategy"] == "proposed") / n_total
    )
    result["exhaustive_vs_initial"] = {
        "n_queries_exhaustive_improves": n_improve,
        "n_queries_total": n_total,
        "mean_ndcg_initial": mean_ndcg_initial,
        "mean_ndcg_exhaustive": mean_ndcg_exhaustive,
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_REPO_ROOT / "configs/offline_active_acquisition_pilot_v1.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with args.config.open() as f:
        config = json.load(f)
    run_pilot(config, args.output_dir)


if __name__ == "__main__":
    main()
