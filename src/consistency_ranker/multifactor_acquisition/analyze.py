"""Offline analysis of multifactor acquisition traces (no network)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.multifactor_acquisition.evaluation_contract import (
    DEFAULT_CONTRACT,
    POLICY_DEFINITIONS,
    EvaluationContract,
    RankingEvalResult,
    evaluate_ranking,
    mean_with_denominator,
    ranking_from_prior,
)
from consistency_ranker.policy_selection.policy_utility import PolicyOutcome

# Re-export for callers that imported these from analyze.
__all__ = [
    "load_qrels",
    "ranking_from_prior",
    "ranking_from_evidence",
    "eval_ranking",
    "evaluate_under_contract",
    "query_clustered_mean_ci",
    "analyze_cell_summaries",
    "build_policy_comparison_table",
    "render_verdict",
    "write_final_report",
    "DEFAULT_CONTRACT",
]


def load_qrels(repo: Path, dataset: str) -> dict[str, dict[str, int]]:
    if dataset == "hotpotqa":
        path = repo / "data/processed/hotpotqa/qrels.jsonl"
    else:
        path = repo / f"data/processed/beir/{dataset}/qrels.jsonl"
    out: dict[str, dict[str, int]] = defaultdict(dict)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            qid = str(row.get("query_id") or row.get("qid"))
            did = str(row.get("doc_id") or row.get("corpus_id"))
            rel = int(row.get("relevance") or row.get("score") or 0)
            if qid and did:
                out[qid][did] = rel
    return dict(out)


def ranking_from_evidence(
    evidence: list[dict[str, Any]],
    candidates: list[str],
    *,
    repair: bool,
) -> list[str]:
    import networkx as nx

    from consistency_ranker.greedy_fas import greedy_fas

    g = nx.DiGraph()
    g.add_nodes_from(candidates)
    for e in evidence:
        if not e.get("valid") and e.get("z", 0) == 0:
            pass
        z = e.get("z")
        di, dj = e.get("doc_i"), e.get("doc_j")
        if di is None or dj is None:
            continue
        if z == 1:
            g.add_edge(str(di), str(dj), weight=1.0)
        elif z == -1:
            g.add_edge(str(dj), str(di), weight=1.0)
    if repair and g.number_of_edges():
        dag, _ = greedy_fas(g)
        g = dag
    scores = {n: float(g.out_degree(n) - g.in_degree(n)) for n in candidates}
    return sorted(candidates, key=lambda d: (-scores.get(d, 0.0), d))


def evaluate_under_contract(
    ranking: list[str],
    qrels: dict[str, int],
    *,
    k: int,
    n_calls: int,
    policy: str,
    prior_ranking: list[str] | None = None,
    candidate_pool: list[str] | None = None,
    catastrophic: bool | None = None,
    buried_recovered: bool | None = None,
    contract: EvaluationContract = DEFAULT_CONTRACT,
) -> tuple[PolicyOutcome, float | None, RankingEvalResult]:
    """Contract evaluation used by every multifactor policy."""
    result = evaluate_ranking(
        ranking,
        qrels,
        k=k,
        n_calls=n_calls,
        prior_ranking=prior_ranking,
        candidate_pool=candidate_pool,
        lambda_c=contract.lambda_c,
        lambda_r=contract.lambda_r,
        catastrophic=catastrophic,
        buried_recovered=buried_recovered,
    )
    outcome = PolicyOutcome(
        policy=policy,
        kendall_tau=result.prior_kendall_tau,
        topk_jaccard=result.relevance_topk_jaccard,
        pairwise_accuracy=None,
        n_calls=n_calls,
        total_cost=float(n_calls),
        catastrophic=bool(result.catastrophic) if result.has_qrels else False,
        buried_recovered=result.buried_recovered,
        extra={
            "ndcg_at_k": result.ndcg_at_k,
            "mrr_at_k": result.mrr_at_k,
            "recall_at_k": result.recall_at_k,
            "prior_topk_jaccard": result.prior_topk_jaccard,
            "prior_kendall_tau": result.prior_kendall_tau,
            "prior_topk_jaccard_informative": result.prior_topk_jaccard_informative,
            "agreement_metric_informative": result.agreement_metric_informative,
            "has_qrels": result.has_qrels,
            "missing_qrels_reason": result.missing_qrels_reason,
            "n_relevant_in_pool": result.n_relevant_in_pool,
            "eval_k": result.k,
            "pool_size": result.pool_size,
            "lambda_c": contract.lambda_c,
            "lambda_r": contract.lambda_r,
            "utility_formula": contract.utility_formula,
            "call_cost_semantics": contract.call_cost_semantics,
            "policy_definition": POLICY_DEFINITIONS.get(policy),
            **dict(result.extra),
        },
    )
    return outcome, result.utility, result


def eval_ranking(
    ranking: list[str],
    qrels: dict[str, int],
    *,
    k: int,
    n_calls: int,
    policy: str,
    catastrophic: bool = False,
    buried_recovered: bool | None = None,
    prior_ranking: list[str] | None = None,
    candidate_pool: list[str] | None = None,
) -> tuple[PolicyOutcome, float | None]:
    """Backward-compatible wrapper around :func:`evaluate_under_contract`.

    Relevance metrics are ``None`` when qrels are missing (never zero-filled,
    never prior-substituted).
    """
    oc, u, _ = evaluate_under_contract(
        ranking,
        qrels,
        k=k,
        n_calls=n_calls,
        policy=policy,
        prior_ranking=prior_ranking,
        candidate_pool=candidate_pool,
        catastrophic=catastrophic if qrels else None,
        buried_recovered=buried_recovered,
    )
    return oc, u


def query_clustered_mean_ci(
    values_by_query: dict[str, float],
    *,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, float]:
    import random

    keys = sorted(values_by_query)
    vals = [values_by_query[k] for k in keys]
    if not vals:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    mean = sum(vals) / len(vals)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [vals[rng.randrange(len(vals))] for _ in range(len(vals))]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    lo = boots[int(0.025 * (n_boot - 1))]
    hi = boots[int(0.975 * (n_boot - 1))]
    return {"mean": mean, "ci_low": lo, "ci_high": hi, "n": len(vals)}


def analyze_cell_summaries(
    cell_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate policy utilities by budget with query as unit."""
    by_key: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in cell_rows:
        key = (r["policy"], int(r["budget"]), r.get("provider"), r.get("prompt_version"))
        by_key[key].append(r)

    uht: dict[tuple[Any, ...], float] = {}
    for r in cell_rows:
        if r["policy"] != "UHT":
            continue
        if r.get("utility") in (None, ""):
            continue
        uht[
            (
                r["query_id"],
                r["provider"],
                r["prompt_version"],
                r["orientation"],
                int(r["budget"]),
            )
        ] = float(r["utility"])

    summaries = []
    for (policy, budget, provider, prompt), rows in sorted(by_key.items()):
        per_q: dict[str, list[float]] = defaultdict(list)
        cat_pol = 0
        n_matched = 0
        ndcg_vals: list[float | None] = []
        for r in rows:
            match_key: tuple[Any, ...] = (
                r["query_id"],
                r["provider"],
                r["prompt_version"],
                r["orientation"],
                budget,
            )
            base = uht.get(match_key)
            if base is None or r.get("utility") in (None, ""):
                continue
            n_matched += 1
            per_q[r["query_id"]].append(float(r["utility"]) - base)
            if r.get("catastrophic") in (True, "True", "true", 1, "1"):
                cat_pol += 1
            ndcg_raw = r.get("ndcg_at_k")
            if ndcg_raw in (None, ""):
                ndcg_vals.append(None)
            else:
                ndcg_vals.append(float(str(ndcg_raw)))
        per_q_mean = {q: sum(v) / len(v) for q, v in per_q.items()}
        ci = query_clustered_mean_ci(per_q_mean, seed=budget)
        ndcg_stats = mean_with_denominator(ndcg_vals)
        summaries.append(
            {
                "policy": policy,
                "budget": budget,
                "provider": provider,
                "prompt_version": prompt,
                "n_query_units": ci["n"],
                "n_matched_cells": n_matched,
                "mean_delta_vs_uht": ci["mean"],
                "ci95_low": ci["ci_low"],
                "ci95_high": ci["ci_high"],
                "catastrophic_rate": (cat_pol / n_matched) if n_matched else None,
                "mean_ndcg_at_k": ndcg_stats["mean"],
                "n_ndcg_valid": ndcg_stats["n_valid"],
                "n_ndcg_missing": ndcg_stats["n_missing"],
            }
        )
    return {"policy_summaries": summaries, "evaluation_contract": DEFAULT_CONTRACT.to_dict()}


def build_policy_comparison_table(
    cell_rows: list[dict[str, Any]],
    *,
    baseline_policy: str = "production_uht",
    policies: tuple[str, ...] | None = None,
    budgets: tuple[int, ...] | None = None,
    lambda_c: float = DEFAULT_CONTRACT.lambda_c,
    lambda_r: float = DEFAULT_CONTRACT.lambda_r,
) -> list[dict[str, Any]]:
    """Prespecified policy×budget comparison against production UHT.

    Uses only rows with valid qrels (non-null nDCG) for relevance aggregates.
    Cost-adjusted utility is reported with explicit coefficients; call savings
    alone cannot declare superiority when quality is equal or worse.
    """
    if not cell_rows:
        return []
    if policies is None:
        policies = tuple(
            sorted({str(r["policy"]) for r in cell_rows if r.get("policy")})
        )
    if budgets is None:
        budgets = tuple(
            sorted({int(r["budget"]) for r in cell_rows if r.get("budget") not in (None, "")})
        )

    def _key(r: dict[str, Any]) -> tuple:
        return (
            r.get("query_id"),
            r.get("provider"),
            r.get("prompt_version"),
            r.get("orientation"),
            int(r["budget"]),
        )

    baseline: dict[tuple, dict[str, Any]] = {}
    by_pol: dict[str, dict[tuple, dict[str, Any]]] = defaultdict(dict)
    for r in cell_rows:
        if r.get("policy") is None or r.get("budget") in (None, ""):
            continue
        pol = str(r["policy"])
        key = _key(r)
        by_pol[pol][key] = r
        if pol == baseline_policy:
            baseline[key] = r

    table: list[dict[str, Any]] = []
    for policy in policies:
        for budget in budgets:
            rows = [
                r
                for key, r in by_pol.get(policy, {}).items()
                if int(key[4]) == int(budget)
            ]
            # Matched keys present for both policy and baseline with valid nDCG.
            paired_ndcg: dict[str, list[float]] = defaultdict(list)
            paired_calls: dict[str, list[float]] = defaultdict(list)
            prior_agree: list[float | None] = []
            prior_tau: list[float | None] = []
            jacc_informative_flags: list[bool] = []
            sg_complete: list[float] = []
            utilities: list[float | None] = []
            ndcgs: list[float | None] = []
            calls: list[float | None] = []
            n_total = 0
            for r in rows:
                n_total += 1
                key = _key(r)
                ndcg_raw = r.get("ndcg_at_k")
                ndcg = None if ndcg_raw in (None, "") else float(str(ndcg_raw))
                call_raw = r.get("n_calls")
                n_calls = None if call_raw in (None, "") else float(str(call_raw))
                ndcgs.append(ndcg)
                calls.append(n_calls)
                util_raw = r.get("utility")
                utilities.append(
                    None if util_raw in (None, "") else float(str(util_raw))
                )
                paj = r.get("prior_topk_jaccard")
                prior_agree.append(None if paj in (None, "") else float(str(paj)))
                ptau = r.get("prior_kendall_tau")
                prior_tau.append(None if ptau in (None, "") else float(str(ptau)))
                info = r.get("prior_topk_jaccard_informative")
                if info is None and isinstance(r.get("extra"), dict):
                    info = (r.get("extra") or {}).get("prior_topk_jaccard_informative")
                jacc_informative_flags.append(
                    info in (True, "True", "true", 1, "1")
                )
                extra = r.get("extra") or {}
                if isinstance(extra, str):
                    try:
                        extra = json.loads(extra.replace("'", '"'))
                    except Exception:  # noqa: BLE001
                        extra = {}
                sg = extra.get("safeguards") if isinstance(extra, dict) else None
                if isinstance(sg, dict) and "production_safeguards_complete" in sg:
                    sg_complete.append(
                        1.0 if sg.get("production_safeguards_complete") else 0.0
                    )
                base = baseline.get(key)
                if (
                    base is not None
                    and ndcg is not None
                    and base.get("ndcg_at_k") not in (None, "")
                ):
                    qid = str(r["query_id"])
                    paired_ndcg[qid].append(ndcg - float(base["ndcg_at_k"]))
                    if n_calls is not None and base.get("n_calls") not in (None, ""):
                        paired_calls[qid].append(n_calls - float(base["n_calls"]))

            paired_mean = {q: sum(v) / len(v) for q, v in paired_ndcg.items()}
            ci = query_clustered_mean_ci(paired_mean, seed=int(budget) + 17)
            ndcg_stats = mean_with_denominator(ndcgs)
            call_stats = mean_with_denominator(calls)
            util_stats = mean_with_denominator(utilities)
            prior_stats = mean_with_denominator(prior_agree)
            tau_stats = mean_with_denominator(prior_tau)
            jacc_info_rate = (
                sum(1 for x in jacc_informative_flags if x) / len(jacc_informative_flags)
                if jacc_informative_flags
                else 0.0
            )
            quality_better = ci["n"] > 0 and ci["mean"] > 0 and ci["ci_low"] > 0
            table.append(
                {
                    "policy": policy,
                    "policy_display_name": (
                        POLICY_DEFINITIONS.get(policy, {}).get("display_name") or policy
                    ),
                    "budget": int(budget),
                    "baseline_policy": baseline_policy,
                    "baseline_display_name": (
                        POLICY_DEFINITIONS.get(baseline_policy, {}).get("display_name")
                        or baseline_policy
                    ),
                    "n_rows": n_total,
                    "n_qrels_valid": ndcg_stats["n_valid"],
                    "n_qrels_missing": ndcg_stats["n_missing"],
                    "mean_ndcg_at_k": ndcg_stats["mean"],
                    "paired_ndcg_minus_baseline_mean": ci["mean"] if ci["n"] else None,
                    "paired_ndcg_ci95_low": ci["ci_low"] if ci["n"] else None,
                    "paired_ndcg_ci95_high": ci["ci_high"] if ci["n"] else None,
                    "n_paired_query_units": ci["n"],
                    "mean_prior_topk_jaccard": prior_stats["mean"],
                    "prior_topk_jaccard_informative_rate": jacc_info_rate,
                    "mean_prior_kendall_tau": tau_stats["mean"],
                    "mean_n_calls": call_stats["mean"],
                    "call_cost_semantics": DEFAULT_CONTRACT.call_cost_semantics,
                    "mean_utility": util_stats["mean"],
                    "lambda_c": lambda_c,
                    "lambda_r": lambda_r,
                    "safeguard_completion_rate": (
                        sum(sg_complete) / len(sg_complete) if sg_complete else None
                    ),
                    "quality_ci_excludes_zero_positive": bool(quality_better),
                    "note": (
                        "prior_topk_jaccard is full-pool membership when k>=pool_size "
                        "and must not be read as ranking equality; use "
                        "prior_kendall_tau as the informative agreement diagnostic. "
                        "n_calls are modeled/replayed acquisition calls, not new "
                        "paid API charges. Utility uses explicit lambda_c/lambda_r."
                    ),
                }
            )
    return table


def render_verdict(
    comparison_table: list[dict[str, Any]],
    *,
    challenger_policies: tuple[str, ...] = (
        "CHALLENGER",
        "HYBRID",
        "ROBUST_COMBINED",
    ),
    min_query_units: int = 10,
) -> dict[str, Any]:
    """Explicit prespecified verdict — never CHALLENGER-only, never cost-only."""
    if not comparison_table:
        return {
            "verdict": "BLOCKED — NO COMPARISON TABLE",
            "reason": "empty comparison table",
            "details": [],
        }

    details = []
    quality_wins = []
    for row in comparison_table:
        if row["policy"] not in challenger_policies:
            continue
        if row["policy"] == row.get("baseline_policy"):
            continue
        details.append(
            {
                "policy": row["policy"],
                "budget": row["budget"],
                "n_paired_query_units": row["n_paired_query_units"],
                "paired_ndcg_minus_baseline_mean": row["paired_ndcg_minus_baseline_mean"],
                "paired_ndcg_ci95_low": row["paired_ndcg_ci95_low"],
                "mean_ndcg_at_k": row["mean_ndcg_at_k"],
                "mean_n_calls": row["mean_n_calls"],
                "mean_utility": row["mean_utility"],
                "quality_ci_excludes_zero_positive": row["quality_ci_excludes_zero_positive"],
            }
        )
        if (
            row["quality_ci_excludes_zero_positive"]
            and int(row["n_paired_query_units"] or 0) >= min_query_units
        ):
            quality_wins.append(row)

    if quality_wins:
        return {
            "verdict": "QUALITY ADVANTAGE DETECTED (MATCHED nDCG)",
            "reason": (
                "At least one prespecified policy beats the baseline on paired "
                "nDCG with CI excluding zero; inspect utility separately. "
                "This does not assert equality for non-winning policies."
            ),
            "criterion": (
                "quality_win := paired_ndcg_mean > 0 AND paired_ndcg_ci95_low > 0 "
                f"AND n_paired_query_units >= {min_query_units}"
            ),
            "quality_wins": [
                {"policy": r["policy"], "budget": r["budget"]} for r in quality_wins
            ],
            "details": details,
        }

    # Higher modeled utility without an established quality win is reported,
    # never declared as ranking-quality success.
    baseline_util = {
        (b.get("budget"), b.get("baseline_policy") or b.get("policy")): b.get(
            "mean_utility"
        )
        for b in comparison_table
        if b.get("policy") == b.get("baseline_policy")
        and b.get("mean_utility") is not None
    }
    util_only = []
    for r in comparison_table:
        if r["policy"] not in challenger_policies:
            continue
        if r.get("quality_ci_excludes_zero_positive"):
            continue
        base_u = baseline_util.get((r.get("budget"), r.get("baseline_policy")))
        if base_u is None or r.get("mean_utility") is None:
            continue
        if float(r["mean_utility"]) > float(base_u):
            util_only.append(r)
    if util_only:
        return {
            "verdict": (
                "NO MATCHED-BUDGET QUALITY WIN ESTABLISHED — "
                "COST-ONLY UTILITY SIGNALS PRESENT"
            ),
            "reason": (
                "No prespecified policy established a matched-budget nDCG win "
                "(paired CI did not exclude zero positively). Some policies show "
                "higher cost-adjusted utility driven by lower modeled call counts; "
                "that is not a retrieval-quality success. A CI crossing zero is "
                "inconclusive, not proof of equal quality."
            ),
            "criterion": (
                "quality_win requires paired_ndcg_ci95_low > 0; otherwise, if "
                "mean_utility > baseline_utility, report cost-only utility signal."
            ),
            "details": details,
        }

    underpowered = any(
        int(r.get("n_paired_query_units") or 0) < min_query_units
        for r in comparison_table
        if r["policy"] in challenger_policies
    )
    if underpowered:
        return {
            "verdict": "INCONCLUSIVE — UNDERPOWERED OR INCOMPLETE PAIRED COMPARISON",
            "reason": f"Fewer than {min_query_units} paired query units for some cells.",
            "details": details,
        }

    return {
        "verdict": (
            "NO MATCHED-BUDGET QUALITY WIN ESTABLISHED OVER PRODUCTION-UHT"
        ),
        "reason": (
            "Across CHALLENGER, HYBRID, and ROBUST_COMBINED, no paired nDCG CI "
            "excluded zero positively against production_uht. This does not assert "
            "that all policies have equal quality."
        ),
        "criterion": (
            "quality_win := paired_ndcg_mean > 0 AND paired_ndcg_ci95_low > 0 "
            f"AND n_paired_query_units >= {min_query_units}"
        ),
        "details": details,
    }


def write_final_report(path: Path, payload: dict[str, Any]) -> None:
    """Write compact markdown; full structured results live in sibling JSON/CSV."""
    verdict = payload.get("verdict", "BLOCKED — INCOMPLETE MATCHED ACQUISITION")
    analysis = payload.get("policy_results") or {}
    summaries = analysis.get("policy_summaries") or []
    comparison = payload.get("comparison_table") or []
    table_lines = [
        "| policy | budget | provider | prompt | n_query | "
        "mean_delta_vs_uht | ci95_low | ci95_high |",
        "|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for s in summaries:
        table_lines.append(
            "| {policy} | {budget} | {provider} | {prompt_version} | {n_query_units} | "
            "{mean_delta_vs_uht:.6f} | {ci95_low:.6f} | {ci95_high:.6f} |".format(
                policy=s.get("policy"),
                budget=s.get("budget"),
                provider=s.get("provider"),
                prompt_version=s.get("prompt_version"),
                n_query_units=s.get("n_query_units"),
                mean_delta_vs_uht=float(s.get("mean_delta_vs_uht") or 0.0),
                ci95_low=float(s.get("ci95_low") or 0.0),
                ci95_high=float(s.get("ci95_high") or 0.0),
            )
        )
    if len(table_lines) == 2:
        table_lines.append("| _(none)_ |  |  |  |  |  |  |  |")

    cmp_lines = [
        "| policy | budget | n_qrels | mean_nDCG | ΔnDCG vs prod_uht | "
        "prior_tau | calls | sg_complete | utility |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in comparison:
        def _f(x: Any, nd: int = 4) -> str:
            if x is None:
                return ""
            return f"{float(x):.{nd}f}"

        cmp_lines.append(
            f"| {row.get('policy')} | {row.get('budget')} | {row.get('n_qrels_valid')} | "
            f"{_f(row.get('mean_ndcg_at_k'))} | {_f(row.get('paired_ndcg_minus_baseline_mean'))} | "
            f"{_f(row.get('mean_prior_kendall_tau'))} | {_f(row.get('mean_n_calls'), 2)} | "
            f"{_f(row.get('safeguard_completion_rate'), 3)} | {_f(row.get('mean_utility'))} |"
        )

    coverage = payload.get("coverage") or {}
    depth_note = coverage.get("depth_heterogeneity_note") or (
        "FiQA may have effective_depth < 12; see QUERY_SAMPLE.csv / FACTOR_CELLS.csv."
    )
    contract = payload.get("evaluation_contract") or DEFAULT_CONTRACT.to_dict()
    lines = [
        "# Real-Query Multifactor Budgeted Acquisition",
        "",
        "## 1. Verdict",
        "",
        f"**{verdict}**",
        "",
        str((payload.get("verdict_detail") or {}).get("reason", "")),
        "",
        "## 2. Evaluation Contract",
        "",
        "```json",
        json.dumps(contract, indent=2),
        "```",
        "",
        "Relevance quality uses qrels only. `prior_kendall_tau` is the informative "
        "prior-agreement diagnostic. `prior_topk_jaccard` is full-pool membership "
        "when k >= pool_size and must not be read as ranking equality.",
        "",
        "## 3. Acquisition Coverage",
        "",
        "```json",
        json.dumps(coverage, indent=2),
        "```",
        "",
        f"Depth note: {depth_note}",
        "",
        "## 4. Cost and Runtime",
        "",
        "```json",
        json.dumps(payload.get("cost", {}), indent=2),
        "```",
        "",
        "## 5. Prespecified Policy Comparison vs Production UHT",
        "",
        *cmp_lines,
        "",
        "Utility coefficients are listed per row (`lambda_c`, `lambda_r`). "
        "Call savings without nDCG gain are not treated as success.",
        "",
        "## 6. Legacy Utility-Delta Summaries (vs plain UHT)",
        "",
        *table_lines,
        "",
        "## 7. Calibration and Predictive Criteria",
        "",
        str(
            (payload.get("criteria") or {}).get(
                "note",
                "Simple criteria evaluated post-hoc in ANALYSIS.json; neural router forbidden.",
            )
        ),
        "",
        "## 8. Safeguard Execution",
        "",
        "```json",
        json.dumps(payload.get("safeguards", {}), indent=2),
        "```",
        "",
        "## 9. Known Limitations",
        "",
        str(payload.get("limitations", "See KNOWN_LIMITATIONS.md if present.")),
        "",
        "## 10. Paid API Calls",
        "",
        str(
            payload.get(
                "api_calls_statement",
                "See MANIFEST.json for whether this run contacted providers.",
            )
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
