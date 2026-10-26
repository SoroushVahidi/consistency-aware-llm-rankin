"""Matched existing repair/evaluation code; raw evidence remains private."""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np

from .common import (
    SEED,
    WORKTREE,
    atomic,
    database,
    digest,
    filehash,
    now,
    paired_disposition,
    requests_for,
    response_rows,
)

sys.path.insert(0, str(WORKTREE / "src"))
from consistency_ranker.baseline_ranking import copeland_ranking  # noqa: E402
from consistency_ranker.evaluation import ndcg_at_k  # noqa: E402
from consistency_ranker.greedy_fas import greedy_fas  # noqa: E402
from consistency_ranker.mwfas_solver import (  # noqa: E402
    _solve_scip,
    verify_canonical_solver_version,
)
from consistency_ranker.statistical_inference import (  # noqa: E402
    holm_adjust,
    proportion_interval,
    sign_flip_pvalue,
)

CLASSES = [
    "no_structural_intervention",
    "intervention_unchanged_ranking",
    "changed_ranking_zero_positive_pool",
    "changed_ranking_equal_grade_profile",
    "changed_profile_equal_metric",
    "utility_gain",
    "utility_harm",
]


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def classify(*, removed, baseline, ranking, qrels, delta):
    if not removed:
        return CLASSES[0]
    if baseline == ranking:
        return CLASSES[1]
    if delta > 1e-12:
        return "utility_gain"
    if delta < -1e-12:
        return "utility_harm"
    if not any(qrels.get(d, 0) > 0 for d in ranking):
        return CLASSES[2]
    if [qrels.get(d, 0) for d in baseline[:10]] == [qrels.get(d, 0) for d in ranking[:10]]:
        return CLASSES[3]
    return CLASSES[4]


def make_graph(pool, records, mode="strict"):
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(pool))
    grouped, dispositions, edges = defaultdict(list), Counter(), []
    for record in records:
        if (
            not record["repeat"]
            and record["variant"] == "primary"
            and set(record["pair"]) <= set(pool)
        ):
            grouped[tuple(record["pair"])].append(record)
    for pair in itertools.combinations(sorted(pool), 2):
        observed = grouped[pair]
        if mode == "strict":
            disposition, winner = paired_disposition(observed)
        else:
            orientation = 0 if mode == "forward" else 1
            chosen = [r for r in observed if r["orientation"] == orientation]
            winner = chosen[0]["winner"] if chosen and chosen[0]["status"] == "valid" else None
            disposition = "directional" if winner else "unresolved"
        dispositions[disposition] += 1
        if winner:
            loser = pair[1] if winner == pair[0] else pair[0]
            edges.append((winner, loser))
    graph.add_edges_from(sorted(edges), weight=1.0)
    return graph, dict(dispositions)


def evaluate_pool(pool, records, qrels, mode="strict"):
    graph, dispositions = make_graph(pool, records, mode)
    raw_ranking = copeland_ranking(graph)
    baseline = ndcg_at_k(raw_ranking, qrels, k=10)
    greedy, removed = greedy_fas(graph)
    exact, exact_removed, status = _solve_scip(graph, time_limit_s=10.0, mip_gap=0.0, quiet=True)
    if (
        status.proven_optimal
        and sum(e[2] for e in exact_removed) > sum(e[2] for e in removed) + 1e-8
    ):
        raise AssertionError("Exact repair exceeds greedy deletion cost")
    methods = [("unrepaired", graph, []), ("greedy", greedy, removed)]
    if status.proven_optimal:
        methods.append(("exact", exact, exact_removed))
    result = {
        "edges": list(graph.edges()),
        "dispositions": dispositions,
        "cyclic": not nx.is_directed_acyclic_graph(graph),
        "positive_in_pool": sum(qrels.get(d, 0) > 0 for d in pool),
        "judged_in_pool": sum(d in qrels for d in pool),
        "positive_global": sum(v > 0 for v in qrels.values()),
        "idcg_zero": not any(v > 0 for v in qrels.values()),
        "exact_status": clean(dataclasses.asdict(status)),
        "methods": {},
    }
    for name, repaired, deleted in methods:
        ranking = copeland_ranking(repaired)
        if set(ranking) != set(pool) or len(ranking) != len(pool):
            raise AssertionError("Candidate lost from ranking")
        if name != "unrepaired" and not nx.is_directed_acyclic_graph(repaired):
            raise AssertionError("Repair is not acyclic")
        score = ndcg_at_k(ranking, qrels, k=10)
        # Independent direct arithmetic verifies the reused metric, without replacing it.
        dcg = sum((2 ** qrels.get(d, 0) - 1) / math.log2(i + 2) for i, d in enumerate(ranking[:10]))
        ideal = sum(
            (2**g - 1) / math.log2(i + 2)
            for i, g in enumerate(sorted(qrels.values(), reverse=True)[:10])
        )
        if abs(score - (dcg / ideal if ideal else 0.0)) > 1e-12:
            raise AssertionError("Independent nDCG check failed")
        delta = score - baseline
        result["methods"][name] = {
            "ranking": ranking,
            "removed": deleted,
            "edges": list(repaired.edges()),
            "ndcg10": score,
            "delta_ndcg10": delta,
            "ndcg10_pool": ndcg_at_k(ranking, {d: qrels.get(d, 0) for d in pool}, k=10),
            "ranking_changed": ranking != raw_ranking,
            "top10_membership_changed": set(ranking[:10]) != set(raw_ranking[:10]),
            "grade_profile": [qrels.get(d, 0) for d in ranking[:10]],
            "grade_profile_changed": [qrels.get(d, 0) for d in ranking[:10]]
            != [qrels.get(d, 0) for d in raw_ranking[:10]],
            "class": classify(
                removed=deleted, baseline=raw_ranking, ranking=ranking, qrels=qrels, delta=delta
            ),
        }
    return result


def evaluate_query(run, uid):
    manifest = json.loads((run / "RUN_MANIFEST.json").read_text())
    gate = json.loads((run / "INSTRUMENT_VALIDATION.json").read_text())
    if not gate["gate_pass"]:
        raise RuntimeError("No utility evaluation after a failed instrument gate")
    verify_canonical_solver_version()
    row = next(
        json.loads(line)
        for line in (run / "inputs/evaluation.jsonl").open()
        if json.loads(line)["uid"] == uid
    )
    connection = database(run / "private/responses.sqlite3")
    records = response_rows(connection, "evaluation", uid)
    expected = {r["id"] for r in requests_for(row)}
    if {r["id"] for r in records} != expected:
        raise RuntimeError("Incomplete query acquisition cannot be evaluated as complete")
    label_path = run / "inputs/QRELS_EVALUATION_ONLY.json"
    if filehash(label_path) != manifest["input_sha256"][label_path.name]:
        raise RuntimeError("Qrels changed")
    qrels = json.loads(label_path.read_text())[uid]
    output = {
        "uid": uid,
        "dataset": row["dataset"],
        "stratum": row["stratum"],
        "input_sha256": row["input_sha256"],
        "response_sha256": digest(records),
        "manifest_sha256": filehash(run / "RUN_MANIFEST.json"),
        "finished_utc": now(),
        "conditions": {},
    }
    for condition, pool in row["pools"].items():
        output["conditions"][condition] = {
            mode: evaluate_pool(pool, records, qrels, mode)
            for mode in ("strict", "forward", "reverse")
        }
    path = run / "results" / (digest(uid) + ".json")
    if path.exists():
        old = json.loads(path.read_text())
        if any(
            old[key] != output[key]
            for key in ("input_sha256", "response_sha256", "manifest_sha256")
        ):
            raise RuntimeError("Refusing to overwrite incompatible result")
        return
    atomic(path, output)


def bootstrap_indices(rows, reps=10000):
    rng = np.random.default_rng(SEED)
    by_dataset = defaultdict(list)
    for index, row in enumerate(rows):
        by_dataset[row["dataset"]].append(index)
    return np.concatenate(
        [
            rng.choice(indices, size=(reps, len(indices)), replace=True)
            for _, indices in sorted(by_dataset.items())
        ],
        axis=1,
    )


def decomposition(rows, condition, method):
    available, missing = [], 0
    for row in rows:
        pool = row["conditions"][condition]["strict"]
        if method not in pool["methods"]:
            missing += 1
        else:
            available.append((row, pool, pool["methods"][method]))
    if not available:
        return {"matched_queries": 0, "missing_exact": missing}
    source_rows = [r[0] for r in available]
    indices = bootstrap_indices(source_rows)
    classes = Counter(r[2]["class"] for r in available)
    changed = np.asarray([r[2]["ranking_changed"] for r in available], dtype=int)
    nonzeros = np.asarray([abs(r[2]["delta_ndcg10"]) > 1e-12 for r in available], dtype=int)
    distribution = {}
    for name in CLASSES:
        indicator = np.asarray([r[2]["class"] == name for r in available], dtype=float)
        bounds = np.quantile(indicator[indices].mean(axis=1), [0.025, 0.975]).tolist()
        wilson = proportion_interval(classes[name], len(available))
        distribution[name] = {
            "count": classes[name],
            "matched_denominator": len(available),
            "pointwise_stratified_bootstrap95": bounds,
            "wilson95": [wilson.lower, wilson.upper],
            "bootstrap_degenerate": bounds[0] == bounds[1],
        }
    denominator = changed[indices].sum(axis=1)
    empty = denominator == 0
    conditional = {}
    for name, indicator in (
        ("gain", np.asarray([r[2]["delta_ndcg10"] > 1e-12 for r in available])),
        ("harm", np.asarray([r[2]["delta_ndcg10"] < -1e-12 for r in available])),
        ("zero", changed.astype(bool) & ~nonzeros.astype(bool)),
    ):
        n = int(changed.sum())
        count = int(indicator.sum())
        boot = indicator[indices].sum(axis=1)[~empty] / denominator[~empty]
        bounds = np.quantile(boot, [0.025, 0.975]).tolist() if len(boot) else None
        wilson = proportion_interval(count, n)
        conditional[name] = {
            "count": count,
            "ranking_changed_denominator": n,
            "rate": count / n if n else None,
            "pointwise_stratified_bootstrap95": bounds,
            "wilson95_descriptive": [wilson.lower, wilson.upper],
            "empty_bootstrap_denominators": int(empty.sum()),
            "bootstrap_degenerate": bounds is None or bounds[0] == bounds[1],
        }
    return {
        "matched_queries": len(available),
        "missing_exact": missing,
        "classes": distribution,
        "conditional_on_ranking_change": conditional,
        "nonzero_query_effects": int(nonzeros.sum()),
        "cyclic_positive": sum(p["cyclic"] and p["positive_in_pool"] > 0 for _, p, _ in available),
        "cyclic_zero_positive": sum(
            p["cyclic"] and p["positive_in_pool"] == 0 for _, p, _ in available
        ),
        "acyclic_positive": sum(
            not p["cyclic"] and p["positive_in_pool"] > 0 for _, p, _ in available
        ),
        "acyclic_zero_positive": sum(
            not p["cyclic"] and p["positive_in_pool"] == 0 for _, p, _ in available
        ),
    }


def summarize(run):
    roster = [json.loads(line) for line in (run / "inputs/evaluation.jsonl").open()]
    planned_ids = {r["uid"] for r in roster}
    rows = [json.loads(p.read_text()) for p in sorted((run / "results").glob("*.json"))]
    if not {r["uid"] for r in rows} <= planned_ids or len({r["uid"] for r in rows}) != len(rows):
        raise RuntimeError("Unexpected or duplicate query result")
    result = {
        "planned_queries": len(roster),
        "completed_queries": len(rows),
        "missing_query_ids": sorted(planned_ids - {r["uid"] for r in rows}),
        "finished_utc": now(),
        "classification": "prospective_exploratory",
        "inference": "pointwise intervals; sign-symmetry-dependent tests; no equivalence",
        "decompositions": {},
        "dataset_composition": {},
        "stratum_composition": {},
    }
    if not rows:
        atomic(run / "ANALYSIS_SUMMARY.json", result)
        return
    for condition in ("natural", "enriched"):
        result["decompositions"][condition] = {
            method: decomposition(rows, condition, method) for method in ("greedy", "exact")
        }
    for field in ("dataset", "stratum"):
        for group in sorted({r[field] for r in rows}):
            subset = [r for r in rows if r[field] == group]
            planned = sum(r[field] == group for r in roster)
            result[field + "_composition"][group] = {
                "planned_queries": planned,
                "completed_queries": len(subset),
                "decompositions": {
                    condition: {
                        method: decomposition(subset, condition, method)
                        for method in ("greedy", "exact")
                    }
                    for condition in ("natural", "enriched")
                },
            }
    effects = []
    for method in ("greedy", "exact"):
        matched = [r for r in rows if method in r["conditions"]["natural"]["strict"]["methods"]]
        deltas = np.asarray(
            [
                r["conditions"]["natural"]["strict"]["methods"][method]["delta_ndcg10"]
                for r in matched
            ]
        )
        if not len(deltas):
            effects.append({"method": method, "planned_n": len(roster), "n": 0, "p": 1.0})
            continue
        test = sign_flip_pvalue(deltas, exact_max_nonzero=16, reps=10000, seed=SEED)
        boot = deltas[bootstrap_indices(matched)].mean(axis=1)
        effects.append(
            {
                "method": method,
                "planned_n": len(roster),
                "n": len(deltas),
                "mean_delta": float(deltas.mean()),
                "median_delta": float(np.median(deltas)),
                "nonzero_n": int(np.sum(abs(deltas) > 1e-12)),
                "ci95_pointwise_stratified": np.quantile(boot, [0.025, 0.975]).tolist(),
                "p": test.pvalue,
                "test": clean(dataclasses.asdict(test)),
                "conditional_complete_case": len(deltas) != len(roster),
            }
        )
    for row, adjusted in zip(effects, holm_adjust([r["p"] for r in effects]), strict=True):
        row["p_holm_two_slot_family"] = adjusted
    result["natural_pool_secondary_effects"] = effects
    atomic(run / "ANALYSIS_SUMMARY.json", clean(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--uid")
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        summarize(args.run)
    elif args.uid:
        evaluate_query(args.run, args.uid)
    else:
        parser.error("Specify --uid or --summarize")


if __name__ == "__main__":
    main()
