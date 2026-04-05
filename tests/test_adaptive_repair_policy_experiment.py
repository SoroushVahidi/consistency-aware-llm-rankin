from __future__ import annotations

from scripts.run_adaptive_repair_policy_experiment import _build_row


def test_build_row_acyclic_skip_policy_math():
    graph_row = {
        "n_queries": "10",
        "mean_ndcg_prior": "0.40",
        "mean_ndcg_uco": "0.35",
        "mean_ndcg_rco": "0.36",
        "mean_ndcg_uba": "0.34",
        "mean_ndcg_rba": "0.345",
    }
    delta_copeland = {
        "strata": {
            "all": {"n": 10},
            "is_cyclic": {"n": 7},
            "acyclic": {"n": 3, "mean_delta_ndcg": 0.02},  # unrepaired - repaired
        }
    }
    delta_balance = {
        "strata": {
            "acyclic": {"mean_delta_ndcg": 0.01},
        }
    }
    row = _build_row(
        dataset="scidocs",
        variant="ms1",
        graph_row=graph_row,
        delta_copeland=delta_copeland,
        delta_balance=delta_balance,
    )
    # skip_rate = 3/10, so adaptive-repaired = 0.3 * 0.02 = 0.006
    assert row.skip_rate_repair == 0.3
    assert row.mean_delta_adaptive_minus_repaired == 0.006
    assert row.mean_ndcg_adaptive_copeland == 0.366
    # balance optional branch also follows same skip-rate scaling
    assert row.mean_delta_adaptive_minus_repaired_balance == 0.003
    assert row.mean_ndcg_adaptive_balance == 0.348
