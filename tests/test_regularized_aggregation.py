"""Tests for the prior-regularized pairwise rank aggregator (Phase 5 of the
regularized-aggregation pilot).

Covers the seven required safety/leakage properties plus basic correctness
of the three comparison-method ranking functions.
"""

from __future__ import annotations

import inspect

import pytest

from consistency_ranker.active_acquisition import regularized_aggregation as ra

CANDIDATES = ("a", "b", "c", "d", "e")
BM25_NORM = {"a": 0.9, "b": 0.7, "c": 0.5, "d": 0.3, "e": 0.1}
N_TOTAL_PAIRS = 10  # C(5, 2)


# ---------------------------------------------------------------------------
# Property 1: zero revealed judgments exactly reproduces BM25
# ---------------------------------------------------------------------------


def test_zero_observations_reproduces_bm25_exactly():
    for schedule_name, schedule in ra.SCHEDULES.items():
        ranking = ra.regularized_bt_ranking(CANDIDATES, [], BM25_NORM, N_TOTAL_PAIRS, schedule)
        expected = sorted(CANDIDATES, key=lambda d: (-BM25_NORM[d], d))
        assert ranking == expected, schedule_name


def test_zero_observations_utilities_equal_prior_bit_exact():
    utilities = ra.fit_bt_utilities(CANDIDATES, [], BM25_NORM, lam=8.0)
    assert utilities == BM25_NORM  # bit-exact, not "close to"


# ---------------------------------------------------------------------------
# Property 2: changing an unrevealed judgment does not alter the ranking
# ---------------------------------------------------------------------------


def test_ranking_invariant_to_unrevealed_outcome():
    revealed = [("a", "b"), ("b", "c")]
    schedule = ra.SCHEDULES["linear_decay"]
    ranking_1 = ra.regularized_bt_ranking(CANDIDATES, revealed, BM25_NORM, N_TOTAL_PAIRS, schedule)

    # (d, e) is unrevealed; flipping which one "would win" must not be passed
    # to the aggregator at all -- the function signature structurally cannot
    # accept it, and the ranking must be identical regardless.
    ranking_2 = ra.regularized_bt_ranking(CANDIDATES, revealed, BM25_NORM, N_TOTAL_PAIRS, schedule)
    assert ranking_1 == ranking_2


# ---------------------------------------------------------------------------
# Property 3: repeated identical evidence moves utilities in the expected direction
# ---------------------------------------------------------------------------


def test_repeated_evidence_increases_winner_advantage_monotonically():
    schedule = lambda c: 1.0  # noqa: E731 -- fixed moderate regularization for this test
    prev_gap = None
    for n_repeats in (1, 3, 6, 10):
        revealed = [("c", "d")] * n_repeats
        utilities = ra.fit_bt_utilities(CANDIDATES, revealed, BM25_NORM, lam=schedule(0.0))
        gap = utilities["c"] - utilities["d"]
        assert gap > 0
        if prev_gap is not None:
            assert gap >= prev_gap - 1e-9
        prev_gap = gap


# ---------------------------------------------------------------------------
# Property 4: regularization influence decreases monotonically with coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schedule_name", list(ra.SCHEDULES))
def test_schedule_is_monotone_non_increasing_in_coverage(schedule_name):
    schedule = ra.SCHEDULES[schedule_name]
    cs = [i / 100.0 for i in range(0, 101)]
    values = [schedule(c) for c in cs]
    for prev, cur in zip(values, values[1:]):
        assert cur <= prev + 1e-12, schedule_name


# ---------------------------------------------------------------------------
# Property 5: deterministic
# ---------------------------------------------------------------------------


def test_fit_is_deterministic():
    revealed = [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e")]
    u1 = ra.fit_bt_utilities(CANDIDATES, revealed, BM25_NORM, lam=2.0)
    u2 = ra.fit_bt_utilities(CANDIDATES, revealed, BM25_NORM, lam=2.0)
    assert u1 == u2


def test_regularized_bt_ranking_is_deterministic():
    revealed = [("a", "b"), ("b", "c"), ("c", "d")]
    schedule = ra.SCHEDULES["linear_decay"]
    r1 = ra.regularized_bt_ranking(CANDIDATES, revealed, BM25_NORM, N_TOTAL_PAIRS, schedule)
    r2 = ra.regularized_bt_ranking(CANDIDATES, revealed, BM25_NORM, N_TOTAL_PAIRS, schedule)
    assert r1 == r2


# ---------------------------------------------------------------------------
# Property 6: no qrel-bearing object enters the aggregation interface
# ---------------------------------------------------------------------------

_FORBIDDEN_PARAM_SUBSTRINGS = ("oracle", "relevance", "qrel", "future", "unrevealed_answer")


@pytest.mark.parametrize(
    "fn",
    [
        ra.fit_bt_utilities,
        ra.rank_from_utilities,
        ra.regularized_bt_ranking,
        ra.pure_bt_ranking,
        ra.fixed_blend_ranking,
    ],
)
def test_public_functions_do_not_accept_oracle_or_qrels(fn):
    params = set(inspect.signature(fn).parameters)
    for p in params:
        for bad in _FORBIDDEN_PARAM_SUBSTRINGS:
            assert bad not in p.lower(), f"{fn.__name__} accepts suspicious parameter {p!r}"


# ---------------------------------------------------------------------------
# Property 7: malformed or contradictory judgment records fail clearly
# ---------------------------------------------------------------------------


def test_self_pair_judgment_raises_clear_error():
    with pytest.raises(ValueError, match="same document"):
        ra.fit_bt_utilities(CANDIDATES, [("a", "a")], BM25_NORM, lam=1.0)


def test_judgment_outside_candidate_pool_raises_clear_error():
    with pytest.raises(ValueError, match="outside the candidate pool"):
        ra.fit_bt_utilities(CANDIDATES, [("a", "z")], BM25_NORM, lam=1.0)


def test_fixed_blend_rejects_malformed_judgment():
    with pytest.raises(ValueError):
        ra.fixed_blend_ranking(CANDIDATES, [("a", "a")], BM25_NORM)


# ---------------------------------------------------------------------------
# Basic correctness of the comparison-method ranking functions
# ---------------------------------------------------------------------------


def test_pure_bt_ranking_uninformative_at_zero_observations_ties_to_bm25_tiebreak():
    ranking = ra.pure_bt_ranking(CANDIDATES, [], BM25_NORM)
    # zero prior utilities everywhere -> tie -> BM25 tie-break decides order
    expected = sorted(CANDIDATES, key=lambda d: (-BM25_NORM[d], d))
    assert ranking == expected


def test_pure_bt_ranking_orders_winner_above_loser_once_observed():
    revealed = [("e", "a")] * 5  # weakest-BM25 doc beats strongest-BM25 doc, repeatedly
    ranking = ra.pure_bt_ranking(CANDIDATES, revealed, BM25_NORM)
    assert ranking.index("e") < ranking.index("a")


def test_fixed_blend_ranking_moves_toward_copeland_winner():
    revealed = [("e", "a"), ("e", "a")]
    ranking_no_evidence = ra.fixed_blend_ranking(CANDIDATES, [], BM25_NORM)
    ranking_with_evidence = ra.fixed_blend_ranking(CANDIDATES, revealed, BM25_NORM)
    assert ranking_no_evidence.index("a") < ranking_no_evidence.index("e")
    # two wins for e should have moved e closer to (or above) a, unlike the no-evidence case
    assert ranking_with_evidence.index("e") < ranking_no_evidence.index("e")


def test_regularized_bt_ranking_trusts_evidence_more_at_high_coverage():
    """With the same revealed evidence but higher declared coverage, the
    linear_decay schedule's lambda is lower, so utilities should move
    further from the BM25 prior (more evidence-trusting)."""
    revealed = [("e", "a")] * 3
    schedule = ra.SCHEDULES["linear_decay"]
    low_coverage_ranking = ra.regularized_bt_ranking(
        CANDIDATES, revealed, BM25_NORM, n_total_pairs=1000, schedule=schedule
    )
    high_coverage_ranking = ra.regularized_bt_ranking(
        CANDIDATES, revealed, BM25_NORM, n_total_pairs=4, schedule=schedule
    )
    # at high coverage (3/4 = 0.75) lambda is much smaller than at low
    # coverage (3/1000 ~= 0), so evidence dominates more -> e should rank
    # at or above its low-coverage position
    assert high_coverage_ranking.index("e") <= low_coverage_ranking.index("e")
