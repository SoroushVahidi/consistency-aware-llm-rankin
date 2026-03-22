from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.generate_paper_tables import _effect_label, main


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_effect_label_logic():
    assert _effect_label(0.01, 0.001, 0.02, 10) == "significant_gain"
    assert _effect_label(-0.01, -0.02, -0.001, 10) == "significant_harm"
    assert _effect_label(0.0, 0.0, 0.0, 10) == "inactive"
    assert _effect_label(0.001, -0.01, 0.02, 10) == "no_significant_change"
    assert _effect_label(0.001, -0.01, 0.02, 0) == "no_data"


def test_generate_paper_tables_end_to_end(tmp_path: Path):
    q1_dir = tmp_path / "q1"
    paper_pkg = tmp_path / "paper_package"
    real_dir = tmp_path / "real_full"
    synthetic_dir = tmp_path / "synthetic"
    out_dir = tmp_path / "reports" / "paper_tables"

    _write_csv(
        q1_dir / "table_significance.csv",
        [
            "dataset",
            "vote_construction",
            "comparison",
            "n_queries",
            "mean_delta_ndcg",
            "ci95_low",
            "ci95_high",
        ],
        [
            ["scidocs", "ms1", "copeland", "100", "-0.01", "-0.02", "-0.005"],
            ["scidocs", "ms1", "balance", "100", "0.0", "0.0", "0.0"],
        ],
    )
    _write_csv(
        q1_dir / "table_main_performance.csv",
        ["dataset", "vote_construction", "pct_cyclic_graphs"],
        [["scidocs", "ms1", "97.5"]],
    )
    _write_csv(
        q1_dir / "table_structural_consistency.csv",
        [
            "dataset",
            "vote_construction",
            "mean_fas_weight_removed",
            "delta_bew_pre_minus_post",
            "delta_pic_pre_minus_post",
        ],
        [["scidocs", "ms1", "2.5", "1.13", "11.75"]],
    )
    _write_csv(
        q1_dir / "table_failure_cases.csv",
        ["dataset", "vote_construction", "method_pair", "n_queries", "mean_delta_ndcg", "ci95_low", "ci95_high"],
        [["scidocs", "ms1", "copeland", "100", "-0.01", "-0.02", "-0.005"]],
    )
    (q1_dir / "summary_report.md").write_text("ok", encoding="utf-8")

    (paper_pkg / "tables").mkdir(parents=True, exist_ok=True)
    _write_csv(
        paper_pkg / "tables" / "table_graph_ndcg_and_consistency.csv",
        ["dataset"],
        [["scidocs"]],
    )
    _write_csv(
        paper_pkg / "tables" / "table_bootstrap_delta_ndcg.csv",
        ["dataset"],
        [["scidocs"]],
    )
    _write_csv(
        paper_pkg / "tables" / "table_consistency_qrels_bew.csv",
        ["dataset"],
        [["scidocs"]],
    )
    (paper_pkg / "MANUSCRIPT_SUMMARY.md").write_text("ok", encoding="utf-8")

    _write_csv(
        real_dir / "scidocs" / "qrels" / "scidocs_summary.csv",
        ["method", "n_queries", "ndcg_mean", "map_mean", "pairwise_accuracy_mean", "tau_mean"],
        [["score_sum", "50", "0.5", "0.4", "0.6", "0.2"]],
    )
    (real_dir / "PROVENANCE.md").write_text("ok", encoding="utf-8")

    run_dir = synthetic_dir / "margin_multiseed_n20_noise0.20" / "seed_42"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "synthetic_results.json").write_text(
        json.dumps(
            {
                "config": {"noise": 0.2},
                "evaluation": {"kendall_tau": {"score_sum": 0.7}},
            }
        ),
        encoding="utf-8",
    )
    noise_dir = synthetic_dir / "noise_sweep_n0.20"
    noise_dir.mkdir(parents=True, exist_ok=True)
    (noise_dir / "synthetic_results.json").write_text(
        json.dumps(
            {
                "config": {"noise": 0.2},
                "evaluation": {"kendall_tau": {"score_sum": 0.71}},
            }
        ),
        encoding="utf-8",
    )

    rc = main(
        [
            "--q1-dir",
            str(q1_dir),
            "--paper-package-dir",
            str(paper_pkg),
            "--real-dir",
            str(real_dir),
            "--synthetic-dir",
            str(synthetic_dir),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0

    repair_rows = _read_csv(out_dir / "table_01_repair_effects.csv")
    assert len(repair_rows) == 2
    assert any(r["effect_label"] == "significant_harm" for r in repair_rows)
    assert (out_dir / "table_02_proxy_baseline_leaderboard.csv").exists()
    assert (out_dir / "table_03_synthetic_multiseed_stability.csv").exists()
    assert (out_dir / "table_04_synthetic_noise_sweep.csv").exists()
    assert (out_dir / "table_05_failure_context.csv").exists()
    assert (out_dir / "table_06_artifact_inventory.csv").exists()
    assert (out_dir / "README.md").exists()

