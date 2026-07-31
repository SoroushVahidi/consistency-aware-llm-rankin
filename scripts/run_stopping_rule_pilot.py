#!/usr/bin/env python
"""
run_stopping_rule_pilot.py
===========================
CLI driver for the risk-controlled stopping-rule pilot: can the regularized
partial-information rank aggregator support a practical, qrel-free stopping
rule that terminates pairwise acquisition early while preserving top-k
quality and controlling harmful premature stopping?

Uses the same frozen, pre-existing, exhaustive real OpenAI (gpt-4o-mini)
pairwise SciDocs judgments and the same 15/35 dev/test query split as
``regularized_aggregation_pilot_v1``. No live provider or API calls; no new
judgments collected; qrels are used only for post-hoc evaluation labels
(Phase 6), never inside the stopping decision itself.

Two stages, invoked together (the expensive per-step simulation is cached to
disk so re-running with the same --output-dir resumes rather than
re-simulating):

1. **Simulate** (expensive): for each (query, acquisition order), replay a
   fixed revealed-edge sequence up to a coverage cap, and at every step
   record: the exact, frozen regularized-aggregation ranking/nDCG at that
   step, and the (deterministic, warm-started) counterfactual worst-case
   top-k-change statistic used by the primary stopping rule
   (``stopping.worst_case_topk_change``).
2. **Analyze** (cheap): apply one or more (tau, patience) threshold settings
   -- and the simple recent-stability baseline rule -- to the *same* cached
   per-step history, with no re-simulation, to determine each setting's stop
   point and downstream metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from consistency_ranker.active_acquisition.evaluate import evaluate_ranking  # noqa: E402
from consistency_ranker.active_acquisition.oracle import (  # noqa: E402
    QueryOracle,
    load_scidocs_pairwise_oracle,
)
from consistency_ranker.active_acquisition.regularized_aggregation import (  # noqa: E402
    SCHEDULES,
    fit_bt_utilities,
    rank_from_utilities,
)
from consistency_ranker.active_acquisition.scoring import normalize_bm25  # noqa: E402
from consistency_ranker.active_acquisition.simulate import (  # noqa: E402
    _static_order,
    reference_rankings,
)
from consistency_ranker.active_acquisition.stats import paired_comparison  # noqa: E402
from consistency_ranker.active_acquisition.stopping import (  # noqa: E402
    apply_counterfactual_rule,
    apply_simple_rule,
    worst_case_topk_change,
)
from consistency_ranker.statistical_inference import (  # noqa: E402
    holm_adjust,
    proportion_interval,
)

STATISTICAL_ANALYSIS_SCHEMA_VERSION = 2
# v2 (this file): binary-proportion rates (severe_harm, premature_stop,
# run_status.*_rate) use proportion_interval() (Wilson by default), not a
# nonparametric bootstrap over a 0/1 indicator -- a bootstrap of an all-zero
# or all-one sample is degenerate and collapses to a zero-width interval,
# understating uncertainty. v2 also adds the "run_status" section
# (n_stopped/n_capped/n_failed) so capped (censored, non-triggering) walks
# are explicit and machine-readable rather than inferable only from
# lower-level rows. Continuous paired-mean statistics (primary_comparisons,
# severe_harm_rate_reduction-style paired differences) are unaffected and
# remain bootstrap-based. Readers of older (v1, unversioned) files should
# treat any *_ci95_lower/upper next to a *_rate field for severe_harm or
# premature_stop as bootstrap-derived and potentially degenerate at 0/n or
# n/n; readers of v2+ files can rely on schema_version to know which applies.

PREMATURE_STOP_NDCG_MARGIN = 0.02  # qrel-bearing evaluation LABEL only, frozen (Phase 6)


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


def _pair_sequence(oe: QueryOracle, order: str, seed: int) -> list[frozenset]:
    candidates = oe.candidates
    if order == "random":
        seq = _all_pairs(candidates)
        random.Random(seed).shuffle(seq)
        return seq
    if order == "static_adjacent":
        return _static_order(candidates, oe.bm25_scores)
    raise ValueError(order)


def _dev_test_split(query_ids: list[str], n_dev: int, seed: int) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)
    shuffled = sorted(query_ids)
    rng.shuffle(shuffled)
    dev = sorted(shuffled[:n_dev])
    test = sorted(shuffled[n_dev:])
    return dev, test


# ---------------------------------------------------------------------------
# Stage 1: simulate (expensive, cached)
# ---------------------------------------------------------------------------


def simulate_query_history(
    oe: QueryOracle,
    order: str,
    seed: int,
    schedule_name: str,
    k: int,
    cap_budget: int,
) -> list[dict]:
    candidates = oe.candidates
    bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
    n_pairs = len(candidates) * (len(candidates) - 1) // 2
    schedule = SCHEDULES[schedule_name]
    relevance = oe.relevance
    _, exhaustive_ranking = reference_rankings(oe, seed=seed)

    pair_seq = _pair_sequence(oe, order, seed)
    remaining = list(pair_seq)
    revealed: list[tuple[str, str]] = []

    history: list[dict] = []
    for step in range(1, min(cap_budget, n_pairs) + 1):
        t0 = time.perf_counter()
        pair = pair_seq[step - 1]
        i, j = sorted(pair)
        winner, loser = oe.reveal(i, j)
        revealed.append((winner, loser))
        remaining.remove(pair)

        coverage = len(revealed) / n_pairs
        lam = schedule(coverage)
        utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam)
        ranking = rank_from_utilities(candidates, utilities, bm25_norm)
        ndcg, overlap_exh, tau_exh = evaluate_ranking(ranking, relevance, exhaustive_ranking, k=k)

        wc = worst_case_topk_change(
            candidates, revealed, bm25_norm, n_pairs, schedule, remaining, k, utilities
        )
        dt = time.perf_counter() - t0

        history.append(
            dict(
                step=step,
                coverage=coverage,
                ndcg=ndcg,
                topk=ranking[:k],
                topk_overlap_vs_exhaustive=overlap_exh,
                kendall_tau_vs_exhaustive=tau_exh,
                worst_case_scalar=wc.scalar,
                worst_case_membership=wc.membership,
                worst_case_ordering=wc.ordering,
                worst_case_displacement=wc.displacement,
                triggering_pair=list(wc.triggering_pair) if wc.triggering_pair else None,
                triggering_outcome=wc.triggering_outcome,
                n_pairs_considered=wc.n_pairs_considered,
                decision_runtime_s=dt,
            )
        )
    return history


def run_simulate(output_dir: Path, config: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = _REPO_ROOT / config["judgments_path"]
    oracles = load_scidocs_pairwise_oracle(judgments_path)
    query_ids = sorted(oracles)
    dev_ids, test_ids = _dev_test_split(
        query_ids, config["n_dev_queries"], config["dev_split_seed"]
    )

    k = config["primary_cutoff_k"]
    seed = config["seed"]
    schedule_name = config["frozen_schedule"]
    n_pairs = (
        config["candidate_pool_size_expected"] * (config["candidate_pool_size_expected"] - 1) // 2
    )
    cap_budget = round(config["max_simulated_budget_fraction"] * n_pairs)

    # (order, query_id) work items: random order on dev+test; static_adjacent
    # (secondary robustness check, Phase 3/9 H4) on test only.
    work: list[tuple[str, str]] = [("random", q) for q in query_ids]
    work += [("static_adjacent", q) for q in test_ids]

    raw_path = output_dir / "raw_stopping_histories.jsonl"
    done: set[tuple[str, str]] = set()
    if raw_path.exists():
        with raw_path.open() as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    done.add((rec["order"], rec["query_id"]))
        print(f"[resume] {len(done)} (order, query) pairs already computed, skipping them")

    t_start = time.time()
    with raw_path.open("a") as out:
        for idx, (order, qid) in enumerate(work):
            if (order, qid) in done:
                continue
            history = simulate_query_history(
                oracles[qid], order, seed, schedule_name, k, cap_budget
            )
            out.write(json.dumps(dict(order=order, query_id=qid, history=history)) + "\n")
            out.flush()
            if (idx + 1) % 5 == 0 or idx + 1 == len(work):
                print(f"[{idx + 1}/{len(work)}] {order}/{qid} done ({time.time() - t_start:.1f}s)")

    manifest = dict(
        protocol=config["protocol"],
        input_judgments_sha256=_sha256_file(judgments_path),
        n_queries=len(query_ids),
        dev_query_ids=dev_ids,
        test_query_ids=test_ids,
        cap_budget=cap_budget,
        n_pairs_per_query=n_pairs,
        seed=seed,
        frozen_schedule=schedule_name,
    )
    with (output_dir / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {raw_path}")


# ---------------------------------------------------------------------------
# Stage 2: analyze (cheap, post-hoc threshold application)
# ---------------------------------------------------------------------------


def row_at_budget(history: list[dict], budget: int) -> dict:
    for row in history:
        if row["step"] == budget:
            return row
    return history[-1]


def run_analyze(sim_dir: Path, output_dir: Path, config: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((sim_dir / "MANIFEST.json").read_text())
    dev_ids = set(manifest["dev_query_ids"])
    test_ids = set(manifest["test_query_ids"])
    n_pairs = manifest["n_pairs_per_query"]
    k = config["primary_cutoff_k"]

    records: dict[tuple[str, str], list[dict]] = {}
    with (sim_dir / "raw_stopping_histories.jsonl").open() as f:
        for line in f:
            rec = json.loads(line)
            records[(rec["order"], rec["query_id"])] = rec["history"]

    all_query_ids = sorted(dev_ids | test_ids)
    expected_keys = {("random", q) for q in all_query_ids} | {
        ("static_adjacent", q) for q in test_ids
    }
    missing = expected_keys - set(records)
    if missing:
        raise RuntimeError(
            f"Refusing to analyze an incomplete simulate run: {len(missing)} of "
            f"{len(expected_keys)} expected (order, query_id) walks are missing from "
            f"{sim_dir / 'raw_stopping_histories.jsonl'} (e.g. {sorted(missing)[:5]}). "
            "Re-run `simulate` on this --output-dir to resume and complete it before "
            "analyzing -- analyzing a truncated simulate run would silently produce a "
            "complete-looking report over incomplete data."
        )
    extra = set(records) - expected_keys
    if extra:
        raise RuntimeError(
            f"raw_stopping_histories.jsonl contains {len(extra)} (order, query_id) walks "
            f"not in the expected work set for this config (e.g. {sorted(extra)[:5]}) -- "
            "likely a config/data mismatch between simulate and analyze."
        )

    oracles = load_scidocs_pairwise_oracle(_REPO_ROOT / config["judgments_path"])
    seed = config["seed"]
    bm25_ndcg: dict[str, float] = {}
    exhaustive_ndcg: dict[str, float] = {}
    exhaustive_topk: dict[str, list[str]] = {}
    for qid, oe in oracles.items():
        initial_ranking, exhaustive_ranking = reference_rankings(oe, seed=seed)
        ndcg_init, _, _ = evaluate_ranking(initial_ranking, oe.relevance, exhaustive_ranking, k=k)
        ndcg_exh, _, _ = evaluate_ranking(exhaustive_ranking, oe.relevance, exhaustive_ranking, k=k)
        bm25_ndcg[qid] = ndcg_init
        exhaustive_ndcg[qid] = ndcg_exh
        exhaustive_topk[qid] = exhaustive_ranking[:k]

    fixed_budgets = {int(round(f * n_pairs)): f for f in config["fixed_budget_fractions"]}

    settings = config["threshold_settings"]  # list of {"name", "tau", "patience_m"}
    simple_patience = config["simple_rule_patience_m"]

    all_rows: list[dict] = []
    for (order, qid), history in records.items():
        split = "dev" if qid in dev_ids else "test"
        ndcg_bm25 = bm25_ndcg[qid]
        ndcg_exh = exhaustive_ndcg[qid]
        topk_exh = set(exhaustive_topk[qid])

        for setting in settings:
            outcome = apply_counterfactual_rule(history, setting["tau"], setting["patience_m"])
            row = outcome["row"]
            _emit_stopping_row(
                all_rows, "counterfactual_" + setting["name"], order, qid, split, outcome,
                row, ndcg_bm25, ndcg_exh, topk_exh, n_pairs, k,
            )

        simple_outcome = apply_simple_rule(history, simple_patience, k)
        _emit_stopping_row(
            all_rows, "simple_recent_stability", order, qid, split, simple_outcome,
            simple_outcome["row"], ndcg_bm25, ndcg_exh, topk_exh, n_pairs, k,
        )

        for budget in fixed_budgets:
            row = row_at_budget(history, budget)
            fake_outcome = dict(stopped=True, stop_step=row["step"], row=row)
            _emit_stopping_row(
                all_rows, f"fixed_{fixed_budgets[budget]:.2f}", order, qid, split, fake_outcome,
                row, ndcg_bm25, ndcg_exh, topk_exh, n_pairs, k,
            )

        exh_row = dict(
            method="exhaustive", order=order, query_id=qid, split=split,
            stop_step=n_pairs, budget_frac=1.0, stopped=True,
            ndcg=ndcg_exh, ndcg_vs_bm25=ndcg_exh - ndcg_bm25, ndcg_vs_exhaustive=0.0,
            topk_overlap_vs_exhaustive=1.0, exact_topk_match=True,
            severe_harm=False,
            premature_stop_qrel_label=False, premature_instability_qrelfree=False,
        )
        all_rows.append(exh_row)

    _write_csv(output_dir / "stopping_results.csv", all_rows)
    stats_result = _statistical_analysis(all_rows, test_ids, config)
    with (output_dir / "statistical_analysis.json").open("w") as f:
        json.dump(stats_result, f, indent=2, default=str)
    with (output_dir / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote outputs to {output_dir}")


def _emit_stopping_row(
    all_rows: list[dict],
    method: str,
    order: str,
    qid: str,
    split: str,
    outcome: dict,
    row: dict,
    ndcg_bm25: float,
    ndcg_exh: float,
    topk_exh: set[str],
    n_pairs: int,
    k: int,
) -> None:
    stopped_topk = set(row["topk"][:k])
    exact_match = stopped_topk == topk_exh
    ndcg_vs_bm25 = row["ndcg"] - ndcg_bm25
    ndcg_vs_exhaustive = row["ndcg"] - ndcg_exh
    severe_harm = ndcg_vs_bm25 <= -0.05
    premature_qrel = (not exact_match) and ((ndcg_exh - row["ndcg"]) >= PREMATURE_STOP_NDCG_MARGIN)
    premature_qrelfree = not exact_match
    all_rows.append(
        dict(
            method=method,
            order=order,
            query_id=qid,
            split=split,
            stop_step=outcome["stop_step"],
            budget_frac=outcome["stop_step"] / n_pairs,
            stopped=outcome["stopped"],
            ndcg=row["ndcg"],
            ndcg_vs_bm25=ndcg_vs_bm25,
            ndcg_vs_exhaustive=ndcg_vs_exhaustive,
            topk_overlap_vs_exhaustive=row["topk_overlap_vs_exhaustive"],
            exact_topk_match=exact_match,
            severe_harm=severe_harm,
            premature_stop_qrel_label=premature_qrel,
            premature_instability_qrelfree=premature_qrelfree,
        )
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _metric_map(
    rows: list[dict], order: str, method: str, ids: set[str], key: str
) -> dict[str, float]:
    return {
        r["query_id"]: r[key]
        for r in rows
        if r["order"] == order and r["method"] == method and r["query_id"] in ids
    }


def _statistical_analysis(rows: list[dict], test_ids: set[str], config: dict) -> dict:
    order = "random"
    proposed = "counterfactual_" + config["frozen_setting_name"]
    fixed10 = "fixed_0.10"
    fixed20 = "fixed_0.20"

    result: dict = {
        "schema_version": STATISTICAL_ANALYSIS_SCHEMA_VERSION,
        "primary_comparisons": [],
        "severe_harm": {},
        "premature_stop": {},
        "run_status": {},
    }
    records = []
    pvals = []

    def add(label, a_map, b_map):
        common = sorted(set(a_map) & set(b_map))
        deltas = [a_map[q] - b_map[q] for q in common]
        comp = paired_comparison(label, deltas)
        records.append((label, comp))
        pvals.append(comp.pvalue)

    p_ndcg = _metric_map(rows, order, proposed, test_ids, "ndcg")
    f10_ndcg = _metric_map(rows, order, fixed10, test_ids, "ndcg")
    f20_ndcg = _metric_map(rows, order, fixed20, test_ids, "ndcg")
    p_budget = _metric_map(rows, order, proposed, test_ids, "budget_frac")
    f10_budget = _metric_map(rows, order, fixed10, test_ids, "budget_frac")
    f20_budget = _metric_map(rows, order, fixed20, test_ids, "budget_frac")
    simple_ndcg = _metric_map(rows, order, "simple_recent_stability", test_ids, "ndcg")

    add("proposed_vs_fixed10_ndcg", p_ndcg, f10_ndcg)
    add("proposed_vs_fixed20_ndcg", p_ndcg, f20_ndcg)
    add("proposed_vs_fixed10_budget", p_budget, f10_budget)
    add("proposed_vs_fixed20_budget", p_budget, f20_budget)
    add("proposed_vs_simple_ndcg", p_ndcg, simple_ndcg)

    holm_ps = holm_adjust(pvals)
    for (label, comp), holm_p in zip(records, holm_ps):
        result["primary_comparisons"].append(
            dict(
                label=label, n=comp.n, mean_delta=comp.mean_delta, cohen_d=comp.cohen_d,
                ci95_lower=comp.ci_lower, ci95_upper=comp.ci_upper,
                sign_flip_pvalue=comp.pvalue, holm_pvalue=holm_p,
                wins=comp.wins, ties=comp.ties, losses=comp.losses,
            )
        )

    for method in (proposed, fixed10, fixed20, "simple_recent_stability"):
        sev = list(_metric_map(rows, order, method, test_ids, "severe_harm").values())
        prem_qrel = list(
            _metric_map(rows, order, method, test_ids, "premature_stop_qrel_label").values()
        )
        prem_free = list(
            _metric_map(rows, order, method, test_ids, "premature_instability_qrelfree").values()
        )
        stopped_flags = list(_metric_map(rows, order, method, test_ids, "stopped").values())
        n = len(sev)
        n_sev = sum(1 for x in sev if x)
        n_prem_qrel = sum(1 for x in prem_qrel if x)
        n_stopped = sum(1 for x in stopped_flags if x)
        # "Capped" = the rule never triggered patience within the simulation
        # budget cap and was evaluated at the cap budget instead (censored,
        # not a triggered stop). n_failed is reserved for optimizer/solver
        # failures; no failure-detection instrumentation exists yet in
        # stopping.py, so it is always 0 here, not a claim that failures are
        # impossible.
        n_capped = n - n_stopped
        n_failed = 0

        ci_sev = proportion_interval(n_sev, n) if n else proportion_interval(0, 0)
        ci_prem = proportion_interval(n_prem_qrel, n) if n else proportion_interval(0, 0)
        ci_stopped = proportion_interval(n_stopped, n) if n else proportion_interval(0, 0)
        ci_capped = proportion_interval(n_capped, n) if n else proportion_interval(0, 0)

        result["severe_harm"][method] = dict(
            n=n, rate=n_sev / n if n else None,
            ci_method=ci_sev.method,
            ci95_lower=ci_sev.lower, ci95_upper=ci_sev.upper,
        )
        result["premature_stop"][method] = dict(
            n=n, qrel_label_rate=n_prem_qrel / n if n else None,
            ci_method=ci_prem.method,
            ci95_lower=ci_prem.lower, ci95_upper=ci_prem.upper,
            qrelfree_instability_rate=sum(1 for x in prem_free if x) / n if n else None,
        )
        result["run_status"][method] = dict(
            n_total_runs=n,
            n_stopped=n_stopped,
            n_capped=n_capped,
            n_failed=n_failed,
            stopped_rate=n_stopped / n if n else None,
            stopped_rate_ci_method=ci_stopped.method,
            stopped_rate_ci95_lower=ci_stopped.lower,
            stopped_rate_ci95_upper=ci_stopped.upper,
            capped_rate=n_capped / n if n else None,
            capped_rate_ci_method=ci_capped.method,
            capped_rate_ci95_lower=ci_capped.lower,
            capped_rate_ci95_upper=ci_capped.upper,
            cap_budget_fraction=config["max_simulated_budget_fraction"],
            capped_runs_included_in_headline_aggregates=True,
        )

    return result


# ---------------------------------------------------------------------------
# Mode: mechanism (Phase 9, exploratory only)
# ---------------------------------------------------------------------------


def _revealed_up_to_step(
    oe: QueryOracle, order: str, seed: int, stop_step: int
) -> list[tuple[str, str]]:
    pair_seq = _pair_sequence(oe, order, seed)
    revealed = []
    for pair in pair_seq[:stop_step]:
        i, j = sorted(pair)
        revealed.append(oe.reveal(i, j))
    return revealed


def _has_cycle(candidates: tuple[str, ...], revealed: list[tuple[str, str]]) -> bool:
    import networkx as nx

    from consistency_ranker.graph_construction import build_graph
    from consistency_ranker.pairwise_prefs import Preference

    prefs = [Preference(w, loser, 1.0) for w, loser in revealed]
    graph = build_graph(prefs) if prefs else nx.DiGraph()
    graph.add_nodes_from(candidates)
    return not nx.is_directed_acyclic_graph(graph)


def run_mechanism(analyze_dir: Path, output_dir: Path, config: dict) -> None:
    """Exploratory-only association analysis (Phase 9): why does the primary
    stopping rule stop early, late, or (sometimes) wrongly? Not a validated
    predictor -- reports simple group summaries and predeclared-criterion
    examples, not a fitted model."""
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = config["seed"]
    k = config["primary_cutoff_k"]
    order = "random"
    method = "counterfactual_" + config["frozen_setting_name"]

    oracles = load_scidocs_pairwise_oracle(_REPO_ROOT / config["judgments_path"])
    results = {}
    import csv

    with (analyze_dir / "stopping_results.csv").open() as f:
        for row in csv.DictReader(f):
            if row["order"] == order and row["method"] == method and row["split"] == "test":
                results[row["query_id"]] = row

    rows_out = []
    for qid, row in results.items():
        oe = oracles[qid]
        candidates = oe.candidates
        bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
        initial_ranking, exhaustive_ranking = reference_rankings(oe, seed=seed)
        ndcg_bm25, _, _ = evaluate_ranking(initial_ranking, oe.relevance, exhaustive_ranking, k=k)
        ndcg_exh, _, _ = evaluate_ranking(exhaustive_ranking, oe.relevance, exhaustive_ranking, k=k)

        bm25_gap_at_cutoff = bm25_norm[initial_ranking[k - 1]] - bm25_norm[initial_ranking[k]]
        stop_step = int(row["stop_step"])
        revealed = _revealed_up_to_step(oe, order, seed, stop_step)
        upsets = sum(1 for w, loser in revealed if bm25_norm[w] < bm25_norm[loser])
        upset_fraction = upsets / len(revealed) if revealed else 0.0
        cycle_at_stop = _has_cycle(candidates, revealed)

        rows_out.append(
            dict(
                query_id=qid,
                stop_budget_frac=float(row["budget_frac"]),
                stopped=row["stopped"] == "True",
                ndcg_vs_bm25=float(row["ndcg_vs_bm25"]),
                premature_stop_qrel_label=row["premature_stop_qrel_label"] == "True",
                exhaustive_improvement_available=ndcg_exh - ndcg_bm25,
                bm25_gap_at_cutoff=bm25_gap_at_cutoff,
                upset_fraction_in_revealed=upset_fraction,
                has_cycle_at_stop=cycle_at_stop,
                n_revealed_at_stop=len(revealed),
            )
        )

    rows_out.sort(key=lambda r: (r["stop_budget_frac"], r["query_id"]))
    n = len(rows_out)
    tercile = max(n // 3, 1)
    early = rows_out[:tercile]
    late = rows_out[-tercile:]
    mid = rows_out[tercile : n - tercile]

    def _mean(group, key):
        vals = [r[key] for r in group]
        return sum(vals) / len(vals) if vals else None

    factors = [
        "exhaustive_improvement_available", "bm25_gap_at_cutoff",
        "upset_fraction_in_revealed", "n_revealed_at_stop",
    ]
    summary = {
        "n_queries": n,
        "early_stop_group": dict(
            n=len(early), mean_budget_frac=_mean(early, "stop_budget_frac"),
            **{f: _mean(early, f) for f in factors},
            frac_cycle_at_stop=_mean(early, "has_cycle_at_stop"),
        ),
        "mid_group": dict(
            n=len(mid), mean_budget_frac=_mean(mid, "stop_budget_frac"),
            **{f: _mean(mid, f) for f in factors},
            frac_cycle_at_stop=_mean(mid, "has_cycle_at_stop"),
        ),
        "late_or_capped_group": dict(
            n=len(late), mean_budget_frac=_mean(late, "stop_budget_frac"),
            **{f: _mean(late, f) for f in factors},
            frac_cycle_at_stop=_mean(late, "has_cycle_at_stop"),
        ),
    }

    premature = [r for r in rows_out if r["premature_stop_qrel_label"]]
    premature.sort(key=lambda r: (r["stop_budget_frac"], r["query_id"]))

    examples = dict(
        earliest_stop=rows_out[0] if rows_out else None,
        latest_stop_or_capped=rows_out[-1] if rows_out else None,
        earliest_premature_stop_failure=premature[0] if premature else None,
    )

    with (output_dir / "mechanism_summary.json").open("w") as f:
        json.dump(dict(disclaimer="EXPLORATORY ONLY -- not a validated predictor",
                        group_summary=summary, examples=examples), f, indent=2)
    _write_csv(output_dir / "mechanism_per_query.csv", rows_out)
    print(f"Wrote mechanism analysis to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["simulate", "analyze", "mechanism"], required=True)
    parser.add_argument("--sim-dir", type=Path, help="required for --mode analyze/mechanism")
    parser.add_argument("--analyze-dir", type=Path, help="required for --mode mechanism")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=_REPO_ROOT / "configs/stopping_rule_pilot_v1.json"
    )
    args = parser.parse_args()
    with args.config.open() as f:
        config = json.load(f)

    if args.mode == "simulate":
        run_simulate(args.output_dir, config)
    elif args.mode == "analyze":
        sim_dir = args.sim_dir or args.output_dir
        run_analyze(sim_dir, args.output_dir, config)
    else:
        analyze_dir = args.analyze_dir or args.output_dir
        run_mechanism(analyze_dir, args.output_dir, config)


if __name__ == "__main__":
    main()
