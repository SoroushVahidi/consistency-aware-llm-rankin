"""
run_repair_frontier_pilot.py
=============================
Orchestrates the repair-frontier program (SCC-local incumbent-protected
repair + repair-frontier discovery/selection evaluation) over the
ALREADY-MATERIALIZED real-LLM graph artifacts from the two finished pilots
-- makes NO new LLM API calls.

Sources:
  - reports/multi_provider_repair_pilot_20260729T032348Z/ (pool_size=6,
    6 base queries; per-provider cache reconstructed via
    run_reviewer_concerns_program.load_original_pilot_prefs).
  - reports/reviewer_concerns_program_20260729T035320Z/ (pool8_complete,
    pool8_sparse57, pool10_sparse56 variants, same 6 base queries; provider
    Preference lists read directly from the already-persisted
    checkpoint/branch_b_provider_prefs.jsonl, no re-derivation from raw
    cache needed).

This is the follow-on the original pilot's and the reviewer-concerns
program's own reports flagged as still needed: does a richer repair
candidate set (SCC-scoped, incumbent-protected, confidence-aware) contain
beneficial rankings that whole-graph MWFAS repair alone did not find?

Reuses (does not duplicate):
  - consistency_ranker.repair_frontier (build_repair_frontier,
    EdgeProtectionRule, compute_edge_confidence, evaluate_query_frontier,
    compute_discovery_result, localization_summary, evaluate_selection).
  - scripts/run_reviewer_concerns_program.py's `_base_queries`,
    `load_original_pilot_prefs`, `BASE_PROVIDERS` (imported as `program_lib`,
    per this repository's established reuse convention: that script itself
    imports `run_multi_provider_repair_pilot as pilot_lib` rather than
    duplicating cost/logging/checkpoint helpers).
  - scripts/run_multi_provider_repair_pilot.py's `_atomic_write_json`,
    `_setup_logging` (imported transitively via program_lib / pilot_lib).
  - consistency_ranker.repair_selector_mining.checkpoint.FlushWriter for all
    JSONL outputs.

Mode: single `run` mode (no cost estimate / smoke-test modes needed --
there is no API cost or failure risk here, only local computation over
data already on disk).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import networkx as nx

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import run_multi_provider_repair_pilot as pilot_lib  # noqa: E402
import run_reviewer_concerns_program as program_lib  # noqa: E402

from consistency_ranker.graph_construction import build_graph  # noqa: E402
from consistency_ranker.pairwise_prefs import Preference  # noqa: E402
from consistency_ranker.repair_frontier import (  # noqa: E402
    EdgeProtectionRule,
    FrontierCandidate,
    build_repair_frontier,
    compute_discovery_result,
    compute_edge_confidence,
    evaluate_query_frontier,
    evaluate_selection,
    localization_summary,
)
from consistency_ranker.repair_selector_mining.checkpoint import FlushWriter  # noqa: E402

log = logging.getLogger("repair_frontier_pilot")

_atomic_write_json = pilot_lib._atomic_write_json
_setup_logging = pilot_lib._setup_logging

BASE_PROVIDERS = program_lib.BASE_PROVIDERS
POOL6_DIR = _REPO_ROOT / "reports" / "multi_provider_repair_pilot_20260729T032348Z"
REVIEWER_CONCERNS_DIR = _REPO_ROOT / "reports" / "reviewer_concerns_program_20260729T035320Z"

# Main-pass configuration: a representative variety of protection rules
# assembled into ONE frontier per (unit, graph_id) -- build_repair_frontier
# accepts a list and generates one protected candidate family per rule.
MAIN_PROTECTION_RULES = [
    EdgeProtectionRule(kind="unanimous_multi_provider", min_providers_for_unanimity=2),
    EdgeProtectionRule(kind="confidence_threshold", reliability_tau=0.5),
    EdgeProtectionRule(kind="margin_threshold", margin_tau=0.5),
    EdgeProtectionRule(kind="topk_boundary_crossing", topk=10, topk_window=2),
    EdgeProtectionRule(kind="low_confidence_first", reliability_tau=0.25),
]
MAIN_TOPK = 10
MAIN_CONSERVATIVE_MARGIN = 0.05
MAIN_WEAK_EDGE_TAU = 0.5
MAIN_EXACT_MAX_N = 12

# Sensitivity sweep grids (Part 4 requirement) -- one parameter varied at a
# time, holding the rest at the MAIN defaults above.
SENSITIVITY_CONFIDENCE_TAUS = [0.1, 0.25, 0.5, 0.75, 0.9]
SENSITIVITY_MARGIN_TAUS = [0.1, 0.5, 1.0, 2.0]
SENSITIVITY_CONSERVATIVE_MARGINS = [0.01, 0.05, 0.1, 0.2]
SENSITIVITY_TOPKS = [3, 5, 10, 20]


# ---------------------------------------------------------------------------
# Stage 1: load provider Preference lists from the two already-finished pilots
# ---------------------------------------------------------------------------


def load_pool6_units() -> list[dict]:
    """Reconstruct the pool_size=6 pilot's per-provider Preference lists and
    relevance maps -- zero new API calls, reuses
    program_lib.load_original_pilot_prefs (which itself reads the pilot's
    persisted JudgmentCache files) plus `_base_queries`'s qrels for the
    relevance maps `load_original_pilot_prefs` does not carry."""
    base_queries = program_lib._base_queries()
    entries = program_lib.load_original_pilot_prefs(POOL6_DIR, base_queries)
    by_key = {(bq["dataset"], bq["query_id"]): bq for bq in base_queries}
    units = []
    for e in entries:
        bq = by_key[(e["dataset"], e["query_id"])]
        relevance_map = {
            qr.doc_id: qr.relevance for qr in bq["qrels_by_query"].get(e["query_id"], [])
        }
        provider_prefs = {
            provider: [Preference(w, loser, wt) for w, loser, wt in prefs]
            for provider, prefs in e["provider_prefs"].items()
        }
        units.append(
            {
                "source": "pool6_pilot",
                "variant": e["variant"],
                "dataset": e["dataset"],
                "query_id": e["query_id"],
                "provider_prefs": provider_prefs,
                "relevance_map": relevance_map,
            }
        )
    return units


def load_branch_b_units(report_dir: Path) -> list[dict]:
    """Read checkpoint/branch_b_provider_prefs.jsonl (one row per
    (variant, dataset, query_id, provider), already-persisted by the
    finished reviewer-concerns program) and group into per-unit
    {provider: [Preference, ...]} + relevance_map -- no re-derivation from
    raw cache needed."""
    path = report_dir / "checkpoint" / "branch_b_provider_prefs.jsonl"
    grouped: dict[tuple[str, str, str], dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = (row["variant"], row["dataset"], row["query_id"])
            entry = grouped.setdefault(
                key,
                {
                    "source": "reviewer_concerns_branch_b",
                    "variant": row["variant"],
                    "dataset": row["dataset"],
                    "query_id": row["query_id"],
                    "relevance_map": row.get("relevance_map") or {},
                    "provider_prefs": {},
                },
            )
            entry["provider_prefs"][row["provider"]] = [
                Preference(w, loser, wt) for w, loser, wt in row["prefs"]
            ]
    return list(grouped.values())


def load_all_units() -> list[dict]:
    return load_pool6_units() + load_branch_b_units(REVIEWER_CONCERNS_DIR)


def graphs_for_unit(unit: dict) -> dict[str, nx.DiGraph]:
    """Build per-provider graphs plus the multi-provider aggregate graph,
    exactly as both source pilots did (aggregation="sum")."""
    provider_prefs = unit["provider_prefs"]
    graphs = {}
    for provider in BASE_PROVIDERS:
        prefs = provider_prefs.get(provider, [])
        if prefs:
            graphs[provider] = build_graph(prefs, aggregation="sum")
    all_prefs = [p for prov in BASE_PROVIDERS for p in provider_prefs.get(prov, [])]
    if all_prefs:
        graphs["aggregate"] = build_graph(all_prefs, aggregation="sum")
    return graphs


# ---------------------------------------------------------------------------
# Stage 2: main pass -- build the frontier for every (unit, graph_id)
# ---------------------------------------------------------------------------


def run_main_pass(units: list[dict], output_dir: Path) -> dict[tuple, list[FrontierCandidate]]:
    """Local computation only (no API calls, no cost/failure risk), so this
    does not use unit_key-skip resumability the way the LLM-calling pilots
    do -- candidates are always rebuilt in memory for this run (fast,
    deterministic), while every output artifact is still written via
    FlushWriter for durability/inspectability."""
    checkpoint_dir = output_dir / "checkpoint"
    results_writer = FlushWriter(checkpoint_dir / "frontier_results.jsonl")
    scc_writer = FlushWriter(output_dir / "scc_decisions.jsonl")
    feature_writer = FlushWriter(output_dir / "feature_rows.jsonl")
    failures_writer = FlushWriter(output_dir / "failures.jsonl")

    candidates_by_query: dict[tuple, list[FrontierCandidate]] = {}
    n_done = 0
    n_total = sum(len(graphs_for_unit(u)) for u in units)
    runtime_total = 0.0

    try:
        for unit in units:
            source, variant = unit["source"], unit["variant"]
            dataset, query_id = unit["dataset"], unit["query_id"]
            relevance_map = unit.get("relevance_map") or {}
            confidences = compute_edge_confidence(unit["provider_prefs"])
            graphs = graphs_for_unit(unit)

            for graph_id, graph in graphs.items():
                unit_key = f"{source}|{variant}|{dataset}|{query_id}|{graph_id}"
                t0 = time.time()
                try:
                    candidates = build_repair_frontier(
                        graph,
                        dataset,
                        query_id,
                        relevance_map=relevance_map or None,
                        confidences=confidences,
                        protection_rules=MAIN_PROTECTION_RULES,
                        conservative_margin=MAIN_CONSERVATIVE_MARGIN,
                        weak_edge_tau=MAIN_WEAK_EDGE_TAU,
                        topk=MAIN_TOPK,
                        exact_max_n=MAIN_EXACT_MAX_N,
                    )
                except Exception as exc:  # noqa: BLE001 - recorded, not silently swallowed
                    failures_writer.write(
                        {
                            "unit_key": unit_key,
                            "source": source,
                            "variant": variant,
                            "dataset": dataset,
                            "query_id": query_id,
                            "graph_id": graph_id,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    )
                    log.error("Frontier build FAILED for %s: %s", unit_key, exc)
                    continue
                runtime_total += time.time() - t0

                key = (dataset, query_id, source, variant, graph_id)
                candidates_by_query[key] = candidates

                for c in candidates:
                    row = {
                        "unit_key": unit_key, "source": source, "variant": variant, **c.to_dict()
                    }
                    results_writer.write(row)
                    feature_writer.write(
                        {
                            "unit_key": unit_key,
                            "candidate_id": c.candidate_id,
                            "graph_features": c.graph_features,
                            "fas_objective": c.fas_objective,
                            "n_reversed_or_removed": c.n_reversed_or_removed,
                            "weight_reversed_or_removed": c.weight_reversed_or_removed,
                            "protected_edge_violations": c.protected_edge_violations,
                            "topk_membership_changes": c.topk_membership_changes,
                            "identical_to_incumbent": c.identical_to_incumbent,
                        }
                    )
                    if c.candidate_id.startswith("scc_local_"):
                        scc_writer.write(
                            {
                                "unit_key": unit_key,
                                "candidate_id": c.candidate_id,
                                "modified_sccs": [sorted(s) for s in c.modified_sccs],
                                "edge_dispositions": row["edge_dispositions"],
                                "protected_edge_violations": c.protected_edge_violations,
                                "acceptance_by_mode": c.acceptance_by_mode,
                            }
                        )

                n_done += 1
                if n_done % 10 == 0 or n_done == n_total:
                    _atomic_write_json(
                        checkpoint_dir / "progress.json",
                        {
                            "timestamp": time.time(),
                            "n_units_completed": n_done,
                            "n_units_total": n_total,
                            "runtime_total_s": runtime_total,
                        },
                    )
    finally:
        results_writer.close()
        scc_writer.close()
        feature_writer.close()
        failures_writer.close()

    log.info(
        "Main pass complete: %d (unit, graph_id) frontiers built in %.1fs", n_done, runtime_total
    )
    return candidates_by_query


# ---------------------------------------------------------------------------
# Stage 3/4: discovery + selection over the main pass
# ---------------------------------------------------------------------------


def _relevance_maps_from_units(units: list[dict], candidates_by_query: dict) -> dict[tuple, dict]:
    by_dataset_query = {(u["dataset"], u["query_id"]): u.get("relevance_map") or {} for u in units}
    return {key: by_dataset_query[(key[0], key[1])] for key in candidates_by_query}


def run_discovery_and_selection(
    candidates_by_query: dict[tuple, list[FrontierCandidate]],
    relevance_maps: dict[tuple, dict],
    output_dir: Path,
) -> dict:
    outcomes_by_query = {}
    for key, candidates in candidates_by_query.items():
        rel = relevance_maps[key]
        if not rel:
            continue  # nDCG is undefined without any relevance labels for this query
        outcomes_by_query[key] = evaluate_query_frontier(candidates, rel, key=key, ndcg_k=MAIN_TOPK)
    outcomes = list(outcomes_by_query.values())

    discovery = compute_discovery_result(outcomes)
    localization = localization_summary(outcomes, candidates_by_query)
    selection = evaluate_selection(
        candidates_by_query, relevance_maps, outcomes_by_query, ndcg_k=MAIN_TOPK
    )

    discovery_dir = output_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        discovery_dir / "FRONTIER_ORACLE_HEADROOM.json",
        {**discovery.to_dict(), "localization": localization},
    )
    best_method_path = discovery_dir / "oracle_best_method_per_query.jsonl"
    with best_method_path.open("w", encoding="utf-8") as fh:
        for key, method in discovery.oracle_best_method_per_query.items():
            entry = {"dataset": key[0], "query_id": key[1], "oracle_best_method": method}
            fh.write(json.dumps(entry) + "\n")

    selection_dir = output_dir / "selection"
    selection_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(selection_dir / "STAGE_SELECTION.json", selection)

    return {
        "discovery": discovery,
        "localization": localization,
        "selection": selection,
        "n_queries_with_relevance": len(outcomes),
    }


# ---------------------------------------------------------------------------
# Stage 5: sensitivity sweeps
# ---------------------------------------------------------------------------


def _discovery_headroom_for_config(units: list[dict], **frontier_kwargs) -> dict:
    """Rebuild the frontier for every (unit, graph_id) under one sensitivity
    configuration and return just the discovery summary (not full candidate
    dumps, to keep sensitivity output small)."""
    outcomes = []
    for unit in units:
        dataset, query_id = unit["dataset"], unit["query_id"]
        relevance_map = unit.get("relevance_map") or {}
        if not relevance_map:
            continue
        confidences = compute_edge_confidence(unit["provider_prefs"])
        for graph_id, graph in graphs_for_unit(unit).items():
            key = (dataset, query_id, unit["source"], unit["variant"], graph_id)
            try:
                candidates = build_repair_frontier(
                    graph, dataset, query_id, relevance_map=relevance_map,
                    confidences=confidences, **frontier_kwargs,
                )
            except Exception:  # noqa: BLE001 - sensitivity point failures are skipped, not fatal
                continue
            ndcg_k = frontier_kwargs.get("topk", MAIN_TOPK)
            outcome = evaluate_query_frontier(candidates, relevance_map, key=key, ndcg_k=ndcg_k)
            outcomes.append(outcome)
    if not outcomes:
        return {"n_queries": 0}
    result = compute_discovery_result(outcomes)
    return {
        "n_queries": len(outcomes),
        "headroom": result.mean_headroom,
        "headroom_ci_lower": result.headroom_ci.lower,
        "headroom_ci_upper": result.headroom_ci.upper,
        "decision": result.decision,
        "frac_beneficial": result.frac_queries_with_beneficial_candidate,
    }


def run_sensitivity_sweep(
    units: list[dict], candidates_by_query: dict[tuple, list[FrontierCandidate]],
    relevance_maps: dict[tuple, dict], output_dir: Path,
) -> list[dict]:
    rows: list[dict] = []

    for tau in SENSITIVITY_CONFIDENCE_TAUS:
        rule = EdgeProtectionRule(kind="confidence_threshold", reliability_tau=tau)
        summary = _discovery_headroom_for_config(
            units, protection_rules=[rule], conservative_margin=MAIN_CONSERVATIVE_MARGIN,
            topk=MAIN_TOPK, exact_max_n=MAIN_EXACT_MAX_N,
        )
        rows.append({"dimension": "confidence_threshold_tau", "value": tau, **summary})

    for tau in SENSITIVITY_MARGIN_TAUS:
        rule = EdgeProtectionRule(kind="margin_threshold", margin_tau=tau)
        summary = _discovery_headroom_for_config(
            units, protection_rules=[rule], conservative_margin=MAIN_CONSERVATIVE_MARGIN,
            topk=MAIN_TOPK, exact_max_n=MAIN_EXACT_MAX_N,
        )
        rows.append({"dimension": "margin_threshold_tau", "value": tau, **summary})

    for margin in SENSITIVITY_CONSERVATIVE_MARGINS:
        rule = EdgeProtectionRule(kind="unanimous_multi_provider", min_providers_for_unanimity=2)
        summary = _discovery_headroom_for_config(
            units, protection_rules=[rule], conservative_margin=margin,
            topk=MAIN_TOPK, exact_max_n=MAIN_EXACT_MAX_N,
        )
        rows.append({"dimension": "conservative_acceptance_margin", "value": margin, **summary})

    for topk in SENSITIVITY_TOPKS:
        summary = _discovery_headroom_for_config(
            units, protection_rules=MAIN_PROTECTION_RULES,
            conservative_margin=MAIN_CONSERVATIVE_MARGIN, topk=topk, exact_max_n=MAIN_EXACT_MAX_N,
        )
        rows.append({"dimension": "topk", "value": topk, **summary})

    # Post-hoc dimensions (no rebuild -- restrict the MAIN pass's already-
    # built candidates to a method-family subset per query, since these are
    # just different views of the same generated candidate set).
    def _restricted_discovery(prefixes: tuple[str, ...]) -> dict:
        outcomes = []
        for key, candidates in candidates_by_query.items():
            rel = relevance_maps[key]
            if not rel:
                continue
            incumbent = next((c for c in candidates if c.candidate_id == "incumbent"), None)
            pool = [
                c for c in candidates
                if c.candidate_id == "incumbent" or c.candidate_id.startswith(prefixes)
            ]
            if incumbent is None or len(pool) < 2:
                continue
            outcomes.append(evaluate_query_frontier(pool, rel, key=key, ndcg_k=MAIN_TOPK))
        if not outcomes:
            return {"n_queries": 0}
        result = compute_discovery_result(outcomes)
        return {
            "n_queries": len(outcomes),
            "headroom": result.mean_headroom,
            "headroom_ci_lower": result.headroom_ci.lower,
            "headroom_ci_upper": result.headroom_ci.upper,
            "decision": result.decision,
            "frac_beneficial": result.frac_queries_with_beneficial_candidate,
        }

    greedy_summary = _restricted_discovery(("scc_local_greedy",))
    exact_summary = _restricted_discovery(("scc_local_exact",))
    whole_graph_summary = _restricted_discovery(("whole_graph_",))
    scc_local_summary = _restricted_discovery(("scc_local_",))
    rows.append({"dimension": "local_method", "value": "greedy_only", **greedy_summary})
    rows.append({"dimension": "local_method", "value": "exact_only", **exact_summary})
    rows.append({"dimension": "repair_scope", "value": "whole_graph_only", **whole_graph_summary})
    rows.append({"dimension": "repair_scope", "value": "scc_local_only", **scc_local_summary})

    sensitivity_dir = output_dir / "sensitivity"
    sensitivity_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for r in rows for k in r})
    import csv

    with (sensitivity_dir / "SENSITIVITY_TABLES.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return rows


# ---------------------------------------------------------------------------
# Stage 6: final report
# ---------------------------------------------------------------------------


def _method_family(candidate_id: str) -> str:
    if candidate_id == "incumbent":
        return "incumbent (no benefit found)"
    if candidate_id.startswith("alt_extraction_"):
        return "alt_extraction"
    if candidate_id.startswith("scc_local_protected_"):
        return "scc_local_protected"
    if candidate_id.startswith("scc_local_"):
        return "scc_local (unprotected)"
    if candidate_id.startswith("whole_graph_"):
        return "whole_graph"
    return candidate_id


def _oracle_best_method_attribution(discovery) -> dict[str, int]:
    """Which method FAMILY produced the oracle-best candidate, aggregated
    across queries -- directly answers "is benefit localized to particular
    methods" (report questions 1/2/4) with concrete counts rather than a
    pointer to a raw file."""
    counts: dict[str, int] = {}
    for candidate_id in discovery.oracle_best_method_per_query.values():
        family = _method_family(candidate_id)
        counts[family] = counts.get(family, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def _sensitivity_row(rows: list[dict], dimension: str, value) -> dict | None:
    return next((r for r in rows if r["dimension"] == dimension and r["value"] == value), None)


def _repair_scope_comparison_text(rows: list[dict]) -> str:
    whole = _sensitivity_row(rows, "repair_scope", "whole_graph_only")
    scc = _sensitivity_row(rows, "repair_scope", "scc_local_only")
    if whole is None or scc is None or not whole.get("n_queries") or not scc.get("n_queries"):
        return "Insufficient data to compare (one of the two restricted pools was empty)."
    if scc["headroom"] > whole["headroom"]:
        winner, loser = "SCC-local", "whole-graph"
        winner_h, loser_h = scc["headroom"], whole["headroom"]
    elif whole["headroom"] > scc["headroom"]:
        winner, loser = "whole-graph", "SCC-local"
        winner_h, loser_h = whole["headroom"], scc["headroom"]
    else:
        winner = None
    if winner is None:
        return (
            f"No difference: whole-graph-only headroom ({whole['headroom']:.6f}) equals "
            f"SCC-local-only headroom ({scc['headroom']:.6f})."
        )
    return (
        f"{winner}-only headroom ({winner_h:.6f}) exceeds {loser}-only headroom "
        f"({loser_h:.6f}) restricted to the same candidate pool."
    )


def _protection_sensitivity_text(rows: list[dict], attribution: dict[str, int]) -> str:
    protected_wins = attribution.get("scc_local_protected", 0)
    dims = ("confidence_threshold_tau", "margin_threshold_tau", "conservative_acceptance_margin")
    headrooms_by_dim = {
        dim: {r["value"]: r["headroom"] for r in rows if r["dimension"] == dim} for dim in dims
    }
    varies = any(len(set(v.values())) > 1 for v in headrooms_by_dim.values() if v)
    if protected_wins == 0 and not varies:
        return (
            "No protected-candidate family ever won the oracle-best race in this dataset "
            "(see the attribution above), so varying protection-rule threshold/margin left "
            "discovery headroom completely unchanged across the confidence_threshold_tau, "
            "margin_threshold_tau, and conservative_acceptance_margin sweeps in "
            "`sensitivity/SENSITIVITY_TABLES.csv` -- protection strictness is not the limiting "
            "factor on this data; see `scc_decisions.jsonl` for per-rule abstention/violation "
            "rates."
        )
    return (
        f"Protected candidates won the oracle-best race on {protected_wins} query-graph(s), "
        "and/or headroom varied across the swept thresholds -- see "
        "`sensitivity/SENSITIVITY_TABLES.csv` (`confidence_threshold_tau`, "
        "`margin_threshold_tau`, `conservative_acceptance_margin` rows) for exactly which "
        "settings preserved headroom without eliminating repair activity, and "
        "`scc_decisions.jsonl` for per-rule abstention/violation rates."
    )


def write_final_report(
    output_dir: Path, discovery_result: dict, sensitivity_rows: list[dict], runtime_s: float
) -> None:
    discovery = discovery_result["discovery"]
    localization = discovery_result["localization"]
    selection = discovery_result["selection"]
    attribution = _oracle_best_method_attribution(discovery)

    headroom_meaningful = discovery.decision == "MEANINGFUL_HEADROOM"
    selector_beats_preserve = selection.get("status") == "SUPPORTED"
    positive_contribution = headroom_meaningful and selector_beats_preserve

    summary = {
        "timestamp": time.time(),
        "runtime_s": runtime_s,
        "n_queries_with_relevance": discovery_result["n_queries_with_relevance"],
        "discovery": discovery.to_dict(),
        "localization": localization,
        "oracle_best_method_attribution": attribution,
        "selection": selection,
        "sensitivity_rows": sensitivity_rows,
        "positive_contribution_claimed": positive_contribution,
    }
    _atomic_write_json(output_dir / "FINAL_SUMMARY.json", summary)

    lines = [
        "# Repair-Frontier Program -- Final Report",
        "",
        f"Runtime: {runtime_s:.1f}s. Queries with relevance labels evaluated: "
        f"{discovery_result['n_queries_with_relevance']}.",
        "",
        "## 1. Does the richer repair frontier contain beneficial rankings the "
        "previous single repair method did not?",
        "",
        f"Frontier oracle headroom (mean of best-candidate-nDCG minus incumbent-nDCG per "
        f"query): **{discovery.mean_headroom:.6f}** "
        f"(one-sided 95% CI [{discovery.headroom_ci.lower:.6f}, "
        f"{discovery.headroom_ci.upper:.6f}]). "
        f"Beneficial/neutral/harmful query counts: {discovery.n_beneficial}/{discovery.n_neutral}/"
        f"{discovery.n_harmful}. Best/median/worst per-query delta: "
        f"{discovery.best_delta:.6f}/{discovery.median_delta:.6f}/{discovery.worst_delta:.6f}. "
        f"Decision: **{discovery.decision}**. Yes, in the narrow sense that "
        f"{discovery.n_beneficial}/{discovery.n_queries} query-graphs had at least one "
        "candidate beat the incumbent (vs. 0 in the original single-method pilot); the "
        "oracle-best-method attribution below shows WHICH methods account for this.",
        "",
        f"Oracle-best-method attribution (which method family won the per-query oracle race, "
        f"aggregated over all {discovery.n_queries} query-graphs): "
        f"{json.dumps(attribution)}.",
        "",
        "## 2. Does SCC-local repair produce more headroom than whole-graph repair?",
        "",
        (
            _repair_scope_comparison_text(sensitivity_rows)
            + " See `sensitivity/SENSITIVITY_TABLES.csv` rows with `dimension=repair_scope` "
            "for the full comparison (restricted to the main pass's own already-generated "
            "candidates for a like-for-like comparison)."
        ),
        "",
        "## 3. Does incumbent protection reduce harmful changes?",
        "",
        "Harmful changes (delta < 0) are 0 by construction across the whole frontier "
        "(the incumbent is always itself a candidate, so no candidate can score below it in "
        "this oracle-discovery framing) -- protection's effect is therefore visible in "
        "`scc_decisions.jsonl`'s `protected_edge_violations` (how often a protected edge had "
        "to be touched anyway to break a cycle) and `acceptance_by_mode` (how often each "
        "acceptance mode would have deployed vs. abstained), not in a harmful-fraction "
        "reduction that has no headroom to begin with.",
        "",
        "## 4. Which protection rules preserve quality without eliminating all repair activity?",
        "",
        _protection_sensitivity_text(sensitivity_rows, attribution),
        "",
        "## 5. Can any observable rule select beneficial candidates on held-out queries?",
        "",
        f"Selection status: **{selection.get('status')}**. {selection.get('reason', '')}",
        "",
        "## 6. If not, is the limiting factor candidate generation or candidate selection?",
        "",
        (
            "Both generation and selection cleared their bars on this data."
            if positive_contribution
            else (
                "Generation found no meaningful oracle headroom (candidate-generation-limited); "
                "selection was not meaningfully evaluated beyond this."
                if not headroom_meaningful
                else "Generation found oracle headroom, but no evaluated selector (fixed or "
                "predictive) realized it on held-out queries (selection-limited, not "
                "generation-limited)."
            )
        ),
        "",
        "## Localization",
        "",
        f"Of {localization['n_beneficial_queries']} queries where the oracle-best candidate "
        f"beat the incumbent, {localization['n_beneficial_with_scc_modification']} involved an "
        f"SCC modification and {localization['n_beneficial_with_topk_membership_change']} "
        "involved a top-k membership change.",
        "",
        "## Bottom line",
        "",
        (
            "**Positive contribution claimed**: frontier headroom is meaningful "
            "(go/no-go PROCEED_TO_LABELING) AND a deployable selector beats always-preserve."
            if positive_contribution
            else "**No positive contribution claimed** on this data -- either the frontier's "
            "oracle headroom does not clear the pre-registered gate, or no evaluated selector "
            "(fixed or predictive) beats always-preserve on held-out queries. See sections 1-6 "
            "above for which."
        ),
        "",
        "## Files in this directory",
        "",
        "- `RUN_CONFIG.json`, `checkpoint/{frontier_results.jsonl,progress.json}`",
        "- `scc_decisions.jsonl`, `feature_rows.jsonl`, `failures.jsonl`",
        "- `discovery/{FRONTIER_ORACLE_HEADROOM.json,oracle_best_method_per_query.jsonl}`",
        "- `selection/STAGE_SELECTION.json`, `sensitivity/SENSITIVITY_TABLES.csv`",
        "- `runtime_stats.json`, `ENVIRONMENT_pip_freeze.txt`",
        "- `FINAL_SUMMARY.json` (this report's machine-readable twin)",
        "",
    ]
    (output_dir / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def write_environment_snapshot(output_dir: Path) -> None:
    import subprocess

    try:
        freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True
        ).stdout
    except Exception as exc:  # noqa: BLE001
        freeze = f"pip freeze failed: {exc}"
    (output_dir / "ENVIRONMENT_pip_freeze.txt").write_text(freeze, encoding="utf-8")


def run_config_snapshot() -> dict:
    return {
        "main_protection_rules": [r.rule_id for r in MAIN_PROTECTION_RULES],
        "main_topk": MAIN_TOPK,
        "main_conservative_margin": MAIN_CONSERVATIVE_MARGIN,
        "main_weak_edge_tau": MAIN_WEAK_EDGE_TAU,
        "main_exact_max_n": MAIN_EXACT_MAX_N,
        "sensitivity_confidence_taus": SENSITIVITY_CONFIDENCE_TAUS,
        "sensitivity_margin_taus": SENSITIVITY_MARGIN_TAUS,
        "sensitivity_conservative_margins": SENSITIVITY_CONSERVATIVE_MARGINS,
        "sensitivity_topks": SENSITIVITY_TOPKS,
        "sources": [str(POOL6_DIR), str(REVIEWER_CONCERNS_DIR)],
    }


def run_program(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(output_dir / "RUN_CONFIG.json", run_config_snapshot())
    write_environment_snapshot(output_dir)

    t_start = time.time()
    units = load_all_units()
    log.info(
        "Loaded %d units (source/variant/dataset/query) from the two finished pilots", len(units)
    )

    candidates_by_query = run_main_pass(units, output_dir)
    relevance_maps = _relevance_maps_from_units(units, candidates_by_query)

    discovery_result = run_discovery_and_selection(candidates_by_query, relevance_maps, output_dir)
    sensitivity_rows = run_sensitivity_sweep(units, candidates_by_query, relevance_maps, output_dir)

    runtime_s = time.time() - t_start
    _atomic_write_json(
        output_dir / "runtime_stats.json",
        {
            "runtime_s": runtime_s,
            "n_units": len(units),
            "n_frontiers_built": len(candidates_by_query),
        },
    )
    write_final_report(output_dir, discovery_result, sensitivity_rows, runtime_s)

    return {
        "n_units": len(units),
        "n_frontiers_built": len(candidates_by_query),
        "runtime_s": runtime_s,
        "discovery_decision": discovery_result["discovery"].decision,
        "selection_status": discovery_result["selection"].get("status"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    run_tag = f"run_{int(time.time())}"
    log_path = _setup_logging(args.output_dir, run_tag)
    log.info("Logging to %s", log_path)

    result = run_program(args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
