"""Reconstruct attribution from supplied numeric rankings/grades, without APIs.

Inputs are NOT bundled or licensed by this verifier. Supply a rights-cleared
numeric projection conforming to the schema documented in the recovery report.
Expected classifications are opened only after computed results are written.
"""

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def dcg(grades):
    return sum((2.0**grade - 1.0) / math.log2(i + 2) for i, grade in enumerate(grades))


def reconstruct(unit):
    grades = unit["grades"]
    judged = unit["judged"]
    count = len(grades)
    assert count == len(judged) and count > 0
    assert all(math.isfinite(g) for g in grades)
    assert all(type(j) is bool for j in judged)
    assert all(j or g == 0 for j, g in zip(judged, grades))
    assert set(unit["rankings"]) == {"none", "greedy", "scip_exact"}
    for ranking in unit["rankings"].values():
        assert sorted(ranking) == list(range(count))
    ideal = unit["full_ideal_top10"]
    assert len(ideal) <= 10 and ideal == sorted(ideal, reverse=True)
    ideal_dcg = dcg(ideal)
    base = unit["rankings"]["none"]
    positions = {d: i for i, d in enumerate(base)}

    def metric(ranking):
        return dcg([grades[d] for d in ranking[:10]]) / ideal_dcg if ideal_dcg > 0 else 0.0

    original_metric = metric(base)
    positive = sum(g > 0 for g in grades)
    result = []
    for branch in ["greedy", "scip_exact"]:
        ranking = unit["rankings"][branch]
        moved = [d for i, d in enumerate(ranking) if positions[d] != i]
        equal = [grades[d] for d in base[:10]] == [grades[d] for d in ranking[:10]]
        value = metric(ranking)
        delta = value - original_metric
        zero = abs(delta) <= 1e-12
        reason = (
            "ranking_unchanged"
            if not moved
            else "saved_metric_changed"
            if not zero
            else "zero_positive_pool"
            if positive == 0
            else "positive_pool_identical_top10_grade_sequence"
            if equal
            else "positive_pool_different_grade_sequence_unverified_zero"
        )
        result.append(
            dict(
                unit=unit["unit"],
                repair=branch,
                positive_in_pool=positive,
                ranking_changed=bool(moved),
                top10_membership_changed=set(base[:10]) != set(ranking[:10]),
                identical_top10_grade_sequence=equal,
                moved_documents=len(moved),
                moved_unjudged=sum(not judged[d] for d in moved),
                moved_explicit_zero=sum(judged[d] and grades[d] == 0 for d in moved),
                moved_positive=sum(grades[d] > 0 for d in moved),
                moved_negative=sum(judged[d] and grades[d] < 0 for d in moved),
                ndcg10=value,
                baseline_ndcg10=original_metric,
                saved_delta_ndcg10=delta,
                saved_metric_zero=zero,
                descriptive_class=reason,
            )
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = json.loads(args.input.read_text())
    assert inputs["schema"] == "numeric-profile-inputs-v1"
    units = inputs["units"]
    assert len({u["unit"] for u in units}) == len(units)
    computed = [row for unit in units for row in reconstruct(unit)]
    (args.output / "COMPUTED_WITHOUT_REFERENCE.json").write_text(
        json.dumps(computed, indent=2) + "\n"
    )
    expected = json.loads(args.reference.read_text())
    lookup = {(r["unit"], r["repair"]): r for r in expected}
    assert len(lookup) == len(expected) == len(computed)
    maximum_error = 0.0
    field_checks = 0
    for row in computed:
        saved = lookup[(row["unit"], row["repair"])]
        for key, value in saved.items():
            if type(value) is float:
                error = abs(row[key] - value)
                maximum_error = max(maximum_error, error)
                assert error <= 1e-12, (row["unit"], row["repair"], key, error)
            else:
                assert row[key] == value, (row["unit"], row["repair"], key)
            field_checks += 1
    summary = {}
    for branch in ["greedy", "scip_exact"]:
        rows = [r for r in computed if r["repair"] == branch]
        same = [
            r
            for r in rows
            if r["descriptive_class"] == "positive_pool_identical_top10_grade_sequence"
        ]
        summary[branch] = dict(
            query_units=len(rows),
            classes=dict(Counter(r["descriptive_class"] for r in rows)),
            equal_profile_all_moved_unjudged=sum(
                r["moved_documents"] == r["moved_unjudged"] for r in same
            ),
            equal_profile_any_moved_positive=sum(r["moved_positive"] > 0 for r in same),
            equal_profile_membership_changes=sum(r["top10_membership_changed"] for r in same),
        )
    report = dict(
        status="COMPLETED_SUCCESS",
        query_units=len(units),
        branch_records=len(computed),
        reference_field_checks=field_checks,
        max_reference_absolute_error=maximum_error,
        summary=summary,
        scope=(
            "Saved permutation/grade reconstruction and nDCG arithmetic; "
            "no original graph construction, model judgments or repair generation"
        ),
    )
    (args.output / "VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
