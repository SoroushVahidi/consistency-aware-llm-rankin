from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "reports" / "full_calibrated_core" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import candidate_pool_policies as cpp  # noqa: E402
import pytest  # noqa: E402


def _synthetic_scores() -> dict[str, dict[str, float]]:
    return {
        "bm25": {f"d{i}": float(20 - i) for i in range(15)},
        "tfidf": {f"d{i}": float(15 - i) for i in range(3, 18)},
        "minilm": {f"d{i}": float(10 - i * 0.5) for i in range(6, 20)},
    }


class TestPoolSpec:
    def test_valid_construction(self):
        spec = cpp.PoolSpec(
            pool_id="x", policy_fn_name="select_candidates_bm25_only", label="X", kind="alternative"
        )
        assert spec.policy_fn is cpp.select_candidates_bm25_only

    def test_rejects_unknown_policy_fn_name(self):
        with pytest.raises(ValueError):
            cpp.PoolSpec(pool_id="x", policy_fn_name="nope", label="X", kind="alternative")

    def test_rejects_unknown_kind(self):
        with pytest.raises(ValueError):
            cpp.PoolSpec(
                pool_id="x", policy_fn_name="select_candidates_bm25_only", label="X", kind="bogus"
            )

    def test_rejects_empty_id_or_label(self):
        with pytest.raises(ValueError):
            cpp.PoolSpec(
                pool_id="",
                policy_fn_name="select_candidates_bm25_only",
                label="X",
                kind="alternative",
            )
        with pytest.raises(ValueError):
            cpp.PoolSpec(
                pool_id="x",
                policy_fn_name="select_candidates_bm25_only",
                label="",
                kind="alternative",
            )

    def test_dict_round_trip(self):
        for spec in cpp.POOL_SPECS.values():
            assert cpp.PoolSpec.from_dict(spec.to_dict()) == spec

    def test_full_registry_validates(self):
        assert len(cpp.POOL_SPECS) == 5
        assert cpp.POOL_SPECS["rrf_union_topk"].kind == "canonical"
        alt_kinds = {p.kind for pid, p in cpp.POOL_SPECS.items() if pid != "rrf_union_topk"}
        assert alt_kinds == {"alternative"}


class TestPoolPolicyBehavior:
    def test_rrf_union_matches_canonical_select_candidates_exactly(self):
        from run_phase0_phase1 import _select_candidates

        scores = _synthetic_scores()
        for top_k in (3, 8, 20, 100):
            assert cpp.select_candidates_rrf_union(scores, top_k) == _select_candidates(
                scores, top_k
            )

    def test_all_policies_deterministic_across_repeated_calls(self):
        scores = _synthetic_scores()
        for spec in cpp.POOL_SPECS.values():
            first = spec.policy_fn(scores, 8)
            second = spec.policy_fn(scores, 8)
            assert first == second, spec.pool_id

    def test_all_policies_return_deduplicated_lists(self):
        scores = _synthetic_scores()
        for spec in cpp.POOL_SPECS.values():
            pool = spec.policy_fn(scores, 8)
            assert len(pool) == len(set(pool)), spec.pool_id

    def test_new_alternative_policies_return_doc_id_sorted_lists(self):
        # The wrapped canonical rrf_union_topk policy intentionally returns
        # its own RRF-score order (matching _select_candidates exactly, see
        # test_rrf_union_matches_canonical_select_candidates_exactly), not
        # doc_id order. Only the four newly-added alternative policies are
        # doc_id-sorted by construction.
        scores = _synthetic_scores()
        for pool_id, spec in cpp.POOL_SPECS.items():
            if pool_id == "rrf_union_topk":
                continue
            pool = spec.policy_fn(scores, 8)
            assert pool == sorted(pool), pool_id

    def test_all_policies_only_return_documents_that_were_actually_scored(self):
        scores = _synthetic_scores()
        all_scored = {d for ranker_scores in scores.values() for d in ranker_scores}
        for spec in cpp.POOL_SPECS.values():
            pool = spec.policy_fn(scores, 8)
            assert set(pool) <= all_scored, spec.pool_id

    def test_equal_depth_union_takes_top_k_per_ranker(self):
        scores = _synthetic_scores()
        pool = cpp.select_candidates_equal_depth_union(scores, 3)
        # bm25 top-3 by score: d0, d1, d2; tfidf top-3: d3, d4, d5; minilm top-3: d6, d7, d8
        assert set(pool) == {"d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8"}

    def test_equal_depth_union_size_bounded_by_three_times_top_k(self):
        scores = _synthetic_scores()
        for top_k in (1, 5, 10):
            pool = cpp.select_candidates_equal_depth_union(scores, top_k)
            assert top_k <= len(pool) <= 3 * top_k

    def test_bm25_only_ignores_other_rankers(self):
        scores = _synthetic_scores()
        pool = cpp.select_candidates_bm25_only(scores, 5)
        assert pool == sorted(["d0", "d1", "d2", "d3", "d4"])
        # Changing tfidf/minilm scores must not change the bm25-only pool.
        mutated = dict(scores)
        mutated["tfidf"] = {"zzz": 999.0}
        mutated["minilm"] = {}
        assert cpp.select_candidates_bm25_only(mutated, 5) == pool

    def test_round_robin_reaches_exact_top_k_when_enough_docs_exist(self):
        scores = _synthetic_scores()
        for top_k in (1, 5, 8, 12):
            pool = cpp.select_candidates_round_robin_union(scores, top_k)
            assert len(pool) == top_k

    def test_round_robin_does_not_use_native_score_magnitude_across_rankers(self):
        # Scaling one ranker's scores by an arbitrary positive affine transform
        # must not change the round-robin pool, since it is rank-based per
        # ranker and never compares raw scores across rankers.
        scores = _synthetic_scores()
        scaled = dict(scores)
        scaled["bm25"] = {d: v * 1000.0 + 5.0 for d, v in scores["bm25"].items()}
        assert cpp.select_candidates_round_robin_union(
            scores, 8
        ) == cpp.select_candidates_round_robin_union(scaled, 8)

    def test_combsum_union_uses_existing_combsum_ranking_function(self):
        from consistency_ranker.combsum_ranking import combsum_ranking

        scores = _synthetic_scores()
        union_docs = sorted({d for s in scores.values() for d in s})
        expected = sorted(
            combsum_ranking(
                [scores["bm25"], scores["tfidf"], scores["minilm"]],
                union_docs,
                normalization="minmax",
            )[:8]
        )
        assert cpp.select_candidates_combsum_union(scores, 8) == expected

    def test_missing_ranker_handled_without_imputation(self):
        scores = {"bm25": {"a": 1.0, "b": 2.0}, "tfidf": {}, "minilm": {}}
        for spec in cpp.POOL_SPECS.values():
            pool = spec.policy_fn(scores, 5)
            assert set(pool) <= {"a", "b"}, spec.pool_id

    def test_empty_scores_returns_empty_pool(self):
        scores = {"bm25": {}, "tfidf": {}, "minilm": {}}
        for spec in cpp.POOL_SPECS.values():
            assert spec.policy_fn(scores, 5) == [], spec.pool_id

    def test_query_set_is_never_the_pool_functions_concern(self):
        # Pool policies operate purely on already-selected per-query score
        # maps; they take no query-id/query-set parameter at all, so they
        # cannot possibly change which queries are evaluated -- only which
        # documents are eligible within a query already chosen upstream.
        import inspect

        for spec in cpp.POOL_SPECS.values():
            params = inspect.signature(spec.policy_fn).parameters
            assert list(params) == ["ranker_scores", "top_k"], spec.pool_id


class TestNoQrelsLeakage:
    def test_no_policy_function_signature_mentions_qrels_or_relevance(self):
        import inspect

        forbidden = ("qrel", "relevance", "rel_map", "gain", "ndcg")
        for spec in cpp.POOL_SPECS.values():
            src = inspect.getsource(spec.policy_fn)
            lowered = src.lower()
            for term in forbidden:
                assert term not in lowered, f"{spec.pool_id} references {term!r}"
