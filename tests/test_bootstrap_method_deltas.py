from __future__ import annotations

import json
from pathlib import Path

from scripts.bootstrap_method_deltas import main


def test_bootstrap_method_deltas_smoke(tmp_path: Path):
    per_query = tmp_path / "per_query.csv"
    per_query.write_text(
        "\n".join(
            [
                "query_id,method,ndcg_at_k,map_at_k,pairwise_accuracy",
                "q1,baseline,0.4,0.4,0.6",
                "q1,hybrid,0.5,0.5,0.7",
                "q2,baseline,0.3,0.2,0.5",
                "q2,hybrid,0.4,0.3,0.6",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_json = tmp_path / "ci.json"
    out_csv = tmp_path / "ci.csv"
    main(
        [
            "--per-query-csv",
            str(per_query),
            "--metric",
            "ndcg_at_k",
            "--method-a",
            "hybrid",
            "--method-b",
            "baseline",
            "--n-bootstrap",
            "500",
            "--seed",
            "7",
            "--output-json",
            str(out_json),
            "--output-csv",
            str(out_csv),
        ]
    )
    rows = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["method_a"] == "hybrid"
    assert rows[0]["method_b"] == "baseline"
    assert rows[0]["n_paired_queries"] == 2
    assert rows[0]["mean_delta"] > 0
    assert out_csv.exists()
