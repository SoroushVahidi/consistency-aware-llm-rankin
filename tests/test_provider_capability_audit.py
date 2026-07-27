"""Mock-based tests for bounded provider-capability audit.

Never initializes live provider clients unexpectedly; injectable call_fn only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from consistency_ranker.provider_capability.audit_engine import (
    request_hash,
    resolve_mode,
    run_provider_audit,
)
from consistency_ranker.provider_capability.cost_estimate import (
    default_plans,
    estimate_complete_matrix_requests,
    unordered_pairs,
)
from consistency_ranker.provider_capability.fixture import fixture_hash, prompt_hash
from consistency_ranker.provider_capability.ledger import LiveCallCapExceeded, LiveCallLedger
from consistency_ranker.provider_capability.parse_smoke import (
    map_preference_to_document,
    parse_smoke_response,
)
from consistency_ranker.provider_capability.sanitize import redact_text, sanitize_mapping

REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [PYTHON, *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env=env,
    )


def test_help_and_fail_closed_mode() -> None:
    proc = _run(["scripts/audit_provider_capabilities.py", "--help"])
    assert proc.returncode == 0
    proc2 = _run(
        [
            "scripts/audit_provider_capabilities.py",
            "--output-dir",
            "/tmp/should_not_matter_mode",
        ]
    )
    assert proc2.returncode != 0
    assert "Refusing to run" in (proc2.stderr + proc2.stdout)


def test_resolve_mode_exclusive() -> None:
    assert resolve_mode(allow_provider_calls=False, dry_run=True, cache_only=False) == "dry_run"
    assert resolve_mode(allow_provider_calls=False, dry_run=False, cache_only=True) == "cache_only"
    with pytest.raises(SystemExit):
        resolve_mode(allow_provider_calls=False, dry_run=False, cache_only=False)
    with pytest.raises(SystemExit):
        resolve_mode(allow_provider_calls=True, dry_run=True, cache_only=False)


def test_parse_and_orientation_mapping() -> None:
    raw = json.dumps(
        {
            "preference": "A",
            "confidence": 0.8,
            "evidence_strength": "strong",
            "reason_code": "direct_relevance",
        }
    )
    parsed = parse_smoke_response(raw)
    assert parsed["structured_ok"] is True
    assert parsed["preference"] == "A"
    assert map_preference_to_document("A", orientation="ab") == "doc_a"
    assert map_preference_to_document("A", orientation="ba") == "doc_b"
    assert map_preference_to_document("B", orientation="ba") == "doc_a"


def test_sanitize_preserves_token_metrics() -> None:
    payload = sanitize_mapping(
        {
            "prompt_tokens": 12,
            "completion_tokens": 3,
            "api_key": "SECRET",
            "access_token": "SECRET2",
        }
    )
    assert payload["prompt_tokens"] == 12
    assert payload["completion_tokens"] == 3
    assert payload["api_key"] == "[REDACTED]"
    assert payload["access_token"] == "[REDACTED]"

    text = "credentials present (Vertex AI, project=my-secret-project-123, location=global)"
    red = redact_text(text)
    assert "my-secret-project-123" not in red
    assert "[REDACTED_PROJECT]" in red
    payload = sanitize_mapping({"api_key": "SECRET", "model": "x", "note": text})
    assert payload["api_key"] == "[REDACTED]"
    assert "my-secret-project-123" not in json.dumps(payload)


def test_ledger_enforces_total_and_per_provider(tmp_path: Path) -> None:
    led = LiveCallLedger(
        max_total_live_calls=2,
        max_live_calls_per_provider=1,
        path=tmp_path / "ledger.jsonl",
    )
    led.begin_request(
        provider="azure",
        purpose="a",
        request_hash="h1",
        estimated_input_tokens=10,
        max_output_tokens=20,
    )
    led.finish_request(
        provider="azure",
        purpose="a",
        request_hash="h1",
        success=True,
        prompt_tokens=10,
        completion_tokens=5,
    )
    with pytest.raises(LiveCallCapExceeded):
        led.begin_request(
            provider="azure",
            purpose="b",
            request_hash="h2",
            estimated_input_tokens=10,
            max_output_tokens=20,
        )
    led.begin_request(
        provider="cohere",
        purpose="c",
        request_hash="h3",
        estimated_input_tokens=10,
        max_output_tokens=20,
    )
    led.finish_request(
        provider="cohere",
        purpose="c",
        request_hash="h3",
        success=True,
    )
    with pytest.raises(LiveCallCapExceeded, match="max_total_live_calls"):
        led.begin_request(
            provider="fireworks",
            purpose="d",
            request_hash="h4",
            estimated_input_tokens=10,
            max_output_tokens=20,
        )


def test_ledger_cost_cap_when_known(tmp_path: Path) -> None:
    led = LiveCallLedger(
        max_total_live_calls=10,
        max_live_calls_per_provider=10,
        max_estimated_cost_usd=1.0,
        path=tmp_path / "ledger.jsonl",
    )
    led.cost_known = True
    led.estimated_cost_usd = 0.9
    with pytest.raises(LiveCallCapExceeded, match="max_estimated_cost_usd"):
        led.begin_request(
            provider="azure",
            purpose="x",
            request_hash="hx",
            estimated_input_tokens=1,
            max_output_tokens=1,
            estimated_usd=0.2,
        )


def test_dry_run_zero_live_calls(tmp_path: Path) -> None:
    out = tmp_path / "dry"
    out.mkdir()
    # Force configured providers via inventory path; dry-run does not need keys
    # but inventory uses detect_llm_providers. Still zero network via call_fn unused.
    result = run_provider_audit(
        providers=["azure", "cohere", "fireworks", "gemini"],
        mode="dry_run",
        out_dir=out,
        seed=0,
        call_fn=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("no live")),
    )
    assert result["paid_api_calls"] == 0
    assert result["batch_jobs_submitted"] == 0
    assert (out / "capabilities.json").exists()
    # Manifests must not contain secret-looking values from our writes.
    text = (out / "capabilities.json").read_text()
    assert "api_key" not in text.lower() or "[REDACTED]" in text


def test_cache_only_zero_calls(tmp_path: Path) -> None:
    out = tmp_path / "cache"
    out.mkdir()
    calls = {"n": 0}

    def boom(prompt, config):
        calls["n"] += 1
        raise RuntimeError("should not be called")

    result = run_provider_audit(
        providers=["azure"],
        mode="cache_only",
        out_dir=out,
        call_fn=boom,
    )
    assert result["paid_api_calls"] == 0
    assert calls["n"] == 0


def test_live_mode_with_mock_respects_caps_and_dedup(tmp_path: Path) -> None:
    out = tmp_path / "live"
    out.mkdir()
    calls = {"n": 0}

    def mock_call(prompt, config):
        calls["n"] += 1
        # Prefer A for AB order (doc seasons tilt first); for BA prompt, prefer B
        # so mapped document stays doc_a.
        if "rotational axis is tilted" in prompt.split("Document A:", 1)[-1][
            :120
        ]:
            pref = "A"
        else:
            pref = "B"
        raw = json.dumps(
            {
                "preference": pref,
                "confidence": 0.7,
                "evidence_strength": "moderate",
                "reason_code": "direct_relevance",
            }
        )
        usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)
        return raw, usage

    result = run_provider_audit(
        providers=["azure"],
        mode="live",
        out_dir=out,
        seed=1,
        max_total_live_calls=16,
        max_live_calls_per_provider=4,
        call_fn=mock_call,
    )
    assert result["paid_api_calls"] == 3  # ab, ba, repeat
    assert calls["n"] == 3
    assert result["live_calls_by_provider"]["azure"] == 3
    # Resume / dedup: second run should not add calls.
    result2 = run_provider_audit(
        providers=["azure"],
        mode="live",
        out_dir=out,
        seed=1,
        max_total_live_calls=16,
        max_live_calls_per_provider=4,
        call_fn=mock_call,
    )
    assert calls["n"] == 3
    assert result2["paid_api_calls"] == 3


def test_retry_cap_single(tmp_path: Path) -> None:
    out = tmp_path / "retry"
    out.mkdir()
    state = {"n": 0}

    def flaky(prompt, config):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("transient")
        raw = json.dumps(
            {
                "preference": "A",
                "confidence": 0.5,
                "evidence_strength": "weak",
                "reason_code": "other",
            }
        )
        return raw, SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)

    result = run_provider_audit(
        providers=["azure"],
        mode="live",
        out_dir=out,
        seed=2,
        max_total_live_calls=16,
        max_live_calls_per_provider=4,
        call_fn=flaky,
    )
    # First attempt fails (counted) + retry success for call1, then call2/call3.
    assert state["n"] >= 2
    assert result["paid_api_calls"] <= 4
    assert result["ledger"]["retries"] >= 1


def test_unknown_capability_remains_null_for_logprobs(tmp_path: Path) -> None:
    out = tmp_path / "unk"
    out.mkdir()

    def mock_call(prompt, config):
        return (
            json.dumps(
                {
                    "preference": "A",
                    "confidence": 0.5,
                    "evidence_strength": "weak",
                    "reason_code": "other",
                }
            ),
            SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    result = run_provider_audit(
        providers=["azure"],
        mode="live",
        out_dir=out,
        call_fn=mock_call,
    )
    cap = result["capabilities"]["azure"]
    assert cap["logprobs"]["supported"] is None
    assert cap["logprobs"]["verified"] is False
    assert cap["rerank_endpoint"]["available"] is None


def test_cli_dry_run_and_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "cli_dry"
    proc = _run(
        [
            "scripts/audit_provider_capabilities.py",
            "--dry-run",
            "--providers",
            "azure",
            "--output-dir",
            str(out),
        ]
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    man = json.loads((out / "run_manifest.json").read_text())
    assert man["config"]["paid_api_calls_allowed"] is False
    assert man["config"]["fixture_hash"] == fixture_hash()
    assert man["config"]["prompt_hash"] == prompt_hash()
    # overwrite protection
    proc2 = _run(
        [
            "scripts/audit_provider_capabilities.py",
            "--dry-run",
            "--providers",
            "azure",
            "--output-dir",
            str(out),
        ]
    )
    assert proc2.returncode != 0


def test_cost_planner_offline(tmp_path: Path) -> None:
    assert unordered_pairs(10) == 45
    m = estimate_complete_matrix_requests(
        n_queries=32, pool_size=10, n_providers=4, presentation_orders=2, repeats=1
    )
    assert m["total_requests"] == 45 * 2 * 1 * 4 * 32
    plans = default_plans()
    assert "minimal_pilot" in plans["plans"]
    assert plans["plans"]["minimal_pilot"]["cost"]["estimated_cost_usd"] is None
    proc = _run(
        [
            "scripts/estimate_counterfactual_benchmark_cost.py",
            "--output-dir",
            str(tmp_path / "cost"),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "cost" / "cost_plans.json").exists()


def test_request_hash_stable() -> None:
    a = request_hash(
        provider="azure", model="m", purpose="structured_ab", orientation="ab", seed=1
    )
    b = request_hash(
        provider="azure", model="m", purpose="structured_ab", orientation="ab", seed=1
    )
    c = request_hash(
        provider="azure", model="m", purpose="structured_ab", orientation="ba", seed=1
    )
    assert a == b
    assert a != c
