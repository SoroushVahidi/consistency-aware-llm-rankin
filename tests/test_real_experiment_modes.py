"""
Tests for alternative preference-source modes in run_real_experiment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.baseline_ranking import fas_balance_score_prior_alpha_beta_ranking
from consistency_ranker.data.schema import QrelEntry
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference
from scripts.run_real_experiment import (
    NON_HYBRID_METHODS,
    _average_precision_at_k,
    _build_hybrid_specs,
    _build_query_preferences,
    _copeland_ranking,
    _filter_methods,
    _flip_preference_directions,
    _has_usable_eval_labels,
    _hybrid_rrf_component_ranking,
    _hybrid_rrf_fas_regularized_ranking,
    _hybrid_rrf_priority_topological_ranking,
    _load_pairwise_preference_file,
    _load_score_file,
    _method_plan,
    _ndcg_at_k,
    _pairwise_accuracy_from_relevance,
    _parse_alpha_values,
    _precision_recall_at_k,
    _prior_only_ranking,
    _priority_topological_ranking,
    _reference_ranking_for_candidates,
    _resolve_output_dir,
    _rrf_prior_scores_for_query,
    _score_entries_to_preferences,
    _score_sum_prior_scores,
    _validate_run_configuration,
    _weighted_out_minus_in_ranking,
)


def _qrels(*rows) -> list[QrelEntry]:
    return [QrelEntry(query_id=str(q), doc_id=str(d), relevance=int(r)) for q, d, r in rows]


def test_has_usable_eval_labels_true():
    assert _has_usable_eval_labels(_qrels(("q1", "d1", 1), ("q1", "d2", 0)))


def test_has_usable_eval_labels_positive_only_implicit_negatives():
    """Two positives, no explicit negatives: still eligible (zeros at eval time)."""
    assert _has_usable_eval_labels(_qrels(("q1", "d1", 1), ("q1", "d2", 1)))


def test_has_usable_eval_labels_single_positive_doc():
    """BEIR-style single judged positive per query."""
    assert _has_usable_eval_labels(_qrels(("q1", "d1", 1)))


def test_has_usable_eval_labels_false_no_positive():
    assert not _has_usable_eval_labels(_qrels(("q1", "d1", 0), ("q1", "d2", 0)))
    assert not _has_usable_eval_labels([])


def test_score_entries_to_preferences_builds_pairs():
    prefs = _score_entries_to_preferences(
        [("d1", 0.9), ("d2", 0.7), ("d3", 0.3)],
        top_k=3,
        seed=42,
    )
    assert len(prefs) == 3
    pairs = {(p.winner, p.loser) for p in prefs}
    assert ("d1", "d2") in pairs
    assert ("d1", "d3") in pairs
    assert ("d2", "d3") in pairs


def test_flip_preference_directions_deterministic():
    from consistency_ranker.pairwise_prefs import Preference

    base = [
        Preference("a", "b", 1.0),
        Preference("a", "c", 1.0),
        Preference("b", "c", 1.0),
    ]
    flipped_1 = _flip_preference_directions(base, flip_prob=1.0, seed=7, query_id="q1")
    flipped_2 = _flip_preference_directions(base, flip_prob=1.0, seed=7, query_id="q1")
    assert flipped_1 == flipped_2
    assert {(p.winner, p.loser) for p in flipped_1} == {("b", "a"), ("c", "a"), ("c", "b")}


def test_load_pairwise_preference_file(tmp_path: Path):
    f = tmp_path / "pairs.jsonl"
    f.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "winner_doc_id": "d1", "loser_doc_id": "d2", "weight": 2}),
                json.dumps({"query_id": "q1", "winner": "d2", "loser": "d3"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    idx = _load_pairwise_preference_file(f)
    assert "q1" in idx
    assert len(idx["q1"]) == 2
    assert idx["q1"][0].weight == pytest.approx(2.0)


def test_load_score_file(tmp_path: Path):
    f = tmp_path / "scores.jsonl"
    f.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "d1", "score": 1.2}),
                json.dumps({"query_id": "q1", "doc_id": "d2", "score": 0.8}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    idx = _load_score_file(f)
    assert idx["q1"] == [("d1", 1.2), ("d2", 0.8)]


def test_build_query_preferences_qrels_flip():
    prefs, note = _build_query_preferences(
        query_id="q1",
        qrels_for_query=_qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0)),
        top_k=3,
        weight_scheme="grade_diff",
        seed=1,
        preference_source="qrels_flip",
        flip_prob=0.5,
        pairwise_index=None,
        score_index=None,
    )
    assert prefs
    assert "synthetic corruption" in note


def test_build_query_preferences_score_file():
    prefs, note = _build_query_preferences(
        query_id="q1",
        qrels_for_query=_qrels(("q1", "d1", 2), ("q1", "d2", 1)),
        top_k=2,
        weight_scheme="grade_diff",
        seed=1,
        preference_source="score_file",
        flip_prob=0.0,
        pairwise_index=None,
        score_index={"q1": [("d1", 0.9), ("d2", 0.2)]},
    )
    assert len(prefs) == 1
    assert prefs[0].winner == "d1"
    assert "score file" in note


def test_candidate_aligned_reference_and_quality_metrics():
    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    ref, rel_map = _reference_ranking_for_candidates(qrels, {"d1", "d2", "dX"})
    assert ref == ["d1", "d2", "dX"]
    assert rel_map["d1"] == 2
    assert rel_map["dX"] == 0

    ranking = ["d2", "dX", "d1"]
    ndcg = _ndcg_at_k(ranking, rel_map, k=2)
    ap = _average_precision_at_k(ranking, rel_map, k=2)
    p_at_k, r_at_k = _precision_recall_at_k(ranking, rel_map, k=2)
    pair_acc = _pairwise_accuracy_from_relevance(ranking, rel_map)
    assert ndcg is not None and 0.0 <= ndcg <= 1.0
    assert ap is not None and 0.0 <= ap <= 1.0
    assert p_at_k is not None and 0.0 <= p_at_k <= 1.0
    assert r_at_k is not None and 0.0 <= r_at_k <= 1.0
    assert pair_acc is not None and 0.0 <= pair_acc <= 1.0


def test_weighted_out_minus_in_ranking_runs():
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    ranking = _weighted_out_minus_in_ranking(graph)
    assert ranking[0] == "a"


def test_copeland_and_priority_topological_rankings():
    graph = build_graph(
        [
            Preference("a", "b", 1.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    copeland = _copeland_ranking(graph)
    assert copeland[0] == "a"

    pri = {"a": 0.2, "b": 0.1, "c": 0.9}
    topo = _priority_topological_ranking(graph, pri)
    assert topo[0] == "a"
    assert topo.index("c") < topo.index("b")


def test_rrf_prior_and_hybrid_ranking():
    prior_sets = [
        {"q1": [("a", 3.0), ("b", 2.0), ("c", 1.0)]},
        {"q1": [("c", 3.0), ("a", 2.0), ("b", 1.0)]},
    ]
    pri = _rrf_prior_scores_for_query("q1", {"a", "b", "c"}, prior_sets)
    assert set(pri) == {"a", "b", "c"}
    graph = build_graph([Preference("a", "b", 1.0), Preference("c", "b", 1.0)])
    ranking = _hybrid_rrf_fas_regularized_ranking(graph, pri, fas_regularization=0.2)
    assert ranking[0] in {"a", "c"}


def test_rrf_prior_falls_back_to_score_sum_scores():
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    pri = _rrf_prior_scores_for_query(
        "q1",
        {"a", "b", "c"},
        score_prior_sets=[],
        fallback_scores=_score_sum_prior_scores(graph),
    )
    assert pri == {"a": 3.0, "b": 0.0, "c": 1.0}


def test_hybrid_component_variants():
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("c", "b", 1.0),
        ]
    )
    pri = {"a": 0.7, "b": 0.1, "c": 0.4}
    r_balance = _hybrid_rrf_component_ranking(
        graph, pri, component="balance", alpha=0.5
    )
    r_copeland = _hybrid_rrf_component_ranking(
        graph, pri, component="copeland", alpha=0.3
    )
    r_prio = _hybrid_rrf_priority_topological_ranking(
        graph, pri, component="balance", alpha=0.3
    )
    assert r_balance[0] in {"a", "c"}
    assert r_copeland[0] in {"a", "c"}
    assert r_prio.index("b") == len(r_prio) - 1


def test_hybrid_spec_builder_ablation_and_sweep():
    specs = _build_hybrid_specs(
        include_ablation=True,
        alpha_sweep_components=["balance"],
        alpha_values=[0.0, 0.3],
    )
    names = {s.name for s in specs}
    assert "hybrid_rrf_prior_only" in names
    assert "hybrid_rrf_unrepaired_balance_a03" in names
    assert "hybrid_rrf_repaired_balance_a0p0" in names
    assert "hybrid_rrf_repaired_balance_a0p3" in names


def test_parse_alpha_values_and_prior_only():
    assert _parse_alpha_values("0.0, 0.3,1.0") == [0.0, 0.3, 1.0]
    with pytest.raises(ValueError):
        _parse_alpha_values("")
    ranking = _prior_only_ranking(["b", "a", "c"], {"a": 0.2, "b": 0.9, "c": 0.9})
    assert ranking == ["b", "c", "a"]


def test_filter_methods_keeps_requested_shortlist():
    methods = [
        "score_sum",
        "borda",
        "greedy_fas_weighted_balance",
        "hybrid_rrf_fas_regularized",
    ]
    filtered_methods, filtered_specs = _filter_methods(
        methods,
        {
            "hybrid_rrf_fas_regularized": _build_hybrid_specs(
                include_ablation=False,
                alpha_sweep_components=None,
                alpha_values=[0.2],
            )[0]
        },
        selected_methods=["score_sum", "hybrid_rrf_fas_regularized"],
    )
    assert filtered_methods == ["score_sum", "hybrid_rrf_fas_regularized"]
    assert list(filtered_specs) == ["hybrid_rrf_fas_regularized"]


def test_resolve_output_dir_nests_dataset_and_source():
    root = Path("outputs/real_small_validation")
    assert _resolve_output_dir(root, "scidocs", "qrels") == root / "scidocs" / "qrels"
    assert _resolve_output_dir(root / "scidocs", "scidocs", "qrels_flip") == (
        root / "scidocs" / "qrels_flip"
    )
    assert _resolve_output_dir(root / "scidocs" / "qrels", "scidocs", "qrels") == (
        root / "scidocs" / "qrels"
    )


def test_method_plan_inserts_rrf_and_combsum_when_score_priors_available():
    methods, _ = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=True,
    )
    assert "markov_graph" in methods
    assert "markov_graph_repaired" in methods
    assert "rrf" in methods
    assert "combsum" in methods
    assert "borda_fuse" in methods
    assert methods.index("markov_graph") == methods.index("pagerank") + 1
    assert methods.index("markov_graph_repaired") == methods.index("markov_graph") + 1
    assert methods.index("rrf") == methods.index("markov_graph_repaired") + 1
    assert methods.index("combsum") == methods.index("rrf") + 1
    assert methods.index("borda_fuse") == methods.index("combsum") + 1


def test_method_plan_omits_fusion_baselines_without_flag():
    methods, _ = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=False,
    )
    assert "markov_graph" in methods
    assert "markov_graph_repaired" in methods
    assert "rrf" not in methods
    assert "combsum" not in methods
    assert "borda_fuse" not in methods


def test_validate_rrf_requires_score_prior_files(tmp_path: Path):
    with pytest.raises(ValueError, match="rrf"):
        _validate_run_configuration(
            max_queries=1,
            top_k=2,
            preference_source="qrels",
            flip_prob=0.0,
            pairwise_file=None,
            score_file=None,
            score_prior_files=None,
            query_id_file=None,
            output_dir=tmp_path,
            save_timings=False,
            overwrite_existing=False,
            dataset="scidocs",
            methods_filter=["rrf"],
        )


def test_validate_combsum_requires_score_prior_files(tmp_path: Path):
    with pytest.raises(ValueError, match="combsum"):
        _validate_run_configuration(
            max_queries=1,
            top_k=2,
            preference_source="qrels",
            flip_prob=0.0,
            pairwise_file=None,
            score_file=None,
            score_prior_files=None,
            query_id_file=None,
            output_dir=tmp_path,
            save_timings=False,
            overwrite_existing=False,
            dataset="scidocs",
            methods_filter=["combsum"],
        )


def test_validate_borda_fuse_requires_score_prior_files(tmp_path: Path):
    with pytest.raises(ValueError, match="borda_fuse"):
        _validate_run_configuration(
            max_queries=1,
            top_k=2,
            preference_source="qrels",
            flip_prob=0.0,
            pairwise_file=None,
            score_file=None,
            score_prior_files=None,
            query_id_file=None,
            output_dir=tmp_path,
            save_timings=False,
            overwrite_existing=False,
            dataset="scidocs",
            methods_filter=["borda_fuse"],
        )


def test_fas_balance_score_prior_alpha_beta_in_non_hybrid_methods():
    """fas_balance_score_prior_alpha_beta must be listed in NON_HYBRID_METHODS."""
    assert "fas_balance_score_prior_alpha_beta" in NON_HYBRID_METHODS


def test_markov_graph_methods_in_non_hybrid_plan():
    assert "markov_graph" in NON_HYBRID_METHODS
    assert "markov_graph_repaired" in NON_HYBRID_METHODS


def test_fas_balance_score_prior_alpha_beta_ranking_runs():
    """fas_balance_score_prior_alpha_beta_ranking produces a valid ordering."""
    graph = build_graph(
        [
            Preference("a", "b", 2.0),
            Preference("a", "c", 1.0),
            Preference("c", "b", 1.0),
        ]
    )
    score_sum_prior = {"a": 3.0, "b": 0.0, "c": 1.0}
    ranking = fas_balance_score_prior_alpha_beta_ranking(graph, score_sum_prior)
    assert set(ranking) == {"a", "b", "c"}
    assert ranking[0] == "a"


def test_fas_balance_score_prior_alpha_beta_in_pipeline(tmp_path: Path):
    """Run a mini pipeline and confirm fas_balance_score_prior_alpha_beta appears
    in the per-query output rows produced by run_query."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
    )
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=[],
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
    )

    assert skip is None
    method_names = {r["method"] for r in rows}
    assert "fas_balance_score_prior_alpha_beta" in method_names


def test_rrf_method_in_run_query_with_score_priors():
    """RRF baseline row appears when score prior maps are provided."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=True,
    )
    methods, hybrid_specs = _filter_methods(methods, hybrid_specs, ["rrf"])
    score_prior_sets = [
        {"q1": [("d1", 10.0), ("d2", 5.0), ("d3", 1.0)]},
        {"q1": [("d3", 9.0), ("d2", 8.0), ("d1", 0.0)]},
    ]
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=score_prior_sets,
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
        rrf_k=60.0,
    )
    assert skip is None
    assert len(rows) == 1
    assert rows[0]["method"] == "rrf"
    assert rows[0]["ndcg_at_k"] is not None


def test_combsum_method_in_run_query_with_score_priors():
    """CombSUM baseline row appears when score prior maps are provided."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=True,
    )
    methods, hybrid_specs = _filter_methods(methods, hybrid_specs, ["combsum"])
    score_prior_sets = [
        {"q1": [("d1", 10.0), ("d2", 5.0), ("d3", 1.0)]},
        {"q1": [("d3", 9.0), ("d2", 8.0), ("d1", 0.0)]},
    ]
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=score_prior_sets,
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
        rrf_k=60.0,
        combsum_normalization="minmax",
    )
    assert skip is None
    assert len(rows) == 1
    assert rows[0]["method"] == "combsum"
    assert rows[0]["ndcg_at_k"] is not None


def test_borda_fuse_method_in_run_query_with_score_priors():
    """Borda list-fusion baseline row appears when score prior maps are provided."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=True,
    )
    methods, hybrid_specs = _filter_methods(methods, hybrid_specs, ["borda_fuse"])
    score_prior_sets = [
        {"q1": [("d1", 10.0), ("d2", 5.0), ("d3", 1.0)]},
        {"q1": [("d3", 9.0), ("d2", 8.0), ("d1", 0.0)]},
    ]
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=score_prior_sets,
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
        rrf_k=60.0,
        combsum_normalization="minmax",
    )
    assert skip is None
    assert len(rows) == 1
    assert rows[0]["method"] == "borda_fuse"
    assert rows[0]["ndcg_at_k"] is not None


def test_markov_graph_method_in_run_query():
    """Rank Centrality–style graph baseline (unrepaired graph)."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=False,
    )
    methods, hybrid_specs = _filter_methods(methods, hybrid_specs, ["markov_graph"])
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=[],
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
    )
    assert skip is None
    assert len(rows) == 1
    assert rows[0]["method"] == "markov_graph"
    assert rows[0]["ndcg_at_k"] is not None


def test_markov_graph_repaired_method_in_run_query():
    """Same Markov chain on greedy-FAS–repaired DAG."""
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        include_score_fusion_baselines=False,
    )
    methods, hybrid_specs = _filter_methods(
        methods, hybrid_specs, ["markov_graph_repaired"]
    )
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=[],
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
    )
    assert skip is None
    assert len(rows) == 1
    assert rows[0]["method"] == "markov_graph_repaired"
    assert rows[0]["ndcg_at_k"] is not None


def test_method_plan_both_adds_ma_method_suffixes():
    methods, _ = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        repair_weighting="both",
    )
    assert "greedy_fas_copeland_ma" in methods
    assert "hybrid_rrf_copeland_a03_ma" in methods


def test_run_query_plain_default_has_repair_metadata():
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
    )
    methods, hybrid_specs = _filter_methods(methods, hybrid_specs, ["score_sum"])
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=[],
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
    )
    assert skip is None
    assert rows[0]["repair_weighting"] == "plain"
    assert rows[0]["fas_repair_variant"] == "none"
    assert rows[0]["runtime_fas_solver_ma_s"] == pytest.approx(0.0)


def test_run_query_metric_aware_enables_ma_variant_for_repaired_method():
    from consistency_ranker.utils.timing import TimingAccumulator
    from scripts.run_real_experiment import _filter_methods, _method_plan, run_query

    class _FakeQuery:
        query_id = "q1"

    qrels = _qrels(("q1", "d1", 2), ("q1", "d2", 1), ("q1", "d3", 0))
    methods, hybrid_specs = _method_plan(
        include_hybrid_ablation=False,
        alpha_sweep_components=None,
        alpha_values=[0.2],
        repair_weighting="metric_aware",
    )
    methods, hybrid_specs = _filter_methods(
        methods, hybrid_specs, ["greedy_fas_copeland"]
    )
    acc = TimingAccumulator()
    rows, skip = run_query(
        query=_FakeQuery(),
        qrels_for_query=qrels,
        dataset="scidocs",
        top_k=3,
        weight_scheme="grade_diff",
        seed=42,
        preference_source="qrels",
        flip_prob=0.0,
        pairwise_index=None,
        score_index=None,
        score_prior_sets=[],
        methods=methods,
        hybrid_specs=hybrid_specs,
        global_acc=acc,
        repair_weighting="metric_aware",
        metric_aware_beta=0.5,
    )
    assert skip is None
    r = rows[0]
    assert r["repair_weighting"] == "metric_aware"
    assert r["fas_repair_variant"] == "ma"
    assert r["fas_weight_removed_ma"] is not None
    assert r["mean_ma_edge_weight"] is not None
