from __future__ import annotations

import csv
from pathlib import Path

from scripts.run_bootstrap import main

HEADER = [
    "dataset",
    "query_id",
    "method",
    "preference_source",
    "ndcg_at_k",
    "kendall_tau",
    "pairwise_accuracy",
]


def _row(
    dataset: str,
    query_id: str,
    method: str,
    preference_source: str,
    ndcg_at_k: str,
    kendall_tau: str,
    pairwise_accuracy: str,
) -> dict[str, str]:
    return {
        "dataset": dataset,
        "query_id": query_id,
        "method": method,
        "preference_source": preference_source,
        "ndcg_at_k": ndcg_at_k,
        "kendall_tau": kendall_tau,
        "pairwise_accuracy": pairwise_accuracy,
    }


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def test_run_bootstrap_generates_expected_comparisons(tmp_path: Path):
    per_query = tmp_path / "toy" / "toy_per_query.csv"
    rows = [
        _row("toy", "q1", "score_sum", "qrels", "0.40", "0.10", "0.60"),
        _row("toy", "q1", "borda", "qrels", "0.42", "0.11", "0.61"),
        _row(
            "toy",
            "q1",
            "greedy_fas_weighted_balance",
            "qrels",
            "0.90",
            "0.70",
            "0.92",
        ),
        _row(
            "toy",
            "q1",
            "hybrid_rrf_fas_regularized",
            "qrels",
            "0.95",
            "0.80",
            "0.96",
        ),
        _row("toy", "q2", "score_sum", "qrels", "0.30", "0.05", "0.55"),
        _row("toy", "q2", "borda", "qrels", "0.31", "0.06", "0.54"),
        _row(
            "toy",
            "q2",
            "greedy_fas_weighted_balance",
            "qrels",
            "0.85",
            "0.65",
            "0.88",
        ),
        _row(
            "toy",
            "q2",
            "hybrid_rrf_fas_regularized",
            "qrels",
            "0.92",
            "0.78",
            "0.94",
        ),
    ]
    _write_rows(per_query, rows)

    output = tmp_path / "bootstrap_results.csv"
    results = main(
        [
            "--input",
            str(per_query),
            "--metrics",
            "ndcg",
            "kendall_tau",
            "pairwise_accuracy",
            "--n-bootstrap",
            "400",
            "--seed",
            "3",
            "--output",
            str(output),
        ]
    )

    assert output.exists()
    assert len(results) == 12
    ndcg_rows = [r for r in results if r.metric == "ndcg"]
    assert {(r.method_a, r.method_b) for r in ndcg_rows} == {
        ("greedy_fas_weighted_balance", "score_sum"),
        ("greedy_fas_weighted_balance", "borda"),
        ("hybrid_rrf_fas_regularized", "score_sum"),
        ("hybrid_rrf_fas_regularized", "borda"),
    }
    assert all(r.significant for r in ndcg_rows)
    assert all(r.mean_diff > 0 for r in ndcg_rows)
    assert all(0.0 <= r.p_value <= 1.0 for r in results)


def test_run_bootstrap_skips_mixed_preference_source_file(tmp_path: Path, capsys):
    per_query = tmp_path / "mixed" / "mixed_per_query.csv"
    rows = [
        _row("mixed", "q1", "score_sum", "qrels", "0.5", "0.3", "0.7"),
        _row("mixed", "q1", "borda", "qrels_flip", "0.4", "0.2", "0.6"),
    ]
    _write_rows(per_query, rows)

    output = tmp_path / "bootstrap_results.csv"
    try:
        main(["--input", str(per_query), "--output", str(output)])
    except SystemExit as exc:
        assert str(exc) == "No valid per-query inputs remained after validation."
    else:
        raise AssertionError("Expected mixed-source file to be rejected")

    stderr = capsys.readouterr().err
    assert "mixed preference_source values" in stderr
    assert not output.exists()


def test_run_bootstrap_scans_new_layout_and_filters_sources(tmp_path: Path):
    qrels_path = (
        tmp_path / "outputs" / "real_small_validation" / "toy" / "qrels" / "toy_per_query.csv"
    )
    qrels_flip_path = (
        tmp_path / "outputs" / "real_small_validation" / "toy" / "qrels_flip" / "toy_per_query.csv"
    )
    shared_rows = [
        _row("toy", "q1", "score_sum", "qrels", "0.40", "0.10", "0.60"),
        _row("toy", "q1", "borda", "qrels", "0.42", "0.11", "0.61"),
        _row("toy", "q1", "greedy_fas_weighted_balance", "qrels", "0.55", "0.25", "0.65"),
        _row("toy", "q1", "hybrid_rrf_fas_regularized", "qrels", "0.56", "0.28", "0.66"),
        _row("toy", "q2", "score_sum", "qrels", "0.41", "0.12", "0.62"),
        _row("toy", "q2", "borda", "qrels", "0.43", "0.13", "0.63"),
        _row("toy", "q2", "greedy_fas_weighted_balance", "qrels", "0.57", "0.27", "0.67"),
        _row("toy", "q2", "hybrid_rrf_fas_regularized", "qrels", "0.58", "0.29", "0.68"),
    ]
    _write_rows(qrels_path, shared_rows)
    _write_rows(
        qrels_flip_path,
        [{**row, "preference_source": "qrels_flip"} for row in shared_rows],
    )

    output = tmp_path / "bootstrap_results_qrels.csv"
    results = main(
        [
            "--input",
            str(qrels_path),
            str(qrels_flip_path),
            "--preference-source",
            "qrels",
            "--output",
            str(output),
            "--n-bootstrap",
            "200",
        ]
    )

    assert output.exists()
    assert results
    assert {result.preference_source for result in results} == {"qrels"}
