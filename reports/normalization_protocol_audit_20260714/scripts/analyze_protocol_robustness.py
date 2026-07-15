"""Task-2 robustness analysis: does any positive repaired-vs-unrepaired nDCG
conclusion survive across independently-defined normalization/threshold
protocols under a joint multiplicity family, and which protocol should be
primary.

Reads only already-generated per-query paired outputs (no new experiments,
no manuscript figures). Writes CSVs to
reports/normalization_protocol_audit_20260714/tables/.

Joint families (pre-specified, not chosen post hoc by which one "wins"):

  F1_headline  = {primary_minmax_retention_matched,
                  independent_minmax_quantile_q0p5,
                  independent_rank_percentile_q0p5}
                 x 4 datasets x 3 regimes x 5 pairs = 180 tests.
                 This is the family relevant to "does the paper's positive/
                 negative repair conclusion hold once we stop anchoring
                 normalized thresholds to the raw protocol."

  F2_all_legitimate = F1_headline + robustness_zscore_retention
                 x 4 x 3 x 5 = 240 tests. Adds the optional robust-scale
                 calibration the task allows evaluating.

  F3_everything = all 12 registered protocols (6 original + 6 new,
                 including the raw_fixed ablation and the q0p3/q0p7
                 sensitivity-grid points) x 4 x 3 x 5 = 720 tests. Reported
                 as a conservative upper bound, not used to justify any
                 primary-protocol decision by itself.

Each family gets its own independent Holm/BH correction (corrections are
never pooled across families, and no family is chosen after seeing which
one produces significant cells).
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "full_calibrated_core" / "scripts"))

from full_calibration_utils import bootstrap_ci, paired_permutation_pvalue  # noqa: E402
from run_full_calibrated_core import (  # noqa: E402
    PROTOCOL_SPECS,
    _bh_adjust,
    _holm_adjust,
)

REPO_ROOT = SCRIPT_DIR.parent.parent.parent
OLD_DELTAS = REPO_ROOT / "reports/full_calibrated_core/tables/full_paired_deltas.csv"
NEW_DELTAS = (
    REPO_ROOT
    / "reports/normalization_protocol_audit_20260714/tables/independent_protocol_paired_deltas.csv"
)
TABLES_DIR = REPO_ROOT / "reports/normalization_protocol_audit_20260714/tables"
DIAGNOSTICS_SUMMARY = TABLES_DIR / "independent_protocol_diagnostics_summary.csv"
OVERLAP = TABLES_DIR / "independent_protocol_removed_edge_overlap.csv"

# full_structural_results.csv (6 original protocols) stores cyclic_query_pct
# and pct_queries_with_mutual_pair as 0-1 FRACTIONS.
# independent_protocol_diagnostics_summary.csv (6 new protocols) stores the
# equivalent columns as 0-100 PERCENTAGES. Both are normalized to
# percentage units below before any cross-protocol comparison -- mixing
# them unconverted previously produced a spurious "two orders of
# magnitude" structural-sensitivity claim that has since been retracted
# (see ANALYSIS.md section 5).
OLD_STRUCTURAL = REPO_ROOT / "reports/full_calibrated_core/tables/full_structural_results.csv"

DATASETS = ("scidocs", "fiqa", "hotpotqa", "bright")
REGIMES = ("ms2", "ms1", "ms1_drop_mutual")
PAIRS = ("balance_graph", "balance_hybrid", "copeland_graph", "copeland_hybrid", "markov_graph")

RAW_PROTOCOL = "ablation_raw_fixed"
PRIMARY_PROTOCOL = "primary_minmax_retention_matched"
MINMAX_QUANTILE = "independent_minmax_quantile_q0p5"
RANK_PERCENTILE = "independent_rank_percentile_q0p5"
ZSCORE_PROTOCOL = "robustness_zscore_retention"

ALL_TWELVE_PROTOCOLS = tuple(PROTOCOL_SPECS.keys())

FAMILIES: dict[str, tuple[str, ...]] = {
    "F1_headline": (PRIMARY_PROTOCOL, MINMAX_QUANTILE, RANK_PERCENTILE),
    "F2_all_legitimate": (PRIMARY_PROTOCOL, MINMAX_QUANTILE, RANK_PERCENTILE, ZSCORE_PROTOCOL),
    "F3_everything": ALL_TWELVE_PROTOCOLS,
}


def _load_deltas(path: Path) -> dict[tuple[str, str, str, str], list[float]]:
    """cell key = (protocol, dataset, regime, pair_name) -> list of delta_ndcg."""
    out: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["protocol"], row["dataset"], row["regime"], row["pair_name"])
            out[key].append(float(row["delta_ndcg"]))
    return out


def main() -> int:
    deltas_by_cell = _load_deltas(OLD_DELTAS)
    new_deltas = _load_deltas(NEW_DELTAS)
    for key, values in new_deltas.items():
        assert key not in deltas_by_cell, f"duplicate cell {key} in old and new paired-delta tables"
        deltas_by_cell[key] = values

    expected_cells = {
        (protocol, dataset, regime, pair)
        for protocol in ALL_TWELVE_PROTOCOLS
        for dataset in DATASETS
        for regime in REGIMES
        for pair in PAIRS
    }
    missing = expected_cells - set(deltas_by_cell.keys())
    if missing:
        raise SystemExit(f"missing {len(missing)} cells, e.g. {sorted(missing)[:5]}")

    stats_rows: list[dict[str, Any]] = []
    for (protocol, dataset, regime, pair), values in deltas_by_cell.items():
        ci_low, ci_high, frac_gt0 = bootstrap_ci(values)
        pvalue = paired_permutation_pvalue(values)
        n = len(values)
        mean_delta = sum(values) / n if n else 0.0
        stats_rows.append(
            {
                "protocol": protocol,
                "protocol_label": PROTOCOL_SPECS[protocol]["label"],
                "protocol_kind": PROTOCOL_SPECS[protocol]["kind"],
                "dataset": dataset,
                "regime": regime,
                "pair_name": pair,
                "n_queries": n,
                "mean_delta_ndcg": mean_delta,
                "bootstrap_ci_low": ci_low,
                "bootstrap_ci_high": ci_high,
                "bootstrap_fraction_means_gt_zero": frac_gt0,
                "paired_permutation_pvalue": pvalue,
            }
        )
    stats_rows.sort(key=lambda r: (r["protocol"], r["dataset"], r["regime"], r["pair_name"]))

    with open(TABLES_DIR / "joint_protocol_statistics_all12.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats_rows[0].keys()))
        writer.writeheader()
        writer.writerows(stats_rows)

    stats_by_cell = {
        (r["protocol"], r["dataset"], r["regime"], r["pair_name"]): r for r in stats_rows
    }

    family_rows: list[dict[str, Any]] = []
    family_summaries: list[dict[str, Any]] = []
    for family_name, protocols in FAMILIES.items():
        cells = [
            stats_by_cell[(protocol, dataset, regime, pair)]
            for protocol in protocols
            for dataset in DATASETS
            for regime in REGIMES
            for pair in PAIRS
        ]
        pvals = [c["paired_permutation_pvalue"] for c in cells]
        holm = _holm_adjust(pvals)
        bh = _bh_adjust(pvals)
        n_reject_holm = 0
        n_reject_bh = 0
        n_reject_holm_positive = 0
        for c, h, b in zip(cells, holm, bh):
            reject_holm = h < 0.05
            reject_bh = b < 0.05
            n_reject_holm += int(reject_holm)
            n_reject_bh += int(reject_bh)
            n_reject_holm_positive += int(reject_holm and c["mean_delta_ndcg"] > 0)
            family_rows.append(
                {
                    "family": family_name,
                    "n_tests_in_family": len(cells),
                    "protocol": c["protocol"],
                    "protocol_label": c["protocol_label"],
                    "dataset": c["dataset"],
                    "regime": c["regime"],
                    "pair_name": c["pair_name"],
                    "n_queries": c["n_queries"],
                    "mean_delta_ndcg": c["mean_delta_ndcg"],
                    "raw_pvalue": c["paired_permutation_pvalue"],
                    "holm_adjusted_pvalue": h,
                    "bh_adjusted_pvalue": b,
                    "reject_holm_0p05": reject_holm,
                    "reject_bh_0p05": reject_bh,
                }
            )
        family_summaries.append(
            {
                "family": family_name,
                "protocols_in_family": ";".join(protocols),
                "n_tests": len(cells),
                "n_reject_holm_0p05": n_reject_holm,
                "n_reject_bh_0p05": n_reject_bh,
                "n_reject_holm_0p05_and_positive": n_reject_holm_positive,
                "any_positive_conclusion_survives_holm": n_reject_holm_positive > 0,
            }
        )

    with open(TABLES_DIR / "joint_multiplicity_by_family.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(family_rows[0].keys()))
        writer.writeheader()
        writer.writerows(family_rows)

    with open(TABLES_DIR / "joint_multiplicity_family_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(family_summaries[0].keys()))
        writer.writeheader()
        writer.writerows(family_summaries)

    print("Family summary:")
    for s in family_summaries:
        print(
            f"  {s['family']}: n_tests={s['n_tests']} "
            f"reject_holm={s['n_reject_holm_0p05']} reject_bh={s['n_reject_bh_0p05']} "
            f"positive_and_significant={s['n_reject_holm_0p05_and_positive']}"
        )

    # Sign-stability: for each (dataset, regime, pair), does mean_delta_ndcg
    # have the same sign across the four canonical protocols (raw excluded,
    # since it is the ablation)?
    sign_rows: list[dict[str, Any]] = []
    canonical = (PRIMARY_PROTOCOL, MINMAX_QUANTILE, RANK_PERCENTILE)
    n_flip = 0
    n_cells = 0
    for dataset in DATASETS:
        for regime in REGIMES:
            for pair in PAIRS:
                means = {
                    protocol: stats_by_cell[(protocol, dataset, regime, pair)]["mean_delta_ndcg"]
                    for protocol in canonical
                }
                signs = {p: (1 if v > 0 else (-1 if v < 0 else 0)) for p, v in means.items()}
                stable = len(set(s for s in signs.values() if s != 0)) <= 1
                n_cells += 1
                if not stable:
                    n_flip += 1
                sign_rows.append(
                    {
                        "dataset": dataset,
                        "regime": regime,
                        "pair_name": pair,
                        **{f"mean_delta_ndcg__{p}": v for p, v in means.items()},
                        "sign_stable_across_canonical_protocols": stable,
                    }
                )
    with open(TABLES_DIR / "sign_stability_canonical_protocols.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sign_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sign_rows)
    print(f"Sign flips across canonical protocols: {n_flip}/{n_cells} (dataset,regime,pair) cells")

    _write_structural_comparison()

    return 0


def _write_structural_comparison() -> None:
    """Unit-normalized (percentage) structural comparison across all 12
    protocols, per dataset x regime cell, so nothing downstream has to
    re-derive the fraction-vs-percentage conversion by hand."""
    rows: list[dict[str, Any]] = []
    with open(OLD_STRUCTURAL, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "protocol": r["protocol"],
                    "protocol_label": r["protocol_label"],
                    "protocol_kind": r["protocol_kind"],
                    "dataset": r["dataset"],
                    "regime": r["regime"],
                    "mutual_pair_query_prevalence_pct": float(r["pct_queries_with_mutual_pair"])
                    * 100.0,
                    "cyclic_query_pct": float(r["cyclic_query_pct"]) * 100.0,
                    "cyclic_query_pct_after_mutual_deletion": float(
                        r["cyclic_query_pct_after_mutual_deletion"]
                    )
                    * 100.0,
                    "source_table": (
                        "full_structural_results.csv (fraction units, converted to pct)"
                    ),
                }
            )
    with open(DIAGNOSTICS_SUMMARY, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "protocol": r["protocol"],
                    "protocol_label": r["protocol_label"],
                    "protocol_kind": r["protocol_kind"],
                    "dataset": r["dataset"],
                    "regime": r["regime"],
                    "mutual_pair_query_prevalence_pct": float(
                        r["mutual_pair_query_prevalence_pct"]
                    ),
                    "cyclic_query_pct": float(r["cyclic_query_pct"]),
                    "cyclic_query_pct_after_mutual_deletion": float(
                        r["cyclic_query_pct_after_mutual_deletion"]
                    ),
                    "source_table": (
                        "independent_protocol_diagnostics_summary.csv (already pct units)"
                    ),
                }
            )
    rows.sort(key=lambda r: (r["protocol"], r["dataset"], r["regime"]))
    with open(TABLES_DIR / "structural_comparison_all12_pct_units.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_protocol_regime: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_protocol_regime[(r["protocol"], r["regime"])].append(r)
    summary_rows = []
    for (protocol, regime), cell_rows in sorted(by_protocol_regime.items()):
        n = len(cell_rows)
        summary_rows.append(
            {
                "protocol": protocol,
                "regime": regime,
                "n_datasets": n,
                "mean_mutual_pair_query_prevalence_pct": sum(
                    r["mutual_pair_query_prevalence_pct"] for r in cell_rows
                )
                / n,
                "mean_cyclic_query_pct": sum(r["cyclic_query_pct"] for r in cell_rows) / n,
                "mean_cyclic_query_pct_after_mutual_deletion": sum(
                    r["cyclic_query_pct_after_mutual_deletion"] for r in cell_rows
                )
                / n,
            }
        )
    with open(
        TABLES_DIR / "structural_comparison_all12_pct_units_summary.csv", "w", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(
        f"Wrote structural_comparison_all12_pct_units.csv ({len(rows)} rows) and its "
        f"per-protocol/regime summary ({len(summary_rows)} rows)."
    )


if __name__ == "__main__":
    raise SystemExit(main())
