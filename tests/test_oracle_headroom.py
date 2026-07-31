"""Tests for the preserve-vs-repair Gate-0 infrastructure:
oracle_headroom, label_generation, and grouped_splits.

Uses small synthetic in-memory records and temp CSVs -- no real oracle
data, no network, no model training (this module doesn't train models).
"""

from __future__ import annotations

import csv
import json

import pytest

from consistency_ranker.repair_selector_mining.grouped_splits import split_records
from consistency_ranker.repair_selector_mining.label_generation import (
    assert_no_outcome_leakage,
    label_sensitivity_table,
    regression_labels,
    three_way_label,
    three_way_labels,
)
from consistency_ranker.repair_selector_mining.oracle_headroom import (
    PreserveRepairRecord,
    compute_oracle_headroom,
    evaluate_go_no_go,
    load_paired_delta_records,
    write_oracle_headroom_report,
)


def _rec(qid, preserve, repair, dataset="ds"):
    return PreserveRepairRecord(
        dataset=dataset, query_id=qid, preserve_metric=preserve, repair_metric=repair
    )


# ---------------------------------------------------------------------------
# Per-query delta / oracle action
# ---------------------------------------------------------------------------


def test_delta_and_oracle_action_repair_helps():
    r = _rec("q1", preserve=0.5, repair=0.7)
    assert r.delta == pytest.approx(0.2)
    assert r.oracle_metric == pytest.approx(0.7)
    assert r.oracle_action == "repair"


def test_delta_and_oracle_action_repair_harms():
    r = _rec("q2", preserve=0.6, repair=0.4)
    assert r.delta == pytest.approx(-0.2)
    assert r.oracle_metric == pytest.approx(0.6)
    assert r.oracle_action == "preserve"


def test_exact_tie_resolves_to_preserve_not_repair():
    r = _rec("q3", preserve=0.5, repair=0.5)
    assert r.delta == 0.0
    assert r.oracle_action == "preserve"
    assert r.oracle_metric == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# compute_oracle_headroom / regret identity
# ---------------------------------------------------------------------------


def test_oracle_headroom_empty_raises():
    with pytest.raises(ValueError):
        compute_oracle_headroom([])


def test_headroom_zero_when_one_action_always_wins():
    # repair is always at least as good as preserve everywhere -> oracle ==
    # always_repair, headroom vs best baseline is exactly 0.
    records = [_rec(f"q{i}", preserve=0.5, repair=0.6) for i in range(10)]
    result = compute_oracle_headroom(records)
    assert result.headroom_vs_best_baseline == pytest.approx(0.0, abs=1e-9)
    assert result.frac_benefit_from_repair == pytest.approx(1.0)
    assert result.frac_harmed_by_repair == pytest.approx(0.0)


def test_headroom_positive_with_heterogeneous_effects():
    # Half the queries strongly favor repair, half strongly favor preserve
    # -> oracle beats either fixed baseline by a lot.
    records = [_rec(f"a{i}", preserve=0.2, repair=0.9) for i in range(5)]
    records += [_rec(f"b{i}", preserve=0.9, repair=0.2) for i in range(5)]
    result = compute_oracle_headroom(records)
    assert result.mean_preserve == pytest.approx(0.55)
    assert result.mean_repair == pytest.approx(0.55)
    assert result.mean_oracle == pytest.approx(0.9)
    assert result.headroom_vs_best_baseline == pytest.approx(0.35)
    assert result.frac_benefit_from_repair == pytest.approx(0.5)
    assert result.frac_harmed_by_repair == pytest.approx(0.5)


def test_headroom_equals_mean_regret_of_stronger_baseline():
    records = [_rec("q1", 0.3, 0.6), _rec("q2", 0.5, 0.4), _rec("q3", 0.2, 0.5)]
    result = compute_oracle_headroom(records)
    stronger = max(result.mean_regret_always_preserve, result.mean_regret_always_repair)
    weaker_baseline_mean = min(result.mean_preserve, result.mean_repair)
    # headroom is defined vs. the BEST (stronger-mean) baseline, i.e. the
    # smaller of the two regrets, not the larger.
    smaller_regret = min(result.mean_regret_always_preserve, result.mean_regret_always_repair)
    assert result.headroom_vs_best_baseline == pytest.approx(smaller_regret)
    assert stronger >= smaller_regret
    assert weaker_baseline_mean <= max(result.mean_preserve, result.mean_repair)


def test_headroom_ci_is_nondegenerate_for_heterogeneous_data():
    records = [_rec(f"a{i}", preserve=0.2, repair=0.9) for i in range(10)]
    records += [_rec(f"b{i}", preserve=0.9, repair=0.2) for i in range(10)]
    result = compute_oracle_headroom(records, bootstrap_reps=2000, bootstrap_seed=7)
    assert result.headroom_ci.lower is not None
    assert result.headroom_ci.upper is not None
    assert result.headroom_ci.lower < result.headroom_ci.upper


# ---------------------------------------------------------------------------
# Go/no-go decision boundaries
# ---------------------------------------------------------------------------


def test_go_no_go_no_headroom_when_actions_are_equivalent():
    records = [_rec(f"q{i}", preserve=0.5, repair=0.5) for i in range(20)]
    result = compute_oracle_headroom(records, bootstrap_reps=500, bootstrap_seed=1)
    decision = evaluate_go_no_go(result, headroom_threshold=0.01, min_heterogeneity_fraction=0.05)
    assert decision.decision == "NO_HEADROOM_DO_NOT_LEARN"


def test_go_no_go_proceed_when_headroom_and_heterogeneity_both_clear():
    records = [_rec(f"a{i}", preserve=0.1, repair=0.9) for i in range(20)]
    records += [_rec(f"b{i}", preserve=0.9, repair=0.1) for i in range(20)]
    result = compute_oracle_headroom(records, bootstrap_reps=2000, bootstrap_seed=3)
    decision = evaluate_go_no_go(result, headroom_threshold=0.01, min_heterogeneity_fraction=0.05)
    assert decision.decision == "PROCEED_TO_LABELING"


def test_go_no_go_ambiguous_when_heterogeneity_is_one_sided():
    # Headroom exists (repair sometimes helps a lot) but essentially no
    # query is harmed -> not genuine two-sided heterogeneity.
    records = [_rec(f"a{i}", preserve=0.5, repair=0.9) for i in range(19)]
    records += [_rec("b0", preserve=0.9, repair=0.5)]  # 1/20 = 5% harmed, right at the edge
    result = compute_oracle_headroom(records, bootstrap_reps=500, bootstrap_seed=1)
    decision = evaluate_go_no_go(result, headroom_threshold=0.01, min_heterogeneity_fraction=0.10)
    assert decision.decision in ("AMBIGUOUS_NEED_MORE_DATA", "NO_HEADROOM_DO_NOT_LEARN")
    assert decision.decision != "PROCEED_TO_LABELING"


# ---------------------------------------------------------------------------
# Loading from CSV, including missing/malformed rows and filters
# ---------------------------------------------------------------------------


def test_load_paired_delta_records_filters_and_skips_missing(tmp_path):
    csv_path = tmp_path / "outcomes.csv"

    def _row(dataset, query_id, regime, unrepaired, repaired):
        return {
            "dataset": dataset,
            "query_id": query_id,
            "regime": regime,
            "unrepaired_ndcg": unrepaired,
            "repaired_ndcg": repaired,
        }

    rows = [
        _row("scidocs", "q1", "ms1", "0.5", "0.6"),
        _row("scidocs", "q2", "ms2", "0.4", "0.3"),
        _row("fiqa", "q3", "ms1", "0.7", "0.8"),
        _row("scidocs", "q4", "ms1", "", "0.9"),
        _row("scidocs", "q5", "ms1", "NA", "0.9"),
    ]
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    all_scidocs = load_paired_delta_records(csv_path, dataset="scidocs")
    # q1 kept; q2 kept (different regime, but no regime filter applied);
    # q4/q5 skipped (missing/non-numeric unrepaired_ndcg).
    assert {r.query_id for r in all_scidocs} == {"q1", "q2"}

    filtered = load_paired_delta_records(
        csv_path, dataset="scidocs", extra_filters={"regime": "ms1"}
    )
    assert {r.query_id for r in filtered} == {"q1"}

    fiqa_only = load_paired_delta_records(csv_path, dataset="fiqa")
    assert {r.query_id for r in fiqa_only} == {"q3"}


def test_load_paired_delta_records_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_paired_delta_records(tmp_path / "does_not_exist.csv")


# ---------------------------------------------------------------------------
# Label generation
# ---------------------------------------------------------------------------


def test_three_way_label_boundaries():
    assert three_way_label(0.05, epsilon=0.02) == "beneficial"
    assert three_way_label(-0.05, epsilon=0.02) == "harmful"
    assert three_way_label(0.01, epsilon=0.02) == "neutral"
    # Exactly at epsilon -> neutral, not beneficial.
    assert three_way_label(0.02, epsilon=0.02) == "neutral"
    assert three_way_label(0.0, epsilon=0.0) == "neutral"


def test_three_way_label_rejects_negative_epsilon():
    with pytest.raises(ValueError):
        three_way_label(0.1, epsilon=-0.01)


def test_regression_labels_match_delta():
    records = [_rec("q1", 0.3, 0.5), _rec("q2", 0.6, 0.4)]
    labels = regression_labels(records)
    assert labels[("ds", "q1")] == pytest.approx(0.2)
    assert labels[("ds", "q2")] == pytest.approx(-0.2)


def test_three_way_labels_keyed_by_dataset_query_id():
    records = [_rec("q1", 0.3, 0.5, dataset="a"), _rec("q1", 0.5, 0.3, dataset="b")]
    labels = three_way_labels(records, epsilon=0.01)
    assert labels[("a", "q1")] == "beneficial"
    assert labels[("b", "q1")] == "harmful"


def test_label_sensitivity_table_monotone_neutral_growth():
    records = [_rec(f"q{i}", 0.5, 0.5 + (i - 5) * 0.01) for i in range(10)]
    rows = label_sensitivity_table(records, [0.0, 0.02, 0.1])
    by_eps = {row.epsilon: row for row in rows}
    # Larger epsilon can only ever keep the same or MORE queries neutral.
    assert by_eps[0.0].n_neutral <= by_eps[0.02].n_neutral <= by_eps[0.1].n_neutral
    assert by_eps[0.1].n_neutral == 10  # all deltas are within +/-0.05 < 0.1
    for row in rows:
        assert row.n_beneficial + row.n_neutral + row.n_harmful == 10


def test_label_sensitivity_table_empty_raises():
    with pytest.raises(ValueError):
        label_sensitivity_table([], [0.01])


def test_assert_no_outcome_leakage_catches_bad_names():
    with pytest.raises(AssertionError):
        assert_no_outcome_leakage(["is_cyclic", "delta_ndcg"])
    with pytest.raises(AssertionError):
        assert_no_outcome_leakage(["oracle_action"])


def test_assert_no_outcome_leakage_passes_clean_names():
    assert_no_outcome_leakage(["is_cyclic", "largest_scc_frac", "graph_density", "n_nodes"])


# ---------------------------------------------------------------------------
# Grouped splitting: no query-level leakage
# ---------------------------------------------------------------------------


def test_split_records_no_query_in_multiple_splits():
    records = [_rec(f"q{i}", preserve=0.5, repair=0.5 + 0.01 * i) for i in range(60)]
    train, val, test = split_records(records, seed=42)
    train_keys = {r.key() for r in train}
    val_keys = {r.key() for r in val}
    test_keys = {r.key() for r in test}
    assert train_keys.isdisjoint(val_keys)
    assert train_keys.isdisjoint(test_keys)
    assert val_keys.isdisjoint(test_keys)
    assert len(train_keys) + len(val_keys) + len(test_keys) == 60


def test_split_records_avoids_fingerprint_collision_with_no_query_text():
    # Regression guard for the documented gotcha: every record must not
    # collapse into a single fingerprint group just because there is no
    # query_text field on PreserveRepairRecord.
    records = [_rec(f"q{i}", preserve=0.5, repair=0.6) for i in range(30)]
    train, val, test = split_records(records, seed=1)
    assert len(train) > 1
    assert len(train) + len(val) + len(test) == 30
    # Not everything landed in one split.
    assert len({len(train) > 0, len(val) > 0, len(test) > 0}) >= 1
    assert (len(val) > 0) or (len(test) > 0)


def test_split_records_same_query_id_different_dataset_can_differ():
    # (dataset, query_id) is the grouping key, not query_id alone.
    records = [_rec("shared_id", 0.5, 0.6, dataset=f"ds{i}") for i in range(20)]
    train, val, test = split_records(records, seed=5)
    assert len(train) + len(val) + len(test) == 20


def test_split_records_deterministic_for_fixed_seed():
    records = [_rec(f"q{i}", preserve=0.5, repair=0.6) for i in range(40)]
    a = split_records(records, seed=99)
    b = split_records(records, seed=99)
    assert [r.key() for r in a[0]] == [r.key() for r in b[0]]
    assert [r.key() for r in a[1]] == [r.key() for r in b[1]]
    assert [r.key() for r in a[2]] == [r.key() for r in b[2]]


# ---------------------------------------------------------------------------
# Deterministic report generation
# ---------------------------------------------------------------------------


def test_write_oracle_headroom_report_is_byte_identical_across_runs(tmp_path):
    records = [_rec(f"q{i}", preserve=0.3 + 0.01 * i, repair=0.5 - 0.005 * i) for i in range(15)]
    csv_path = tmp_path / "in.csv"
    with csv_path.open("w", newline="") as f:
        fieldnames = ["dataset", "query_id", "unrepaired_ndcg", "repaired_ndcg"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "dataset": r.dataset,
                    "query_id": r.query_id,
                    "unrepaired_ndcg": r.preserve_metric,
                    "repaired_ndcg": r.repair_metric,
                }
            )

    result = compute_oracle_headroom(records, bootstrap_reps=500, bootstrap_seed=1)
    decision = evaluate_go_no_go(result)

    out1, out2 = tmp_path / "out1", tmp_path / "out2"
    write_oracle_headroom_report(result, decision, out1, input_csv=csv_path)
    write_oracle_headroom_report(result, decision, out2, input_csv=csv_path)

    assert (out1 / "REPORT.md").read_text() == (out2 / "REPORT.md").read_text()
    m1 = json.loads((out1 / "MANIFEST.json").read_text())
    m2 = json.loads((out2 / "MANIFEST.json").read_text())
    assert m1 == m2
    assert m1["input_csv_sha256"] == m2["input_csv_sha256"]
