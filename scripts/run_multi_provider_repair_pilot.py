"""
run_multi_provider_repair_pilot.py
===================================
Small, real-LLM multi-provider pairwise-preference-graph pilot.

Purpose: build real LLM preference graphs (Azure OpenAI gpt-4.1-mini, Vertex
AI gemini-2.5-flash, Cohere command-r-plus-08-2024, Fireworks
gpt-oss-120b) over a modest, fixed set of (dataset, query, candidate-pool)
units, then measure whether repairing those graphs (MWFAS, greedy + exact)
has materially greater oracle headroom than the repository-scale classical
score-derived graphs (~0.0025 nDCG, CI [0.0020, 0.0030], n=419 -- see
reports/repository_scale_headroom_analysis/summary.json), against this
project's own minimum meaningful effect (~0.0207 -- see
papers/JDIQ_2026/manuscript/main.tex lines 429-430).

This script deliberately reuses existing infrastructure rather than
reimplementing it:

- rerankers.llm_pairwise.{PairwiseConfig, compare_pair, collect_all_pairs}
  for the actual LLM calls (retry/backoff, disk-backed caching, position
  de-biasing via debias_position=True already runs BOTH A/B and B/A and
  majority-votes them per pair -- see collect_all_pairs docstring).
- rerankers.common.{JudgmentCache, BudgetTracker} for idempotent, resumable
  disk-backed judgment caching.
- consistency_ranker.failure_mining.llm_runner._provider_call_config for the
  shared provider configuration path (this is what gives Fireworks
  reasoning_effort="low" + max_tokens=512 automatically).
- consistency_ranker.graph_construction.build_graph / graph_summary
- consistency_ranker.mwfas_solver.solve (greedy heuristic + exact SCIP)
- consistency_ranker.baseline_ranking.copeland_ranking
- consistency_ranker.evaluation.ndcg_at_k
- consistency_ranker.data.unified_loader.load_dataset_splits
- rerankers.common.build_candidate_pool for deterministic qrel-based pools
- consistency_ranker.repair_selector_mining.oracle_headroom.{
    PreserveRepairRecord, compute_oracle_headroom, evaluate_go_no_go}
  for the final headroom computation, directly comparable to the
  repository-scale figure.
- consistency_ranker.repair_selector_mining.checkpoint.FlushWriter for
  atomic, append-only, flush-per-record disk writes (crash-resilient
  checkpointing / full raw-call provenance).

Modes (mirrors the --mode convention of scripts/run_stopping_rule_pilot.py):

  estimate  Load data, select queries/pools deterministically, compute the
            exact planned API-call count and a rough cost estimate. Makes
            NO network calls. Safe to run repeatedly.
  smoke     Very small end-to-end run (1 dataset, 1 query, pool_size=3)
            covering every provider, parsing, graph construction, repair
            (greedy + exact), evaluation, checkpointing, and resume
            behavior (run twice; second run must hit cache, make 0 new
            calls). Writes SMOKE_TEST_REPORT.md and a machine-readable
            smoke_result.json with an explicit pass/fail verdict.
  run       The main pilot. Idempotent and resumable: already-cached
            provider judgments are not re-requested, and already-completed
            (dataset, query_id, graph_id, repair_method) analysis units are
            skipped on restart.
  analyze   Post-hoc: reads pilot_results.jsonl, computes per-query and
            aggregate metrics, oracle headroom (query-level, with CI), and
            an explicit comparison to the repository-scale figures.

Provider-failure policy (explicit, per user instruction): a provider that
raises during collect_all_pairs is NEVER silently skipped, replaced, or
merged with another provider's results. The failure is logged in full to
provider_failures.jsonl and then RE-RAISED, halting the process. Restarting
the same command resumes safely (already-cached pairs and already-completed
analysis units are not repeated).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.baseline_ranking import copeland_ranking  # noqa: E402
from consistency_ranker.data.unified_loader import load_dataset_splits  # noqa: E402
from consistency_ranker.evaluation import ndcg_at_k  # noqa: E402
from consistency_ranker.failure_mining.llm_runner import _provider_call_config  # noqa: E402
from consistency_ranker.graph_construction import build_graph, graph_summary  # noqa: E402
from consistency_ranker.mwfas_solver import solve as mwfas_solve  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402
from consistency_ranker.repair_selector_mining.checkpoint import FlushWriter  # noqa: E402
from consistency_ranker.repair_selector_mining.oracle_headroom import (  # noqa: E402
    OracleHeadroomResult,
    PreserveRepairRecord,
    compute_oracle_headroom,
    evaluate_go_no_go,
)
from rerankers.common import BudgetTracker, build_candidate_pool  # noqa: E402
from rerankers.llm_pairwise import (  # noqa: E402
    LLMCallStats,
    PairwiseConfig,
    collect_all_pairs,
)

log = logging.getLogger("multi_provider_repair_pilot")


def _setup_logging(output_dir: Path, run_tag: str) -> Path:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_tag}.log"
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(stream)
    return log_path


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class DiskAppendList:
    """Duck-types list.append() for llm_pairwise's detail_sink, but writes
    each record to disk immediately (crash-resilient full provenance),
    reusing checkpoint.FlushWriter's atomic append-and-flush pattern.

    Adds dataset/provider/model/prompt_version/seed/timestamp to every
    record, plus an honest (labeled, not overclaimed) latency proxy: the
    wall-clock gap since the previous record was written to *this*
    provider's sink. Under concurrency > 1 this reflects completion-order
    spacing, not exact per-call server latency -- see module docstring.
    """

    def __init__(self, path: Path, *, dataset: str, provider: str, model: str,
                 prompt_version: str, seed: int) -> None:
        self._writer = FlushWriter(path)
        self._dataset = dataset
        self._provider = provider
        self._model = model
        self._prompt_version = prompt_version
        self._seed = seed
        self._last_write_ts: float | None = None

    def append(self, obj: dict) -> None:
        now = time.time()
        elapsed = None if self._last_write_ts is None else (now - self._last_write_ts)
        self._last_write_ts = now
        record = {
            "timestamp": now,
            "dataset": self._dataset,
            "provider": self._provider,
            "model": self._model,
            "prompt_version": self._prompt_version,
            "seed": self._seed,
            "elapsed_since_prev_write_s": elapsed,
            **obj,
        }
        self._writer.write(record)

    def close(self) -> None:
        self._writer.close()


def _prompt_version(prompt_template_path: Path) -> str:
    return hashlib.sha256(prompt_template_path.read_bytes()).hexdigest()[:12]


def build_pairwise_config(
    provider: str,
    *,
    cache_dir: Path,
    seed: int,
    debias: bool,
    prompt_template_path: Path,
) -> PairwiseConfig:
    cfg = _provider_call_config(provider)
    return PairwiseConfig(
        model=cfg["model"],
        provider=cfg["family"],
        api_key=cfg.get("api_key"),
        base_url=cfg.get("base_url"),
        extra_body=cfg.get("extra_body"),
        max_tokens=cfg.get("max_tokens_override", 4),
        gemini_use_vertex=cfg.get("gemini_use_vertex", False),
        vertex_project=cfg.get("vertex_project"),
        vertex_location=cfg.get("vertex_location"),
        concurrency=cfg.get("concurrency", 1),
        debias_position=debias,
        seed=seed,
        cache_dir=cache_dir,
        prompt_template_path=prompt_template_path,
        dry_run=False,
    )


def select_pilot_queries(
    dataset_name: str, *, pool_size: int, n_queries: int, seed: int
) -> tuple[list[str], dict, dict, dict]:
    """Deterministically select a modest, representative set of queries.

    Eligible queries are those with >= pool_size qrel-judged documents (so a
    full candidate pool can be built without padding). Selection uses
    random.Random(seed).sample over the sorted eligible-query-id list, then
    re-sorts the sample for a stable output order -- reproducible and
    auditable, with the required random seed explicitly recorded.

    Returns (selected_query_ids, queries_by_id, docs_by_id, qrels_by_query).
    """
    queries, documents, qrels = load_dataset_splits(dataset_name)
    queries_by_id = {q.query_id: q for q in queries}
    docs_by_id = {d.doc_id: d for d in documents}
    qrels_by_query: dict[str, list] = defaultdict(list)
    for qr in qrels:
        qrels_by_query[qr.query_id].append(qr)

    eligible = sorted(qid for qid, entries in qrels_by_query.items() if len(entries) >= pool_size)
    rng = random.Random(seed)
    n = min(n_queries, len(eligible))
    selected = sorted(rng.sample(eligible, k=n))
    return selected, queries_by_id, docs_by_id, qrels_by_query


def build_pool(query_id: str, qrels_by_query: dict, docs_by_id: dict, pool_size: int) -> list[tuple[str, str]]:
    return build_candidate_pool(query_id, qrels_by_query, docs_by_id, pool_size)


@dataclass
class PlannedQuery:
    dataset: str
    query_id: str
    query_text: str
    pool: list[tuple[str, str]]
    relevance_map: dict[str, int]


def plan_queries(config: dict, *, smoke: bool) -> list[PlannedQuery]:
    datasets = config["smoke_datasets"] if smoke else config["datasets"]
    n_queries = config["smoke_n_queries_per_dataset"] if smoke else config["n_queries_per_dataset"]
    pool_size = config["smoke_pool_size"] if smoke else config["pool_size"]
    seed = config["seed"]

    planned: list[PlannedQuery] = []
    for dataset_name in datasets:
        selected, queries_by_id, docs_by_id, qrels_by_query = select_pilot_queries(
            dataset_name, pool_size=pool_size, n_queries=n_queries, seed=seed
        )
        for qid in selected:
            pool = build_pool(qid, qrels_by_query, docs_by_id, pool_size)
            relevance_map = {e.doc_id: e.relevance for e in qrels_by_query[qid]}
            planned.append(
                PlannedQuery(
                    dataset=dataset_name,
                    query_id=qid,
                    query_text=queries_by_id[qid].text,
                    pool=pool,
                    relevance_map=relevance_map,
                )
            )
    return planned


def _n_pairs(pool_len: int) -> int:
    return pool_len * (pool_len - 1) // 2


def run_estimate(config: dict, output_dir: Path, *, smoke: bool) -> dict:
    planned = plan_queries(config, smoke=smoke)
    providers = config["providers"]
    debias = config["debias_position"]
    per_query_rows = []
    total_calls = 0
    for pq in planned:
        n_pairs = _n_pairs(len(pq.pool))
        calls_per_provider = n_pairs * (2 if debias else 1)
        calls_this_query = calls_per_provider * len(providers)
        total_calls += calls_this_query
        per_query_rows.append(
            {
                "dataset": pq.dataset,
                "query_id": pq.query_id,
                "pool_size": len(pq.pool),
                "n_pairs": n_pairs,
                "calls_per_provider": calls_per_provider,
                "calls_all_providers": calls_this_query,
            }
        )

    # Rough, unverified-against-live-pricing per-provider cost bands (USD).
    # These are order-of-magnitude planning estimates only -- see report
    # note. Non-fireworks providers use max_tokens=4 (tiny completions);
    # fireworks uses max_tokens=512 (reasoning model budget, only ~20-100
    # actually consumed for a trivial pairwise judgment per the Fireworks
    # verification smoke test).
    calls_per_provider_total = total_calls // len(providers) if providers else 0
    est_prompt_tokens_per_call = 450  # query + 2 short doc snippets, rough
    cost_bands_usd_per_provider = {
        "azure": (0.02, 0.15),
        "gemini": (0.005, 0.05),
        "cohere": (0.05, 0.35),
        "fireworks": (0.02, 0.15),
    }
    per_provider_cost = {}
    for p in providers:
        lo, hi = cost_bands_usd_per_provider.get(p, (0.01, 0.3))
        scale = calls_per_provider_total / 180.0  # bands calibrated around ~180 calls/provider
        per_provider_cost[p] = {"low_usd": round(lo * scale, 3), "high_usd": round(hi * scale, 3)}
    total_low = round(sum(v["low_usd"] for v in per_provider_cost.values()), 3)
    total_high = round(sum(v["high_usd"] for v in per_provider_cost.values()), 3)

    estimate = {
        "smoke": smoke,
        "n_queries": len(planned),
        "n_providers": len(providers),
        "providers": providers,
        "debias_position": debias,
        "total_planned_api_calls": total_calls,
        "calls_per_provider_total": calls_per_provider_total,
        "per_query": per_query_rows,
        "est_prompt_tokens_per_call_rough": est_prompt_tokens_per_call,
        "cost_estimate_usd": {
            "per_provider": per_provider_cost,
            "total_low": total_low,
            "total_high": total_high,
            "caveat": (
                "Rough order-of-magnitude planning estimate only, based on typical "
                "published per-token rate bands I have not verified against current "
                "live pricing pages for these exact models. Treat as a sanity check, "
                "not an exact prediction. Non-Fireworks providers use max_tokens=4; "
                "Fireworks uses max_tokens=512 (reasoning-model budget) but the "
                "verification smoke test showed only ~20-100 completion tokens "
                "actually consumed for a trivial prompt."
            ),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "smoke" if smoke else "main"
    _atomic_write_json(output_dir / f"ESTIMATE_{suffix}.json", estimate)
    return estimate


def _largest_scc_frac(graph: nx.DiGraph) -> float:
    if graph.number_of_nodes() == 0:
        return 0.0
    sccs = list(nx.strongly_connected_components(graph))
    largest = max((len(s) for s in sccs), default=0)
    return largest / graph.number_of_nodes()


def _load_completed_units(results_path: Path) -> set[str]:
    completed: set[str] = set()
    if not results_path.exists():
        return completed
    with results_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            completed.add(row["unit_key"])
    return completed


def run_pilot(config: dict, output_dir: Path, *, smoke: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_root = output_dir / "cache"
    raw_calls_dir = output_dir / "raw_calls"
    checkpoint_dir = output_dir / "checkpoint"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    raw_calls_dir.mkdir(parents=True, exist_ok=True)

    prompt_template_path = _REPO_ROOT / config["prompt_template_path"]
    prompt_version = _prompt_version(prompt_template_path)
    seed = config["seed"]
    providers = config["providers"]
    repair_methods = config["repair_methods"]
    ndcg_k = config["ndcg_k"]
    debias = config["debias_position"]

    planned = plan_queries(config, smoke=smoke)
    results_path = checkpoint_dir / "pilot_results.jsonl"
    results_writer = FlushWriter(results_path)
    failures_writer = FlushWriter(output_dir / "provider_failures.jsonl")
    completed_units = _load_completed_units(results_path)

    provider_usage_writer = FlushWriter(output_dir / "provider_usage.jsonl")

    n_total_units = len(planned) * (len(providers) + 1) * len(repair_methods)
    n_done_at_start = len(completed_units)
    log.info(
        "Planned %d queries x (%d providers + 1 aggregate) x %d repair methods = %d units "
        "(%d already completed on resume)",
        len(planned), len(providers), len(repair_methods), n_total_units, n_done_at_start,
    )

    try:
        for qi, pq in enumerate(planned):
            log.info(
                "[%d/%d] dataset=%s query_id=%s pool_size=%d",
                qi + 1, len(planned), pq.dataset, pq.query_id, len(pq.pool),
            )
            provider_prefs: dict[str, list[Preference]] = {}

            for provider in providers:
                pairwise_cfg = build_pairwise_config(
                    provider,
                    cache_dir=cache_root / provider,
                    seed=seed,
                    debias=debias,
                    prompt_template_path=prompt_template_path,
                )
                sink = DiskAppendList(
                    raw_calls_dir / f"{provider}_calls.jsonl",
                    dataset=pq.dataset,
                    provider=provider,
                    model=pairwise_cfg.model,
                    prompt_version=prompt_version,
                    seed=seed,
                )
                stats = LLMCallStats()
                cache_query_id = f"{pq.dataset}:{pq.query_id}"
                t0 = time.time()
                try:
                    pairs, metadata = collect_all_pairs(
                        cache_query_id,
                        pq.query_text,
                        pq.pool,
                        config=pairwise_cfg,
                        stats=stats,
                        detail_sink=sink,
                    )
                except Exception as exc:  # noqa: BLE001 - deliberate: log full context, then re-raise
                    failures_writer.write(
                        {
                            "timestamp": time.time(),
                            "dataset": pq.dataset,
                            "query_id": pq.query_id,
                            "provider": provider,
                            "model": pairwise_cfg.model,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    )
                    log.error(
                        "Provider %s FAILED on dataset=%s query_id=%s: %s -- halting "
                        "(per policy: never silently skip/replace/merge a failed provider). "
                        "Restart the same command to resume safely.",
                        provider, pq.dataset, pq.query_id, exc,
                    )
                    raise
                finally:
                    sink.close()
                wall_s = time.time() - t0

                provider_usage_writer.write(
                    {
                        "timestamp": time.time(),
                        "dataset": pq.dataset,
                        "query_id": pq.query_id,
                        "provider": provider,
                        "model": pairwise_cfg.model,
                        "n_pairs": len(pairs),
                        "collect_all_pairs_wall_time_s": wall_s,
                        "llm_stats": stats.summary(),
                        "budget": metadata.get("budget"),
                    }
                )
                if stats.api_calls > 0:
                    non_empty = sum(1 for r in pairs if r[0] and r[1])
                    if non_empty < len(pairs):
                        log.warning(
                            "Provider %s: %d/%d pairs had an empty winner/loser id "
                            "(dataset=%s query_id=%s)",
                            provider, len(pairs) - non_empty, len(pairs), pq.dataset, pq.query_id,
                        )
                provider_prefs[provider] = [Preference(w, l, wt) for w, l, wt in pairs]

            graph_ids = list(providers) + ["aggregate"]
            for graph_id in graph_ids:
                if graph_id == "aggregate":
                    prefs: list[Preference] = []
                    for p in providers:
                        prefs.extend(provider_prefs[p])
                else:
                    prefs = provider_prefs[graph_id]

                graph = build_graph(prefs, aggregation="sum")
                summ = graph_summary(graph)
                scc_frac = _largest_scc_frac(graph)
                preserve_ranking = copeland_ranking(graph)
                ndcg_preserve = ndcg_at_k(preserve_ranking, pq.relevance_map, k=ndcg_k)

                for repair_method in repair_methods:
                    unit_key = f"{pq.dataset}|{pq.query_id}|{graph_id}|{repair_method}"
                    if unit_key in completed_units:
                        continue
                    dag, removed_edges = mwfas_solve(graph, method=repair_method)
                    repair_ranking = copeland_ranking(dag)
                    ndcg_repair = ndcg_at_k(repair_ranking, pq.relevance_map, k=ndcg_k)
                    delta = ndcg_repair - ndcg_preserve
                    row = {
                        "unit_key": unit_key,
                        "dataset": pq.dataset,
                        "query_id": pq.query_id,
                        "graph_id": graph_id,
                        "repair_method": repair_method,
                        "pool_size": len(pq.pool),
                        "n_nodes": summ["n_nodes"],
                        "n_edges": summ["n_edges"],
                        "is_dag_pre_repair": summ["is_dag"],
                        "n_sccs": summ["n_sccs"],
                        "largest_scc_frac": scc_frac,
                        "repair_activated": (not summ["is_dag"]),
                        "n_removed_edges": len(removed_edges),
                        "removed_weight": sum(w for _, _, w in removed_edges),
                        "ndcg_preserve": ndcg_preserve,
                        "ndcg_repair": ndcg_repair,
                        "delta": delta,
                        "seed": seed,
                    }
                    results_writer.write(row)
                    completed_units.add(unit_key)

            _atomic_write_json(
                checkpoint_dir / "progress.json",
                {
                    "timestamp": time.time(),
                    "n_queries_total": len(planned),
                    "n_queries_done": qi + 1,
                    "last_dataset": pq.dataset,
                    "last_query_id": pq.query_id,
                    "n_units_completed": len(completed_units),
                    "n_units_total": n_total_units,
                },
            )
    finally:
        results_writer.close()
        failures_writer.close()
        provider_usage_writer.close()

    return {
        "n_queries": len(planned),
        "n_units_completed": len(completed_units),
        "n_units_total": n_total_units,
        "results_path": str(results_path),
    }


def run_analyze(config: dict, output_dir: Path) -> dict:
    results_path = output_dir / "checkpoint" / "pilot_results.jsonl"
    rows = []
    with results_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    primary_method = config["primary_repair_method"]
    primary_rows = [r for r in rows if r["repair_method"] == primary_method]

    # Row-level (pseudo-replicated across graph_id: multiple graphs per
    # query) -- exploratory only, mirrors the repo-scale analysis's own
    # row-level-vs-query-level distinction.
    row_level_records = [
        PreserveRepairRecord(
            dataset=r["dataset"],
            query_id=f"{r['query_id']}::{r['graph_id']}",
            preserve_metric=r["ndcg_preserve"],
            repair_metric=r["ndcg_repair"],
        )
        for r in primary_rows
    ]

    # Query-level (recommended): collapse across graph_id (providers +
    # aggregate) per (dataset, query_id) via the mean, matching the
    # repository-scale analysis's query_level_headroom() convention so the
    # two headroom figures are directly comparable.
    by_query: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in primary_rows:
        by_query[(r["dataset"], r["query_id"])].append(r)
    query_level_records = []
    for (dataset, query_id), group in sorted(by_query.items()):
        mean_preserve = sum(g["ndcg_preserve"] for g in group) / len(group)
        mean_repair = sum(g["ndcg_repair"] for g in group) / len(group)
        query_level_records.append(
            PreserveRepairRecord(
                dataset=dataset, query_id=query_id,
                preserve_metric=mean_preserve, repair_metric=mean_repair,
            )
        )

    row_level_result = compute_oracle_headroom(row_level_records, bootstrap_seed=config["seed"])
    query_level_result = compute_oracle_headroom(query_level_records, bootstrap_seed=config["seed"])
    go_no_go = evaluate_go_no_go(query_level_result)

    repo_scale = config["repo_scale_comparison"]
    comparison = {
        "pilot_query_level_headroom": query_level_result.headroom_vs_best_baseline,
        "pilot_query_level_headroom_ci": [
            query_level_result.headroom_ci.lower, query_level_result.headroom_ci.upper,
        ],
        "pilot_n_queries": query_level_result.n_queries,
        "repo_scale_classical_headroom": repo_scale["classical_graph_oracle_headroom"],
        "repo_scale_classical_headroom_ci": repo_scale["classical_graph_oracle_headroom_ci"],
        "repo_scale_n_queries": repo_scale["classical_graph_n_queries"],
        "ratio_pilot_to_classical": (
            query_level_result.headroom_vs_best_baseline
            / repo_scale["classical_graph_oracle_headroom"]
            if repo_scale["classical_graph_oracle_headroom"] else None
        ),
        "minimum_meaningful_effect_mde": repo_scale["minimum_meaningful_effect_mde"],
        "pilot_headroom_exceeds_mde": (
            query_level_result.headroom_ci.lower > repo_scale["minimum_meaningful_effect_mde"]
        ),
    }

    n_beneficial = sum(1 for r in primary_rows if r["delta"] > 0)
    n_harmful = sum(1 for r in primary_rows if r["delta"] < 0)
    n_neutral = sum(1 for r in primary_rows if r["delta"] == 0)
    n_activated = sum(1 for r in primary_rows if r["repair_activated"])

    analysis = {
        "n_rows_all_methods": len(rows),
        "n_rows_primary_method": len(primary_rows),
        "primary_repair_method": primary_method,
        "repair_activation_rate": n_activated / len(primary_rows) if primary_rows else None,
        "n_beneficial": n_beneficial,
        "n_harmful": n_harmful,
        "n_neutral": n_neutral,
        "frac_beneficial": n_beneficial / len(primary_rows) if primary_rows else None,
        "frac_harmful": n_harmful / len(primary_rows) if primary_rows else None,
        "frac_neutral": n_neutral / len(primary_rows) if primary_rows else None,
        "row_level_oracle_headroom": row_level_result.to_dict(),
        "query_level_oracle_headroom": query_level_result.to_dict(),
        "go_no_go": {
            "decision": go_no_go.decision,
            "rationale": go_no_go.rationale,
        },
        "comparison_to_repo_scale": comparison,
    }
    _atomic_write_json(output_dir / "ANALYSIS.json", analysis)
    return analysis


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["estimate", "smoke", "run", "analyze"], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=_REPO_ROOT / "configs/multi_provider_repair_pilot_v1.json"
    )
    args = parser.parse_args()
    config = load_config(args.config)

    run_tag = f"{args.mode}_{int(time.time())}"
    log_path = _setup_logging(args.output_dir, run_tag)
    log.info("Logging to %s", log_path)

    if args.mode == "estimate":
        est = run_estimate(config, args.output_dir, smoke=False)
        print(json.dumps(est, indent=2))
    elif args.mode == "smoke":
        est = run_estimate(config, args.output_dir, smoke=True)
        print(json.dumps(est, indent=2))
        result = run_pilot(config, args.output_dir, smoke=True)
        print(json.dumps(result, indent=2))
    elif args.mode == "run":
        result = run_pilot(config, args.output_dir, smoke=False)
        print(json.dumps(result, indent=2))
    else:
        analysis = run_analyze(config, args.output_dir)
        print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
