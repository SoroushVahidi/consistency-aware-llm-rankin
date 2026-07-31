from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK3_SCRIPTS = (
    REPO_ROOT / "reports" / "final_revision_task3_ranker_dependence_20260715" / "scripts"
)
FULL_CAL_SCRIPTS = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT, FULL_CAL_SCRIPTS, TASK3_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    import full_calibration_utils as fcu  # noqa: E402
    import run_coverage_and_dependence as cad  # noqa: E402
    import run_leave_one_out as loo  # noqa: E402
    import run_pre_post_normalization as ppn  # noqa: E402
    import task3_common as t3  # noqa: E402
except ImportError:
    pytest.skip(
        f"local-only Task 3 reproduction scripts not present at {TASK3_SCRIPTS} "
        "(gitignored scratch dir, not part of the tracked repository -- this "
        "module only runs on a machine that has locally generated them)",
        allow_module_level=True,
    )


def _synthetic_dataset_inputs(*, candidate_pool, raw_scores_by_ranker, qrels_for_query=None):
    item = {
        "query_id": "q1",
        "candidate_pool": candidate_pool,
        "raw_scores_by_ranker": raw_scores_by_ranker,
        "qrels_for_query": qrels_for_query or [],
    }
    return {
        "dataset": "synthetic",
        "per_query_inputs": [item],
        "analysis_query_ids": ["q1"],
    }


# ---------------------------------------------------------------------------
# Coverage accounting, missing-score abstention, tie abstention
# ---------------------------------------------------------------------------


def test_coverage_accounting_missing_and_tie_abstention(monkeypatch):
    # 4-doc pool -> 6 unordered pairs.
    pool = ["a", "b", "c", "d"]
    raw_scores = {
        # bm25 scores everything, one genuine tie (a vs b)
        "bm25": {"a": 1.0, "b": 1.0, "c": 2.0, "d": 3.0},
        # tfidf misses doc "d" entirely (missing-score abstention)
        "tfidf": {"a": 0.1, "b": 0.2, "c": 0.3},
        # minilm misses two docs
        "minilm": {"a": 0.5, "b": 0.6},
    }
    dataset_inputs = _synthetic_dataset_inputs(candidate_pool=pool, raw_scores_by_ranker=raw_scores)
    monkeypatch.setattr(t3, "dataset_inputs_for_pool", lambda dataset, pool_size: dataset_inputs)

    result = cad.coverage_and_pair_funnel_for_dataset("synthetic", "canonical", 4)
    by_ranker = {r["ranker"]: r for r in result["coverage_rows"]}

    assert by_ranker["bm25"]["n_scored"] == 4
    assert by_ranker["bm25"]["eligible_pairs"] == 6
    assert by_ranker["bm25"]["native_ties"] == 1  # a==b
    assert by_ranker["bm25"]["missing_abstention_fraction"] == 0.0

    assert by_ranker["tfidf"]["n_scored"] == 3
    assert by_ranker["tfidf"]["eligible_pairs"] == 3  # only pairs among {a,b,c}
    assert by_ranker["tfidf"]["missing_abstention_fraction"] == pytest.approx((6 - 3) / 6)

    assert by_ranker["minilm"]["n_scored"] == 2
    assert by_ranker["minilm"]["eligible_pairs"] == 1  # only pair (a,b)
    assert by_ranker["minilm"]["native_ties"] == 0


# ---------------------------------------------------------------------------
# Pairwise ranker agreement (directional agreement + margin correlation)
# ---------------------------------------------------------------------------


def test_directional_agreement_perfect_and_conflicting(monkeypatch):
    pool = ["a", "b", "c"]
    # bm25 and tfidf agree on every ordering; minilm reverses everything.
    raw_scores = {
        "bm25": {"a": 1.0, "b": 2.0, "c": 3.0},
        "tfidf": {"a": 0.1, "b": 0.2, "c": 0.3},
        "minilm": {"a": 0.9, "b": 0.5, "c": 0.1},
    }
    dataset_inputs = _synthetic_dataset_inputs(candidate_pool=pool, raw_scores_by_ranker=raw_scores)
    monkeypatch.setattr(t3, "dataset_inputs_for_pool", lambda dataset, pool_size: dataset_inputs)

    rows = cad.directional_agreement_and_margin_correlation("synthetic", "canonical", 3)
    by_pair = {(r["ranker_a"], r["ranker_b"]): r for r in rows}
    assert by_pair[("bm25", "tfidf")]["directional_agreement_rate_given_nontied"] == 1.0
    assert by_pair[("bm25", "minilm")]["directional_agreement_rate_given_nontied"] == 0.0


# ---------------------------------------------------------------------------
# Mutual-pair vote attribution
# ---------------------------------------------------------------------------


def test_mutual_pair_attribution_classification(monkeypatch):
    pool = ["a", "b"]
    # bm25 says a>b, tfidf says a>b (agree), minilm says b>a (opposes both):
    # ms1 keeps both directions -> mutual pair, configuration = lexical_pair_vs_minilm.
    raw_scores = {
        "bm25": {"a": 1.0, "b": 0.0},
        "tfidf": {"a": 1.0, "b": 0.0},
        "minilm": {"a": 0.0, "b": 1.0},
    }
    dataset_inputs = _synthetic_dataset_inputs(candidate_pool=pool, raw_scores_by_ranker=raw_scores)
    monkeypatch.setattr(t3, "dataset_inputs_for_pool", lambda dataset, pool_size: dataset_inputs)
    monkeypatch.setattr(
        t3,
        "canonical_threshold_config",
        lambda dataset_inputs, regime: fcu.ThresholdConfig(
            vote_thresholds={"bm25": 0.0, "tfidf": 0.0, "minilm": 0.0},
            aggregate_threshold=0.0,
            min_support=1,
            postprocess_drop_mutual=False,
            target_vote_rates=None,
            target_edge_count=None,
            notes="test",
        ),
    )

    rows = cad.mutual_pair_attribution_for_dataset("synthetic", "canonical", 2)
    assert len(rows) == 1
    assert rows[0]["configuration"] == "lexical_pair_vs_minilm"
    assert {rows[0]["direction_1_rankers"], rows[0]["direction_2_rankers"]} == {
        "bm25+tfidf",
        "minilm",
    }


def test_mutual_pair_single_vs_single_classification(monkeypatch):
    pool = ["a", "b"]
    # bm25 says a>b, minilm says b>a, tfidf abstains (missing) -> single vs single.
    raw_scores = {
        "bm25": {"a": 1.0, "b": 0.0},
        "tfidf": {},
        "minilm": {"a": 0.0, "b": 1.0},
    }
    dataset_inputs = _synthetic_dataset_inputs(candidate_pool=pool, raw_scores_by_ranker=raw_scores)
    monkeypatch.setattr(t3, "dataset_inputs_for_pool", lambda dataset, pool_size: dataset_inputs)
    monkeypatch.setattr(
        t3,
        "canonical_threshold_config",
        lambda dataset_inputs, regime: fcu.ThresholdConfig(
            vote_thresholds={"bm25": 0.0, "tfidf": 0.0, "minilm": 0.0},
            aggregate_threshold=0.0,
            min_support=1,
            postprocess_drop_mutual=False,
            target_vote_rates=None,
            target_edge_count=None,
            notes="test",
        ),
    )
    rows = cad.mutual_pair_attribution_for_dataset("synthetic", "canonical", 2)
    assert len(rows) == 1
    assert rows[0]["configuration"] == "single_voter_vs_single_voter"


# ---------------------------------------------------------------------------
# ms2 density accounting: mutual pairs are combinatorially impossible
# ---------------------------------------------------------------------------


def test_ms2_mutual_pairs_structurally_impossible(monkeypatch):
    pool = ["a", "b"]
    raw_scores = {
        "bm25": {"a": 1.0, "b": 0.0},
        "tfidf": {"a": 1.0, "b": 0.0},
        "minilm": {"a": 0.0, "b": 1.0},
    }
    dataset_inputs = _synthetic_dataset_inputs(candidate_pool=pool, raw_scores_by_ranker=raw_scores)
    monkeypatch.setattr(t3, "dataset_inputs_for_pool", lambda dataset, pool_size: dataset_inputs)
    monkeypatch.setattr(
        t3,
        "canonical_threshold_config",
        lambda dataset_inputs, regime: fcu.ThresholdConfig(
            vote_thresholds={"bm25": 0.0, "tfidf": 0.0, "minilm": 0.0},
            aggregate_threshold=0.0,
            min_support=2,
            postprocess_drop_mutual=False,
            target_vote_rates=None,
            target_edge_count=None,
            notes="test",
        ),
    )
    result = cad.ms2_sparsity_for_dataset("synthetic", "canonical", 2)
    assert result["summary"]["total_edges_all3_agree"] == 0
    # bm25+tfidf both support a>b (support=2) -> exactly one edge, no mutual pair possible.
    per_query = result["per_query"][0]
    assert per_query["n_edges"] == 1
    assert per_query["is_cyclic"] is False


# ---------------------------------------------------------------------------
# Leave-one-ranker-out graph construction
# ---------------------------------------------------------------------------


def test_leave_one_out_two_ranker_vote_construction():
    pool = ["a", "b", "c"]
    raw_scores = {
        "bm25": {"a": 3.0, "b": 2.0, "c": 1.0},
        "tfidf": {"a": 0.3, "b": 0.2, "c": 0.1},
        "minilm": {"a": 0.1, "b": 0.9, "c": 0.5},
    }
    # pair_any (min_support=1): both bm25 and tfidf vote a>b>c, minilm irrelevant since excluded.
    rows = loo.build_vote_rows_subset(
        query_id="q1",
        raw_scores_by_ranker=raw_scores,
        candidate_pool=pool,
        rankers_subset=("bm25", "tfidf"),
        min_support=1,
        aggregate_threshold=0.0,
        drop_mutual=False,
    )
    edges = {(r["winner_doc_id"], r["loser_doc_id"]) for r in rows}
    assert ("a", "b") in edges and ("b", "c") in edges and ("a", "c") in edges
    # minilm must not appear as a voter since it's excluded from this subset.
    assert all(r["voter"] in ("bm25", "tfidf") for r in rows)


def test_leave_one_out_pair_unanimous_requires_both_voters():
    pool = ["a", "b"]
    raw_scores = {
        "bm25": {"a": 1.0, "b": 0.0},
        "tfidf": {"a": 0.0, "b": 1.0},  # disagrees with bm25
        "minilm": {"a": 1.0, "b": 0.0},
    }
    rows = loo.build_vote_rows_subset(
        query_id="q1",
        raw_scores_by_ranker=raw_scores,
        candidate_pool=pool,
        rankers_subset=("bm25", "tfidf"),
        min_support=2,  # pair_unanimous: both voters must agree
        aggregate_threshold=0.1,
        drop_mutual=False,
    )
    assert rows == []  # bm25 and tfidf disagree -> no direction reaches support=2


# ---------------------------------------------------------------------------
# Pre-pool vs post-pool normalization
# ---------------------------------------------------------------------------


def test_pre_pool_normalization_invariant_to_downstream_truncation():
    full_list = [("a", 1.0), ("b", 5.0), ("c", 10.0), ("d", 20.0)]
    full_score_lists_by_ranker = {
        "bm25": {"q1": full_list},
        "tfidf": {"q1": []},
        "minilm": {"q1": []},
    }
    raw_scores_by_ranker = {"bm25": dict(full_list), "tfidf": {}, "minilm": {}}

    calibrated_full_pool = ppn._calibrated_scores_for_construction(
        construction="pre_pool_minmax",
        raw_scores_by_ranker=raw_scores_by_ranker,
        full_score_lists_by_ranker=full_score_lists_by_ranker,
        query_id="q1",
        candidate_pool=["a", "b", "c", "d"],
    )
    calibrated_truncated_pool = ppn._calibrated_scores_for_construction(
        construction="pre_pool_minmax",
        raw_scores_by_ranker=raw_scores_by_ranker,
        full_score_lists_by_ranker=full_score_lists_by_ranker,
        query_id="q1",
        candidate_pool=["a", "b"],  # downstream pool truncation excludes the extrema doc "d"
    )
    # normalization domain is the FULL stored list in both cases, so shared docs
    # get identical normalized values regardless of downstream pool truncation.
    assert calibrated_full_pool["bm25"]["a"] == pytest.approx(
        calibrated_truncated_pool["bm25"]["a"]
    )
    assert calibrated_full_pool["bm25"]["b"] == pytest.approx(
        calibrated_truncated_pool["bm25"]["b"]
    )


def test_post_pool_normalization_changes_when_extrema_removed():
    raw_scores_by_ranker = {
        "bm25": {"a": 1.0, "b": 5.0, "c": 10.0, "d": 20.0},
        "tfidf": {},
        "minilm": {},
    }
    full_score_lists_by_ranker = {"bm25": {"q1": []}, "tfidf": {"q1": []}, "minilm": {"q1": []}}

    calibrated_full_pool = ppn._calibrated_scores_for_construction(
        construction="post_pool_minmax",
        raw_scores_by_ranker=raw_scores_by_ranker,
        full_score_lists_by_ranker=full_score_lists_by_ranker,
        query_id="q1",
        candidate_pool=["a", "b", "c", "d"],
    )
    calibrated_truncated_pool = ppn._calibrated_scores_for_construction(
        construction="post_pool_minmax",
        raw_scores_by_ranker=raw_scores_by_ranker,
        full_score_lists_by_ranker=full_score_lists_by_ranker,
        query_id="q1",
        candidate_pool=["a", "b"],  # removes the max-score doc "d" (and "c")
    )
    # post_pool_minmax recomputes min/max over whatever pool is given, so the
    # SAME raw score for "b" normalizes differently once the extrema ("c","d")
    # are removed from the pool: "b" goes from an interior value to the new max.
    assert calibrated_full_pool["bm25"]["b"] != pytest.approx(
        calibrated_truncated_pool["bm25"]["b"]
    )
    assert calibrated_full_pool["bm25"]["a"] == pytest.approx(0.0)  # min of {1,5,10,20}
    assert calibrated_truncated_pool["bm25"]["a"] == pytest.approx(
        0.0
    )  # still min of {1,5}, coincidentally same
    assert calibrated_full_pool["bm25"]["b"] == pytest.approx(4.0 / 19.0)
    assert calibrated_truncated_pool["bm25"]["b"] == pytest.approx(
        1.0
    )  # now the max of the truncated pool


# ---------------------------------------------------------------------------
# Deterministic correlation summaries
# ---------------------------------------------------------------------------


def test_rank_correlation_is_deterministic(monkeypatch):
    score_lists = {
        "bm25": {"q1": [("a", 3.0), ("b", 2.0), ("c", 1.0)]},
        "tfidf": {"q1": [("a", 0.9), ("b", 0.5), ("c", 0.1)]},
        "minilm": {"q1": [("a", 0.1), ("b", 0.2), ("c", 0.9)]},
    }
    monkeypatch.setattr(cad, "_load_raw_score_lists", lambda dataset: score_lists)
    # use a real dataset name so cad.LARGE_DEPTH[...] resolves; the score
    # lists themselves are monkeypatched regardless of the name passed in.
    result_1 = cad.ranker_dependence_for_dataset_full_lists("hotpotqa")
    result_2 = cad.ranker_dependence_for_dataset_full_lists("hotpotqa")
    assert result_1["correlation_rows"] == result_2["correlation_rows"]
    by_pair = {(r["ranker_a"], r["ranker_b"]): r for r in result_1["correlation_rows"]}
    assert by_pair[("bm25", "tfidf")]["kendall_tau_b"] == pytest.approx(1.0)
    assert by_pair[("bm25", "minilm")]["kendall_tau_b"] == pytest.approx(-1.0)


def test_rbo_identical_lists_is_one():
    assert cad._rbo(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(1.0)


def test_rbo_disjoint_lists_is_zero():
    assert cad._rbo(["a", "b"], ["c", "d"]) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TF-IDF reference-validation utilities
# ---------------------------------------------------------------------------


def test_tfidf_custom_matches_sklearn_reference_on_toy_corpus():
    import importlib

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    gsf = importlib.import_module("generate_score_file")
    from sklearn.feature_extraction.text import TfidfVectorizer

    from consistency_ranker.data.schema import Document

    documents = [
        Document(doc_id="d1", text="the cat sat on the mat", title=""),
        Document(doc_id="d2", text="dogs are loyal animals", title=""),
        Document(doc_id="d3", text="the cat chased the mouse", title=""),
    ]
    custom_ranker = gsf.TfidfRanker(documents)
    custom_top = custom_ranker.top_docs("cat mouse", 3)

    vectorizer = TfidfVectorizer(
        token_pattern=r"[A-Za-z0-9]+",
        lowercase=True,
        sublinear_tf=True,
        smooth_idf=True,
        norm="l2",
        use_idf=True,
    )
    doc_matrix = vectorizer.fit_transform([d.text for d in documents])
    q_vec = vectorizer.transform(["cat mouse"])
    import numpy as np

    scores = np.asarray((doc_matrix @ q_vec.T).todense()).ravel()
    sklearn_ranked = sorted(zip([d.doc_id for d in documents], scores), key=lambda x: -x[1])

    assert [d for d, _s in custom_top] == [d for d, _s in sklearn_ranked]
    for (cd, cs), (sd, ss) in zip(custom_top, sklearn_ranked):
        assert cd == sd
        assert cs == pytest.approx(float(ss), abs=1e-9)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
