"""Fake-provider, end-to-end integration test for the micro-pilot collector.

Runs the entire 8-query x 4-provider pipeline against the real frozen config
and real corpora, but with a deterministic fake ``call_fn`` standing in for
every provider so the test makes zero network calls. Exercises reserve
scheduling, request counts, cap enforcement, trajectory/report generation,
resume, and terminal qrels evaluation together, in one realistic run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.counterfactual_benchmark.collector import run_collection
from consistency_ranker.counterfactual_pilot.trajectory import validate_step_record

pytestmark = pytest.mark.real_data

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "counterfactual_micro_pilot_v1.json"


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


def _make_fake_call_fn():
    """Deterministic fake covering: agreement, disagreement, one tie, one
    abstention, one parse failure, and cutoff-critical conflicts -- all
    derived purely from a call counter, never from real provider traffic."""
    state = {"n": 0}

    def fake_call_llm(prompt: str, config: object) -> tuple[str, object]:
        state["n"] += 1
        n = state["n"]
        if n % 41 == 0:
            return "this is not valid json", _FakeUsage(40, 4)
        if n % 17 == 0:
            pref = "TIE"
        elif n % 23 == 0:
            pref = "ABSTAIN"
        else:
            pref = "A" if n % 2 == 0 else "B"
        confidence = 0.3 if n % 7 == 0 else 0.85
        body = {
            "schema_version": "counterfactual_pairwise_judgment_v1",
            "preference": pref,
            "confidence": confidence,
            "evidence_strength": "moderate",
            "reason_code": "direct_relevance",
        }
        return json.dumps(body), _FakeUsage(40, 8)

    return fake_call_llm, state


def test_fake_provider_full_pipeline(tmp_path: Path, monkeypatch) -> None:
    for var, value in (
        ("AZURE_OPENAI_API_KEY", "fake"),
        ("AZURE_OPENAI_ENDPOINT", "https://fake.example.invalid"),
        ("COHERE_API_KEY", "fake"),
        ("FIREWORKS_API_KEY", "fake"),
        ("GEMINI_API_KEY", "fake"),
    ):
        monkeypatch.setenv(var, value)

    fake_call_llm, state = _make_fake_call_fn()
    out_dir = tmp_path / "fake_pilot_run"

    summary = run_collection(
        config_path=CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        call_fn=fake_call_llm,
    )

    # -- Request counts and cap compliance -----------------------------
    assert summary["queries_loaded"] == 8
    assert all(size == 10 for size in summary["pool_sizes"].values())
    assert summary["initial_request_count"] == 256
    assert summary["reserved_followup_calls"] == 128
    assert summary["hard_max_live_calls"] == 384
    assert summary["paid_api_calls"] <= 384
    assert state["n"] == summary["paid_api_calls"]  # every fake call counted once

    # -- Reserve scheduling: priority tiers reachable, cap respected ---
    reserve_decisions = [
        json.loads(line)
        for line in (out_dir / "reserve_decisions.jsonl").read_text().splitlines()
        if line.strip()
    ]
    scheduled = [d for d in reserve_decisions if d["scheduled"]]
    assert len(scheduled) == summary["reserve_scheduled"]
    assert len(scheduled) <= 128
    triggers_seen = {d["trigger"] for d in scheduled}
    assert "structured_output_retry" in triggers_seen  # from the parse failures
    assert "cutoff_critical_inconsistency" in triggers_seen  # from cutoff_boundary pairs
    for d in reserve_decisions:
        if not d["scheduled"]:
            assert d["skip_reason"] == "reserve_exhausted"

    # -- Trajectory schema validity for every processed request --------
    trajectory = [
        json.loads(line)
        for line in (out_dir / "trajectory_events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(trajectory) == summary["paid_api_calls"]
    for step in trajectory:
        validate_step_record(step)

    # -- Resume: re-running against the same output dir must not repeat
    #    successful requests or double-count calls/tokens. -------------
    calls_before_resume = state["n"]
    ledger_before = json.loads((out_dir / "ledger_summary.json").read_text())
    summary2 = run_collection(
        config_path=CONFIG_PATH,
        output_dir=out_dir,
        mode="live",
        repo_root=REPO_ROOT,
        call_fn=fake_call_llm,
        overwrite=True,
    )
    # Only cells that failed (parse failures beyond the retry, or capped out)
    # may have re-attempted; already-completed successes must not re-call.
    new_calls = state["n"] - calls_before_resume
    assert new_calls <= (summary["failures"])
    assert summary2["paid_api_calls"] >= ledger_before["total_live_calls"]

    # -- Reports and required output files ------------------------------
    for name in (
        "run_manifest.json",
        "collection_plan.json",
        "candidate_pools.jsonl",
        "request_ledger.jsonl",
        "normalized_judgments.jsonl",
        "trajectory_events.jsonl",
        "terminal_outcomes.jsonl",
        "reserve_decisions.jsonl",
        "ledger_summary.json",
        "validation_report.json",
        "FINAL_REPORT.md",
    ):
        assert (out_dir / name).exists(), f"missing {name}"

    report_text = (out_dir / "FINAL_REPORT.md").read_text()
    assert "MICRO-PILOT — OPERATIONAL VALIDATION ONLY" in report_text
    for non_claim in ("provider superiority", "policy superiority", "production readiness"):
        assert non_claim in report_text

    # -- Terminal qrels evaluation: one outcome per (dataset, query,
    #    provider), each explicit about policy-replay readiness. --------
    terminal = [
        json.loads(line)
        for line in (out_dir / "terminal_outcomes.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(terminal) == 8 * 4
    for outcome in terminal:
        assert outcome["policy_replay_ready"] is False
        assert outcome["executed_policies"] == []
        if not outcome["has_qrels"]:
            assert outcome["ndcg_at_5"] is None
            assert outcome["missing_qrels_reason"] is not None
