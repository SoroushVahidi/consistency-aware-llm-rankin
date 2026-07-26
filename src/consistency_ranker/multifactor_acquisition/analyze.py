"""Offline analysis of multifactor acquisition traces (no network)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.policy_selection.policy_utility import (
    PolicyOutcome,
    UtilityWeights,
)


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


def ranking_from_prior(prior: dict[str, float]) -> list[str]:
    return sorted(prior, key=lambda d: (-float(prior[d]), d))


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
            # still allow z from normalized rows
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
    scores = {
        n: float(g.out_degree(n) - g.in_degree(n)) for n in candidates
    }
    return sorted(candidates, key=lambda d: (-scores.get(d, 0.0), d))


def eval_ranking(
    ranking: list[str],
    qrels: dict[str, int],
    *,
    k: int,
    n_calls: int,
    policy: str,
    catastrophic: bool = False,
    buried_recovered: bool | None = None,
) -> tuple[PolicyOutcome, float]:
    ndcg = float(ndcg_at_k(ranking, qrels, k=k)) if qrels else 0.0
    # topk jaccard vs relevant set (binary)
    rel = {d for d, r in qrels.items() if r > 0}
    top = set(ranking[:k])
    jacc = (len(top & rel) / len(top | rel)) if (top or rel) else 0.0
    outcome = PolicyOutcome(
        policy=policy,
        kendall_tau=None,
        topk_jaccard=float(jacc),
        pairwise_accuracy=None,
        n_calls=n_calls,
        total_cost=float(n_calls),
        catastrophic=catastrophic,
        buried_recovered=buried_recovered,
        extra={"ndcg_at_k": ndcg},
    )
    # Prefer nDCG as quality for real-query utility
    w = UtilityWeights(quality_metric="topk_jaccard")
    # Override quality via extra: compute utility with ndcg
    u = float(ndcg - w.lambda_c * n_calls - w.lambda_r * (1.0 if catastrophic else 0.0))
    return outcome, u


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
    # cell_rows: one row per (query, provider, prompt, orientation, policy, budget)
    by_key: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in cell_rows:
        key = (r["policy"], int(r["budget"]), r.get("provider"), r.get("prompt_version"))
        by_key[key].append(r)

    # UHT baseline per (query, provider, prompt, orientation, budget)
    uht = {}
    for r in cell_rows:
        if r["policy"] != "UHT":
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
        # mean utility delta vs UHT at matched cells
        deltas: dict[str, float] = {}
        for r in rows:
            key = (
                r["query_id"],
                r["provider"],
                r["prompt_version"],
                r["orientation"],
                budget,
            )
            base = uht.get(key)
            if base is None:
                continue
            # one value per original query (average orientations/prompts later separately)
            q = r["query_id"]
            deltas.setdefault(q, [])
            # store list then average
        # rebuild properly
        per_q: dict[str, list[float]] = defaultdict(list)
        cat_pol = 0
        n_matched = 0
        for r in rows:
            key = (
                r["query_id"],
                r["provider"],
                r["prompt_version"],
                r["orientation"],
                budget,
            )
            base = uht.get(key)
            if base is None:
                continue
            n_matched += 1
            per_q[r["query_id"]].append(float(r["utility"]) - base)
            if r.get("catastrophic"):
                cat_pol += 1
        per_q_mean = {q: sum(v) / len(v) for q, v in per_q.items()}
        ci = query_clustered_mean_ci(per_q_mean, seed=budget)
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
            }
        )
    return {"policy_summaries": summaries}


def write_final_report(path: Path, payload: dict[str, Any]) -> None:
    """Write compact markdown; full structured results live in sibling JSON/CSV."""
    verdict = payload.get("verdict", "BLOCKED — INCOMPLETE MATCHED ACQUISITION")
    analysis = payload.get("policy_results") or {}
    summaries = analysis.get("policy_summaries") or []
    # Compact table (no giant JSON dump / no 8000-char truncation).
    table_lines = [
        "| policy | budget | provider | prompt | n_query | mean_delta_vs_uht | ci95_low | ci95_high |",
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

    coverage = payload.get("coverage") or {}
    depth_note = coverage.get("depth_heterogeneity_note") or (
        "FiQA may have effective_depth < 12; see QUERY_SAMPLE.csv / FACTOR_CELLS.csv."
    )
    lines = [
        "# Real-Query Multifactor Budgeted Acquisition",
        "",
        "## 1. Verdict",
        "",
        f"**{verdict}**",
        "",
        "## 2. Acquisition Coverage",
        "",
        "```json",
        json.dumps(coverage, indent=2),
        "```",
        "",
        f"Depth note: {depth_note}",
        "",
        "Full structured coverage also in `MANIFEST.json`, `FACTOR_CELLS.csv`, "
        "`completed_cells.json`.",
        "",
        "## 3. Cost and Runtime",
        "",
        "```json",
        json.dumps(payload.get("cost", {}), indent=2),
        "```",
        "",
        "See also `COST_LEDGER.csv`, `STATUS.json`.",
        "",
        "## 4. Policy Results",
        "",
        "Compact summary (full rows in `ANALYSIS.json` and `CELL_SUMMARY.csv`):",
        "",
        *table_lines,
        "",
        "Artifact: `ANALYSIS.json`.",
        "",
        "## 5. Calibration and Predictive Criteria",
        "",
        str(
            (payload.get("criteria") or {}).get(
                "note",
                "Simple criteria evaluated post-hoc in ANALYSIS.json; neural router forbidden.",
            )
        ),
        "",
        "## 6. Provider, Prompt, and Orientation Transfer",
        "",
        "```json",
        json.dumps(payload.get("transfer", {}), indent=2),
        "```",
        "",
        "## 7. Safeguard Cost",
        "",
        str(
            (payload.get("safeguards") or {}).get(
                "note",
                "plain_uht vs production_uht rows in CELL_SUMMARY.csv at budgets 3/5/8",
            )
        ),
        "",
        "## 8. Reviewer Concerns Addressed",
        "",
        payload.get(
            "reviewer",
            "- C2/C11 actionable criterion: evaluated under prespecified rule.\n"
            "- C4 real-LLM breadth: matched non-OpenAI factorial acquisition.\n"
            "- Orientation/prompt sensitivity: factorial factors collected.",
        ),
        "",
        "## 9. Remaining Missing Cells",
        "",
        payload.get("remaining", "See INCOMPLETE.md and FACTOR_CELLS.csv."),
        "",
        "## 10. Recommended Next Step",
        "",
        payload.get("next_step", "Resume incomplete cells or expand only missing factor cells."),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
