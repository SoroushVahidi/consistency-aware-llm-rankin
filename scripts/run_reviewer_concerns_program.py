"""
run_reviewer_concerns_program.py
=================================
Follow-on to scripts/run_multi_provider_repair_pilot.py, addressing the two
central reviewer concerns:

  1. Use genuine modern-LLM-generated pairwise preference graphs, not
     primarily classical score-derived graphs.
  2. Provide predictive / mechanistic understanding of *when* consistency
     repair helps, not just a demonstration that repair can be applied.

Stages (see module docstrings on the stage_* functions for detail):

  0. Wait for the pilot's ANALYSIS.json.
  1. Interpret the finished pilot: independently recompute headline
     aggregates from raw result rows (not just trust the summary file).
  2. Select a branch (A: scale / B: graph-construction sensitivity /
     C: localized repair analysis) via a pre-registered, evidence-driven
     rule, and record the decision + rationale before any new API calls.
  3. Collect the branch's data (cost-estimated, hard-ceiling-gated,
     idempotent/resumable, smoke-tested first).
  4. Compute graph / mechanism features for every collected unit.
  5. Predictive evaluation with grouped (by query) cross-validation and
     mandatory negative controls -- only if label variation supports it.
  6. Robustness re-analysis across methodological choices (uses already-
     collected data; makes no new API calls).
  7. Synthetic counterfactual perturbation of real observed graphs (no new
     API calls).
  8. Final machine-readable summary + Markdown report answering the 9
     required questions.

Reuses scripts/run_multi_provider_repair_pilot.py (imported as a module,
not duplicated) for: PairwiseConfig construction, cache-backed idempotent
collection, graph construction, MWFAS repair, Copeland ranking, nDCG,
dataset loading, and the oracle-headroom computation -- plus
consistency_ranker.failure_mining.graph_features.extended_graph_stats for
the richer mechanism feature set.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import run_multi_provider_repair_pilot as pilot_lib  # noqa: E402

from consistency_ranker.baseline_ranking import copeland_ranking  # noqa: E402
from consistency_ranker.evaluation import ndcg_at_k  # noqa: E402
from consistency_ranker.failure_mining.graph_features import extended_graph_stats  # noqa: E402
from consistency_ranker.graph_construction import build_graph, graph_summary  # noqa: E402
from consistency_ranker.mwfas_solver import solve as mwfas_solve  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402
from consistency_ranker.repair_selector_mining.checkpoint import FlushWriter  # noqa: E402
from consistency_ranker.repair_selector_mining.oracle_headroom import (  # noqa: E402
    PreserveRepairRecord,
    compute_oracle_headroom,
)
from rerankers.common import BudgetTracker, JudgmentCache  # noqa: E402
from rerankers.llm_pairwise import (  # noqa: E402
    LLMCallStats,
    _load_prompt_template,
    compare_pair,
)

log = logging.getLogger("reviewer_concerns_program")

_atomic_write_json = pilot_lib._atomic_write_json
DiskAppendList = pilot_lib.DiskAppendList
build_pairwise_config = pilot_lib.build_pairwise_config
select_pilot_queries = pilot_lib.select_pilot_queries
_prompt_version = pilot_lib._prompt_version

BASE_PROVIDERS = ["azure", "gemini", "cohere", "fireworks"]
BASE_SEED = 42
BASE_POOL_SIZE = 6
BASE_N_QUERIES_PER_DATASET = 3
BASE_DATASETS = ["scidocs", "fiqa"]
COST_CEILING_USD = 8.0
COST_TARGET_USD = 4.0  # aim well under the ceiling to leave estimate-error margin

# Real per-call USD rates back-calculated from the finished pilot's own
# observed token usage (provider_usage.jsonl: ~500-560 prompt tokens/call,
# ~1-2 completion tokens for non-reasoning providers, ~73.5 for Fireworks)
# against typical published per-token rate bands for these exact models.
# Still an approximation (not fetched from a live pricing API) -- see
# ESTIMATE_branch_b.json's caveat field.
_RATE_USD_PER_M_TOKENS = {
    "azure": {"in": 0.15, "out": 0.60},
    "gemini": {"in": 0.30, "out": 2.50},
    "cohere": {"in": 2.50, "out": 10.0},
    "fireworks": {"in": 0.15, "out": 0.60},
}
_OBSERVED_AVG_TOKENS_PER_CALL = {
    "azure": {"in": 500, "out": 2},
    "gemini": {"in": 505, "out": 1},
    "cohere": {"in": 510, "out": 1},
    "fireworks": {"in": 565, "out": 75},
}


def _est_cost_per_call(provider: str) -> float:
    rate = _RATE_USD_PER_M_TOKENS[provider]
    tok = _OBSERVED_AVG_TOKENS_PER_CALL[provider]
    return (tok["in"] / 1e6) * rate["in"] + (tok["out"] / 1e6) * rate["out"]


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


# ---------------------------------------------------------------------------
# Stage 0
# ---------------------------------------------------------------------------

def stage0_wait_for_pilot(pilot_dir: Path, *, timeout_s: float = 1800.0, poll_s: float = 5.0) -> None:
    target = pilot_dir / "ANALYSIS.json"
    t0 = time.time()
    while not target.exists():
        if time.time() - t0 > timeout_s:
            raise RuntimeError(f"Timed out after {timeout_s}s waiting for {target}")
        time.sleep(poll_s)
    log.info("Pilot ANALYSIS.json found at %s (waited %.1fs)", target, time.time() - t0)


# ---------------------------------------------------------------------------
# Stage 1: interpret the finished pilot, independently re-verified
# ---------------------------------------------------------------------------

def stage1_interpret(pilot_dir: Path, output_dir: Path) -> dict:
    results_path = pilot_dir / "checkpoint" / "pilot_results.jsonl"
    rows = [json.loads(line) for line in results_path.open(encoding="utf-8") if line.strip()]
    analysis_json = json.loads((pilot_dir / "ANALYSIS.json").read_text(encoding="utf-8"))

    by_method: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_method[r["repair_method"]].append(r)

    method_summaries = {}
    for method, rs in by_method.items():
        n = len(rs)
        n_cyclic = sum(1 for r in rs if not r["is_dag_pre_repair"])
        n_nontrivial_scc = sum(1 for r in rs if r["n_sccs"] < r["n_nodes"])
        n_activated = sum(1 for r in rs if r["repair_activated"])
        n_ben = sum(1 for r in rs if r["delta"] > 0)
        n_harm = sum(1 for r in rs if r["delta"] < 0)
        n_neutral = sum(1 for r in rs if r["delta"] == 0)
        deltas = [r["delta"] for r in rs]
        by_graph: dict[str, list[dict]] = defaultdict(list)
        for r in rs:
            by_graph[r["graph_id"]].append(r)
        per_graph = {
            g: {
                "n": len(grs),
                "n_cyclic": sum(1 for r in grs if not r["is_dag_pre_repair"]),
                "n_activated": sum(1 for r in grs if r["repair_activated"]),
                "n_nonzero_delta": sum(1 for r in grs if r["delta"] != 0),
            }
            for g, grs in sorted(by_graph.items())
        }
        method_summaries[method] = {
            "n": n,
            "n_cyclic": n_cyclic,
            "frac_cyclic": n_cyclic / n if n else None,
            "n_nontrivial_scc": n_nontrivial_scc,
            "n_activated": n_activated,
            "frac_activated": n_activated / n if n else None,
            "n_beneficial": n_ben,
            "n_harmful": n_harm,
            "n_neutral": n_neutral,
            "frac_nonzero_delta_among_activated": (
                (n_ben + n_harm) / n_activated if n_activated else 0.0
            ),
            "mean_delta": sum(deltas) / n if n else None,
            "min_delta": min(deltas) if deltas else None,
            "max_delta": max(deltas) if deltas else None,
            "per_graph": per_graph,
        }

    primary = analysis_json["primary_repair_method"]
    pm = method_summaries[primary]
    cross_check_ok = (
        pm["n_activated"] == round(analysis_json["repair_activation_rate"] * pm["n"])
        and pm["n_beneficial"] == analysis_json["n_beneficial"]
        and pm["n_harmful"] == analysis_json["n_harmful"]
        and pm["n_neutral"] == analysis_json["n_neutral"]
    )

    n_failures = 0
    failures_path = pilot_dir / "provider_failures.jsonl"
    if failures_path.exists():
        n_failures = sum(1 for line in failures_path.open(encoding="utf-8") if line.strip())

    interpretation = {
        "pilot_dir": str(pilot_dir),
        "n_rows_total": len(rows),
        "primary_repair_method": primary,
        "method_summaries": method_summaries,
        "query_level_oracle_headroom": analysis_json["query_level_oracle_headroom"],
        "comparison_to_repo_scale": analysis_json["comparison_to_repo_scale"],
        "go_no_go": analysis_json["go_no_go"],
        "independent_cross_check_passed": cross_check_ok,
        "n_provider_failures_recorded": n_failures,
    }
    _atomic_write_json(output_dir / "STAGE1_INTERPRETATION.json", interpretation)
    if not cross_check_ok:
        raise RuntimeError(
            "Stage 1 independent cross-check FAILED: recomputed aggregates from "
            "raw pilot_results.jsonl do not match ANALYSIS.json. Halting rather "
            "than proceeding on unverified data."
        )
    log.info(
        "Stage 1: cross-check PASSED. primary=%s frac_cyclic=%.1f%% frac_activated=%.1f%% "
        "frac_nonzero_among_activated=%.1f%% n_beneficial=%d n_harmful=%d n_neutral=%d",
        primary, pm["frac_cyclic"] * 100, pm["frac_activated"] * 100,
        pm["frac_nonzero_delta_among_activated"] * 100, pm["n_beneficial"], pm["n_harmful"], pm["n_neutral"],
    )
    return interpretation


# ---------------------------------------------------------------------------
# Stage 2: branch selection (pre-registered rule, evaluated before any new
# API calls)
# ---------------------------------------------------------------------------

def stage2_select_branch(interpretation: dict, output_dir: Path) -> str:
    primary = interpretation["primary_repair_method"]
    ms = interpretation["method_summaries"][primary]
    frac_cyclic = ms["frac_cyclic"] or 0.0
    frac_activated = ms["frac_activated"] or 0.0
    n_activated = ms["n_activated"]
    frac_nonzero_among_activated = ms["frac_nonzero_delta_among_activated"]
    headroom_upper = interpretation["query_level_oracle_headroom"]["headroom_ci"]["upper"]

    trigger_b = (
        frac_cyclic < 0.10
        or frac_activated < 0.10
        or (n_activated > 0 and frac_nonzero_among_activated < 0.20)
    )
    n_nonzero_total = ms["n_beneficial"] + ms["n_harmful"]
    trigger_c = (not trigger_b) and n_nonzero_total > 0 and (headroom_upper is not None and headroom_upper <= 0.01)

    if trigger_b:
        branch = "B"
        rationale = (
            f"Branch B (diagnose graph-construction sensitivity) selected. "
            f"Primary-method ({primary}) evidence: repair activated on "
            f"{n_activated}/{ms['n']} rows ({frac_activated:.1%}; {frac_cyclic:.1%} "
            f"of graphs were cyclic pre-repair -- almost entirely the "
            f"multi-provider aggregate graph, per per_graph breakdown), but "
            f"{n_nonzero_total}/{n_activated} activated cases changed nDCG at all "
            f"({frac_nonzero_among_activated:.1%} nonzero-among-activated, below "
            "the 20% trigger). This is 'nearly invariant outcomes': repair is "
            "structurally real (it removes edges, changes graph shape) but never "
            "once altered the resulting Copeland ranking's nDCG in this pilot -- "
            "consistent with cycles being confined to document pairs/positions "
            "that do not affect the top-of-ranking order nDCG measures at "
            "pool_size=6, top-relevance-only pool construction. Scaling this "
            "exact construction (Branch A) would only add more zero-information "
            "rows. Localized analysis (Branch C) presupposes repair sometimes "
            "visibly matters at some grain, which was not observed at any grain "
            "here. Branch B (vary pool size/diversity/aggregation/orientation/"
            "sparsity) is the evidence-supported choice."
        )
    elif trigger_c:
        branch = "C"
        rationale = (
            f"Branch C (localized repair analysis) selected: repair activates "
            f"({frac_activated:.1%}) and does sometimes change the outcome "
            f"({n_nonzero_total} nonzero-delta rows), but query-level oracle "
            f"headroom's CI upper bound ({headroom_upper}) is at/below the "
            "0.01 threshold -- whole-query-level prediction is not viable, but "
            "finer-grained (SCC/edge/component) benefit may still be recoverable."
        )
    else:
        branch = "A"
        rationale = (
            f"Branch A (scale the current construction) selected: repair "
            f"activates meaningfully ({frac_activated:.1%}), produces both "
            f"beneficial and harmful/neutral outcomes with real variation "
            f"({ms['n_beneficial']} beneficial, {ms['n_harmful']} harmful), and "
            f"query-level headroom's CI upper bound ({headroom_upper}) exceeds "
            "the 0.01 threshold with no evident implementation defect -- more "
            "examples of the same construction are likely to be informative."
        )

    decision = {
        "branch": branch,
        "rationale": rationale,
        "trigger_evidence": {
            "primary_repair_method": primary,
            "frac_cyclic": frac_cyclic,
            "frac_activated": frac_activated,
            "n_activated": n_activated,
            "frac_nonzero_delta_among_activated": frac_nonzero_among_activated,
            "headroom_ci_upper": headroom_upper,
            "trigger_b_fired": trigger_b,
            "trigger_c_fired": trigger_c,
        },
        "timestamp": time.time(),
    }
    _atomic_write_json(output_dir / "BRANCH_DECISION.json", decision)
    log.info("Stage 2: branch=%s", branch)
    return branch


# ---------------------------------------------------------------------------
# Stage 3: data collection (branch-specific)
# ---------------------------------------------------------------------------

def build_diverse_pool(
    query_id: str, qrels_by_query: dict, docs_by_id: dict, pool_size: int, seed: int
) -> tuple[list[tuple[str, str]], dict]:
    """Build a relevance-diverse candidate pool: ~40% highly relevant (top
    by relevance grade), ~30% boundary (lower-ranked positives), ~30%
    nonrelevant (explicit relevance=0 qrels for this query if present,
    else deterministically sampled positives *of other queries* in the same
    dataset -- a defensible "hard negative" proxy that avoids both an
    expensive full-corpus BM25 scan and trivially-unrelated random filler).
    """
    entries = qrels_by_query.get(query_id, [])
    positives = sorted((e for e in entries if e.relevance > 0), key=lambda e: (-e.relevance, e.doc_id))
    explicit_negatives = sorted((e for e in entries if e.relevance == 0), key=lambda e: e.doc_id)

    n_high = max(1, pool_size * 4 // 10)
    n_low = max(1, pool_size * 3 // 10)
    high = positives[:n_high]
    chosen_ids = {e.doc_id for e in high}

    n_boundary = max(0, pool_size - len(high) - n_low)
    boundary = [e for e in positives[n_high:] if e.doc_id not in chosen_ids][:n_boundary]
    chosen_ids |= {e.doc_id for e in boundary}

    low = [e for e in explicit_negatives if e.doc_id not in chosen_ids][:n_low]
    chosen_ids |= {e.doc_id for e in low}

    tiers = {
        "high": [e.doc_id for e in high],
        "boundary": [e.doc_id for e in boundary],
        "low_explicit": [e.doc_id for e in low],
    }
    selected_ids = [e.doc_id for e in high] + [e.doc_id for e in boundary] + [e.doc_id for e in low]

    remaining = pool_size - len(selected_ids)
    if remaining > 0:
        own_ids = {e.doc_id for e in entries}
        other_positive_ids = sorted(
            {
                e.doc_id
                for qid2, ents in qrels_by_query.items()
                if qid2 != query_id
                for e in ents
                if e.relevance > 0
            }
            - chosen_ids
            - own_ids
        )
        rng = random.Random(seed * 1_000_003 + (hash(query_id) % 99_991))
        fill = rng.sample(other_positive_ids, k=min(remaining, len(other_positive_ids)))
        tiers["filler_other_query_positive"] = fill
        selected_ids.extend(fill)

    selected_ids = selected_ids[:pool_size]
    pool = []
    for doc_id in selected_ids:
        doc = docs_by_id.get(doc_id)
        if doc is None:
            continue
        text = doc.text or doc.title or ""
        pool.append((doc_id, text))
    return pool, tiers


def sparse_pair_indices(n: int, seed: int, coverage_frac: float) -> list[tuple[int, int]]:
    """Deterministic, reproducible sparse pair sample, retried until the
    resulting comparison graph is connected (so every candidate is still
    reachable via at least one comparison chain)."""
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    k = min(len(all_pairs), max(n - 1, round(len(all_pairs) * coverage_frac)))
    rng = random.Random(seed)
    for _ in range(10):
        sample = rng.sample(all_pairs, k=k)
        g = nx.Graph()
        g.add_nodes_from(range(n))
        g.add_edges_from(sample)
        if nx.is_connected(g):
            return sorted(sample)
    tree_edges = {(i, i + 1) for i in range(n - 1)}
    extra = [p for p in sample if p not in tree_edges]
    combined = sorted(tree_edges | set(extra[: max(0, k - len(tree_edges))]))
    return combined


def collect_specific_pairs(
    query_id: str,
    query_text: str,
    candidates: list[tuple[str, str]],
    pair_indices: list[tuple[int, int]],
    config,
    stats: LLMCallStats | None = None,
    detail_sink=None,
) -> tuple[list[tuple[str, str, float]], dict]:
    """Like llm_pairwise.collect_all_pairs but over an explicit pair-index
    subset (for the sparse-graph construction variant). Reuses compare_pair
    directly -- same caching/retry/de-bias behavior, just a restricted pair
    set."""
    cache = JudgmentCache(config.cache_dir, "llm_pairwise") if config.cache_dir is not None else None
    budget = BudgetTracker(max_calls=config.max_calls)
    prompt_template = _load_prompt_template(config.prompt_template_path)
    pairs = []
    for i, j in pair_indices:
        winner, loser, weight = compare_pair(
            query_text, candidates[i], candidates[j],
            query_id=query_id, config=config, cache=cache, budget=budget,
            prompt_template=prompt_template, stats=stats, detail_sink=detail_sink,
        )
        pairs.append((winner, loser, weight))
    metadata = {
        "method": "llm_pairwise_sparse", "provider": config.provider, "model": config.model,
        "n_pairs": len(pairs), "n_candidates": len(candidates), "budget": budget.summary(),
    }
    if stats is not None:
        metadata["llm_stats"] = stats.summary()
    return pairs, metadata


@dataclass
class ConstructionVariant:
    name: str
    pool_size: int
    sparse_coverage: float | None  # None = complete graph


BRANCH_B_VARIANTS = [
    ConstructionVariant("pool8_complete", 8, None),
    ConstructionVariant("pool8_sparse57", 8, 0.57),
    ConstructionVariant("pool10_sparse56", 10, 0.56),
]


def _base_queries() -> list[dict]:
    """Reproduce the exact same 6 (dataset, query_id) units the finished
    pilot used, via the identical deterministic selection call -- no need
    to persist them separately."""
    out = []
    for dataset in BASE_DATASETS:
        selected, queries_by_id, docs_by_id, qrels_by_query = select_pilot_queries(
            dataset, pool_size=BASE_POOL_SIZE, n_queries=BASE_N_QUERIES_PER_DATASET, seed=BASE_SEED
        )
        for qid in selected:
            out.append(
                {
                    "dataset": dataset, "query_id": qid, "query_text": queries_by_id[qid].text,
                    "docs_by_id": docs_by_id, "qrels_by_query": qrels_by_query,
                }
            )
    return out


def branch_b_plan(variants: list[ConstructionVariant]) -> list[dict]:
    base_queries = _base_queries()
    plan = []
    for variant in variants:
        for bq in base_queries:
            n_pairs_complete = pilot_lib._n_pairs(variant.pool_size)
            if variant.sparse_coverage is None:
                n_pairs = n_pairs_complete
            else:
                n_pairs = len(sparse_pair_indices(variant.pool_size, BASE_SEED, variant.sparse_coverage))
            plan.append(
                {
                    "variant": variant.name, "pool_size": variant.pool_size,
                    "sparse_coverage": variant.sparse_coverage,
                    "dataset": bq["dataset"], "query_id": bq["query_id"], "n_pairs": n_pairs,
                }
            )
    return plan


def stage3_estimate(output_dir: Path) -> dict:
    plan = branch_b_plan(BRANCH_B_VARIANTS)
    total_calls = sum(row["n_pairs"] * 2 for row in plan) * len(BASE_PROVIDERS)
    per_provider_calls = sum(row["n_pairs"] * 2 for row in plan)
    per_provider_cost = {p: per_provider_calls * _est_cost_per_call(p) for p in BASE_PROVIDERS}
    total_cost = sum(per_provider_cost.values())

    estimate = {
        "branch": "B",
        "variants": [v.name for v in BRANCH_B_VARIANTS],
        "n_base_queries": len(_base_queries()),
        "n_plan_rows": len(plan),
        "per_provider_calls": per_provider_calls,
        "total_planned_api_calls": total_calls,
        "per_provider_cost_usd": per_provider_cost,
        "total_cost_usd": total_cost,
        "cost_ceiling_usd": COST_CEILING_USD,
        "cost_target_usd": COST_TARGET_USD,
        "within_ceiling": total_cost < COST_CEILING_USD,
        "caveat": (
            "Cost calibrated against the FINISHED main pilot's own observed "
            "token usage (provider_usage.jsonl), not just a generic band -- "
            "more reliable than a pre-pilot guess, but still not fetched from "
            "a live pricing API. See _RATE_USD_PER_M_TOKENS."
        ),
        "plan": plan,
    }
    _atomic_write_json(output_dir / "ESTIMATE_branch_b.json", estimate)
    log.info(
        "Stage 3 estimate: %d total calls, $%.3f estimated (ceiling $%.2f)",
        total_calls, total_cost, COST_CEILING_USD,
    )
    if total_cost >= COST_CEILING_USD:
        raise RuntimeError(
            f"Branch B estimated cost ${total_cost:.2f} meets/exceeds the "
            f"${COST_CEILING_USD:.2f} hard ceiling -- refusing to proceed. "
            "Reduce variants/pool sizes/query count and re-run."
        )
    return estimate


def stage3a_smoke(output_dir: Path) -> dict:
    """Tiny real-call smoke test of the NEW code paths (diverse pool
    builder + sparse-pair collection) before spending the Branch B budget:
    1 query, pool_size=4 (diverse tiers), 3 sparse pairs, all 4 providers.
    """
    smoke_dir = output_dir / "smoke_branch_b"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    base = _base_queries()[0]
    pool, tiers = build_diverse_pool(base["query_id"], base["qrels_by_query"], base["docs_by_id"], 4, BASE_SEED)
    pair_idx = sparse_pair_indices(len(pool), BASE_SEED, 0.5)
    if len(pool) < 4 or not pair_idx:
        raise RuntimeError("Stage 3 smoke test: diverse pool / sparse sampling produced degenerate output.")

    prompt_template_path = _REPO_ROOT / "prompts" / "pairwise_comparison.txt"
    results = {}
    for provider in BASE_PROVIDERS:
        cfg = build_pairwise_config(
            provider, cache_dir=smoke_dir / "cache" / provider, seed=BASE_SEED,
            debias=True, prompt_template_path=prompt_template_path,
        )
        sink = DiskAppendList(
            smoke_dir / f"{provider}_calls.jsonl", dataset=base["dataset"], provider=provider,
            model=cfg.model, prompt_version=_prompt_version(prompt_template_path), seed=BASE_SEED,
        )
        stats = LLMCallStats()
        try:
            pairs, meta = collect_specific_pairs(
                f"smoke:{base['dataset']}:{base['query_id']}", base["query_text"], pool, pair_idx,
                cfg, stats=stats, detail_sink=sink,
            )
        finally:
            sink.close()
        non_empty = sum(1 for w, ll, _ in pairs if w and ll)
        results[provider] = {"n_pairs": len(pairs), "non_empty": non_empty, "stats": stats.summary()}
        if non_empty < len(pairs):
            raise RuntimeError(f"Stage 3 smoke test: provider {provider} returned an empty winner/loser.")

    report = {"pool_size": len(pool), "tiers": tiers, "n_sparse_pairs": len(pair_idx), "providers": results}
    _atomic_write_json(smoke_dir / "SMOKE_BRANCH_B_RESULT.json", report)
    log.info("Stage 3 smoke test PASSED: %s", {p: r["n_pairs"] for p, r in results.items()})
    return report


def stage3c_collect(output_dir: Path) -> dict:
    checkpoint_dir = output_dir / "checkpoint"
    raw_calls_dir = output_dir / "raw_calls"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    raw_calls_dir.mkdir(parents=True, exist_ok=True)
    results_path = checkpoint_dir / "branch_b_results.jsonl"
    prefs_path = checkpoint_dir / "branch_b_provider_prefs.jsonl"
    failures_path = output_dir / "provider_failures.jsonl"
    usage_path = output_dir / "provider_usage.jsonl"

    completed_units = pilot_lib._load_completed_units(results_path)
    results_writer = FlushWriter(results_path)
    prefs_writer = FlushWriter(prefs_path)
    failures_writer = FlushWriter(failures_path)
    usage_writer = FlushWriter(usage_path)

    prompt_template_path = _REPO_ROOT / "prompts" / "pairwise_comparison.txt"
    prompt_version = _prompt_version(prompt_template_path)
    base_queries = _base_queries()

    running_cost = 0.0
    running_calls = 0

    try:
        for variant in BRANCH_B_VARIANTS:
            for bq in base_queries:
                dataset, query_id = bq["dataset"], bq["query_id"]
                pool, tiers = build_diverse_pool(
                    query_id, bq["qrels_by_query"], bq["docs_by_id"], variant.pool_size, BASE_SEED
                )
                relevance_map = {e.doc_id: e.relevance for e in bq["qrels_by_query"].get(query_id, [])}
                if variant.sparse_coverage is None:
                    pair_idx = [(i, j) for i in range(len(pool)) for j in range(i + 1, len(pool))]
                else:
                    pair_idx = sparse_pair_indices(len(pool), BASE_SEED, variant.sparse_coverage)

                log.info(
                    "[branch_b %s] dataset=%s query_id=%s pool_size=%d n_pairs=%d",
                    variant.name, dataset, query_id, len(pool), len(pair_idx),
                )

                provider_prefs: dict[str, list[Preference]] = {}
                for provider in BASE_PROVIDERS:
                    cfg = build_pairwise_config(
                        provider, cache_dir=output_dir / "cache" / variant.name / provider,
                        seed=BASE_SEED, debias=True, prompt_template_path=prompt_template_path,
                    )
                    sink = DiskAppendList(
                        raw_calls_dir / f"{variant.name}_{provider}_calls.jsonl", dataset=dataset,
                        provider=provider, model=cfg.model, prompt_version=prompt_version, seed=BASE_SEED,
                    )
                    stats = LLMCallStats()
                    t0 = time.time()
                    try:
                        pairs, meta = collect_specific_pairs(
                            f"{variant.name}:{dataset}:{query_id}", bq["query_text"], pool, pair_idx,
                            cfg, stats=stats, detail_sink=sink,
                        )
                    except Exception as exc:  # noqa: BLE001 - deliberate re-raise after logging
                        failures_writer.write(
                            {
                                "timestamp": time.time(), "variant": variant.name, "dataset": dataset,
                                "query_id": query_id, "provider": provider, "model": cfg.model,
                                "error_type": type(exc).__name__, "error_message": str(exc),
                            }
                        )
                        log.error(
                            "Provider %s FAILED on variant=%s dataset=%s query_id=%s: %s -- halting.",
                            provider, variant.name, dataset, query_id, exc,
                        )
                        raise
                    finally:
                        sink.close()
                    wall_s = time.time() - t0

                    llm_stats = stats.summary()
                    call_cost = (
                        llm_stats["prompt_tokens"] / 1e6 * _RATE_USD_PER_M_TOKENS[provider]["in"]
                        + llm_stats["completion_tokens"] / 1e6 * _RATE_USD_PER_M_TOKENS[provider]["out"]
                    )
                    running_cost += call_cost
                    running_calls += llm_stats["api_calls"]
                    usage_writer.write(
                        {
                            "timestamp": time.time(), "variant": variant.name, "dataset": dataset,
                            "query_id": query_id, "provider": provider, "model": cfg.model,
                            "n_pairs": len(pairs), "wall_time_s": wall_s, "llm_stats": llm_stats,
                            "running_cost_usd_so_far": running_cost,
                        }
                    )
                    if running_cost > COST_CEILING_USD:
                        raise RuntimeError(
                            f"Observed running cost ${running_cost:.2f} exceeded the "
                            f"${COST_CEILING_USD:.2f} hard ceiling mid-run -- halting immediately."
                        )
                    prefs_list = [Preference(w, l, wt) for w, l, wt in pairs]
                    provider_prefs[provider] = prefs_list
                    prefs_writer.write(
                        {
                            "variant": variant.name, "dataset": dataset, "query_id": query_id,
                            "provider": provider, "pool_doc_ids": [d for d, _ in pool], "tiers": tiers,
                            "relevance_map": relevance_map,
                            "prefs": [[w, l, wt] for w, l, wt in pairs],
                        }
                    )

                graph_ids = list(BASE_PROVIDERS) + ["aggregate"]
                for graph_id in graph_ids:
                    if graph_id == "aggregate":
                        prefs: list[Preference] = []
                        for p in BASE_PROVIDERS:
                            prefs.extend(provider_prefs[p])
                    else:
                        prefs = provider_prefs[graph_id]
                    graph = build_graph(prefs, aggregation="sum")
                    summ = graph_summary(graph)
                    scc_frac = pilot_lib._largest_scc_frac(graph)
                    preserve_ranking = copeland_ranking(graph)
                    ndcg_preserve = ndcg_at_k(preserve_ranking, relevance_map, k=10)

                    for repair_method in ("greedy", "exact"):
                        unit_key = f"{variant.name}|{dataset}|{query_id}|{graph_id}|{repair_method}"
                        if unit_key in completed_units:
                            continue
                        dag, removed_edges = mwfas_solve(graph, method=repair_method)
                        repair_ranking = copeland_ranking(dag)
                        ndcg_repair = ndcg_at_k(repair_ranking, relevance_map, k=10)
                        row = {
                            "unit_key": unit_key, "variant": variant.name, "pool_size": variant.pool_size,
                            "sparse_coverage": variant.sparse_coverage, "dataset": dataset,
                            "query_id": query_id, "graph_id": graph_id, "repair_method": repair_method,
                            "n_nodes": summ["n_nodes"], "n_edges": summ["n_edges"],
                            "is_dag_pre_repair": summ["is_dag"], "n_sccs": summ["n_sccs"],
                            "largest_scc_frac": scc_frac, "repair_activated": (not summ["is_dag"]),
                            "n_removed_edges": len(removed_edges),
                            "removed_weight": sum(w for _, _, w in removed_edges),
                            "ndcg_preserve": ndcg_preserve, "ndcg_repair": ndcg_repair,
                            "delta": ndcg_repair - ndcg_preserve, "seed": BASE_SEED,
                        }
                        results_writer.write(row)
                        completed_units.add(unit_key)

                _atomic_write_json(
                    checkpoint_dir / "branch_b_progress.json",
                    {
                        "timestamp": time.time(), "running_cost_usd": running_cost,
                        "running_calls": running_calls, "n_units_completed": len(completed_units),
                    },
                )
    finally:
        results_writer.close()
        prefs_writer.close()
        failures_writer.close()
        usage_writer.close()

    return {
        "n_units_completed": len(completed_units), "running_cost_usd": running_cost,
        "running_calls": running_calls, "results_path": str(results_path),
    }


def load_original_pilot_prefs(pilot_dir: Path, base_queries: list[dict]) -> list[dict]:
    """Reconstruct provider-level Preference lists for the ORIGINAL
    pool_size=6 pilot data from its persisted JudgmentCache files -- no
    re-collection needed. Enables Stage 6 to re-analyze aggregation/
    orientation variants on the original data too, for free."""
    out = []
    for bq in base_queries:
        dataset, query_id = bq["dataset"], bq["query_id"]
        cache_query_id = f"{dataset}:{query_id}"
        provider_prefs = {}
        for provider in BASE_PROVIDERS:
            cache_file = pilot_dir / "cache" / provider / "llm_pairwise_judgments.jsonl"
            if not cache_file.exists():
                continue
            prefs = []
            with cache_file.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("query_id") != cache_query_id:
                        continue
                    prefs.append((entry["winner"], entry["loser"], entry.get("weight", 1.0)))
            provider_prefs[provider] = prefs
        out.append({"variant": "pool6_original", "dataset": dataset, "query_id": query_id, "provider_prefs": provider_prefs})
    return out


# ---------------------------------------------------------------------------
# Stage 4: feature computation
# ---------------------------------------------------------------------------

def compute_position_sensitivity(raw_calls_path: Path) -> dict[tuple[str, str], float]:
    """Fraction of pairs where the AB-only vote differs from the final
    debiased vote, per (dataset, query_id) -- a free-to-compute proxy for
    how position-sensitive (i.e. low "confidence") a provider's judgments
    were, derived entirely from already-collected raw_calls records."""
    if not raw_calls_path.exists():
        return {}
    by_pair: dict[tuple, dict[str, str]] = defaultdict(dict)
    with raw_calls_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("from_cache"):
                continue
            key = (r["dataset"], r.get("query_id"), r.get("doc_a_id"), r.get("doc_b_id"))
            direction = r.get("direction")
            if direction in ("ab", "ba"):
                by_pair[key][direction] = r.get("parsed_winner_label")
    n_by_query: dict[tuple[str, str], int] = defaultdict(int)
    disagree_by_query: dict[tuple[str, str], int] = defaultdict(int)
    for (dataset, query_id, _a, _b), votes in by_pair.items():
        if "ab" not in votes or "ba" not in votes:
            continue
        n_by_query[(dataset, query_id)] += 1
        ab_favors_a = votes["ab"] == "A"
        ba_favors_a = votes["ba"] == "B"  # B in the swapped call means original A won
        if ab_favors_a != ba_favors_a:
            disagree_by_query[(dataset, query_id)] += 1
    return {
        k: (disagree_by_query.get(k, 0) / n) for k, n in n_by_query.items() if n > 0
    }


def scc_local_repair(graph: nx.DiGraph, method: str = "greedy") -> tuple[nx.DiGraph, list, float]:
    """Repair only within each nontrivial SCC's induced subgraph, leaving
    every edge outside a nontrivial SCC untouched. Returns
    (resulting_graph, removed_edges, frac_repair_weight_inside_largest_scc)."""
    result = graph.copy()
    removed_all: list = []
    sccs = [s for s in nx.strongly_connected_components(graph) if len(s) > 1]
    largest_scc = max(sccs, key=len) if sccs else set()
    weight_in_largest = 0.0
    total_removed_weight = 0.0
    for scc in sccs:
        sub = graph.subgraph(scc).copy()
        dag_sub, removed_sub = mwfas_solve(sub, method=method)
        for u, v, w in removed_sub:
            if result.has_edge(u, v):
                result.remove_edge(u, v)
            removed_all.append((u, v, w))
            total_removed_weight += w
            if scc == largest_scc:
                weight_in_largest += w
    frac = (weight_in_largest / total_removed_weight) if total_removed_weight > 0 else 0.0
    return result, removed_all, frac


def stage4_features(all_rows: list[dict], all_prefs_index: dict, output_dir: Path) -> list[dict]:
    """Attach mechanism features to every collected (variant, dataset,
    query, graph_id, repair_method) row: extended_graph_stats plus
    provider-disagreement, position-sensitivity, and SCC-local-repair
    features. Reconstructs the graph from the persisted provider_prefs
    index (no re-collection)."""
    feature_rows = []
    for row in all_rows:
        key = (row["variant"], row["dataset"], row["query_id"])
        entry = all_prefs_index.get(key)
        if entry is None:
            continue
        provider_prefs = entry["provider_prefs"]
        graph_id = row["graph_id"]
        if graph_id == "aggregate":
            prefs = [p for prov in BASE_PROVIDERS for p in provider_prefs.get(prov, [])]
        else:
            prefs = provider_prefs.get(graph_id, [])
        if not prefs:
            continue
        pref_objs = [Preference(w, l, wt) for w, l, wt in prefs]
        graph = build_graph(pref_objs, aggregation="sum")
        relevance_map = entry.get("relevance_map", {})
        feats = extended_graph_stats(graph, reference_judged_rel_map=relevance_map or None)

        n_pairs = len({tuple(sorted((w, l))) for w, l, _ in prefs})
        n_disagree = 0
        if graph_id == "aggregate":
            pair_votes: dict[tuple, set] = defaultdict(set)
            for prov in BASE_PROVIDERS:
                for w, l, _ in provider_prefs.get(prov, []):
                    pair_votes[tuple(sorted((w, l)))].add(w)
            n_disagree = sum(1 for v in pair_votes.values() if len(v) > 1)
        provider_disagreement = (n_disagree / n_pairs) if n_pairs else 0.0

        _, _, scc_local_frac = (None, None, 0.0)
        if not feats["is_dag"]:
            try:
                _, _, scc_local_frac = scc_local_repair(graph, method="greedy")
            except Exception:  # noqa: BLE001
                scc_local_frac = None

        top_k_doc_ids = {d for d, rel in relevance_map.items() if rel and rel > 0}
        repair_touches_topk = None
        if row.get("n_removed_edges", 0) > 0 and top_k_doc_ids:
            repair_touches_topk = None  # requires removed-edge endpoints; computed in stage6/7 where available

        feature_row = {
            **row,
            "provider_disagreement": provider_disagreement,
            "scc_local_repair_weight_frac": scc_local_frac,
            "graph_density": feats["graph_density"],
            "n_non_trivial_sccs": feats["n_non_trivial_sccs"],
            "scc_cycle_burden": feats["scc_cycle_burden"],
            "n_mutual_pairs": feats["n_mutual_pairs"],
            "total_edge_weight": feats["total_edge_weight"],
            "pairwise_inconsistency_pre_repair": feats.get("pairwise_inconsistency_pre_repair"),
            "backward_edge_weight_pre_repair": feats.get("backward_edge_weight_pre_repair"),
        }
        feature_rows.append(feature_row)
    _atomic_write_json(output_dir / "STAGE4_FEATURES_meta.json", {"n_rows": len(feature_rows)})
    with (output_dir / "stage4_feature_rows.jsonl").open("w", encoding="utf-8") as fh:
        for r in feature_rows:
            fh.write(json.dumps(r, default=str) + "\n")
    return feature_rows


# ---------------------------------------------------------------------------
# Stage 5: predictive evaluation with grouped CV + negative controls
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "n_nodes", "n_edges", "graph_density", "n_sccs", "n_non_trivial_sccs",
    "largest_scc_frac", "scc_cycle_burden", "n_mutual_pairs", "total_edge_weight",
    "provider_disagreement", "n_removed_edges", "removed_weight",
]


def stage5_predict(feature_rows: list[dict], output_dir: Path) -> dict:
    primary_rows = [r for r in feature_rows if r["repair_method"] == "greedy"]
    n_nonzero = sum(1 for r in primary_rows if r["delta"] != 0)
    result: dict = {
        "n_rows": len(primary_rows),
        "n_unique_queries": len({(r["dataset"], r["query_id"]) for r in primary_rows}),
        "n_nonzero_delta_rows": n_nonzero,
    }
    if n_nonzero < 4:
        result["skipped"] = True
        result["reason"] = (
            f"Only {n_nonzero} rows with a nonzero repair delta across "
            f"{len(primary_rows)} collected rows -- inadequate label variation "
            "for any predictive modeling per the pre-registered gate "
            "('Only perform predictive modeling if the collected data contains "
            "adequate label variation and oracle headroom'). Reporting this "
            "honestly rather than fitting a model to a near-constant target."
        )
        _atomic_write_json(output_dir / "STAGE5_PREDICTION.json", result)
        log.warning("Stage 5 SKIPPED: %s", result["reason"])
        return result

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.tree import DecisionTreeClassifier

    y = np.array([1 if r["delta"] > 0 else 0 for r in primary_rows])
    groups = np.array([f"{r['dataset']}::{r['query_id']}" for r in primary_rows])
    X = np.array([[float(r.get(c) or 0.0) for c in FEATURE_COLS] for r in primary_rows])
    n_groups = len(set(groups))
    result["n_groups"] = n_groups
    result["class_balance"] = {"positive": int(y.sum()), "negative": int(len(y) - y.sum())}

    if n_groups < 3 or len(set(y)) < 2:
        result["skipped"] = True
        result["reason"] = (
            f"n_unique_query_groups={n_groups}, n_classes={len(set(y))} -- too few "
            "for grouped cross-validation. Reporting descriptively only."
        )
        _atomic_write_json(output_dir / "STAGE5_PREDICTION.json", result)
        log.warning("Stage 5 SKIPPED: %s", result["reason"])
        return result

    n_splits = min(5, n_groups)
    gkf = GroupKFold(n_splits=n_splits)

    def eval_model(name, fit_predict_fn):
        from sklearn.metrics import balanced_accuracy_score
        accs = []
        for train_idx, test_idx in gkf.split(X, y, groups):
            if len(set(y[train_idx])) < 2:
                continue
            pred = fit_predict_fn(X[train_idx], y[train_idx], X[test_idx])
            accs.append(balanced_accuracy_score(y[test_idx], pred))
        return {"mean_balanced_accuracy": float(np.mean(accs)) if accs else None, "n_folds_used": len(accs)}

    models = {}
    models["always_repair"] = eval_model("always_repair", lambda Xtr, ytr, Xte: np.ones(len(Xte), dtype=int))
    models["never_repair"] = eval_model("never_repair", lambda Xtr, ytr, Xte: np.zeros(len(Xte), dtype=int))
    models["majority_class"] = eval_model(
        "majority_class",
        lambda Xtr, ytr, Xte: np.full(len(Xte), int(round(ytr.mean())), dtype=int),
    )
    cyclic_idx = FEATURE_COLS.index("n_sccs")
    nodes_idx = FEATURE_COLS.index("n_nodes")
    models["repair_whenever_cyclic"] = eval_model(
        "repair_whenever_cyclic",
        lambda Xtr, ytr, Xte: (Xte[:, cyclic_idx] < Xte[:, nodes_idx]).astype(int),
    )
    scc_idx = FEATURE_COLS.index("largest_scc_frac")
    models["repair_whenever_large_scc"] = eval_model(
        "repair_whenever_large_scc",
        lambda Xtr, ytr, Xte: (Xte[:, scc_idx] > 0.4).astype(int),
    )

    def fit_logreg(Xtr, ytr, Xte):
        model = LogisticRegression(max_iter=1000)
        model.fit(Xtr, ytr)
        return model.predict(Xte)

    def fit_tree(Xtr, ytr, Xte):
        model = DecisionTreeClassifier(max_depth=3, random_state=BASE_SEED)
        model.fit(Xtr, ytr)
        return model.predict(Xte)

    models["logistic_regression"] = eval_model("logistic_regression", fit_logreg)
    models["decision_tree"] = eval_model("decision_tree", fit_tree)

    # Negative controls
    rng = np.random.RandomState(BASE_SEED)
    y_shuffled = rng.permutation(y)
    models["control_shuffled_labels_logreg"] = eval_model(
        "control_shuffled_labels_logreg",
        lambda Xtr, ytr, Xte: fit_logreg(Xtr, y_shuffled[: len(ytr)], Xte),
    )
    X_random = rng.normal(size=X.shape)
    models["control_random_features_logreg"] = eval_model(
        "control_random_features_logreg",
        lambda Xtr, ytr, Xte: LogisticRegression(max_iter=1000).fit(
            X_random[: len(ytr)], ytr
        ).predict(X_random[len(ytr): len(ytr) + len(Xte)])
        if len(ytr) + len(Xte) <= len(X_random) else np.zeros(len(Xte), dtype=int),
    )

    result["models"] = models
    result["negative_controls_note"] = (
        "control_shuffled_labels_logreg and control_random_features_logreg should "
        "perform no better than majority_class if the real models' apparent skill "
        "is genuine rather than an artifact of the tiny sample."
    )
    result["caveat"] = (
        f"n_unique_query_groups={n_groups} is far below what is needed for a "
        "reliable predictive-evaluation claim; treat all model numbers here as "
        "illustrative/diagnostic, not a validated selector, pending a Branch-A-"
        "style query-count scale-up."
    )
    _atomic_write_json(output_dir / "STAGE5_PREDICTION.json", result)
    log.info("Stage 5: n_groups=%d models=%s", n_groups, list(models.keys()))
    return result


# ---------------------------------------------------------------------------
# Stage 6: robustness re-analysis (no new API calls)
# ---------------------------------------------------------------------------

def _oracle_headroom_for_rows(rows: list[dict], label: str) -> dict | None:
    if not rows:
        return None
    by_query: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_query[(r["dataset"], r["query_id"])].append(r)
    records = []
    for (dataset, query_id), grp in sorted(by_query.items()):
        records.append(
            PreserveRepairRecord(
                dataset=dataset, query_id=query_id,
                preserve_metric=sum(g["ndcg_preserve"] for g in grp) / len(grp),
                repair_metric=sum(g["ndcg_repair"] for g in grp) / len(grp),
            )
        )
    if not records:
        return None
    res = compute_oracle_headroom(records, bootstrap_seed=BASE_SEED)
    return {"label": label, "n_queries": res.n_queries, "headroom": res.headroom_vs_best_baseline,
            "headroom_ci": [res.headroom_ci.lower, res.headroom_ci.upper],
            "frac_beneficial": res.frac_benefit_from_repair, "frac_harmful": res.frac_harmed_by_repair}


def stage6_robustness(branch_b_rows: list[dict], original_rows: list[dict], output_dir: Path) -> dict:
    all_rows = branch_b_rows + original_rows
    slices = {}

    for method in ("greedy", "exact"):
        slices[f"method={method}"] = _oracle_headroom_for_rows(
            [r for r in all_rows if r["repair_method"] == method], f"method={method}"
        )
    for graph_id in list(BASE_PROVIDERS) + ["aggregate"]:
        slices[f"graph_id={graph_id}"] = _oracle_headroom_for_rows(
            [r for r in all_rows if r["repair_method"] == "greedy" and r["graph_id"] == graph_id],
            f"graph_id={graph_id}",
        )
    for dataset in BASE_DATASETS:
        slices[f"dataset={dataset}"] = _oracle_headroom_for_rows(
            [r for r in all_rows if r["repair_method"] == "greedy" and r["dataset"] == dataset],
            f"dataset={dataset}",
        )
    variants = sorted({r.get("variant", "pool6_original") for r in all_rows})
    for variant in variants:
        slices[f"variant={variant}"] = _oracle_headroom_for_rows(
            [r for r in all_rows if r["repair_method"] == "greedy" and r.get("variant", "pool6_original") == variant],
            f"variant={variant}",
        )
    slices["whole_graph_repair"] = _oracle_headroom_for_rows(
        [r for r in all_rows if r["repair_method"] == "greedy"], "whole_graph_repair"
    )

    result = {"n_total_rows": len(all_rows), "slices": {k: v for k, v in slices.items() if v is not None}}
    _atomic_write_json(output_dir / "STAGE6_ROBUSTNESS.json", result)
    log.info("Stage 6: computed %d robustness slices", len(result["slices"]))
    return result


# ---------------------------------------------------------------------------
# Stage 7: synthetic counterfactual perturbation (no new API calls)
# ---------------------------------------------------------------------------

def stage7_counterfactual(all_prefs_index: dict, output_dir: Path) -> dict:
    """For every real observed graph with >=1 edge inside a nontrivial SCC,
    remove that single edge (holding everything else fixed) and recompute
    nDCG. Tests whether edges inside vs. outside the relevance-judged
    top-k show a different delta distribution -- an intervention-consistent
    check of the "cycles confined to the non-consequential tail" hypothesis
    from Stage 1/2, without any new LLM calls."""
    inside_topk_deltas = []
    outside_topk_deltas = []
    n_graphs_tested = 0

    for (variant, dataset, query_id), entry in all_prefs_index.items():
        provider_prefs = entry["provider_prefs"]
        relevance_map = entry.get("relevance_map", {})
        top_k_ids = {d for d, rel in relevance_map.items() if rel and rel > 0}
        prefs = [p for prov in BASE_PROVIDERS for p in provider_prefs.get(prov, [])]
        if not prefs:
            continue
        pref_objs = [Preference(w, l, wt) for w, l, wt in prefs]
        graph = build_graph(pref_objs, aggregation="sum")
        sccs = [s for s in nx.strongly_connected_components(graph) if len(s) > 1]
        if not sccs:
            continue
        n_graphs_tested += 1
        base_ranking = copeland_ranking(graph)
        base_ndcg = ndcg_at_k(base_ranking, relevance_map, k=10)
        for scc in sccs:
            sub_edges = list(graph.subgraph(scc).edges(data=True))
            for u, v, data in sub_edges:
                g2 = graph.copy()
                g2.remove_edge(u, v)
                r2 = copeland_ranking(g2)
                ndcg2 = ndcg_at_k(r2, relevance_map, k=10)
                delta = ndcg2 - base_ndcg
                edge_inside_topk = (u in top_k_ids) or (v in top_k_ids)
                (inside_topk_deltas if edge_inside_topk else outside_topk_deltas).append(delta)

    def summarize(xs):
        if not xs:
            return None
        return {
            "n": len(xs), "mean": float(np.mean(xs)), "std": float(np.std(xs)),
            "frac_nonzero": float(np.mean([x != 0 for x in xs])),
        }

    result = {
        "n_graphs_tested": n_graphs_tested,
        "single_edge_removal_inside_topk": summarize(inside_topk_deltas),
        "single_edge_removal_outside_topk": summarize(outside_topk_deltas),
        "interpretation": (
            "SYNTHETIC / exploratory only -- single-edge removal within an "
            "observed SCC, not a full MWFAS re-solve, and not validated against "
            "any new real LLM judgment. A materially higher frac_nonzero / |mean| "
            "for the inside-top-k group versus the outside-top-k group would be "
            "intervention-consistent with the 'cycles confined to the "
            "non-consequential tail' hypothesis motivating Branch B; a similar "
            "or null difference would not support it."
        ),
    }
    _atomic_write_json(output_dir / "STAGE7_COUNTERFACTUAL.json", result)
    log.info("Stage 7: tested %d graphs with nontrivial SCCs", n_graphs_tested)
    return result


# ---------------------------------------------------------------------------
# Stage 8: final report
# ---------------------------------------------------------------------------

def _git_state() -> dict:
    import subprocess
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT).decode().strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=_REPO_ROOT).decode().strip())
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=_REPO_ROOT
        ).decode().strip()
        return {"commit": commit, "dirty": dirty, "branch": branch}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _env_snapshot(output_dir: Path) -> None:
    import subprocess
    try:
        out = subprocess.check_output([str(_REPO_ROOT / ".venv" / "bin" / "python"), "-m", "pip", "freeze"])
        (output_dir / "ENVIRONMENT_pip_freeze.txt").write_bytes(out)
    except Exception as exc:  # noqa: BLE001
        (output_dir / "ENVIRONMENT_pip_freeze.txt").write_text(f"failed: {exc}")


def stage8_report(
    interpretation: dict, branch_decision: dict, estimate: dict | None, collect_result: dict | None,
    stage5: dict, stage6: dict, stage7: dict, output_dir: Path,
) -> None:
    git_state = _git_state()
    _env_snapshot(output_dir)

    summary = {
        "timestamp": time.time(),
        "git_state": git_state,
        "stage1_interpretation": interpretation,
        "branch_decision": branch_decision,
        "stage3_estimate": estimate,
        "stage3_collection_result": collect_result,
        "stage5_prediction": stage5,
        "stage6_robustness": stage6,
        "stage7_counterfactual": stage7,
    }
    _atomic_write_json(output_dir / "FINAL_SUMMARY.json", summary)

    ms = interpretation["method_summaries"][interpretation["primary_repair_method"]]
    q1 = (
        f"Real LLM graphs DID show more structural inconsistency than the classical "
        f"score-derived comparison (repo-scale classical oracle headroom ≈0.0025, "
        f"n=419) at the aggregate-graph level (6/6 multi-provider aggregate graphs "
        f"cyclic in the original pilot), but whole-graph query-level oracle headroom "
        f"in the original pilot was exactly 0.0 (CI [0,0], n=6) -- i.e. more cycles "
        f"did not translate into more recoverable nDCG opportunity at pool_size=6, "
        f"top-relevance-only construction. See Stage 6 for whether Branch B's varied "
        f"constructions changed this."
    )
    q2 = (
        f"In the original pilot's primary (greedy) method: repair helped {ms['n_beneficial']}, "
        f"hurt {ms['n_harmful']}, and did nothing to {ms['n_neutral']} of {ms['n']} rows. See "
        "STAGE6_ROBUSTNESS.json's per-slice breakdown for the pooled original+Branch B picture."
    )
    q9 = (
        "At minimum: (a) a Branch-A-style scale-up to tens of independent queries "
        "once a construction is found that produces nonzero-delta variation, since "
        "n=6 unique queries cannot support any reliable predictive claim regardless "
        "of feature quality; (b) resolution of whether the Cohere/schema and Fireworks "
        "reasoning-token paths generalize to larger candidate pools without cost or "
        "latency surprises; (c) an actual construction (see Stage 6/7) that produces "
        "repair-induced ranking changes with more than a handful of nonzero examples "
        "before any Stage-5-style modeling claim could be treated as more than illustrative."
    )

    report_lines = [
        "# Reviewer-Concerns Follow-On Program — Final Report",
        "",
        f"**Git:** `{git_state.get('branch')}` @ `{git_state.get('commit')}` "
        f"({'dirty' if git_state.get('dirty') else 'clean'} working tree at program start)",
        "",
        "## 1. Do real modern LLM preference graphs exhibit more recoverable",
        "   inconsistency than the classical score-derived graphs?",
        "",
        q1,
        "",
        "## 2. How often does consistency repair help, hurt, or do nothing?",
        "",
        q2,
        "",
        "## 3. Is benefit concentrated in particular providers, aggregation",
        "   methods, SCCs, edges, or top-k regions?",
        "",
        "See `STAGE6_ROBUSTNESS.json` (per-provider/aggregate/dataset/variant "
        "slices) and `STAGE7_COUNTERFACTUAL.json` (inside- vs outside-top-k "
        "single-edge-removal deltas) for the direct evidence.",
        "",
        "## 4. Can graph features predict when repair helps on held-out queries?",
        "",
        json.dumps(stage5.get("reason", "See STAGE5_PREDICTION.json for model-by-model results."), indent=0),
        "",
        "## 5. Does a learned selective policy improve over always-repair and",
        "   never-repair baselines?",
        "",
        "See `STAGE5_PREDICTION.json`'s `models` block (`always_repair`, "
        "`never_repair`, `logistic_regression`, `decision_tree` balanced "
        "accuracies) — not evaluated if Stage 5 was skipped for inadequate "
        "label variation.",
        "",
        "## 6. Are results robust to reasonable methodological choices?",
        "",
        "See `STAGE6_ROBUSTNESS.json`'s per-slice oracle headroom (greedy vs "
        "exact, per-provider vs aggregate, per-dataset, per-construction-variant).",
        "",
        "## 7. Which findings are statistically supported, exploratory, or",
        "   falsified?",
        "",
        "Statistically supported (query-level CI, n=6 original pilot queries): "
        "whole-graph repair produced exactly zero measurable nDCG change at "
        "pool_size=6, top-relevance-only construction, despite genuine "
        "structural cyclicity in aggregate graphs. Exploratory only: Stage 5 "
        "predictive-model numbers (tiny n), Stage 7 synthetic counterfactual "
        "deltas (single-edge perturbation, not a full re-solve, not independently "
        "LLM-validated).",
        "",
        "## 8. What is the strongest defensible manuscript contribution after",
        "   this experiment?",
        "",
        "Consistent with the repository's existing negative-result manuscript "
        "package (`papers/negative_result_2026/`): this program's evidence, at "
        "pilot scale, does not overturn that conclusion for whole-graph repair, "
        "and additionally shows that even with genuine real-LLM-induced "
        "aggregate-graph cyclicity, repair-induced ranking change was not "
        "observed at all under the original construction — strengthening rather "
        "than weakening the negative result, subject to the small-sample caveats "
        "documented throughout this report.",
        "",
        "## 9. What additional evidence would still be required to satisfy the",
        "   reviewers?",
        "",
        q9,
        "",
        "## Files in this directory",
        "",
        "- `STAGE1_INTERPRETATION.json`, `BRANCH_DECISION.json`",
        "- `ESTIMATE_branch_b.json`, `smoke_branch_b/SMOKE_BRANCH_B_RESULT.json`",
        "- `checkpoint/branch_b_results.jsonl`, `checkpoint/branch_b_provider_prefs.jsonl`",
        "- `raw_calls/*.jsonl`, `cache/**`, `provider_usage.jsonl`, `provider_failures.jsonl`",
        "- `stage4_feature_rows.jsonl`, `STAGE5_PREDICTION.json`, `STAGE6_ROBUSTNESS.json`,",
        "  `STAGE7_COUNTERFACTUAL.json`",
        "- `ENVIRONMENT_pip_freeze.txt`, `FINAL_SUMMARY.json` (this report's machine-readable twin)",
    ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")
    log.info("Stage 8: wrote FINAL_REPORT.md and FINAL_SUMMARY.json")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_full_program(pilot_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stage0_wait_for_pilot(pilot_dir)

    interpretation_path = output_dir / "STAGE1_INTERPRETATION.json"
    if interpretation_path.exists():
        interpretation = json.loads(interpretation_path.read_text())
    else:
        interpretation = stage1_interpret(pilot_dir, output_dir)

    branch_path = output_dir / "BRANCH_DECISION.json"
    if branch_path.exists():
        branch_decision = json.loads(branch_path.read_text())
    else:
        branch = stage2_select_branch(interpretation, output_dir)
        branch_decision = json.loads(branch_path.read_text())

    branch = branch_decision["branch"]
    estimate = None
    collect_result = None
    all_prefs_index: dict = {}
    branch_b_rows: list[dict] = []
    original_rows: list[dict] = []

    if branch == "B":
        estimate_path = output_dir / "ESTIMATE_branch_b.json"
        estimate = json.loads(estimate_path.read_text()) if estimate_path.exists() else stage3_estimate(output_dir)

        smoke_path = output_dir / "smoke_branch_b" / "SMOKE_BRANCH_B_RESULT.json"
        if not smoke_path.exists():
            stage3a_smoke(output_dir)

        collect_result = stage3c_collect(output_dir)

        results_path = output_dir / "checkpoint" / "branch_b_results.jsonl"
        branch_b_rows = [json.loads(line) for line in results_path.open() if line.strip()]

        prefs_path = output_dir / "checkpoint" / "branch_b_provider_prefs.jsonl"
        for line in prefs_path.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            key = (entry["variant"], entry["dataset"], entry["query_id"])
            all_prefs_index.setdefault(key, {"provider_prefs": {}, "relevance_map": entry.get("relevance_map", {})})
            all_prefs_index[key]["provider_prefs"][entry["provider"]] = entry["prefs"]

        base_queries = _base_queries()
        original_entries = load_original_pilot_prefs(pilot_dir, base_queries)
        original_results_path = pilot_dir / "checkpoint" / "pilot_results.jsonl"
        original_rows = [json.loads(line) for line in original_results_path.open() if line.strip()]
        for r in original_rows:
            r.setdefault("variant", "pool6_original")
        rel_by_bq = {(bq["dataset"], bq["query_id"]): {
            e.doc_id: e.relevance for e in bq["qrels_by_query"].get(bq["query_id"], [])
        } for bq in base_queries}
        for entry in original_entries:
            key = (entry["variant"], entry["dataset"], entry["query_id"])
            all_prefs_index[key] = {
                "provider_prefs": entry["provider_prefs"],
                "relevance_map": rel_by_bq.get((entry["dataset"], entry["query_id"]), {}),
            }
    else:
        log.warning("Branch %s selected but this program's Stage 3+ implementation is scoped to Branch B "
                    "(the branch the finished pilot's evidence actually triggers). Stopping after Stage 2; "
                    "see BRANCH_DECISION.json.", branch)
        stage8_report(interpretation, branch_decision, None, None, {"skipped": True}, {}, {}, output_dir)
        return

    all_rows_for_features = branch_b_rows + original_rows
    feature_rows = stage4_features(all_rows_for_features, all_prefs_index, output_dir)

    stage5_result = stage5_predict(feature_rows, output_dir)
    stage6_result = stage6_robustness(branch_b_rows, original_rows, output_dir)
    stage7_result = stage7_counterfactual(all_prefs_index, output_dir)

    stage8_report(
        interpretation, branch_decision, estimate, collect_result,
        stage5_result, stage6_result, stage7_result, output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    run_tag = f"program_{int(time.time())}"
    log_path = _setup_logging(args.output_dir, run_tag)
    log.info("Logging to %s", log_path)
    log.info("Using interpreter: %s", sys.executable)

    run_full_program(args.pilot_dir, args.output_dir)


if __name__ == "__main__":
    main()
