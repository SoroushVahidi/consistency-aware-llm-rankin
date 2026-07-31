"""Unit tests for multi-provider eval (mocked APIs; no billed calls)."""

from __future__ import annotations

from pathlib import Path

from consistency_ranker.multi_provider_eval.cache import (
    ProvenanceJudgmentStore,
    make_cache_key,
)
from consistency_ranker.multi_provider_eval.ensemble import (
    agreement_only_edges,
    majority_across_models,
)
from consistency_ranker.multi_provider_eval.graph_eval import (
    evaluate_preference_graph,
    records_to_preferences,
)
from consistency_ranker.multi_provider_eval.manifest import (
    build_pilot_manifest,
    estimate_call_budget,
)
from consistency_ranker.multi_provider_eval.orientation import (
    majority_vote,
    orientation_consistency,
)
from consistency_ranker.multi_provider_eval.parsing import (
    normalize_winner,
    parse_pairwise_response,
)
from consistency_ranker.multi_provider_eval.prompts import PROMPT_FAMILY, get_prompt
from consistency_ranker.multi_provider_eval.schema import JudgmentRecord
from consistency_ranker.multi_provider_eval.spending import SpendingCeiling


class TestParsing:
    def test_plaintext_a(self):
        c, conf, note = parse_pairwise_response("A", allow_tie=False)
        assert c == "A" and note.startswith("plaintext")

    def test_json_b(self):
        c, conf, note = parse_pairwise_response(
            '{"choice":"B","confidence":"high"}',
            allow_tie=True,
            structured_json=True,
        )
        assert c == "B" and conf == "HIGH"

    def test_tie_rejected_when_disallowed(self):
        c, _, note = parse_pairwise_response(
            '{"choice":"TIE"}', allow_tie=False, structured_json=True
        )
        assert c == "INVALID"

    def test_tie_allowed(self):
        c, _, _ = parse_pairwise_response(
            '{"choice":"TIE"}', allow_tie=True, structured_json=True
        )
        assert c == "TIE"

    def test_ambiguous_is_invalid_not_default_a(self):
        c, _, note = parse_pairwise_response("Maybe both are fine.")
        assert c == "INVALID"

    def test_normalize_orientation_ba(self):
        w, abstain = normalize_winner(
            "A", doc_a_id="x", doc_b_id="y", orientation="ba"
        )
        assert w == "y" and not abstain


class TestOrientation:
    def test_consistent_reverse(self):
        r = orientation_consistency("x", "x", doc_a_id="x", doc_b_id="y")
        assert r["position_consistent"] and not r["contradictory"]

    def test_first_position_bias(self):
        r = orientation_consistency("x", "y", doc_a_id="x", doc_b_id="y")
        assert r["contradictory"] and r["first_position_bias_signal"]

    def test_majority_vote(self):
        m = majority_vote(["a", "a", "b"])
        assert m["winner"] == "a" and m["margin"] > 0


class TestCacheKey:
    def test_different_prompt_different_key(self):
        k1 = make_cache_key(
            provider="azure",
            model="m",
            prompt_version="legacy_v1",
            query_id="q",
            doc_a_id="a",
            doc_b_id="b",
            orientation="ab",
            temperature=0.0,
            top_p=None,
            max_tokens=32,
            seed=0,
        )
        k2 = make_cache_key(
            provider="azure",
            model="m",
            prompt_version="concise_v1",
            query_id="q",
            doc_a_id="a",
            doc_b_id="b",
            orientation="ab",
            temperature=0.0,
            top_p=None,
            max_tokens=32,
            seed=0,
        )
        assert k1 != k2

    def test_orientation_in_key(self):
        base = dict(
            provider="azure",
            model="m",
            prompt_version="legacy_v1",
            query_id="q",
            doc_a_id="a",
            doc_b_id="b",
            temperature=0.0,
            top_p=None,
            max_tokens=32,
            seed=0,
        )
        assert make_cache_key(**base, orientation="ab") != make_cache_key(
            **base, orientation="ba"
        )

    def test_store_resume(self, tmp_path: Path):
        store = ProvenanceJudgmentStore(tmp_path / "j.jsonl")
        rec = JudgmentRecord(
            provider="azure",
            model="m",
            deployment_or_endpoint=None,
            query_id="q",
            doc_a_id="a",
            doc_b_id="b",
            canonical_pair_id="q::a::b",
            displayed_orientation="ab",
            prompt_version="legacy_v1",
            raw_response="A",
            parsed_choice="A",
            normalized_winner_id="a",
            tie_or_abstention=False,
            valid=True,
            cache_key="abc",
        )
        store.put(rec)
        store2 = ProvenanceJudgmentStore(tmp_path / "j.jsonl")
        assert store2.get("abc") is not None
        assert len(store2) == 1


class TestSpending:
    def test_ceiling_stops(self):
        ceil = SpendingCeiling(
            max_new_calls_global=2,
            max_new_calls_per_provider={"azure": 10},
        )
        assert ceil.allow("azure")
        ceil.record("azure")
        ceil.record("azure")
        assert not ceil.allow("azure")
        assert ceil.stopped_reason == "global_call_ceiling"


class TestEnsembleAndGraph:
    def test_majority_and_agreement(self):
        records = [
            {
                "canonical_pair_id": "q::a::b",
                "query_id": "q",
                "doc_a_id": "a",
                "doc_b_id": "b",
                "provider": "azure",
                "model": "m1",
                "valid": True,
                "normalized_winner_id": "a",
            },
            {
                "canonical_pair_id": "q::a::b",
                "query_id": "q",
                "doc_a_id": "a",
                "doc_b_id": "b",
                "provider": "cohere",
                "model": "m2",
                "valid": True,
                "normalized_winner_id": "a",
            },
            {
                "canonical_pair_id": "q::a::b",
                "query_id": "q",
                "doc_a_id": "a",
                "doc_b_id": "b",
                "provider": "fireworks",
                "model": "m3",
                "valid": True,
                "normalized_winner_id": "b",
            },
        ]
        maj = majority_across_models(records)
        assert maj["q::a::b"]["winner"] == "a"
        agree = agreement_only_edges(records, min_models=2)
        assert "q::a::b" not in agree  # disputed

    def test_graph_eval_acyclic(self):
        records = [
            {
                "query_id": "q",
                "doc_a_id": "a",
                "doc_b_id": "b",
                "canonical_pair_id": "q::a::b",
                "displayed_orientation": "ab",
                "valid": True,
                "normalized_winner_id": "a",
            },
            {
                "query_id": "q",
                "doc_a_id": "b",
                "doc_b_id": "c",
                "canonical_pair_id": "q::b::c",
                "displayed_orientation": "ab",
                "valid": True,
                "normalized_winner_id": "b",
            },
        ]
        prefs = records_to_preferences(records, query_id="q")
        stats = evaluate_preference_graph(prefs)
        assert stats["originally_acyclic"]
        assert stats["ranking"][0] == "a"


class TestManifest:
    def test_deterministic(self):
        queries = [{"query_id": "q1", "text": "t1"}, {"query_id": "q2", "text": "t2"}]
        cands = {
            "q1": [{"doc_id": f"d{i}", "text": f"doc{i}"} for i in range(6)],
            "q2": [{"doc_id": f"e{i}", "text": f"doc{i}"} for i in range(6)],
        }
        m1 = build_pilot_manifest(
            dataset="scidocs", queries=queries, candidates_by_query=cands, seed=42
        )
        m2 = build_pilot_manifest(
            dataset="scidocs", queries=queries, candidates_by_query=cands, seed=42
        )
        assert m1 == m2
        est = estimate_call_budget(m1, n_providers=4, n_prompts=4, orientations=2)
        assert est["estimated_max_calls"] == m1["n_unordered_pairs"] * 2 * 4 * 4


class TestPrompts:
    def test_family_has_four(self):
        assert set(PROMPT_FAMILY) >= {
            "legacy_v1",
            "concise_v1",
            "json_ab_v1",
            "json_tie_v1",
        }
        assert "Document A" in get_prompt("legacy_v1").template or "document_a" in get_prompt(
            "legacy_v1"
        ).template.lower() or "{document_a}" in get_prompt("legacy_v1").template
