from __future__ import annotations

from pathlib import Path

from scripts.run_synthetic import run_experiment


def test_run_experiment_exposes_followup_fas_variants(tmp_path: Path):
    results = run_experiment(
        n_items=8,
        noise=0.2,
        seed=7,
        weight_scheme="margin",
        output_dir=tmp_path,
        save_timings=False,
        profile=False,
    )

    tau = results["evaluation"]["kendall_tau"]
    rankings = results["rankings"]
    expected_methods = {
        "score_sum",
        "borda",
        "greedy_fas_topological",
        "priority_topological_score_sum",
        "fas_weighted_balance",
        "fas_copeland",
        "hybrid_rrf_fas_regularized",
    }

    assert expected_methods.issubset(rankings)
    assert expected_methods.issubset(tau)
