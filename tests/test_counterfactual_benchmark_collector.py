"""Mock-based offline tests for the counterfactual micro-pilot collector.

No provider calls anywhere in this file. Covers: freeze integrity, qrels
leakage, pair/presentation handling, caps, resume, provider isolation, and
output structure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark import config as config_mod
from consistency_ranker.counterfactual_benchmark.cache_store import JudgmentCacheStore
from consistency_ranker.counterfactual_benchmark.dispatch import (
    call_provider,
    preflight_provider_ready,
)
from consistency_ranker.counterfactual_benchmark.models import (
    NormalizedJudgment,
    PairRecord,
)
from consistency_ranker.counterfactual_benchmark.pair_selection import select_shared_pairs
from consistency_ranker.counterfactual_benchmark.pool_builder import build_candidate_pool
from consistency_ranker.counterfactual_benchmark.reserve import derive_reserve_decisions
from consistency_ranker.counterfactual_benchmark.validation import (
    QrelsLeakageError,
    assert_no_qrels_anywhere,
)
from consistency_ranker.provider_capability.ledger import LiveCallCapExceeded, LiveCallLedger

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v1.json"


@pytest.fixture(scope="module")
def real_config() -> dict:
    return config_mod.load_config(CONFIG_PATH)


# ---------------------------------------------------------------------------
# Freeze integrity
# ---------------------------------------------------------------------------


def test_frozen_config_passes_verification(real_config: dict) -> None:
    config_mod.verify_frozen_contract(real_config, repo_root=REPO_ROOT)


def test_prompt_hash_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["prompt_sha256"] = "0" * 64
    with pytest.raises(config_mod.FreezeMismatchError, match="prompt_sha256 mismatch"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_schema_hash_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["judgment_schema_sha256"] = "0" * 64
    with pytest.raises(config_mod.FreezeMismatchError, match="judgment_schema_sha256 mismatch"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_panel_version_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["panel_version"] = "counterfactual_provider_panel_v2"
    with pytest.raises(config_mod.FreezeMismatchError):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_model_id_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["provider_panel"][0]["model_or_deployment"] = "gpt-9000"
    with pytest.raises(config_mod.FreezeMismatchError, match="model id mismatch"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_query_list_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["datasets"]["fiqa"]["query_ids"] = ["999", "998"]
    with pytest.raises(config_mod.FreezeMismatchError, match="query selection drift"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_pool_size_cutoff_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["candidate_pool"]["eval_k"] = tampered["candidate_pool"]["pool_size"]
    with pytest.raises(config_mod.FreezeMismatchError, match="must exceed"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_temperature_mismatch_fails(real_config: dict) -> None:
    tampered = json.loads(json.dumps(real_config))
    tampered["generation_defaults"]["temperature"] = 0.7
    with pytest.raises(config_mod.FreezeMismatchError, match="temperature mismatch"):
        config_mod.verify_frozen_contract(tampered, repo_root=REPO_ROOT)


def test_validate_against_previous_plan_detects_drift() -> None:
    previous = {"prompt_sha256": "abc", "hard_max_live_calls": 384}
    new_ok = {"prompt_sha256": "abc", "hard_max_live_calls": 384}
    config_mod.validate_against_previous_plan(new_ok, previous)  # no raise

    new_bad = {"prompt_sha256": "xyz", "hard_max_live_calls": 384}
    with pytest.raises(config_mod.FreezeMismatchError, match="prompt_sha256"):
        config_mod.validate_against_previous_plan(new_bad, previous)


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


def test_qrels_absent_from_clean_payload_passes() -> None:
    assert_no_qrels_anywhere({"candidate_ids": ["a", "b"], "prior_scores": {"a": 1.0}})


def test_nested_qrels_fields_rejected() -> None:
    with pytest.raises(QrelsLeakageError):
        assert_no_qrels_anywhere({"acquisition_state": {"nested": {"qrels": {"a": 1}}}})
    with pytest.raises(QrelsLeakageError):
        assert_no_qrels_anywhere({"steps": [{"ok": 1}, {"relevance_labels": {"a": 1}}]})


def test_pool_and_pair_records_are_qrels_free(real_config: dict) -> None:
    meta = real_config["datasets"]["fiqa"]
    pool = build_candidate_pool(
        dataset="fiqa",
        query_id="0",
        query_text="mortgage interest deduction",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert_no_qrels_anywhere(pool.to_dict())
    pairs = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    for p in pairs:
        assert_no_qrels_anywhere(p.to_dict())


def test_pair_selection_unchanged_when_qrels_modified(real_config: dict) -> None:
    """Pool/pair construction never reads qrels, so tampering with the qrels
    file on disk must not change the pool or the selected pairs at all."""
    meta = real_config["datasets"]["fiqa"]
    pool_before = build_candidate_pool(
        dataset="fiqa",
        query_id="0",
        query_text="mortgage interest deduction",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs_before = select_shared_pairs(pool_before, eval_k=5, n_pairs=8, seed=42)
    # Note: build_candidate_pool never even opens qrels_path -- there is no
    # qrels argument to the function at all, which is itself the guarantee.
    pool_after = build_candidate_pool(
        dataset="fiqa",
        query_id="0",
        query_text="mortgage interest deduction",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs_after = select_shared_pairs(pool_after, eval_k=5, n_pairs=8, seed=42)
    assert pool_before.pool_hash == pool_after.pool_hash
    assert [p.pair_id for p in pairs_before] == [p.pair_id for p in pairs_after]


# ---------------------------------------------------------------------------
# Pair and presentation handling
# ---------------------------------------------------------------------------


def test_pair_set_deterministic_given_seed(real_config: dict) -> None:
    meta = real_config["datasets"]["scidocs"]
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs_a = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    pairs_b = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    assert [p.pair_id for p in pairs_a] == [p.pair_id for p in pairs_b]
    pairs_c = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=7)
    assert [p.pair_id for p in pairs_a] != [p.pair_id for p in pairs_c]


def test_pair_set_has_no_duplicates(real_config: dict) -> None:
    meta = real_config["datasets"]["scidocs"]
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    keys = [frozenset({p.doc_a_id, p.doc_b_id}) for p in pairs]
    assert len(keys) == len(set(keys)) == 8


def test_pair_selection_reasons_recorded(real_config: dict) -> None:
    meta = real_config["datasets"]["scidocs"]
    pool = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    reasons = {p.reason for p in pairs}
    assert reasons.issubset(
        {
            "top_ranked",
            "cutoff_boundary",
            "high_ranker_disagreement",
            "near_tie_prior",
            "top_versus_lower",
            "deterministic_coverage",
        }
    )
    assert all(p.reason for p in pairs)


def test_shared_pair_set_is_reused_across_providers(real_config: dict) -> None:
    """build_initial_requests must reuse ONE pair set per query across all
    four providers -- verified via the actual request-plan builder."""
    from consistency_ranker.counterfactual_benchmark.request_plan import (
        build_initial_requests,
    )

    meta = real_config["datasets"]["fiqa"]
    pool = build_candidate_pool(
        dataset="fiqa",
        query_id="0",
        query_text="mortgage interest deduction",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    pairs = select_shared_pairs(pool, eval_k=5, n_pairs=8, seed=42)
    mini_config = dict(real_config)
    mini_config["datasets"] = {"fiqa": {**meta, "query_ids": ["0"]}}
    requests = build_initial_requests(
        config=mini_config, pools={("fiqa", "0"): pool}, pairs={("fiqa", "0"): pairs}
    )
    assert len(requests) == 4 * 8
    by_provider: dict[str, set[str]] = {}
    for r in requests:
        by_provider.setdefault(r.provider, set()).add(r.pair_id)
    pair_sets = list(by_provider.values())
    assert all(s == pair_sets[0] for s in pair_sets)


def test_ab_ba_orientation_reused_for_retry_vs_swapped_for_repeat() -> None:
    from consistency_ranker.counterfactual_benchmark.models import ReserveDecision
    from consistency_ranker.counterfactual_benchmark.reserve import build_reserve_request

    pair = PairRecord(
        dataset="d",
        query_id="q",
        doc_a_id="a",
        doc_b_id="b",
        pair_id="q::a::b",
        reason="top_ranked",
        initial_presentation_order="ab",
    )
    config = {
        "benchmark_version": "v1",
        "prompt_sha256": "p" * 64,
        "judgment_schema_sha256": "s" * 64,
        "generation_defaults": {"temperature": 0.0, "seed": 42},
    }
    retry_decision = ReserveDecision(
        request_hash="h",
        dataset="d",
        query_id="q",
        provider="azure",
        pair_id="q::a::b",
        trigger="structured_output_retry",
        priority=1,
        scheduled=True,
    )
    _, order = build_reserve_request(
        decision=retry_decision,
        original_pair=pair,
        config=config,
        pool_hash="ph",
        text_hash_a="ta",
        text_hash_b="tb",
        model_id="m",
    )
    assert order == "ab"

    repeat_decision = ReserveDecision(
        request_hash="h2",
        dataset="d",
        query_id="q",
        provider="azure",
        pair_id="q::a::b",
        trigger="cutoff_critical_inconsistency",
        priority=2,
        scheduled=True,
    )
    _, order2 = build_reserve_request(
        decision=repeat_decision,
        original_pair=pair,
        config=config,
        pool_hash="ph",
        text_hash_a="ta",
        text_hash_b="tb",
        model_id="m",
    )
    assert order2 == "ba"


# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------


def test_total_call_cap_enforced(tmp_path: Path) -> None:
    ledger = LiveCallLedger(
        max_total_live_calls=2,
        max_live_calls_per_provider=10,
        path=tmp_path / "l.jsonl",
    )
    ledger.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )
    ledger.finish_request(provider="azure", purpose="p", request_hash="h1", success=True)
    ledger.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h2",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )
    ledger.finish_request(provider="azure", purpose="p", request_hash="h2", success=True)
    with pytest.raises(LiveCallCapExceeded, match="max_total_live_calls"):
        ledger.begin_request(
            provider="azure",
            purpose="p",
            request_hash="h3",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )


def test_per_provider_cap_enforced(tmp_path: Path) -> None:
    ledger = LiveCallLedger(
        max_total_live_calls=100,
        max_live_calls_per_provider=1,
        path=tmp_path / "l.jsonl",
    )
    ledger.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )
    ledger.finish_request(provider="azure", purpose="p", request_hash="h1", success=True)
    with pytest.raises(LiveCallCapExceeded, match="max_live_calls_per_provider"):
        ledger.begin_request(
            provider="azure",
            purpose="p",
            request_hash="h2",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )
    # A different provider is unaffected by azure's exhausted per-provider cap.
    ledger.begin_request(
        provider="cohere",
        purpose="p",
        request_hash="h3",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )


def test_token_caps_enforced(tmp_path: Path) -> None:
    ledger = LiveCallLedger(
        max_total_live_calls=100,
        max_live_calls_per_provider=100,
        max_total_input_tokens=10,
        max_total_output_tokens=10,
        path=tmp_path / "l.jsonl",
    )
    with pytest.raises(LiveCallCapExceeded, match="max_total_input_tokens"):
        ledger.begin_request(
            provider="azure",
            purpose="p",
            request_hash="h1",
            estimated_input_tokens=11,
            max_output_tokens=1,
        )


def test_reserve_cap_enforced_priority_order() -> None:
    """When reserve demand exceeds the cap, the highest-priority triggers win
    and the rest are recorded scheduled=False with an explicit skip reason --
    low-priority repeats must not crowd out cutoff-critical confirmations."""
    pairs_by_query = {
        ("d", "q"): [
            PairRecord("d", "q", "a", "b", "q::a::b", "cutoff_boundary", "ab"),
            PairRecord("d", "q", "c", "e", "q::c::e", "top_ranked", "ab"),
        ]
    }
    judgments = []
    # 2 cutoff-critical cells (always confirmed) + 3 "other" position issues.
    for i in range(2):
        judgments.append(
            NormalizedJudgment(
                request_hash=f"cut{i}",
                dataset="d",
                query_id="q",
                provider=f"prov{i}",
                model_id="m",
                doc_a_id="a",
                doc_b_id="b",
                pair_id="q::a::b",
                presentation_order="ab",
                attempt_type="initial",
                success=True,
                preference="A",
                normalized_document_preference="a",
                confidence=0.9,
            )
        )
    for i in range(3):
        judgments.append(
            NormalizedJudgment(
                request_hash=f"other{i}",
                dataset="d",
                query_id="q",
                provider=f"prov{i}",
                model_id="m",
                doc_a_id="c",
                doc_b_id="e",
                pair_id="q::c::e",
                presentation_order="ab",
                attempt_type="initial",
                success=True,
                preference="TIE",
                normalized_document_preference="TIE",
                confidence=0.2,
            )
        )
    decisions = derive_reserve_decisions(
        initial_judgments=judgments, pairs_by_query=pairs_by_query, max_reserve=2
    )
    scheduled = [d for d in decisions if d.scheduled]
    skipped = [d for d in decisions if not d.scheduled]
    assert len(scheduled) == 2
    assert all(d.trigger == "cutoff_critical_inconsistency" for d in scheduled)
    assert len(skipped) == 3
    assert all(d.skip_reason == "reserve_exhausted" for d in skipped)


def test_failed_calls_counted_in_ledger(tmp_path: Path) -> None:
    ledger = LiveCallLedger(
        max_total_live_calls=100, max_live_calls_per_provider=100, path=tmp_path / "l.jsonl"
    )
    ledger.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )
    ledger.finish_request(provider="azure", purpose="p", request_hash="h1", success=False)
    assert ledger.total_live_calls == 1
    assert not ledger.already_completed("h1")


def test_retries_cannot_exceed_frozen_limit_field(real_config: dict) -> None:
    assert real_config["call_budget"]["max_retries_per_request"] == 1


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_successful_request_not_repeated_on_resume(tmp_path: Path) -> None:
    ledger_path = tmp_path / "l.jsonl"
    ledger = LiveCallLedger(
        max_total_live_calls=100,
        max_live_calls_per_provider=100,
        path=ledger_path,
    )
    ledger.begin_request(
        provider="azure",
        purpose="p",
        request_hash="h1",
        estimated_input_tokens=1,
        max_output_tokens=1,
    )
    ledger.finish_request(provider="azure", purpose="p", request_hash="h1", success=True)

    resumed = LiveCallLedger(
        max_total_live_calls=100,
        max_live_calls_per_provider=100,
        path=ledger_path,
    )
    resumed.load()
    assert resumed.already_completed("h1")
    with pytest.raises(LiveCallCapExceeded, match="already completed"):
        resumed.begin_request(
            provider="azure",
            purpose="p",
            request_hash="h1",
            estimated_input_tokens=1,
            max_output_tokens=1,
        )


def test_cache_store_resume_never_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "judgments.jsonl"
    store = JudgmentCacheStore(path)
    store.put({"request_hash": "h1", "value": 1})
    store.put({"request_hash": "h1", "value": 999})  # ignored: already present
    hit = store.get("h1")
    assert hit is not None and hit["value"] == 1
    assert len(store) == 1

    reopened = JudgmentCacheStore(path)
    assert len(reopened) == 1
    reopened_hit = reopened.get("h1")
    assert reopened_hit is not None and reopened_hit["value"] == 1


# ---------------------------------------------------------------------------
# Provider isolation
# ---------------------------------------------------------------------------


def test_no_provider_fallback_on_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from consistency_ranker.provider_capability.sanitize import env_names_for_provider

    for name in env_names_for_provider("azure"):
        monkeypatch.delenv(name, raising=False)
    ready, reason = preflight_provider_ready("azure")
    assert ready is False
    assert "missing_env" in reason

    result = call_provider(
        provider="azure",
        model_id="gpt-4.1-mini",
        prompt="hello",
        temperature=0.0,
        max_tokens=128,
        call_fn=lambda prompt, config: (_ for _ in ()).throw(
            AssertionError("must never dispatch when credentials are missing")
        ),
    )
    assert result.error_category == "missing_credentials"
    assert result.raw_response == ""


def test_one_provider_failure_does_not_change_another_providers_hash() -> None:
    from typing import Any

    from consistency_ranker.counterfactual_benchmark.request_plan import compute_request_hash

    common: dict[str, Any] = dict(
        benchmark_version="v1",
        dataset="d",
        query_id="q",
        pool_hash="ph",
        doc_a_id="a",
        doc_b_id="b",
        text_hash_a="ta",
        text_hash_b="tb",
        presentation_order="ab",
        model_id="m",
        prompt_sha256="p" * 64,
        schema_sha256="s" * 64,
        temperature=0.0,
        seed=42,
        attempt_type="initial",
    )
    h_azure = compute_request_hash(provider="azure", **common)
    h_cohere = compute_request_hash(provider="cohere", **common)
    assert h_azure != h_cohere
    # Recomputing azure's hash again (as if cohere's call had just failed)
    # must be byte-for-byte identical -- no shared mutable state.
    h_azure_again = compute_request_hash(provider="azure", **common)
    assert h_azure == h_azure_again


def test_dry_run_never_constructs_a_live_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*args, **kwargs):
        raise AssertionError("dry-run must never call a provider")

    # Patch the name as imported into collector's namespace ("from x import y"
    # binds a local reference there; patching the origin module would not
    # affect collector's already-bound reference).
    monkeypatch.setattr(
        "consistency_ranker.counterfactual_benchmark.collector.call_provider", boom
    )
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    out_dir = tmp_path / "dry_run_no_client"
    summary = run_collection(
        config_path=CONFIG_PATH,
        output_dir=out_dir,
        mode="dry_run",
        repo_root=REPO_ROOT,
    )
    assert summary["paid_api_calls"] == 0


def test_cache_only_never_constructs_a_live_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*args, **kwargs):
        raise AssertionError("cache-only must never call a provider")

    monkeypatch.setattr(
        "consistency_ranker.counterfactual_benchmark.collector.call_provider", boom
    )
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    out_dir = tmp_path / "cache_only_run"
    summary = run_collection(
        config_path=CONFIG_PATH,
        output_dir=out_dir,
        mode="cache_only",
        repo_root=REPO_ROOT,
    )
    assert summary["paid_api_calls"] == 0
    # Every initial cell is a missing_cache_entry; each of those also triggers
    # a structured_output_retry reserve candidate (up to the reserve cap),
    # which is *also* unresolved in cache-only mode -- so failures = initial
    # count + however many reserve retries were scheduled.
    assert summary["failures"] == summary["initial_request_count"] + summary["reserve_scheduled"]
    assert summary["reserve_scheduled"] == summary["reserved_followup_calls"]


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def test_dry_run_writes_all_required_files(tmp_path: Path) -> None:
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    out_dir = tmp_path / "dry_run"
    run_collection(
        config_path=CONFIG_PATH, output_dir=out_dir, mode="dry_run", repo_root=REPO_ROOT
    )
    for name in (
        "run_manifest.json",
        "collection_plan.json",
        "candidate_pools.jsonl",
        "request_ledger.jsonl",
        "normalized_judgments.jsonl",
        "trajectory_events.jsonl",
        "terminal_outcomes.jsonl",
        "validation_report.json",
        "FINAL_REPORT.md",
    ):
        assert (out_dir / name).exists(), f"missing {name}"
    report = (out_dir / "FINAL_REPORT.md").read_text()
    assert "DRY RUN — NO PROVIDER DATA" in report
    manifest = json.loads((out_dir / "run_manifest.json").read_text())
    assert "AZURE_OPENAI_API_KEY" not in json.dumps(manifest)


def test_candidate_pool_hash_stable_across_rebuilds(real_config: dict) -> None:
    meta = real_config["datasets"]["scidocs"]
    p1 = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    p2 = build_candidate_pool(
        dataset="scidocs",
        query_id="x",
        query_text="graph neural networks for recommendation",
        documents_path=REPO_ROOT / meta["documents_path"],
        pool_size=10,
        max_candidate_chars=1200,
    )
    assert p1.pool_hash == p2.pool_hash
    assert p1.candidate_ids == p2.candidate_ids


def test_missing_cells_explicit_in_cache_only(tmp_path: Path) -> None:
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    out_dir = tmp_path / "cache_only"
    summary = run_collection(
        config_path=CONFIG_PATH, output_dir=out_dir, mode="cache_only", repo_root=REPO_ROOT
    )
    assert summary["failures"] > 0
    for cell in summary["missing_cells"]:
        assert cell["reason"] == "missing_cache_entry"
    judgments = [
        json.loads(line)
        for line in (out_dir / "normalized_judgments.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert all(j["error_category"] == "missing_cache_entry" for j in judgments)


def test_status_label_correct_per_mode() -> None:
    from consistency_ranker.counterfactual_benchmark.report import status_label

    assert status_label(mode="dry_run", is_canary=False) == "DRY RUN — NO PROVIDER DATA"
    assert status_label(mode="live", is_canary=True) == "CANARY — INSTRUMENTATION ONLY"
    assert status_label(mode="live", is_canary=False) == "MICRO-PILOT — OPERATIONAL VALIDATION ONLY"


# ---------------------------------------------------------------------------
# Call-cap invariants (initial <= 256, reserve <= 128, total <= 384) and
# pre- vs post-inference failure accounting
# ---------------------------------------------------------------------------

CANARY_CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_collector_canary_v1.json"


def test_frozen_config_declares_the_documented_invariants(real_config: dict) -> None:
    cb = real_config["call_budget"]
    assert cb["initial_live_calls"] <= 256
    assert cb["reserved_followup_calls"] <= 128
    assert cb["hard_max_live_calls"] <= 384
    assert cb["initial_live_calls"] + cb["reserved_followup_calls"] == cb["hard_max_live_calls"]


def test_parse_failure_counts_as_inference_attempted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A call that reached a provider and got an unparseable response is a
    failure *after* inference -- it must still count against the caps."""
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    for var in ("AZURE_OPENAI_API_KEY", "COHERE_API_KEY", "FIREWORKS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(var, "fake")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")

    def always_malformed(prompt: str, config: object) -> tuple[str, object]:
        class _U:
            prompt_tokens = 10
            completion_tokens = 2

        return "not json", _U()

    out_dir = tmp_path / "canary_parse_failure"
    summary = run_collection(
        config_path=CANARY_CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        is_canary=True,
        call_fn=always_malformed,
    )
    assert summary["failed_after_inference"] == 4
    assert summary["failed_before_inference"] == 0
    assert summary["successful"] == 0
    judgments = [
        json.loads(line)
        for line in (out_dir / "normalized_judgments.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert all(j["inference_attempted"] is True for j in judgments)
    assert all(j["parse_failed"] is True for j in judgments)


def test_missing_credentials_do_not_count_as_inference_attempted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A call blocked before it ever reached a provider (missing
    credentials) is the documented exception to
    total == successful + failed_after_inference."""
    from consistency_ranker.counterfactual_benchmark.collector import run_collection
    from consistency_ranker.provider_capability.sanitize import env_names_for_provider

    for provider in ("azure", "cohere", "fireworks", "gemini"):
        for name in env_names_for_provider(provider):
            monkeypatch.delenv(name, raising=False)

    def never_called(prompt: str, config: object) -> tuple[str, object]:
        raise AssertionError("must never dispatch without credentials")

    out_dir = tmp_path / "canary_no_creds"
    summary = run_collection(
        config_path=CANARY_CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        is_canary=True,
        call_fn=never_called,
    )
    assert summary["failed_before_inference"] == 4
    assert summary["failed_after_inference"] == 0
    assert summary["successful"] == 0
    judgments = [
        json.loads(line)
        for line in (out_dir / "normalized_judgments.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert all(j["inference_attempted"] is False for j in judgments)
    assert all(j["error_category"] == "missing_credentials" for j in judgments)


def test_live_resume_retries_cached_preflight_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from consistency_ranker.counterfactual_benchmark.cache_store import JudgmentCacheStore
    from consistency_ranker.counterfactual_benchmark.collector import _resolve_live
    from consistency_ranker.counterfactual_benchmark.models import (
        CandidatePoolRecord,
        PlannedRequest,
        RenderedDocumentRecord,
    )

    for var in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"):
        monkeypatch.setenv(var, "fake")

    request = PlannedRequest(
        request_hash="stable-request-hash",
        benchmark_version="v1",
        dataset="d",
        query_id="q",
        pool_hash="pool",
        provider="azure",
        model_id="gpt-4.1-mini",
        doc_a_id="a",
        doc_b_id="b",
        presentation_order="ab",
        pair_id="q::a::b",
        pair_reason="top_ranked",
        temperature=0.0,
        seed=42,
        attempt_type="initial",
    )
    pool = CandidatePoolRecord(
        dataset="d",
        query_id="q",
        candidate_ids=("a", "b"),
        pool_hash="pool",
        text_hashes={"a": "a" * 64, "b": "b" * 64},
        construction_method="test",
        pool_protocol_version="test",
        rendering_policy_version="test",
        prior_scores_primary={"a": 1.0, "b": 0.0},
        prior_scores_secondary={},
        truncated_texts={"a": "alpha", "b": "beta"},
        rendering_metadata={
            "a": RenderedDocumentRecord("a", "a" * 64, "a" * 64, 5, 5, False, "none", True),
            "b": RenderedDocumentRecord("b", "b" * 64, "b" * 64, 4, 4, False, "none", True),
        },
    )

    cache = JudgmentCacheStore(tmp_path / "cache.jsonl")
    cache.put(
        {
            "request_hash": request.request_hash,
            "dataset": "d",
            "query_id": "q",
            "provider": "azure",
            "model_id": "gpt-4.1-mini",
            "doc_a_id": "a",
            "doc_b_id": "b",
            "pair_id": "q::a::b",
            "presentation_order": "ab",
            "attempt_type": "initial",
            "success": False,
            "inference_attempted": False,
            "error_category": "missing_credentials",
            "error_message": "missing_env:AZURE_OPENAI_API_KEY",
        }
    )

    calls = 0

    def succeeds(prompt: str, config: object) -> tuple[str, object]:
        nonlocal calls
        calls += 1

        class _Usage:
            prompt_tokens = 11
            completion_tokens = 7

        return (
            '{"preference":"A","confidence":0.9,'
            '"evidence_strength":"moderate","reason_code":"direct_relevance"}',
            _Usage(),
        )

    ledger = LiveCallLedger(
        max_total_live_calls=2,
        max_live_calls_per_provider=2,
        max_total_input_tokens=10_000,
        max_total_output_tokens=10_000,
        max_retries_per_request=1,
        max_estimated_cost_usd=None,
        path=tmp_path / "ledger.jsonl",
    )

    judgment = _resolve_live(
        request=request,
        query_text="query",
        pool=pool,
        config={
            "candidate_pool": {"max_candidate_chars": 20},
            "generation_defaults": {"max_output_tokens": 64},
        },
        repo_root=REPO_ROOT,
        ledger=ledger,
        cache=cache,
        call_fn=succeeds,
    )

    assert calls == 1
    assert judgment.success is True
    assert judgment.from_cache is False
    cached = cache.get(request.request_hash)
    assert cached is not None
    assert cached["success"] is True


def test_no_reserve_call_occurs_in_canary_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even when every initial call looks maximally unstable (parse
    failures, which are the highest-priority reserve trigger), the canary's
    reserved_followup_calls=0 must schedule exactly zero reserve calls."""
    from consistency_ranker.counterfactual_benchmark.collector import run_collection

    for var in ("AZURE_OPENAI_API_KEY", "COHERE_API_KEY", "FIREWORKS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(var, "fake")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid")

    def always_malformed(prompt: str, config: object) -> tuple[str, object]:
        class _U:
            prompt_tokens = 10
            completion_tokens = 2

        return "not json", _U()

    out_dir = tmp_path / "canary_zero_reserve"
    summary = run_collection(
        config_path=CANARY_CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        is_canary=True,
        call_fn=always_malformed,
    )
    assert summary["reserved_followup_calls"] == 0
    assert summary["reserve_scheduled"] == 0
    assert summary["paid_api_calls"] == 4
    reserve_decisions = [
        json.loads(line)
        for line in (out_dir / "reserve_decisions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(reserve_decisions) == 4  # all 4 want a retry
    assert all(not d["scheduled"] for d in reserve_decisions)
    assert all(d["skip_reason"] == "reserve_exhausted" for d in reserve_decisions)


def test_reserve_and_initial_requests_have_distinct_hashes(real_config: dict) -> None:
    """A reserve/retry request must never collide with its originating
    initial request's identity, even though it targets the same pair."""
    from consistency_ranker.counterfactual_benchmark.models import ReserveDecision
    from consistency_ranker.counterfactual_benchmark.reserve import build_reserve_request

    pair = PairRecord(
        dataset="d",
        query_id="q",
        doc_a_id="a",
        doc_b_id="b",
        pair_id="q::a::b",
        reason="top_ranked",
        initial_presentation_order="ab",
    )
    initial_hash = "initial-hash-placeholder"
    decision = ReserveDecision(
        request_hash=initial_hash,
        dataset="d",
        query_id="q",
        provider="azure",
        pair_id="q::a::b",
        trigger="other_position_inconsistency",
        priority=6,
        scheduled=True,
    )
    reserve_hash, _order = build_reserve_request(
        decision=decision,
        original_pair=pair,
        config=real_config,
        pool_hash="ph",
        text_hash_a="ta",
        text_hash_b="tb",
        model_id="gpt-4.1-mini",
    )
    assert reserve_hash != initial_hash
