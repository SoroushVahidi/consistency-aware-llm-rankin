"""Reconstruct repair / ranking outcomes from cached pairwise judgments."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from consistency_ranker.baseline_ranking import (
    copeland_ranking,
    score_sum_scores,
    weighted_out_minus_in_ranking,
)
from consistency_ranker.cycle_detection import has_cycle
from consistency_ranker.evaluation import ndcg_at_k
from consistency_ranker.greedy_fas import greedy_fas, greedy_fas_total_weight
from consistency_ranker.mwfas_solver import solve as solve_mwfas
from consistency_ranker.real_query_replay.evidence_index import REPO_ROOT


def _load_qrels(dataset: str) -> dict[str, dict[str, float]]:
    candidates = [
        REPO_ROOT / "data" / "processed" / "beir" / dataset / "qrels.jsonl",
        REPO_ROOT / "data" / "processed" / dataset / "qrels.jsonl",
    ]
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for p in candidates:
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                qid = str(row.get("query_id") or row.get("qid") or "")
                did = str(row.get("doc_id") or row.get("document_id") or "")
                rel = float(row.get("relevance") or row.get("rel") or 0.0)
                if qid and did:
                    out[qid][did] = rel
        break
    return out


def _graph_from_openai_judgments(
    judgments: list[dict[str, Any]],
) -> nx.DiGraph:
    g = nx.DiGraph()
    for j in judgments:
        winner = j.get("winner") or j.get("winner_doc_id")
        loser = j.get("loser") or j.get("loser_doc_id")
        if not winner or not loser:
            docs = j.get("doc_ids") or []
            if len(docs) == 2 and winner:
                loser = docs[0] if docs[1] == winner else docs[1]
        if not winner or not loser:
            continue
        wt = float(j.get("weight") or 1.0)
        g.add_edge(str(winner), str(loser), weight=wt)
        if str(winner) not in g.nodes:
            g.add_node(str(winner))
        if str(loser) not in g.nodes:
            g.add_node(str(loser))
    return g


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _hybrid_ranking(
    graph: nx.DiGraph,
    prior: dict[str, float],
    component: str,
    alpha: float,
) -> list[str]:
    if component == "copeland":
        # Score via out-in degree (unweighted Copeland).
        comp = {n: float(graph.out_degree(n) - graph.in_degree(n)) for n in graph.nodes()}
    else:
        # Weighted balance.
        bal = {n: 0.0 for n in graph.nodes()}
        for u, v, data in graph.edges(data=True):
            w = float(data.get("weight", 1.0))
            bal[u] = bal.get(u, 0.0) + w
            bal[v] = bal.get(v, 0.0) - w
        comp = bal
    pn = _normalize({n: float(prior.get(n, 0.0)) for n in graph.nodes()})
    cn = _normalize(comp)
    combo = {n: pn.get(n, 0.0) + alpha * cn.get(n, 0.0) for n in graph.nodes()}
    return sorted(combo, key=lambda n: (-combo[n], n))


def reconstruct_openai_pairwise_dir(
    dir_path: Path,
    *,
    dataset: str,
    max_queries: int | None = None,
    run_exact: bool = True,
    exact_max_n: int = 12,
) -> list[dict[str, Any]]:
    """Independently reconstruct unrepaired / greedy / exact rankings + nDCG."""
    cache = dir_path / "judgment_cache" / "llm_pairwise_judgments.jsonl"
    cfg = json.loads((dir_path / "config.json").read_text())
    top_k = int(cfg.get("top_k") or 15)
    qrels = _load_qrels(dataset)

    by_q: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with cache.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            by_q[str(row["query_id"])].append(row)

    qids = sorted(by_q)
    if max_queries is not None:
        qids = qids[: max_queries]

    rows: list[dict[str, Any]] = []
    for qid in qids:
        judgments = by_q[qid]
        graph = _graph_from_openai_judgments(judgments)
        if graph.number_of_nodes() == 0:
            continue
        prior = score_sum_scores(graph)
        cyclic = bool(has_cycle(graph))
        # Avoid enumerating simple cycles on dense n=15 tournaments.
        n_scc = nx.number_strongly_connected_components(graph)
        largest_scc = max((len(c) for c in nx.strongly_connected_components(graph)), default=0)
        n_cycles = -1 if cyclic else 0
        relevance_raw = qrels.get(qid, {})
        relevance = {k: int(v) for k, v in relevance_raw.items()}

        # Unrepaired extractors
        unrepaired_copeland = copeland_ranking(graph)
        unrepaired_balance = weighted_out_minus_in_ranking(graph)
        hybrid_u = _hybrid_ranking(graph, prior, "copeland", 0.3)

        # Greedy repair
        dag_g, removed_g = greedy_fas(graph)
        greedy_w = greedy_fas_total_weight(removed_g) if cyclic else 0.0
        greedy_copeland = copeland_ranking(dag_g)
        greedy_balance = weighted_out_minus_in_ranking(dag_g)
        hybrid_g = _hybrid_ranking(dag_g, prior, "copeland", 0.3)

        # Exact repair (SCIP when available)
        exact_status = "skipped"
        exact_w = float("nan")
        exact_copeland: list[str] = []
        exact_balance: list[str] = []
        hybrid_e: list[str] = []
        if run_exact and cyclic:
            try:
                dag_e, removed_e, status = solve_mwfas(
                    graph, method="exact", return_status=True, time_limit_s=60.0
                )
                exact_status = str(getattr(status, "status", None) or status)
                obj = getattr(status, "objective", None)
                if obj is not None:
                    exact_w = float(obj)
                elif removed_e and len(removed_e[0]) >= 3:
                    exact_w = float(sum(float(t[2]) for t in removed_e))
                else:
                    exact_w = float(
                        sum(
                            float(graph[u][v].get("weight", 1.0))
                            for u, v in ((t[0], t[1]) for t in removed_e)
                        )
                    )
                exact_copeland = copeland_ranking(dag_e)
                exact_balance = weighted_out_minus_in_ranking(dag_e)
                hybrid_e = _hybrid_ranking(dag_e, prior, "copeland", 0.3)
            except Exception as exc:  # noqa: BLE001 — record and continue
                exact_status = f"error:{type(exc).__name__}"



        def _ndcg(ranking: list[str]) -> float:
            if not relevance or not ranking:
                return float("nan")
            return float(ndcg_at_k(ranking, relevance, k=top_k))

        cell_base = {
            "dataset": dataset,
            "query_id": qid,
            "provider": str(cfg.get("provider") or "openai"),
            "model": str(cfg.get("model") or "gpt-4o-mini"),
            "prompt": "legacy_pairwise",
            "orientation": "none",
            "judgment_mode": "pairwise",
            "top_k": top_k,
            "n_candidates": graph.number_of_nodes(),
            "n_judgments": len(judgments),
            "is_cyclic": cyclic,
            "n_cycles": n_cycles,
            "n_scc": n_scc,
            "largest_scc": largest_scc,
            "has_qrels": bool(relevance),
            "cell_status": "complete" if relevance else "missing_qrels",
        }

        policies = [
            ("unrepaired_copeland", unrepaired_copeland, 0.0, "none"),
            ("unrepaired_balance", unrepaired_balance, 0.0, "none"),
            ("hybrid_unrepaired_copeland_a03", hybrid_u, 0.0, "none"),
            ("greedy_copeland", greedy_copeland, greedy_w, "greedy"),
            ("greedy_balance", greedy_balance, greedy_w, "greedy"),
            ("hybrid_greedy_copeland_a03", hybrid_g, greedy_w, "greedy"),
        ]
        if exact_copeland:
            policies.extend(
                [
                    ("exact_copeland", exact_copeland, exact_w, "exact"),
                    ("exact_balance", exact_balance, exact_w, "exact"),
                    ("hybrid_exact_copeland_a03", hybrid_e, exact_w, "exact"),
                ]
            )

        for name, ranking, fas_w, repair in policies:
            nd = _ndcg(ranking)
            rows.append(
                {
                    **cell_base,
                    "policy": name,
                    "repair": repair,
                    "fas_weight_removed": fas_w,
                    "exact_status": exact_status if repair == "exact" else "",
                    "ndcg_at_k": nd,
                    "n_calls": len(judgments),  # full all-pairs already observed
                    "token_cost": float("nan"),
                    "utility": nd if relevance else float("nan"),
                }
            )
    return rows


def load_failure_mining_repair_deltas(
    metrics_csv: Path,
) -> list[dict[str, Any]]:
    """Load precomputed failure-mining repaired-vs-unrepaired deltas (query clustered)."""
    rows: list[dict[str, Any]] = []
    with metrics_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            method = str(r.get("method") or "")
            # Keep unrepaired / repaired pairs when present.
            rows.append(
                {
                    "dataset": r.get("dataset"),
                    "query_id": r.get("query_id"),
                    "provider": "azure+cohere",
                    "model": "mixed",
                    "prompt": "failure_mining",
                    "orientation": "debias_position",
                    "judgment_mode": "pairwise",
                    "policy": method,
                    "repair": (
                        "greedy"
                        if "repair" in method.lower() or "fas" in method.lower()
                        else "unknown"
                    ),
                    "ndcg_at_k": float(r["ndcg_at_k"]) if r.get("ndcg_at_k") not in (None, "") else float("nan"),
                    "delta_vs_unrepaired": (
                        float(r["delta_vs_unrepaired"])
                        if r.get("delta_vs_unrepaired") not in (None, "")
                        else float("nan")
                    ),
                    "is_cyclic": str(r.get("is_cyclic") or "").lower() in {"1", "true", "yes"},
                    "fas_weight_removed": (
                        float(r["fas_removed_weight"])
                        if r.get("fas_removed_weight") not in (None, "")
                        else float("nan")
                    ),
                    "cell_status": "reconstructible",
                    "source": "failure_mining_llm_v3_metrics",
                }
            )
    return rows


def pivot_repair_gains(policy_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-query repair_gain = best_repaired_ndcg - matching_unrepaired_ndcg."""
    by_q: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in policy_rows:
        if r.get("ndcg_at_k") != r.get("ndcg_at_k"):  # NaN
            continue
        key = (str(r["dataset"]), str(r["query_id"]))
        by_q[key][str(r["policy"])] = r

    out: list[dict[str, Any]] = []
    for (dataset, qid), pols in by_q.items():
        pairs = [
            ("greedy_copeland", "unrepaired_copeland"),
            ("exact_copeland", "unrepaired_copeland"),
            ("hybrid_greedy_copeland_a03", "hybrid_unrepaired_copeland_a03"),
            ("hybrid_exact_copeland_a03", "hybrid_unrepaired_copeland_a03"),
        ]
        for repaired, unrepaired in pairs:
            if repaired not in pols or unrepaired not in pols:
                continue
            rg = float(pols[repaired]["ndcg_at_k"]) - float(pols[unrepaired]["ndcg_at_k"])
            out.append(
                {
                    "dataset": dataset,
                    "query_id": qid,
                    "repaired_policy": repaired,
                    "unrepaired_policy": unrepaired,
                    "repair_gain": rg,
                    "repaired_ndcg": float(pols[repaired]["ndcg_at_k"]),
                    "unrepaired_ndcg": float(pols[unrepaired]["ndcg_at_k"]),
                    "is_cyclic": bool(pols[repaired].get("is_cyclic")),
                    "fas_weight_removed": pols[repaired].get("fas_weight_removed"),
                    "provider": pols[repaired].get("provider"),
                    "n_cycles": pols[repaired].get("n_cycles"),
                }
            )
    return out
