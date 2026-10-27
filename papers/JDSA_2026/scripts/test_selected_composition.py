"""Synthetic unit fixtures only; no research payload or significance tests."""

import copy
import math
import unittest

from stratify_selected_cache import aggregate, compute, historical_contract, summarize


def fixture(name="fixture", **overrides):
    # Query has a positive at rank one; only two unjudged zeros exchange.
    unit = dict(
        unit=name,
        query_id=name,
        dataset="scidocs",
        providers=2,
        cyclic=True,
        grades=[1, 0, 0],
        judged=[True, False, False],
        full_ideal_top10=[1, 1],  # Includes one out-of-pool positive.
        rankings={"none": [0, 1, 2], "greedy": [0, 2, 1], "scip_exact": [1, 0, 2]},
    )
    unit.update(overrides)
    return unit


class CompositionTests(unittest.TestCase):
    def test_profile_invariance_and_harm_with_full_query_ideal(self):
        greedy, exact = compute([fixture()])
        self.assertEqual(greedy["baseline_ndcg10"], 1 / (1 + 1 / math.log2(3)))
        self.assertTrue(greedy["ranking_changed"])
        self.assertTrue(greedy["identical_top10_grade_sequence"])
        self.assertEqual(greedy["saved_delta_ndcg10"], 0)
        self.assertEqual(greedy["moved_unjudged"], 2)
        self.assertLess(exact["saved_delta_ndcg10"], 0)
        self.assertFalse(exact["identical_top10_grade_sequence"])

    def test_dependent_branches_and_empty_cells(self):
        summary = summarize(compute([fixture()]))
        self.assertEqual(len(summary["intersections"]), 16)
        self.assertEqual(summary["all"]["greedy"]["queries"], 1)
        self.assertEqual(summary["all"]["scip_exact"]["queries"], 1)
        self.assertEqual(summary["dataset"]["fiqa"]["greedy"]["queries"], 0)
        self.assertEqual(summary["all"]["greedy"]["changed_positive_equal_profile"], 1)
        self.assertEqual(summary["all"]["scip_exact"]["deteriorations"], 1)

    def test_zero_positive_is_not_a_positive_profile_case(self):
        unit = fixture(grades=[0, 0, 0], judged=[True, False, False], full_ideal_top10=[1])
        summary = summarize(compute([unit]))["all"]["greedy"]
        self.assertEqual(summary["changed_zero_positive"], 1)
        self.assertEqual(summary["changed_positive_equal_profile"], 0)
        self.assertEqual(summary["utility_changed"], 0)

    def test_query_identity_collision_rejected(self):
        first = fixture()
        second = copy.deepcopy(first)
        second["unit"] = "different-numeric-linkage-same-query"
        with self.assertRaisesRegex(ValueError, "original dataset/query"):
            compute([first, second])
        with self.assertRaisesRegex(ValueError, "one repair record"):
            aggregate([compute([first])[0]] * 2)

    def test_missing_identity_bad_stratum_and_permutation_rejected(self):
        for values in ({"query_id": ""}, {"providers": 3}, {"cyclic": 1}):
            with self.assertRaises(ValueError):
                compute([fixture(**values)])
        unit = fixture()
        unit["rankings"]["greedy"] = [0, 0, 2]
        with self.assertRaises(AssertionError):
            compute([unit])

    def test_nonfinite_ideal_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaisesRegex(ValueError, "Nonfinite"):
                compute([fixture(full_ideal_top10=[bad])])

    def test_historical_mismatch_stops_instead_of_forcing_totals(self):
        with self.assertRaisesRegex(ValueError, "Historical discrepancy"):
            historical_contract(summarize(compute([fixture()])))


if __name__ == "__main__":
    unittest.main()
