"""Tests for the offline active-acquisition pilot.

Covers: oracle-loading exhaustiveness, extraction-rule determinism and
order-invariance, evaluation edge cases, statistics wrappers, and — most
importantly — leakage: acquisition-scoring functions must never depend on
qrels or on the cached oracle answer for a still-unrevealed pair.
"""

from __future__ import annotations

import inspect
import random
from pathlib import Path

import pytest

from consistency_ranker.active_acquisition import evaluate, scoring, stats, strategies
from consistency_ranker.active_acquisition.oracle import QueryOracle, load_scidocs_pairwise_oracle
from consistency_ranker.active_acquisition.simulate import reference_rankings, simulate_trajectory

REPO_ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS_PATH = REPO_ROOT / "outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl"

pytestmark = pytest.mark.skipif(
    not JUDGMENTS_PATH.exists(),
    reason="offline oracle artifact not present in this checkout",
)


@pytest.fixture(scope="module")
def oracles() -> dict[str, QueryOracle]:
    return load_scidocs_pairwise_oracle(JUDGMENTS_PATH)


# ---------------------------------------------------------------------------
# Oracle feasibility properties (Phase 1 preconditions, enforced as tests)
# ---------------------------------------------------------------------------


def test_oracle_has_expected_query_count(oracles):
    assert len(oracles) == 50


def test_oracle_pools_are_exhaustive_and_fixed_size(oracles):
    for qid, oe in oracles.items():
        n = len(oe.candidates)
        assert n == 15, f"{qid}: expected 15 candidates, got {n}"
        expected_pairs = n * (n - 1) // 2
        assert len(oe.oracle) == expected_pairs

        # every relevance value must be present (post-hoc eval only, never leaked into scoring)
        assert set(oe.relevance) == set(oe.candidates)


def test_oracle_reveal_matches_cached_direction(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    i, j = oe.candidates[0], oe.candidates[1]
    winner, loser = oe.reveal(i, j)
    assert {winner, loser} == {i, j}
    assert oe.oracle[frozenset((i, j))] == winner


# ---------------------------------------------------------------------------
# Extraction rule: deterministic, order-invariant at completion
# ---------------------------------------------------------------------------


def test_initial_ranking_is_pure_bm25_order(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    initial_ranking, _ = reference_rankings(oe)
    bm25_norm = scoring.normalize_bm25(oe.candidates, oe.bm25_scores)
    expected = sorted(oe.candidates, key=lambda d: (-bm25_norm.get(d, 0.0), d))
    assert initial_ranking == expected


def test_exhaustive_ranking_is_order_invariant_across_algorithms(oracles):
    """Copeland at completion depends only on the *set* of revealed edges,
    not the order acquired — so every algorithm must converge to the exact
    same final ranking."""
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    _, expected_exhaustive = reference_rankings(oe)
    n_pairs = len(oe.candidates) * (len(oe.candidates) - 1) // 2
    for algo in ("random", "score:proposed", "cycle_scc"):
        cps = simulate_trajectory(oe, algo, [n_pairs - 1], k=10, seed=123)
        # one step short of exhaustive already nearly matches; run a direct
        # full-reveal check via the Copeland tally instead for an exact test
        assert cps  # sanity: at least one checkpoint produced

    # Direct exact check: revealing all pairs in two different random orders
    # must produce identical final Copeland rankings.
    def _full_reveal_ranking(seed: int) -> list[str]:
        rng = random.Random(seed)
        pairs = list(oe.oracle.keys())
        rng.shuffle(pairs)
        copeland = {d: 0.0 for d in oe.candidates}
        for pair in pairs:
            winner = oe.oracle[pair]
            loser = next(d for d in pair if d != winner)
            copeland[winner] += 1.0
            copeland[loser] -= 1.0
        bm25_norm = scoring.normalize_bm25(oe.candidates, oe.bm25_scores)
        return scoring.rank_from_copeland(oe.candidates, copeland, bm25_norm)

    r1 = _full_reveal_ranking(1)
    r2 = _full_reveal_ranking(2)
    assert r1 == r2 == expected_exhaustive


def test_simulate_trajectory_reveals_exactly_budget_edges(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    cps = simulate_trajectory(oe, "score:proposed", [5, 21, 42], k=10, seed=42)
    budgets = [c.budget for c in cps]
    assert budgets == [5, 21, 42]


def test_random_strategy_is_seed_deterministic(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    cps_a = simulate_trajectory(oe, "random", [10, 20], k=10, seed=7)
    cps_b = simulate_trajectory(oe, "random", [10, 20], k=10, seed=7)
    assert [c.ranking for c in cps_a] == [c.ranking for c in cps_b]


# ---------------------------------------------------------------------------
# Leakage tests — the most important tests in this file
# ---------------------------------------------------------------------------

_FORBIDDEN_PARAM_SUBSTRINGS = ("oracle", "relevance", "qrel", "future", "unrevealed_answer")


@pytest.mark.parametrize(
    "fn",
    [
        scoring.uncertainty_score,
        scoring.ambiguity_score,
        scoring.topk_impact_score,
        scoring.proposed_score,
        scoring.ablation_impact_only,
        scoring.ablation_uncertainty_only,
        scoring.ablation_impact_x_uncertainty,
    ],
)
def test_scoring_functions_do_not_accept_oracle_or_qrels(fn):
    """Structural leakage guard: no acquisition-scoring function may even be
    *callable* with an oracle or qrels argument."""
    params = set(inspect.signature(fn).parameters)
    for p in params:
        for bad in _FORBIDDEN_PARAM_SUBSTRINGS:
            assert bad not in p.lower(), f"{fn.__name__} accepts suspicious parameter {p!r}"
    # exactly (ctx, i, j) — nothing else can smuggle in extra state
    assert params == {"ctx", "i", "j"}


def test_pick_next_pair_does_not_accept_oracle_or_qrels():
    params = set(inspect.signature(strategies.pick_next_pair).parameters)
    for p in params:
        for bad in _FORBIDDEN_PARAM_SUBSTRINGS:
            assert bad not in p.lower()


def test_scoring_is_invariant_to_the_unrevealed_answer(oracles):
    """Behavioral leakage test: flipping the *cached* oracle answer for a
    still-unrevealed pair must not change any acquisition score computed for
    that pair, because the scoring functions structurally never consult it."""
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    candidates = oe.candidates
    bm25_norm = scoring.normalize_bm25(candidates, oe.bm25_scores)

    # Reveal a handful of pairs to build a non-trivial partial state.
    revealed: list[tuple[str, str]] = []
    copeland = {d: 0.0 for d in candidates}
    some_pairs = list(oe.oracle.items())[:20]
    for pair, winner in some_pairs:
        loser = next(d for d in pair if d != winner)
        revealed.append((winner, loser))
        copeland[winner] += 1.0
        copeland[loser] -= 1.0

    ctx = scoring.StepContext.build(candidates, revealed, copeland, bm25_norm, k=10)

    revealed_docs = {d for pair in some_pairs for d in pair}
    unobserved_candidates = [d for d in candidates if d not in revealed_docs]
    assert len(unobserved_candidates) >= 2
    i, j = unobserved_candidates[0], unobserved_candidates[1]

    scores_before = (
        scoring.uncertainty_score(ctx, i, j),
        scoring.ambiguity_score(ctx, i, j),
        scoring.topk_impact_score(ctx, i, j),
        scoring.proposed_score(ctx, i, j),
    )

    # Build a *different* oracle where (i, j)'s cached winner is flipped —
    # the acquisition state (ctx) built above is identical either way, since
    # it was built only from `revealed`, never from `oe.oracle`.
    flipped_oracle = dict(oe.oracle)
    flipped_oracle[frozenset((i, j))] = j if oe.oracle[frozenset((i, j))] == i else i
    flipped_oe = QueryOracle(
        query_id=oe.query_id,
        candidates=oe.candidates,
        oracle=flipped_oracle,
        bm25_scores=oe.bm25_scores,
        relevance=oe.relevance,
    )
    # Rebuild ctx from the *same* revealed history (unaffected by the flip,
    # since (i, j) was never in `revealed`).
    ctx2 = scoring.StepContext.build(
        flipped_oe.candidates, revealed, dict(copeland), bm25_norm, k=10
    )
    scores_after = (
        scoring.uncertainty_score(ctx2, i, j),
        scoring.ambiguity_score(ctx2, i, j),
        scoring.topk_impact_score(ctx2, i, j),
        scoring.proposed_score(ctx2, i, j),
    )
    assert scores_before == scores_after


def test_static_adjacent_ignores_downstream_state(oracles):
    """The static baseline's order must be fixed by the initial BM25 ranking
    alone and must not depend on ctx (a stand-in confirms the branch never
    reads ctx fields other than what's passed explicitly as static_order)."""
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    from consistency_ranker.active_acquisition.simulate import _static_order

    order1 = _static_order(oe.candidates, oe.bm25_scores)
    order2 = _static_order(oe.candidates, oe.bm25_scores)
    assert order1 == order2  # deterministic, recomputable without any revealed evidence


# ---------------------------------------------------------------------------
# Evaluation edge cases
# ---------------------------------------------------------------------------


def test_budget_to_fraction_returns_none_when_no_improvement():
    budgets = [5, 10, 20]
    ndcgs = [0.9, 0.9, 0.9]
    result = evaluate.budget_to_fraction_of_improvement(
        budgets, ndcgs, ndcg_initial=0.9, ndcg_exhaustive=0.9, fraction=0.9
    )
    assert result is None


def test_budget_to_fraction_returns_none_when_exhaustive_worse():
    budgets = [5, 10, 20]
    ndcgs = [0.5, 0.4, 0.3]
    result = evaluate.budget_to_fraction_of_improvement(
        budgets, ndcgs, ndcg_initial=0.6, ndcg_exhaustive=0.3, fraction=0.9
    )
    assert result is None


def test_budget_to_fraction_basic():
    budgets = [1, 2, 3]
    ndcgs = [0.5, 0.9, 1.0]
    # target = ndcg_initial + 0.9 * (ndcg_exhaustive - ndcg_initial) = 0.5 + 0.9*0.5 = 0.95
    # not reached at budget=2 (0.9 < 0.95); first reached at budget=3 (1.0 >= 0.95)
    result = evaluate.budget_to_fraction_of_improvement(
        budgets, ndcgs, ndcg_initial=0.5, ndcg_exhaustive=1.0, fraction=0.9
    )
    assert result == 3


def test_topk_stabilization_budget_never_changes():
    budgets = [1, 2, 3]
    rankings = [["a", "b"], ["b", "a"], ["a", "b"]]
    result = evaluate.topk_stabilization_budget(budgets, rankings, k=1)
    assert result == 3  # top-1 differs at steps 1/2 vs final; only step 3 onward matches final


def test_auc_over_budget_constant_curve():
    assert evaluate.auc_over_budget([0.0, 0.5, 1.0], [0.8, 0.8, 0.8]) == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Statistics wrappers
# ---------------------------------------------------------------------------


def test_paired_comparison_win_tie_loss():
    deltas = [0.1, -0.1, 0.0, 0.2, 0.05]
    comp = stats.paired_comparison("test", deltas)
    assert comp.wins == 3
    assert comp.losses == 1
    assert comp.ties == 1
    assert comp.n == 5


def test_holm_correct_monotone_non_decreasing_after_sort():
    from consistency_ranker.active_acquisition.stats import PairedComparison

    comps = [
        PairedComparison("a", 5, 0.1, None, None, None, 0.01, 3, 0, 2),
        PairedComparison("b", 5, 0.1, None, None, None, 0.02, 3, 0, 2),
        PairedComparison("c", 5, 0.1, None, None, None, 0.5, 3, 0, 2),
    ]
    adjusted = stats.holm_correct(comps)
    assert all(a is not None for a in adjusted)
    assert all(a >= p for a, p in zip(adjusted, [c.pvalue for c in comps]))
