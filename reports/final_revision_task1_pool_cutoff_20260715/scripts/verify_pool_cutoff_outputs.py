#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPORT_ROOT = THIS_DIR.parent
TABLES_DIR = REPORT_ROOT / "tables"
GREEDY_OUTPUTS_DIR = REPORT_ROOT / "outputs" / "greedy_pool_cutoff"
EXACT_OUTPUTS_DIR = REPORT_ROOT / "outputs" / "exact_pool_cutoff"
VALIDATION_DIR = REPORT_ROOT / "validation"

GREEDY_PAIR_KEYS = [
    "dataset",
    "regime",
    "config_id",
    "pool_size",
    "metric_cutoff",
    "pair_name",
    "pair_family",
]
STRUCT_KEYS = [
    "dataset",
    "regime",
    "config_id",
    "pool_size",
    "metric_cutoff",
    "pair_name",
]


def _assert_close(label: str, left: float, right: float, tol: float = 1.0e-12) -> None:
    if abs(left - right) > tol:
        raise AssertionError(f"{label}: {left} != {right}")


def _check_cell_files() -> dict[str, int]:
    feasible = pd.read_csv(TABLES_DIR / "feasible_config_grid.csv")
    greedy_files_checked = 0
    for row in feasible.itertuples(index=False):
        if not bool(row.supported_by_complete_scores):
            continue
        for regime in ("ms2", "ms1", "ms1_drop_mutual"):
            cell_dir = GREEDY_OUTPUTS_DIR / row.dataset / regime / row.config_id
            for name in (
                "manifest.json",
                "query_records.jsonl",
                "query_pair_metrics.csv",
                "query_method_metrics.csv",
            ):
                path = cell_dir / name
                if not path.exists():
                    raise FileNotFoundError(path)
                greedy_files_checked += 1

    exact_stats = pd.read_csv(TABLES_DIR / "pool_cutoff_exact_solver_status.csv")
    exact_files_checked = 0
    exact_cells = exact_stats[["dataset", "regime", "config_id"]].drop_duplicates()
    for keys in exact_cells.itertuples(index=False):
        cell_dir = EXACT_OUTPUTS_DIR / keys.dataset / keys.regime / keys.config_id
        for name in ("manifest.json", "query_records.jsonl", "query_pair_metrics.csv"):
            path = cell_dir / name
            if not path.exists():
                raise FileNotFoundError(path)
            exact_files_checked += 1

    return {
        "greedy_files_checked": greedy_files_checked,
        "exact_files_checked": exact_files_checked,
    }


def _recompute_greedy_stats() -> dict[str, object]:
    pair_df = pd.read_csv(TABLES_DIR / "pool_cutoff_pair_metrics.csv")
    stats_df = pd.read_csv(TABLES_DIR / "pool_cutoff_statistics.csv")
    struct_df = pd.read_csv(TABLES_DIR / "pool_cutoff_structural_summary.csv")

    metric_checks = 0
    for metric_name, delta_col, unrepaired_col, repaired_col in (
        ("ndcg", "delta_ndcg", "unrepaired_ndcg", "repaired_ndcg"),
        ("map", "delta_map", "unrepaired_map", "repaired_map"),
        ("mrr", "delta_mrr", "unrepaired_mrr", "repaired_mrr"),
    ):
        for keys, group in pair_df.groupby(GREEDY_PAIR_KEYS, dropna=False):
            row = stats_df[
                (stats_df["dataset"] == keys[0])
                & (stats_df["regime"] == keys[1])
                & (stats_df["config_id"] == keys[2])
                & (stats_df["pool_size"] == keys[3])
                & (stats_df["metric_cutoff"] == keys[4])
                & (stats_df["pair_name"] == keys[5])
                & (stats_df["pair_family"] == keys[6])
                & (stats_df["metric"] == metric_name)
            ]
            if len(row) != 1:
                raise AssertionError(f"missing stats row for {metric_name} {keys}")
            row = row.iloc[0]
            deltas = group[delta_col].astype(float)
            _assert_close(
                f"{metric_name} mean_delta {keys}",
                float(row["mean_delta"]),
                float(deltas.mean()),
            )
            _assert_close(
                f"{metric_name} median_delta {keys}",
                float(row["median_delta"]),
                float(deltas.median()),
            )
            _assert_close(
                f"{metric_name} std_delta {keys}",
                float(row["std_delta"]),
                float(deltas.std(ddof=0)),
            )
            _assert_close(
                f"{metric_name} mean_unrepaired {keys}",
                float(row["mean_unrepaired"]),
                float(group[unrepaired_col].astype(float).mean()),
            )
            _assert_close(
                f"{metric_name} mean_repaired {keys}",
                float(row["mean_repaired"]),
                float(group[repaired_col].astype(float).mean()),
            )
            if int(row["n_paired_queries"]) != len(group):
                raise AssertionError(f"{metric_name} n mismatch for {keys}")
            if int(row["helped_queries"]) != int((deltas > 1.0e-12).sum()):
                raise AssertionError(f"{metric_name} helped mismatch for {keys}")
            if int(row["harmed_queries"]) != int((deltas < -1.0e-12).sum()):
                raise AssertionError(f"{metric_name} harmed mismatch for {keys}")
            if int(row["unchanged_queries"]) != int((deltas.abs() <= 1.0e-12).sum()):
                raise AssertionError(f"{metric_name} unchanged mismatch for {keys}")
            metric_checks += 1

    structural_checks = 0
    for keys, group in pair_df.groupby(STRUCT_KEYS, dropna=False):
        row = struct_df[
            (struct_df["dataset"] == keys[0])
            & (struct_df["regime"] == keys[1])
            & (struct_df["config_id"] == keys[2])
            & (struct_df["pool_size"] == keys[3])
            & (struct_df["metric_cutoff"] == keys[4])
            & (struct_df["pair_name"] == keys[5])
        ]
        if len(row) != 1:
            raise AssertionError(f"missing structural row for {keys}")
        row = row.iloc[0]
        if int(row["n_queries"]) != len(group):
            raise AssertionError(f"structural n mismatch for {keys}")
        for field in (
            "graph_is_cyclic",
            "repair_applied",
            "full_ranking_changed",
            "top_k_membership_changed",
            "top_k_order_changed",
            "differently_graded_judged_pairs_changed",
        ):
            expected = float(group[field].astype(float).mean())
            actual = float(
                row[
                    {
                        "graph_is_cyclic": "cycle_rate",
                        "repair_applied": "repair_applied_rate",
                        "full_ranking_changed": "full_ranking_changed_rate",
                        "top_k_membership_changed": "top_k_membership_changed_rate",
                        "top_k_order_changed": "top_k_order_changed_rate",
                        "differently_graded_judged_pairs_changed": (
                            "differently_graded_judged_pairs_changed_rate"
                        ),
                    }[field]
                ]
            )
            _assert_close(f"structural {field} {keys}", actual, expected)
        _assert_close(
            f"structural ndcg_changed_rate {keys}",
            float(row["ndcg_changed_rate"]),
            float((group["delta_ndcg"].astype(float).abs() > 1.0e-12).mean()),
        )
        for field, col in (
            ("mean_removed_weight_fraction", "removed_weight_fraction"),
            ("mean_graph_density_pre", "graph_density_pre"),
            ("mean_graph_density_post", "graph_density_post"),
            ("mean_largest_scc_size_pre", "largest_scc_size_pre"),
            ("mean_largest_scc_size_post", "largest_scc_size_post"),
            ("mean_total_edge_weight_pre", "total_edge_weight_pre"),
            ("mean_total_edge_weight_post", "total_edge_weight_post"),
        ):
            _assert_close(
                f"structural {field} {keys}",
                float(row[field]),
                float(group[col].astype(float).mean()),
            )
        structural_checks += 1

    return {
        "metric_checks": metric_checks,
        "structural_checks": structural_checks,
    }


def _recompute_exact_stats() -> dict[str, object]:
    pair_df = pd.read_csv(TABLES_DIR / "pool_cutoff_exact_pair_metrics.csv")
    stats_df = pd.read_csv(TABLES_DIR / "pool_cutoff_exact_statistics.csv")
    solver_df = pd.read_csv(TABLES_DIR / "pool_cutoff_exact_solver_status.csv")

    metric_checks = 0
    for metric_name, delta_col, unrepaired_col, repaired_col in (
        ("ndcg", "delta_ndcg", "unrepaired_ndcg", "repaired_ndcg"),
        ("map", "delta_map", "unrepaired_map", "repaired_map"),
        ("mrr", "delta_mrr", "unrepaired_mrr", "repaired_mrr"),
    ):
        for keys, group in pair_df.groupby(GREEDY_PAIR_KEYS, dropna=False):
            row = stats_df[
                (stats_df["dataset"] == keys[0])
                & (stats_df["regime"] == keys[1])
                & (stats_df["config_id"] == keys[2])
                & (stats_df["pool_size"] == keys[3])
                & (stats_df["metric_cutoff"] == keys[4])
                & (stats_df["pair_name"] == keys[5])
                & (stats_df["pair_family"] == keys[6])
                & (stats_df["metric"] == metric_name)
            ]
            if len(row) != 1:
                raise AssertionError(f"missing exact stats row for {metric_name} {keys}")
            row = row.iloc[0]
            deltas = group[delta_col].astype(float)
            _assert_close(
                f"exact {metric_name} mean_delta {keys}",
                float(row["mean_delta"]),
                float(deltas.mean()),
            )
            _assert_close(
                f"exact {metric_name} median_delta {keys}",
                float(row["median_delta"]),
                float(deltas.median()),
            )
            _assert_close(
                f"exact {metric_name} std_delta {keys}",
                float(row["std_delta"]),
                float(deltas.std(ddof=0)),
            )
            _assert_close(
                f"exact {metric_name} mean_unrepaired {keys}",
                float(row["mean_unrepaired"]),
                float(group[unrepaired_col].astype(float).mean()),
            )
            _assert_close(
                f"exact {metric_name} mean_repaired {keys}",
                float(row["mean_repaired"]),
                float(group[repaired_col].astype(float).mean()),
            )
            metric_checks += 1

    solver_checks = 0
    for keys, group in solver_df.groupby(["dataset", "config_id"], dropna=False):
        if not group["proven_optimal"].astype(bool).all():
            raise AssertionError(f"non-optimal exact row in {keys}")
        _assert_close(f"exact max gap {keys}", float(group["gap"].astype(float).max()), 0.0)
        solver_checks += len(group)

    return {
        "metric_checks": metric_checks,
        "solver_rows_checked": solver_checks,
    }


def _claim_checks() -> dict[str, object]:
    struct_df = pd.read_csv(TABLES_DIR / "pool_cutoff_structural_summary.csv")
    stats_df = pd.read_csv(TABLES_DIR / "pool_cutoff_statistics.csv")
    exact_solver_df = pd.read_csv(TABLES_DIR / "pool_cutoff_exact_solver_status.csv")

    ndcg_rows = stats_df[stats_df["metric"] == "ndcg"].copy()
    active_rows = ndcg_rows[ndcg_rows["regime"] == "ms1"].copy()

    claims = {
        "p_gt_k_membership_change_rate": float(
            struct_df.loc[
                struct_df["pool_size"] > struct_df["metric_cutoff"],
                "top_k_membership_changed_rate",
            ].mean()
        ),
        "p_eq_k_membership_change_rate": float(
            struct_df.loc[
                struct_df["pool_size"] == struct_df["metric_cutoff"],
                "top_k_membership_changed_rate",
            ].mean()
        ),
        "p_gt_k_ndcg_change_rate": float(
            struct_df.loc[
                struct_df["pool_size"] > struct_df["metric_cutoff"],
                "ndcg_changed_rate",
            ].mean()
        ),
        "p_eq_k_ndcg_change_rate": float(
            struct_df.loc[
                struct_df["pool_size"] == struct_df["metric_cutoff"],
                "ndcg_changed_rate",
            ].mean()
        ),
        "n_holm_significant_full_family": int(
            (ndcg_rows["holm_full_family"] <= 0.05).fillna(False).sum()
        ),
        "n_holm_significant_active_ms1_family": int(
            (active_rows["holm_active_ms1_family"] <= 0.05).fillna(False).sum()
        ),
        "exact_all_proven_optimal": bool(exact_solver_df["proven_optimal"].astype(bool).all()),
        "exact_max_gap": float(exact_solver_df["gap"].astype(float).max()),
    }
    return claims


def main() -> int:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    file_counts = _check_cell_files()
    greedy_checks = _recompute_greedy_stats()
    exact_checks = _recompute_exact_stats()
    claims = _claim_checks()
    payload = {
        "file_counts": file_counts,
        "greedy_checks": greedy_checks,
        "exact_checks": exact_checks,
        "claims": claims,
    }
    out_path = VALIDATION_DIR / "pool_cutoff_verification.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
