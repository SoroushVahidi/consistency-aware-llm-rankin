"""
Build the Figure 4 evidence CSVs from already-committed canonical outputs.

This script performs ONLY a join/reformat of two existing canonical CSVs:
  - outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv
  - outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv

No bootstrap resampling, no statistics, and no numeric recalculation are
performed. mean_delta_ndcg / ci95_low / ci95_high are copied verbatim from the
canonical bootstrap table. mean_before / mean_after are copied verbatim from
the canonical graph/nDCG table and are cross-checked (not derived) against
mean_after - mean_before ~= mean_delta_ndcg.

Run from the repository root:
    python papers/JDIQ_2026/figure4_evidence/build_figure4_evidence.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOT_CSV = ROOT / "outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv"
GRAPH_CSV = ROOT / "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv"
ANALYSIS_DIR = ROOT / "outputs/pub_vote_cmp_all4/analysis"
OUT_DIR = Path(__file__).resolve().parent

PAIR_COLS = {
    "copeland": ("mean_ndcg_uco", "mean_ndcg_rco"),
    "balance": ("mean_ndcg_uba", "mean_ndcg_rba"),
}
METHOD_LABELS = {
    "copeland": ("hybrid_rrf_unrepaired_copeland_a03", "hybrid_rrf_repaired_copeland_a03"),
    "balance": ("hybrid_rrf_unrepaired_balance_a03", "hybrid_rrf_repaired_balance_a03"),
}

DATASET_ORDER = ["fiqa", "scidocs", "bright", "hotpotqa"]  # descending ms1 pct_cyclic (matches Fig 2 convention)
REGIME_ORDER = ["ms2", "ms1", "ms1_drop_mutual"]
PAIR_ORDER = ["copeland", "balance"]


def load_graph_table():
    rows = {}
    with open(GRAPH_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows[(row["dataset"], row["variant"])] = row
    return rows


def load_bootstrap_table():
    rows = []
    with open(BOOT_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def main():
    graph = load_graph_table()
    boot = load_bootstrap_table()

    fig4_rows = []
    for row in boot:
        dataset, variant, pair = row["dataset"], row["variant"], row["pair"]
        if pair not in PAIR_COLS:
            continue  # skip *_scc_high / *_scc_low stratified sub-rows (supplementary only)

        n_queries = int(row["n_queries"])
        delta = float(row["mean_delta_ndcg"])
        ci_low = float(row["ci95_low"])
        ci_high = float(row["ci95_high"])

        gkey = (dataset, variant)
        before_col, after_col = PAIR_COLS[pair]
        mean_before = float(graph[gkey][before_col])
        mean_after = float(graph[gkey][after_col])

        # Cross-check only -- not a recalculation of the CI/statistic itself.
        implied_delta = mean_after - mean_before
        assert abs(implied_delta - delta) < 1e-6, (
            f"Mismatch {dataset}/{variant}/{pair}: "
            f"table delta={delta} vs implied={implied_delta}"
        )

        # NOTE on the zero-boundary convention (see FIGURE4_SPECIFICATION.md /
        # FINAL_REPORT.md for full discussion): several canonical CIs have
        # ci_low == 0.0 exactly (not negative) with ci_high > 0, e.g. HotpotQA
        # ms1 copeland = [0.0, 0.0405]. A naive `ci_low <= 0 <= ci_high` check
        # would flag this identically to genuinely straddling intervals like
        # FiQA ms1 copeland = [-0.000515, 0.004236]. The manuscript's own
        # planning docs deliberately distinguish these ("does not cross zero
        # below") so we do too:
        #   - crosses_zero  = interval genuinely spans negative and positive
        #                     (ci_low < 0 < ci_high)
        #   - significant   = interval is bounded at/above zero AND has
        #                     non-degenerate positive support (ci_low >= 0
        #                     and ci_high > 0) -- excludes the exactly-[0,0]
        #                     null rows.
        crosses_zero = ci_low < 0.0 < ci_high
        significant = (ci_low >= 0.0 and ci_high > 0.0) or (ci_high <= 0.0 and ci_low < 0.0)
        if delta > 0:
            effect_direction = "positive"
        elif delta < 0:
            effect_direction = "negative"
        else:
            effect_direction = "zero"

        if ci_low == 0.0 and ci_high == 0.0:
            ci_relation_to_zero = "exactly_zero"
        elif ci_low >= 0.0 and ci_high > 0.0:
            ci_relation_to_zero = "positive_bounded_at_zero"
        elif ci_high <= 0.0 and ci_low < 0.0:
            ci_relation_to_zero = "negative_bounded_at_zero"
        else:
            ci_relation_to_zero = "straddles_zero"

        method_before, method_after = METHOD_LABELS[pair]
        json_path = ANALYSIS_DIR / f"{dataset}_{variant}_delta_{pair}.json"

        fig4_rows.append({
            "dataset": dataset,
            "regime": variant,
            "method_before": method_before,
            "method_after": method_after,
            "n_queries": n_queries,
            "mean_before": mean_before,
            "mean_after": mean_after,
            "delta_ndcg": delta,
            "bootstrap_ci_low": ci_low,
            "bootstrap_ci_high": ci_high,
            "bootstrap_std": "",  # not stored anywhere in canonical outputs; see quality checks
            "significant": significant,
            "crosses_zero": crosses_zero,
            "ci_relation_to_zero": ci_relation_to_zero,
            "effect_direction": effect_direction,
            "bootstrap_reps": int(row["bootstrap_reps"]),
            "canonical_source_file": "outputs/pub_vote_cmp_all4/paper_package/tables/table_bootstrap_delta_ndcg.csv",
            "canonical_table": "table_bootstrap_delta_ndcg",
            "means_source_file": "outputs/pub_vote_cmp_all4/paper_package/tables/table_graph_ndcg_and_consistency.csv",
            "per_cell_json_source": str(json_path.relative_to(ROOT)) if json_path.exists() else "",
        })

    # Order rows per forest_plot_order.csv convention: dataset severity order,
    # natural regime order within dataset, copeland before balance.
    def sort_key(r):
        return (
            DATASET_ORDER.index(r["dataset"]),
            REGIME_ORDER.index(r["regime"]),
            PAIR_ORDER.index("copeland" if r["method_before"].endswith("copeland_a03") else "balance"),
        )

    fig4_rows.sort(key=sort_key)

    fieldnames = [
        "dataset", "regime", "method_before", "method_after", "n_queries",
        "mean_before", "mean_after", "delta_ndcg", "bootstrap_ci_low",
        "bootstrap_ci_high", "bootstrap_std", "significant", "crosses_zero",
        "ci_relation_to_zero", "effect_direction", "bootstrap_reps", "canonical_source_file",
        "canonical_table", "means_source_file", "per_cell_json_source",
    ]
    with open(OUT_DIR / "figure4_bootstrap_data.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(fig4_rows)

    # Ready-to-plot: minimal columns only.
    plot_fields = ["label", "delta", "ci_low", "ci_high", "group", "dataset", "regime"]
    with open(OUT_DIR / "figure4_ready_to_plot.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=plot_fields)
        w.writeheader()
        for r in fig4_rows:
            group = "Copeland (repaired - unrepaired)" if r["method_before"].endswith("copeland_a03") else "Balance (repaired - unrepaired)"
            label = f"{r['dataset']} / {r['regime']} / {'copeland' if group.startswith('Copeland') else 'balance'}"
            w.writerow({
                "label": label,
                "delta": r["delta_ndcg"],
                "ci_low": r["bootstrap_ci_low"],
                "ci_high": r["bootstrap_ci_high"],
                "group": group,
                "dataset": r["dataset"],
                "regime": r["regime"],
            })

    print(f"Wrote {len(fig4_rows)} rows to figure4_bootstrap_data.csv and figure4_ready_to_plot.csv")


if __name__ == "__main__":
    main()
