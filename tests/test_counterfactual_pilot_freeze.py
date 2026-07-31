"""Offline tests for the frozen counterfactual micro-pilot contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_pilot.panel import (
    PANEL_VERSION,
    frozen_panel,
    panel_providers,
    require_panel_version,
)
from consistency_ranker.counterfactual_pilot.presentation import (
    map_displayed_preference_to_document,
    position_consistent,
    presentation_orders,
)
from consistency_ranker.counterfactual_pilot.prompt import (
    PROMPT_VERSION,
    load_prompt,
    prompt_sha256,
    render_prompt,
)
from consistency_ranker.counterfactual_pilot.query_selection import (
    load_frozen_query_ids,
    select_lexicographic_queries,
)
from consistency_ranker.counterfactual_pilot.schema import (
    JUDGMENT_SCHEMA_VERSION,
    validate_judgment,
)
from consistency_ranker.counterfactual_pilot.trajectory import (
    assert_no_qrels_in_policy_inputs,
    assert_same_candidate_pool,
    validate_step_record,
    validate_terminal_record,
)
from consistency_ranker.provider_capability.ledger import LiveCallCapExceeded, LiveCallLedger

REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO / "configs" / "counterfactual_micro_pilot_v1.json"


@pytest.fixture(scope="module")
def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_prompt_hash_stability() -> None:
    expected = "6e8038363393bb3e6c70edb61619107a29253fda60b35295c040c3925661fcf0"
    assert prompt_sha256(REPO) == expected
    assert PROMPT_VERSION == "counterfactual_pairwise_judge_v1"
    text = load_prompt(REPO)
    assert "{query}" in text and "{candidate_a}" in text and "{candidate_b}" in text
    assert "qrels" not in text.lower()
    assert "chain-of-thought" in text.lower() or "chain of thought" in text.lower()
    rendered = render_prompt(text, query="q", candidate_a="a", candidate_b="b")
    assert "Candidate A:\na" in rendered


def test_schema_validation() -> None:
    ok = validate_judgment(
        {
            "schema_version": JUDGMENT_SCHEMA_VERSION,
            "preference": "A",
            "confidence": 0.5,
            "evidence_strength": "moderate",
            "reason_code": "partial_answer",
        }
    )
    assert ok["preference"] == "A"
    with pytest.raises(ValueError):
        validate_judgment(
            {
                "schema_version": JUDGMENT_SCHEMA_VERSION,
                "preference": "C",
                "confidence": 0.5,
                "evidence_strength": "moderate",
                "reason_code": "other",
            }
        )
    schema_bytes = (REPO / "schemas" / "counterfactual_pairwise_judgment_v1.json").read_bytes()
    assert (
        hashlib.sha256(schema_bytes).hexdigest()
        == "f8332b7eadcbe92e1c4aed5299a0e3b1214c6d53a68aff3c826fe86147366de7"
    )


def test_ab_ba_document_normalization() -> None:
    assert presentation_orders() == ("ab", "ba")
    assert (
        map_displayed_preference_to_document(
            "A", orientation="ab", doc_a_id="d1", doc_b_id="d2"
        )
        == "d1"
    )
    assert (
        map_displayed_preference_to_document(
            "A", orientation="ba", doc_a_id="d1", doc_b_id="d2"
        )
        == "d2"
    )
    assert position_consistent("A", "B", doc_a_id="d1", doc_b_id="d2") is True
    assert position_consistent("A", "A", doc_a_id="d1", doc_b_id="d2") is False


def test_frozen_panel_configuration(config: dict) -> None:
    require_panel_version(PANEL_VERSION)
    with pytest.raises(ValueError, match="panel_v2"):
        require_panel_version("counterfactual_provider_panel_v2")
    panel = frozen_panel()
    assert len(panel) == 4
    assert panel_providers() == ["azure", "cohere", "fireworks", "gemini"]
    assert config["panel_version"] == PANEL_VERSION
    ids = {m["model_or_deployment"] for m in config["provider_panel"]}
    assert ids == {
        "gpt-4.1-mini",
        "command-r-plus-08-2024",
        "accounts/fireworks/models/gpt-oss-120b",
        "gemini-2.5-flash",
    }


def test_candidate_pool_equality_and_cutoff(config: dict) -> None:
    pool = ["c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9"]
    assert_same_candidate_pool(pool, list(pool), context="policy_cell")
    with pytest.raises(ValueError, match="mismatch"):
        assert_same_candidate_pool(pool, pool[:-1] + ["other"])
    assert config["candidate_pool"]["pool_size"] == 10
    assert config["candidate_pool"]["eval_k"] == 5
    assert config["candidate_pool"]["pool_size"] > config["candidate_pool"]["eval_k"]


def test_qrels_not_passed_into_policy_execution() -> None:
    assert_no_qrels_in_policy_inputs(
        {"candidate_ids": ["a", "b"], "prior_scores": {"a": 1.0}}
    )
    with pytest.raises(ValueError, match="qrels leakage"):
        assert_no_qrels_in_policy_inputs({"qrels": {"a": 1}, "candidate_ids": ["a"]})
    with pytest.raises(ValueError, match="qrels leakage"):
        assert_no_qrels_in_policy_inputs({"relevance_map": {"a": 1}})


@pytest.mark.real_data
def test_query_selection_reproducibility(config: dict) -> None:
    frozen = load_frozen_query_ids(config)
    assert sum(len(v) for v in frozen.values()) == 8
    for ds, meta in config["datasets"].items():
        qrels = REPO / meta["qrels_path"]
        queries = REPO / meta["queries_path"]
        got = select_lexicographic_queries(qrels_path=qrels, queries_path=queries, n=2)
        assert got == meta["query_ids"]


def test_trajectory_schema_validation() -> None:
    step = {
        "benchmark_version": "counterfactual_micro_pilot_v1",
        "dataset": "scidocs",
        "query_id": "q",
        "candidate_pool_id": "pool",
        "candidate_ids": ["a", "b", "c"],
        "policy": "production_uht",
        "budget": 8,
        "provider": "azure",
        "model_id": "gpt-4.1-mini",
        "step": 0,
        "available_action_count": 10,
        "selected_pair": ["a", "b"],
        "presentation_order": "ab",
        "request_hash": "abc",
        "judgment": {"preference": "A"},
        "normalized_document_preference": "a",
        "confidence": 0.5,
        "remaining_budget": 7,
        "graph_state_summary": {},
        "ranking_after_step": ["a", "b", "c"],
        "stop_reason": None,
        "calls_used": 1,
        "tokens_used": {"prompt": 1, "completion": 1},
        "latency": 0.1,
    }
    validate_step_record(step)
    with pytest.raises(ValueError):
        validate_step_record({k: v for k, v in step.items() if k != "request_hash"})
    terminal = {
        "final_ranking": ["a", "b"],
        "ndcg_at_5": 0.5,
        "mrr": 0.5,
        "recall_at_5": 0.5,
        "modeled_cost": None,
        "catastrophic_indicator": False,
        "prior_agreement_diagnostic": {},
    }
    validate_terminal_record(terminal)


def test_hard_live_call_cap_and_dedup(tmp_path: Path) -> None:
    led = LiveCallLedger(
        max_total_live_calls=384,
        max_live_calls_per_provider=96,
        path=tmp_path / "ledger.jsonl",
    )
    led.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        estimated_input_tokens=10,
        max_output_tokens=20,
    )
    led.finish_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        success=True,
        prompt_tokens=10,
        completion_tokens=5,
    )
    assert led.already_completed("h1")
    with pytest.raises(LiveCallCapExceeded, match="already completed"):
        led.begin_request(
            provider="azure",
            purpose="p",
            request_hash="h1",
            estimated_input_tokens=10,
            max_output_tokens=20,
        )


def test_micro_pilot_call_budget_arithmetic(config: dict) -> None:
    cb = config["call_budget"]
    assert cb["initial_live_calls"] == 8 * 4 * 8
    assert cb["hard_max_live_calls"] == 384
    assert cb["execute_in_this_task"] is False
    assert config["status"] == "frozen_not_executed"


def test_token_caps_are_tighter_than_call_cap_would_allow_by_default(config: dict) -> None:
    cb = config["call_budget"]
    pool = config["candidate_pool"]
    assert pool["max_candidate_chars"] == 1200
    assert cb["max_input_tokens_per_request"] == 2000
    assert cb["max_output_tokens_per_request"] == cb.get("max_output_tokens_per_request")
    assert cb["max_output_tokens_per_request"] == config["generation_defaults"]["max_output_tokens"]
    # Cumulative caps must be consistent with hard_max_live_calls * per-request caps,
    # with headroom (not equal to the old 2,000,000 / 200,000 placeholders).
    assert cb["max_total_input_tokens"] == 800000
    assert (
        cb["max_total_input_tokens"]
        >= cb["hard_max_live_calls"] * cb["max_input_tokens_per_request"]
    )
    assert cb["max_total_output_tokens"] == 60000
    assert (
        cb["max_total_output_tokens"]
        >= cb["hard_max_live_calls"] * cb["max_output_tokens_per_request"]
    )
    # The call cap remains authoritative even if token estimates are wrong.
    assert cb["hard_max_live_calls"] == 384


@pytest.mark.real_data
def test_worst_case_rendered_fixture_within_per_request_token_cap(config: dict) -> None:
    """Render the real frozen prompt against the longest real query/candidate text
    (truncated per the frozen max_candidate_chars) and confirm the resulting
    conservative token estimate stays under the frozen per-request cap.
    """
    template = load_prompt(REPO)
    max_chars = config["candidate_pool"]["max_candidate_chars"]
    longest_query = ""
    for meta in config["datasets"].values():
        queries_path = REPO / meta["queries_path"]
        with queries_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                qid = str(rec.get("query_id") or rec.get("id"))
                if qid in meta["query_ids"]:
                    text = str(rec.get("text") or rec.get("query") or "")
                    if len(text) > len(longest_query):
                        longest_query = text
    rendered = render_prompt(
        template,
        query=longest_query,
        candidate_a="x" * max_chars,
        candidate_b="x" * max_chars,
    )
    conservative_tokens = len(rendered) / 3.0
    assert conservative_tokens <= config["call_budget"]["max_input_tokens_per_request"]
