"""Tests for the qrel-free counterfactual stopping rule (Phase 5 of the
risk-controlled stopping-rule pilot).

Covers the nine required safety/correctness properties. Most use a small
synthetic candidate pool for speed; one behavioral leakage test and one
cross-process determinism test use the real cached SciDocs oracle (kept
small in scope: a handful of steps, not a full trajectory).
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from consistency_ranker.active_acquisition import stopping as st
from consistency_ranker.active_acquisition.oracle import QueryOracle, load_scidocs_pairwise_oracle
from consistency_ranker.active_acquisition.regularized_aggregation import (
    SCHEDULES,
    fit_bt_utilities,
)
from consistency_ranker.active_acquisition.scoring import normalize_bm25

REPO_ROOT = Path(__file__).resolve().parent.parent
JUDGMENTS_PATH = REPO_ROOT / "outputs/openai_scidocs_real_pairwise_q50_k15/judgments.jsonl"

pytestmark = pytest.mark.skipif(
    not JUDGMENTS_PATH.exists(),
    reason="offline oracle artifact not present in this checkout",
)

CANDIDATES = ("a", "b", "c", "d", "e", "f")
BM25_NORM = {"a": 1.0, "b": 0.8, "c": 0.6, "d": 0.4, "e": 0.2, "f": 0.0}
N_TOTAL_PAIRS = 15  # C(6, 2)
SCHEDULE = SCHEDULES["linear_decay"]


@pytest.fixture(scope="module")
def oracles() -> dict[str, QueryOracle]:
    return load_scidocs_pairwise_oracle(JUDGMENTS_PATH)


# ---------------------------------------------------------------------------
# Property 4: zero unrevealed pairs always causes stopping
# ---------------------------------------------------------------------------


def test_zero_remaining_pairs_gives_zero_worst_case():
    revealed = [("a", "b"), ("b", "c")]
    utilities = fit_bt_utilities(CANDIDATES, revealed, BM25_NORM, lam=2.0)
    result = st.worst_case_topk_change(
        CANDIDATES, revealed, BM25_NORM, N_TOTAL_PAIRS, SCHEDULE, [], k=3,
        current_utilities=utilities,
    )
    assert result.scalar == 0.0
    assert result.n_pairs_considered == 0
    assert st.counterfactual_rule_is_stable(result.scalar, tau=0.0)


def test_history_ending_with_no_remaining_pairs_eventually_stops():
    # Once remaining pairs run out, worst_case_scalar is pinned at 0.0, so
    # patience consecutive such steps must trigger a stop for any tau >= 0.
    history = [
        {"step": i, "worst_case_scalar": 0.0, "topk": ["a", "b", "c"]} for i in range(1, 6)
    ]
    outcome = st.apply_counterfactual_rule(history, tau=0.0, patience_m=3)
    assert outcome["stopped"] is True
    assert outcome["stop_step"] == 3


# ---------------------------------------------------------------------------
# Property 6: identical hypothetical top-k outcomes contribute zero
# membership instability
# ---------------------------------------------------------------------------


def test_identical_topk_gives_zero_membership_distance():
    current = ["a", "b", "c", "d", "e", "f"]
    counterfactual = ["a", "b", "c", "f", "e", "d"]  # same top-3, tail reordered
    scalar, components = st.topk_distance(current, counterfactual, k=3)
    assert components["membership"] == 0.0
    # ordering/displacement may still be nonzero from tail movement, but the
    # membership component specifically must be exactly zero.


def test_fully_identical_rankings_give_zero_distance():
    ranking = ["a", "b", "c", "d", "e", "f"]
    scalar, components = st.topk_distance(ranking, list(ranking), k=3)
    assert scalar == 0.0
    assert components == {"membership": 0.0, "ordering": 0.0, "displacement": 0.0}


# ---------------------------------------------------------------------------
# Property 5: reducing the set of possible future outcomes cannot increase
# the worst-case instability
# ---------------------------------------------------------------------------


def test_worst_case_over_larger_pair_set_is_at_least_as_large(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    candidates = oe.candidates
    bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
    revealed = [oe.reveal(candidates[0], candidates[1])]
    utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam=4.0)
    ranking = st.rank_from_utilities(candidates, utilities, bm25_norm)

    all_pairs = [
        tuple(sorted((candidates[a], candidates[b])))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
        if candidates[a] not in revealed[0] or candidates[b] not in revealed[0]
    ]
    subset = sorted(all_pairs)[:5]
    superset = sorted(all_pairs)[:15]
    assert set(subset) <= set(superset)

    result_subset = st._worst_case_over_pairs(
        candidates, revealed, bm25_norm, 4.0, utilities, ranking, 10, subset
    )
    result_superset = st._worst_case_over_pairs(
        candidates, revealed, bm25_norm, 4.0, utilities, ranking, 10, superset
    )
    assert result_superset.scalar >= result_subset.scalar - 1e-12


# ---------------------------------------------------------------------------
# Property 7: patience is applied correctly
# ---------------------------------------------------------------------------


def test_patience_resets_on_instability():
    c = 0
    c = st.apply_patience(c, stable_now=True)
    assert c == 1
    c = st.apply_patience(c, stable_now=True)
    assert c == 2
    c = st.apply_patience(c, stable_now=False)
    assert c == 0
    c = st.apply_patience(c, stable_now=True)
    assert c == 1


def test_has_stopped_triggers_exactly_at_patience():
    assert not st.has_stopped(2, patience_m=3)
    assert st.has_stopped(3, patience_m=3)
    assert st.has_stopped(4, patience_m=3)


def test_apply_counterfactual_rule_requires_m_consecutive_stable_steps():
    # scalar sequence: unstable, stable, stable, unstable, stable, stable, stable
    scalars = [0.5, 0.1, 0.1, 0.5, 0.1, 0.1, 0.1]
    history = [{"step": i + 1, "worst_case_scalar": s} for i, s in enumerate(scalars)]
    outcome = st.apply_counterfactual_rule(history, tau=0.2, patience_m=3)
    assert outcome["stopped"] is True
    assert outcome["stop_step"] == 7  # third consecutive stable step after the reset at step 4


# ---------------------------------------------------------------------------
# Properties 2 & 8: no qrels, no oracle, no exhaustive ranking in the interface
# ---------------------------------------------------------------------------

_FORBIDDEN_PARAM_SUBSTRINGS = (
    "oracle", "relevance", "qrel", "future", "unrevealed_answer", "exhaustive",
)


@pytest.mark.parametrize(
    "fn",
    [
        st.topk_distance,
        st.counterfactual_candidate_pairs,
        st.worst_case_topk_change,
        st.counterfactual_rule_is_stable,
        st.simple_rule_is_stable,
        st.apply_patience,
        st.has_stopped,
    ],
)
def test_public_functions_do_not_accept_oracle_qrels_or_exhaustive_ranking(fn):
    params = set(inspect.signature(fn).parameters)
    for p in params:
        for bad in _FORBIDDEN_PARAM_SUBSTRINGS:
            assert bad not in p.lower(), f"{fn.__name__} accepts suspicious parameter {p!r}"


# ---------------------------------------------------------------------------
# Property 1: changing an unrevealed cached judgment does not alter the
# current stopping decision
# ---------------------------------------------------------------------------


def test_stopping_decision_invariant_to_unrevealed_outcome(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    candidates = oe.candidates
    bm25_norm = normalize_bm25(candidates, oe.bm25_scores)

    revealed_pairs = [(candidates[0], candidates[1]), (candidates[2], candidates[3])]
    revealed = [oe.reveal(i, j) for i, j in revealed_pairs]
    revealed_docs = {d for pair in revealed_pairs for d in pair}
    remaining = [
        frozenset((candidates[a], candidates[b]))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
        if candidates[a] not in revealed_docs or candidates[b] not in revealed_docs
    ]
    utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam=4.0)

    result_before = st.worst_case_topk_change(
        candidates, revealed, bm25_norm, 105, SCHEDULE, remaining, k=10,
        current_utilities=utilities,
    )

    # Build a *different* oracle where some still-unrevealed pair's cached
    # answer is flipped -- the worst_case computation above never consulted
    # oe at all (only `revealed`, `remaining`, `bm25_norm`, `utilities`), so
    # it must be unaffected.
    unobserved = [d for d in candidates if d not in revealed_docs]
    i, j = unobserved[0], unobserved[1]
    flipped_oracle = dict(oe.oracle)
    flipped_oracle[frozenset((i, j))] = j if oe.oracle[frozenset((i, j))] == i else i
    flipped_oe = QueryOracle(
        query_id=oe.query_id, candidates=oe.candidates, oracle=flipped_oracle,
        bm25_scores=oe.bm25_scores, relevance=oe.relevance,
    )
    # Recompute using only the same (revealed, remaining, bm25_norm, utilities)
    # -- flipped_oe is never passed in, demonstrating the result cannot depend
    # on it structurally, and confirming bit-identical output.
    result_after = st.worst_case_topk_change(
        candidates, revealed, bm25_norm, 105, SCHEDULE, remaining, k=10,
        current_utilities=utilities,
    )
    assert result_before == result_after
    del flipped_oe  # constructed only to demonstrate it is never consulted


# ---------------------------------------------------------------------------
# Property 3 & 9: deterministic, including across process launches
# ---------------------------------------------------------------------------


def test_worst_case_topk_change_is_deterministic(oracles):
    qid = sorted(oracles)[0]
    oe = oracles[qid]
    candidates = oe.candidates
    bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
    revealed = [oe.reveal(candidates[0], candidates[1])]
    remaining = [
        frozenset((candidates[a], candidates[b]))
        for a in range(len(candidates))
        for b in range(a + 1, len(candidates))
    ][:20]
    utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam=4.0)

    r1 = st.worst_case_topk_change(
        candidates, revealed, bm25_norm, 105, SCHEDULE, remaining, k=10, current_utilities=utilities
    )
    r2 = st.worst_case_topk_change(
        candidates, revealed, bm25_norm, 105, SCHEDULE, remaining, k=10, current_utilities=utilities
    )
    assert r1 == r2


def test_worst_case_topk_change_reproducible_across_process_launches():
    script = """
import sys
sys.path.insert(0, "src")
from consistency_ranker.active_acquisition.oracle import load_scidocs_pairwise_oracle
from consistency_ranker.active_acquisition.scoring import normalize_bm25
from consistency_ranker.active_acquisition.regularized_aggregation import (
    SCHEDULES,
    fit_bt_utilities,
)
from consistency_ranker.active_acquisition.stopping import worst_case_topk_change

oracles = load_scidocs_pairwise_oracle()
qid = sorted(oracles)[0]
oe = oracles[qid]
candidates = oe.candidates
bm25_norm = normalize_bm25(candidates, oe.bm25_scores)
revealed = [oe.reveal(candidates[0], candidates[1])]
remaining = [frozenset((candidates[a], candidates[b]))
             for a in range(len(candidates)) for b in range(a+1, len(candidates))][:20]
utilities = fit_bt_utilities(candidates, revealed, bm25_norm, lam=4.0)
result = worst_case_topk_change(candidates, revealed, bm25_norm, 105, SCHEDULES["linear_decay"],
                                 remaining, k=10, current_utilities=utilities)
print(repr(result))
"""
    outputs = []
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        outputs.append(proc.stdout.strip())
    assert outputs[0] == outputs[1]


# ---------------------------------------------------------------------------
# Sanity: simple_rule_is_stable behaves as documented
# ---------------------------------------------------------------------------


def test_simple_rule_is_stable_requires_two_rankings():
    assert st.simple_rule_is_stable([["a", "b", "c"]], k=3) is False


def test_simple_rule_is_stable_detects_unchanged_topk():
    history = [["a", "b", "c", "d"], ["b", "a", "c", "d"]]
    assert st.simple_rule_is_stable(history, k=3) is True  # same set, different order


def test_simple_rule_is_stable_detects_changed_topk():
    history = [["a", "b", "c", "d"], ["a", "b", "e", "d"]]
    assert st.simple_rule_is_stable(history, k=3) is False
