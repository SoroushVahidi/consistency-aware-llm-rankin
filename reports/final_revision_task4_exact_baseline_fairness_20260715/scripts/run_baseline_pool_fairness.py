#!/usr/bin/env python3
"""JDIQ Task 4, sections 4/5: candidate-pool fairness for the baseline
comparison, and targeted statistical precision for the "simple baselines
remain strong" claim.

Reuses the existing per-query-per-method nDCG tables already produced by
reports/candidate_pool_conditional_audit_20260714/scripts/run_pool_robustness.py
(60 files: 5 pool policies x 4 datasets x 3 regimes, one row per query per
method_key) rather than re-running the pipeline -- these already cover
Prior/RRF/CombSUM/Borda and every graph-dependent method, at the
manuscript's own evaluation cutoff (spec.top_k) for every pool policy.

"Best graph method" is never selected post hoc: we report each of the 5
methods in run_full_calibrated_core.PRIMARY_BASELINE_COMPARISON_METHODS
individually plus their mean, using that pre-existing, pre-task-4 fixed
method family rather than picking a per-pool winner.
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from typing import Any

import task4_common as t4

BASELINE_METHODS = ("prior_only", "rrf", "combsum", "borda_fuse")
BASELINE_LABELS = {
    "prior_only": "Prior",
    "rrf": "RRF",
    "combsum": "CombSUM",
    "borda_fuse": "Borda fusion",
}
FIXED_GRAPH_METHOD_FAMILY = (
    t4.rfc.PRIMARY_BASELINE_COMPARISON_METHODS
)  # pre-existing, not chosen post hoc
FOCUS_REGIME = "ms1"

# Primary pre-specified targeted comparison family (section 5): under the
# CANONICAL pool only, each of {RRF, CombSUM} vs the fixed repaired
# Copeland hybrid, per dataset. Declared before inspecting any p-value.
PRIMARY_TARGETED_PAIRS = (
    ("rrf", "hybrid_repaired_copeland_a0p3_minmax"),
    ("combsum", "hybrid_repaired_copeland_a0p3_minmax"),
)
SECONDARY_POOL_FOR_ROBUSTNESS = (
    "neutral_round_robin_union"  # reported separately, not jointly corrected
)


def load_pool_run(pool_id: str, dataset: str, regime: str) -> list[dict[str, Any]]:
    path = t4.POOL_RUNS_ROOT / pool_id / dataset / regime / "query_method_metrics.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def descriptive_table() -> list[dict[str, Any]]:
    """Section 4: descriptive mean nDCG per (pool, dataset) for the 4
    baselines and the 5 fixed graph methods, ms1 regime."""
    rows: list[dict[str, Any]] = []
    for pool_id in t4.POOL_IDS:
        for dataset in t4.DATASETS:
            all_rows = load_pool_run(pool_id, dataset, FOCUS_REGIME)
            by_method: dict[str, list[float]] = defaultdict(list)
            for r in all_rows:
                by_method[r["method_key"]].append(float(r["ndcg_at_k"]))
            entry: dict[str, Any] = {"pool_id": pool_id, "dataset": dataset, "regime": FOCUS_REGIME}
            n_queries = len(set(r["query_id"] for r in all_rows))
            entry["n_queries"] = n_queries
            for m in BASELINE_METHODS:
                vals = by_method.get(m, [])
                entry[f"mean_ndcg_{m}"] = sum(vals) / len(vals) if vals else None
            fixed_family_means = []
            for m in FIXED_GRAPH_METHOD_FAMILY:
                vals = by_method.get(m, [])
                mean_val = sum(vals) / len(vals) if vals else None
                entry[f"mean_ndcg_{m}"] = mean_val
                if mean_val is not None:
                    fixed_family_means.append(mean_val)
            entry["mean_ndcg_fixed_graph_family_average"] = (
                sum(fixed_family_means) / len(fixed_family_means) if fixed_family_means else None
            )
            rows.append(entry)
    return rows


def _paired_deltas(all_rows: list[dict[str, Any]], method_a: str, method_b: str) -> list[float]:
    by_query: dict[str, dict[str, float]] = defaultdict(dict)
    for r in all_rows:
        if r["method_key"] in (method_a, method_b):
            by_query[r["query_id"]][r["method_key"]] = float(r["ndcg_at_k"])
    deltas = []
    for qid, vals in by_query.items():
        if method_a in vals and method_b in vals:
            deltas.append(vals[method_a] - vals[method_b])
    return deltas


def targeted_tests(pool_id: str, family_tag: str) -> list[dict[str, Any]]:
    rows = []
    for dataset in t4.DATASETS:
        all_rows = load_pool_run(pool_id, dataset, FOCUS_REGIME)
        for baseline_method, graph_method in PRIMARY_TARGETED_PAIRS:
            deltas = _paired_deltas(all_rows, baseline_method, graph_method)
            stats = t4.rich_cell_statistics(deltas)
            stats.update(
                {
                    "family_tag": family_tag,
                    "pool_id": pool_id,
                    "dataset": dataset,
                    "baseline_method": baseline_method,
                    "graph_method": graph_method,
                    "comparison": f"{baseline_method}_minus_{graph_method}",
                }
            )
            rows.append(stats)
    return rows


def holm_correct(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pvals = [r["sign_flip_pvalue"] for r in rows]
    holm = t4.stats_inf.holm_adjust(pvals)
    out = []
    for row, holm_p in zip(rows, holm):
        r = dict(row)
        r["holm_adjusted_pvalue"] = holm_p
        r["holm_significant_at_0.05"] = bool(holm_p is not None and holm_p < 0.05)
        # Cohen's-d-style standardized effect size (mean delta / sd delta)
        r["standardized_effect_size"] = (
            (r["mean_delta"] / r["std_delta"]) if r.get("std_delta") not in (None, 0) else None
        )
        out.append(r)
    return out


def main() -> int:
    t0 = time.time()
    desc_rows = descriptive_table()
    t4.write_csv(t4.TABLES_DIR / "baseline_pool_fairness_descriptive.csv", desc_rows)

    primary_targeted = targeted_tests("rrf_union_topk", "primary_canonical_pool")
    primary_targeted = holm_correct(primary_targeted)
    t4.write_csv(t4.TABLES_DIR / "baseline_targeted_tests_primary_canonical.csv", primary_targeted)

    secondary_targeted = targeted_tests(
        SECONDARY_POOL_FOR_ROBUSTNESS, "secondary_neutral_pool_robustness"
    )
    secondary_targeted = holm_correct(secondary_targeted)
    t4.write_csv(
        t4.TABLES_DIR / "baseline_targeted_tests_secondary_neutral_pool.csv", secondary_targeted
    )

    # For every non-canonical pool too, so the "does RRF have a home-field
    # advantage" question can be answered for every pool, not just the two above.
    all_pool_targeted = []
    for pool_id in t4.POOL_IDS:
        tag = "primary_canonical_pool" if pool_id == "rrf_union_topk" else f"pool_{pool_id}"
        rows = targeted_tests(pool_id, tag)
        rows = holm_correct(rows)
        all_pool_targeted.extend(rows)
    t4.write_csv(t4.TABLES_DIR / "baseline_targeted_tests_all_pools.csv", all_pool_targeted)

    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "baseline_methods": list(BASELINE_METHODS),
        "fixed_graph_method_family": list(FIXED_GRAPH_METHOD_FAMILY),
        "fixed_graph_method_family_source": (
            "run_full_calibrated_core.PRIMARY_BASELINE_COMPARISON_METHODS -- pre-existing "
            "in the codebase before Task 4, not chosen post hoc from these results"
        ),
        "focus_regime": FOCUS_REGIME,
        "primary_targeted_family_definition": (
            "PRE-SPECIFIED before inspecting p-values: {RRF, CombSUM} vs fixed repaired "
            "Copeland hybrid, 4 datasets, CANONICAL (rrf_union_topk) pool only = 8 cells, "
            "Holm-corrected jointly. This is the only family used for an inferential claim."
        ),
        "primary_targeted_family_size": len(primary_targeted),
        "primary_targeted_n_significant": sum(
            1 for r in primary_targeted if r["holm_significant_at_0.05"]
        ),
        "secondary_pool_for_robustness": SECONDARY_POOL_FOR_ROBUSTNESS,
        "secondary_targeted_family_size": len(secondary_targeted),
        "secondary_targeted_n_significant": sum(
            1 for r in secondary_targeted if r["holm_significant_at_0.05"]
        ),
        "note": (
            "secondary and all-pool tables are reported descriptively/for robustness "
            "context; only the primary_canonical_pool family above is treated as an "
            "inferential claim, per the task's 'small pre-specified family' instruction"
        ),
        "elapsed_seconds": time.time() - t0,
    }
    t4.write_json(t4.MANIFESTS_DIR / "baseline_pool_fairness_run_summary.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
