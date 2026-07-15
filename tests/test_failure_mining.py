"""Tests for failure-mining analysis and query processing."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pytest

from consistency_ranker.failure_mining.analysis import (
    OUR_REPAIRED_METHOD,
    OUR_UNREPAIRED_METHOD,
    build_summary_markdown,
    compute_failure_labels,
    write_aggregate_tables,
)
from consistency_ranker.failure_mining.graph_features import extended_graph_stats
from consistency_ranker.graph_construction import build_graph
from consistency_ranker.pairwise_prefs import Preference


def _make_prefs() -> list[Preference]:
    return [
        Preference("d1", "d2", 1.0),
        Preference("d1", "d3", 0.8),
        Preference("d2", "d3", 0.5),
        Preference("d3", "d2", 0.4),  # cycle
    ]


def test_summarize_failure_mining_rebuilds_from_partial_records(tmp_path: Path):
    """The rebuild script must work on a partial (in-progress) record set and
    must not require the source experiment to have finished."""
    import subprocess
    import sys

    record = {
        "query_metadata": {"dataset": "scidocs", "vote_regime": "ms1", "query_id": "q1"},
        "graph_stats": {"largest_scc_size": 2, "is_cyclic": True, "prior_top1_margin": 0.3},
        "repair_info": {"fas_removed_weight": 0.4},
        "failure_labels": {
            "loss_size_vs_best_baseline": 0.1,
            "loses_to_prior_only": True,
            "loses_to_rrf": True,
            "loses_to_score_sum": False,
            "loses_to_borda": False,
            "repair_harms_vs_unrepaired": True,
            "repair_helps_vs_unrepaired": False,
            "repair_inactive_vs_unrepaired": False,
            "our_ndcg": 0.4,
            "unrepaired_ndcg": 0.45,
            "best_external_baseline": "rrf",
        },
        "method_outputs": {
            OUR_REPAIRED_METHOD: {"ndcg_at_k": 0.4, "ranking": ["d1", "d2"]},
            "prior_only": {"ndcg_at_k": 0.5, "ranking": ["d1", "d2"]},
            "rrf": {"ndcg_at_k": 0.5, "ranking": ["d1", "d2"]},
        },
    }
    input_dir = tmp_path / "partial_run"
    input_dir.mkdir()
    with (input_dir / "query_level_full_records.jsonl").open("w") as fh:
        fh.write(json.dumps(record) + "\n")
        fh.write('{"query_metadata": {"dataset": "scidocs"')  # truncated line mid-write

    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "summarize_failure_mining.py"),
         "--input-dir", str(input_dir)],
        capture_output=True, text=True, cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    assert "skipped 1 incomplete/corrupt line" in result.stdout
    assert (input_dir / "table_baseline_win_rates.csv").exists()
    assert (input_dir / "failure_mining_summary.md").exists()
    assert (input_dir / "dataset_regime_coverage.csv").exists()


def test_rank_centrality_ranks_clear_winner_first():
    from consistency_ranker.baseline_ranking import rank_centrality_ranking, rank_centrality_scores

    # a beats b and c; b beats c. a should be the clear top-ranked item.
    prefs = [
        Preference("a", "b", 1.0),
        Preference("a", "c", 1.0),
        Preference("b", "c", 1.0),
    ]
    graph = build_graph(prefs)
    ranking = rank_centrality_ranking(graph)
    assert ranking[0] == "a"
    assert ranking[-1] == "c"

    scores = rank_centrality_scores(graph)
    assert set(scores) == {"a", "b", "c"}
    assert abs(sum(scores.values()) - 1.0) < 1e-6
    assert scores["a"] > scores["b"] > scores["c"]


def test_rank_centrality_handles_single_node_and_empty_graph():
    from consistency_ranker.baseline_ranking import rank_centrality_scores

    empty_graph = nx.DiGraph()
    assert rank_centrality_scores(empty_graph) == {}

    single = nx.DiGraph()
    single.add_node("only")
    assert rank_centrality_scores(single) == {"only": 1.0}


def test_extended_graph_stats_detects_cycle():
    graph = build_graph(_make_prefs())
    stats = extended_graph_stats(graph, prior_scores={"d1": 2.0, "d2": 1.0, "d3": 0.5})
    assert stats["is_cyclic"] is True
    assert stats["n_mutual_pairs"] >= 0
    assert stats["n_nodes"] == 3


def test_compute_failure_labels_ranking():
    metrics = {
        OUR_REPAIRED_METHOD: {"ndcg_at_k": 0.4},
        OUR_UNREPAIRED_METHOD: {"ndcg_at_k": 0.45},
        "prior_only": {"ndcg_at_k": 0.5},
        "rrf": {"ndcg_at_k": 0.55},
        "score_sum": {"ndcg_at_k": 0.42},
    }
    fl = compute_failure_labels(metrics)
    assert fl["loses_to_prior_only"] is True
    assert fl["loses_to_rrf"] is True
    assert fl["repair_harms_vs_unrepaired"] is True
    assert fl["loss_size_vs_best_baseline"] == pytest.approx(0.15, abs=1e-6)
    assert fl["best_external_baseline"] == "rrf"


def test_write_aggregate_tables_and_summary(tmp_path: Path):
    record = {
        "query_metadata": {
            "dataset": "scidocs",
            "vote_regime": "ms1",
            "query_id": "q1",
        },
        "graph_stats": {
            "largest_scc_size": 2,
            "is_cyclic": True,
            "prior_top1_margin": 0.3,
        },
        "repair_info": {"fas_removed_weight": 0.4},
        "failure_labels": {
            "loss_size_vs_best_baseline": 0.1,
            "loses_to_prior_only": True,
            "loses_to_rrf": True,
            "loses_to_score_sum": False,
            "loses_to_borda": False,
            "repair_harms_vs_unrepaired": True,
            "repair_helps_vs_unrepaired": False,
            "repair_inactive_vs_unrepaired": False,
            "our_ndcg": 0.4,
            "unrepaired_ndcg": 0.45,
            "best_external_baseline": "rrf",
        },
        "method_outputs": {
            OUR_REPAIRED_METHOD: {"ndcg_at_k": 0.4, "ranking": ["d1", "d2"]},
            OUR_UNREPAIRED_METHOD: {"ndcg_at_k": 0.45, "ranking": ["d2", "d1"]},
            "prior_only": {"ndcg_at_k": 0.5, "ranking": ["d1", "d2"]},
            "rrf": {"ndcg_at_k": 0.5, "ranking": ["d1", "d2"]},
        },
    }
    write_aggregate_tables(tmp_path, [record])
    assert (tmp_path / "table_baseline_win_rates.csv").exists()
    assert (tmp_path / "table_failure_cases_top_losses.csv").exists()
    md = build_summary_markdown(tmp_path, [record], {"status": "test"})
    assert "Failure Mining Summary" in md
    assert (tmp_path / "failure_mining_summary.md").exists()


def test_detect_llm_providers_no_secrets(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import detect_llm_providers

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    st = detect_llm_providers(["gemini"])
    assert st[0].available is False
    assert st[0].mode is None
    assert "GEMINI" in st[0].reason
    assert "sk-" not in st[0].reason


def test_detect_llm_providers_gemini_api_key_mode(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import detect_llm_providers

    monkeypatch.setenv("GEMINI_API_KEY", "sk-super-secret-not-real")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    st = detect_llm_providers(["gemini"])
    assert st[0].available is True
    assert st[0].mode == "api_key"
    assert "sk-super-secret-not-real" not in st[0].reason


def test_detect_llm_providers_gemini_vertex_mode(monkeypatch):
    """No direct API key, but GOOGLE_GENAI_USE_VERTEXAI + project + ADC are usable."""
    from consistency_ranker.failure_mining.llm_runner import detect_llm_providers

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    class _FakeCreds:
        pass

    monkeypatch.setattr("google.auth.default", lambda: (_FakeCreds(), "test-project-123"), raising=False)

    st = detect_llm_providers(["gemini"])
    assert st[0].available is True
    assert st[0].mode == "vertex"
    assert "test-project-123" in st[0].reason
    assert "us-central1" in st[0].reason


def test_detect_llm_providers_gemini_vertex_missing_project(monkeypatch):
    """GOOGLE_GENAI_USE_VERTEXAI set but no project resolvable anywhere -> unavailable."""
    from consistency_ranker.failure_mining.llm_runner import detect_llm_providers

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    for k in ("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GCP_PROJECT", "VERTEXAI_PROJECT"):
        monkeypatch.delenv(k, raising=False)

    class _FakeCreds:
        pass

    # ADC resolves credentials but with no project of its own either.
    monkeypatch.setattr("google.auth.default", lambda: (_FakeCreds(), None), raising=False)

    st = detect_llm_providers(["gemini"])
    assert st[0].available is False
    assert st[0].mode is None


def test_detect_llm_providers_gemini_vertex_invalid_adc(monkeypatch):
    """GOOGLE_GENAI_USE_VERTEXAI set, project set, but ADC fails to load -> unavailable."""
    from consistency_ranker.failure_mining.llm_runner import detect_llm_providers

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")

    def _raise():
        raise RuntimeError("Could not automatically determine credentials")

    monkeypatch.setattr("google.auth.default", lambda: _raise(), raising=False)

    st = detect_llm_providers(["gemini"])
    assert st[0].available is False
    assert st[0].mode is None


def test_run_pairwise_rerank_gemini_vertex_client_init(monkeypatch, tmp_path):
    """Provider health-check success in Vertex mode: the adapter constructs a
    Vertex-mode genai.Client (vertexai=True, project=..., location=...) and
    returns a usable pairwise judgment, without ever touching a real network
    call (google.genai.Client is mocked)."""
    import rerankers.llm_pairwise as llm_pairwise
    from consistency_ranker.failure_mining.llm_runner import LLMRunner

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    class _FakeCreds:
        pass

    monkeypatch.setattr("google.auth.default", lambda: (_FakeCreds(), "test-project-123"), raising=False)

    init_calls: list[dict] = []

    class _FakeUsage:
        prompt_token_count = 10
        candidates_token_count = 1

    class _FakeResponse:
        text = "A"
        usage_metadata = _FakeUsage()

    class _FakeModels:
        def generate_content(self, *, model, contents, config):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, *, vertexai=False, project=None, location=None, api_key=None):
            init_calls.append(
                {"vertexai": vertexai, "project": project, "location": location, "api_key": api_key}
            )
            self.models = _FakeModels()

    import google.genai as real_genai

    monkeypatch.setattr(real_genai, "Client", _FakeClient, raising=False)

    runner = LLMRunner(
        output_path=tmp_path / "llm_call_records.jsonl",
        cache_dir=tmp_path / "llm_cache",
        max_calls=10,
        use_cache=True,
    )
    out = runner.run_pairwise_rerank(
        provider="gemini",
        query_id="q1",
        query_text="test query",
        doc_texts={"d1": "doc one text", "d2": "doc two text"},
        candidate_ids=["d1", "d2"],
    )

    assert out is not None
    assert out["llm_record"]["provider_mode"] == "vertex"
    assert init_calls, "expected genai.Client to be constructed"
    assert init_calls[0]["vertexai"] is True
    assert init_calls[0]["project"] == "test-project-123"
    assert init_calls[0]["api_key"] is None


def test_run_pairwise_rerank_calls_real_signature(monkeypatch, tmp_path):
    """Regression test: run_pairwise_rerank must call collect_all_pairs/rerank_query
    with its actual signature (candidates: list[tuple[id, text]]), not the
    doc_texts=/candidate_ids= kwargs that don't exist on that function. Also
    verifies the second identical call is served from the on-disk cache."""
    import rerankers.llm_pairwise as llm_pairwise
    from consistency_ranker.failure_mining.llm_runner import LLMRunner

    call_count = {"n": 0}

    def fake_call_llm(prompt, config):
        call_count["n"] += 1
        return "A", None

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    runner = LLMRunner(
        output_path=tmp_path / "llm_call_records.jsonl",
        cache_dir=tmp_path / "llm_cache",
        max_calls=10,
        use_cache=True,
    )

    doc_texts = {"d1": "doc one text", "d2": "doc two text"}
    out = runner.run_pairwise_rerank(
        provider="openai",
        query_id="q1",
        query_text="test query",
        doc_texts=doc_texts,
        candidate_ids=["d1", "d2"],
    )

    assert out is not None
    assert set(out["ranking"]) == {"d1", "d2"}
    assert out["llm_record"]["from_cache"] is False
    calls_after_first = call_count["n"]
    assert calls_after_first > 0

    out2 = runner.run_pairwise_rerank(
        provider="openai",
        query_id="q1",
        query_text="test query",
        doc_texts=doc_texts,
        candidate_ids=["d1", "d2"],
    )
    assert out2 is not None
    assert out2["llm_record"]["from_cache"] is True
    assert call_count["n"] == calls_after_first  # no new LLM calls on cache hit

    prompt_log = tmp_path / "llm_prompt_call_log.jsonl"
    assert prompt_log.exists()
    entries = [json.loads(l) for l in prompt_log.read_text().splitlines()]
    fresh = [e for e in entries if not e["from_cache"]]
    cached = [e for e in entries if e["from_cache"]]
    assert fresh, "expected at least one fresh prompt/response entry"
    assert cached, "expected at least one cache-hit entry from the second call"
    for e in fresh:
        assert e["prompt"], "exact prompt text must be recorded"
        assert e["raw_response"] == "A"
        assert e["parsed_winner_label"] == "A"
        assert e["parse_error"] is None
        assert e["provider"] == "openai"
        assert e["query_id"] == "q1"


def test_classify_llm_error_model_unavailable_503_not_generic_budget():
    """Regression test for the CloudRift diagnostic: a 503 'no active servers
    for model X' must not be conflated with real budget exhaustion or an
    unknown error -- it needs its own distinct, actionable category."""
    import openai

    from consistency_ranker.failure_mining.llm_runner import classify_llm_error

    exc = openai.InternalServerError(
        message="Error code: 503 - {'error': {'message': \"No active servers for model 'Qwen/Qwen3.6-35B-A3B-FP8'\", 'type': 'server_error'}}",
        response=_fake_httpx_response(503),
        body=None,
    )
    assert classify_llm_error(exc) == "model_unavailable"


def test_classify_llm_error_generic_server_error_stays_server_error():
    import openai

    from consistency_ranker.failure_mining.llm_runner import classify_llm_error

    exc = openai.InternalServerError(
        message="Error code: 500 - internal error", response=_fake_httpx_response(500), body=None
    )
    assert classify_llm_error(exc) == "server_error"


def test_classify_llm_error_auth_and_rate_limit_and_not_found():
    import openai

    from consistency_ranker.failure_mining.llm_runner import classify_llm_error

    auth_exc = openai.AuthenticationError(
        message="Incorrect API key provided", response=_fake_httpx_response(401), body=None
    )
    assert classify_llm_error(auth_exc) == "auth_error"

    not_found_exc = openai.NotFoundError(
        message="Model 'bogus-model' not found", response=_fake_httpx_response(404), body=None
    )
    assert classify_llm_error(not_found_exc) == "model_not_found"

    rate_limit_exc = openai.RateLimitError(
        message="Rate limit reached", response=_fake_httpx_response(429), body=None
    )
    assert classify_llm_error(rate_limit_exc) == "rate_limited"

    budget_exc = openai.RateLimitError(
        message="You exceeded your current quota, insufficient_quota",
        response=_fake_httpx_response(429),
        body=None,
    )
    assert classify_llm_error(budget_exc) == "budget_exhausted"


def test_classify_llm_error_message_fallback_for_non_openai_exceptions():
    from consistency_ranker.failure_mining.llm_runner import classify_llm_error

    assert classify_llm_error(RuntimeError("Connection timed out after 30s")) == "timeout"
    assert classify_llm_error(ValueError("no active servers for this model")) == "model_unavailable"
    assert classify_llm_error(RuntimeError("something truly unexpected happened")) == "unknown_error"


def _fake_httpx_response(status_code: int):
    import httpx

    return httpx.Response(status_code, request=httpx.Request("POST", "https://example.test/v1/chat/completions"))


def test_run_pairwise_rerank_records_error_category_on_failure(monkeypatch, tmp_path):
    """The api_failures.csv-facing last_error / error_category must reflect
    the real classified cause, not a generic placeholder -- this is what the
    overnight orchestrator now reads instead of hardcoding
    "unavailable_or_budget" for every failure regardless of cause."""
    import rerankers.llm_pairwise as llm_pairwise
    from consistency_ranker.failure_mining.llm_runner import LLMRunner

    monkeypatch.setenv("CLOUDRIFT_API_KEY", "test-cloudrift-key")
    monkeypatch.setenv("CLOUDRIFT_BASE_URL", "https://inference.cloudrift.ai/v1")
    monkeypatch.setenv("CLOUDRIFT_MODEL", "some/unavailable-model")

    def fake_call_llm(prompt, config):
        import openai

        raise openai.InternalServerError(
            message="Error code: 503 - {'error': {'message': \"No active servers for model 'some/unavailable-model'\", 'type': 'server_error'}}",
            response=_fake_httpx_response(503),
            body=None,
        )

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)

    runner = LLMRunner(
        output_path=tmp_path / "llm_call_records.jsonl",
        cache_dir=tmp_path / "llm_cache",
        max_calls=10,
        use_cache=True,
    )
    out = runner.run_pairwise_rerank(
        provider="cloudrift",
        query_id="q1",
        query_text="test query",
        doc_texts={"d1": "doc one text", "d2": "doc two text"},
        candidate_ids=["d1", "d2"],
    )

    assert out is None
    assert runner.last_error is not None
    assert runner.last_error["category"] == "model_unavailable"
    assert runner.last_error["http_status"] == 503
    assert runner.last_error["model"] == "some/unavailable-model"

    import json as _json

    records = [_json.loads(line) for line in (tmp_path / "llm_call_records.jsonl").read_text().splitlines()]
    assert records[-1]["error_category"] == "model_unavailable"
    assert records[-1]["http_status"] == 503


def test_provider_call_config_maps_openai_compatible_endpoints(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key")
    monkeypatch.setenv("CLOUDRIFT_API_KEY", "test-cloudrift-key")
    monkeypatch.setenv("CLOUDRIFT_BASE_URL", "https://inference.cloudrift.ai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-azure-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1")

    cohere_cfg = _provider_call_config("cohere")
    assert cohere_cfg["family"] == "openai"
    assert cohere_cfg["api_key"] == "test-cohere-key"
    assert "cohere.ai" in cohere_cfg["base_url"]

    cloudrift_cfg = _provider_call_config("cloudrift")
    assert cloudrift_cfg["base_url"] == "https://inference.cloudrift.ai/v1"

    azure_cfg = _provider_call_config("azure")
    assert azure_cfg["base_url"] == "https://example.openai.azure.com/openai/v1"

    gemini_cfg = _provider_call_config("gemini")
    assert gemini_cfg["family"] == "gemini"
    assert "api_key" not in gemini_cfg


def test_provider_call_config_fireworks_default_model_is_not_the_dead_llama_model(monkeypatch):
    """Regression test for the Fireworks diagnostic: the previous default,
    accounts/fireworks/models/llama-v3p1-8b-instruct, 404s on every call
    (removed from Fireworks' serverless catalog -- confirmed via a live
    GET /v1/models call). The default must not silently regress back to it."""
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("FIREWORKS_API_KEY", "test-fireworks-key")
    monkeypatch.delenv("FIREWORKS_MODEL", raising=False)
    monkeypatch.delenv("FIREWORKS_BASE_URL", raising=False)

    cfg = _provider_call_config("fireworks")

    assert cfg["family"] == "openai"
    assert cfg["model"] != "accounts/fireworks/models/llama-v3p1-8b-instruct"
    assert cfg["model"].startswith("accounts/fireworks/models/")
    assert cfg["base_url"] == "https://api.fireworks.ai/inference/v1"
    assert cfg["api_key"] == "test-fireworks-key"


def test_provider_call_config_fireworks_missing_key(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)

    cfg = _provider_call_config("fireworks")
    assert cfg["api_key"] is None


def test_provider_call_config_fireworks_reasoning_model_gets_extra_body_and_larger_budget(monkeypatch):
    """gpt-oss-* is a reasoning model: with the pipeline's normal max_tokens=4
    (sized for a single A/B letter on non-reasoning models), it silently
    returns content=None (all budget spent on hidden reasoning_content). The
    adapter must request low reasoning effort and a larger token budget for
    this specific model family, without changing behavior for a non-reasoning
    model a user might configure instead."""
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("FIREWORKS_API_KEY", "test-fireworks-key")
    monkeypatch.setenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")

    cfg = _provider_call_config("fireworks")
    assert cfg["extra_body"] == {"reasoning_effort": "low"}
    assert cfg["max_tokens_override"] and cfg["max_tokens_override"] > 4

    monkeypatch.setenv("FIREWORKS_MODEL", "accounts/fireworks/models/some-other-non-reasoning-model")
    cfg2 = _provider_call_config("fireworks")
    assert "extra_body" not in cfg2
    assert "max_tokens_override" not in cfg2


def test_run_pairwise_rerank_fireworks_reasoning_model_empty_content_classified(monkeypatch, tmp_path):
    """If a reasoning model still returns empty content (e.g. max_tokens
    still too small), the adapter must raise a classifiable error instead of
    crashing on `.strip()` against None, and last_error must reflect
    "malformed_response" rather than an unhandled AttributeError."""
    from consistency_ranker.failure_mining.llm_runner import LLMRunner

    monkeypatch.setenv("FIREWORKS_API_KEY", "test-fireworks-key")
    monkeypatch.setenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")

    class _FakeUsage:
        prompt_tokens = 78
        completion_tokens = 128

    class _FakeMessage:
        content = None

    class _FakeChoice:
        message = _FakeMessage()
        finish_reason = "length"

    class _FakeResponse:
        choices = [_FakeChoice()]
        usage = _FakeUsage()

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAIClient:
        def __init__(self, **kwargs):
            self.chat = _FakeChat()

    import openai as real_openai

    monkeypatch.setattr(real_openai, "OpenAI", _FakeOpenAIClient, raising=False)

    runner = LLMRunner(
        output_path=tmp_path / "llm_call_records.jsonl",
        cache_dir=tmp_path / "llm_cache",
        max_calls=10,
        use_cache=False,
    )
    out = runner.run_pairwise_rerank(
        provider="fireworks",
        query_id="q1",
        query_text="test query",
        doc_texts={"d1": "doc one text", "d2": "doc two text"},
        candidate_ids=["d1", "d2"],
    )

    assert out is None
    assert runner.last_error is not None
    assert runner.last_error["category"] == "malformed_response"


def test_classify_llm_error_insufficient_credit_is_budget_exhausted():
    from consistency_ranker.failure_mining.llm_runner import classify_llm_error

    exc = RuntimeError("Error code: 402 - insufficient balance, please add credit to your account")
    assert classify_llm_error(exc) == "budget_exhausted"
    assert classify_llm_error(RuntimeError("insufficient balance")) == "budget_exhausted"


def test_fireworks_api_key_no_secret_leakage_in_config(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config, detect_llm_providers

    monkeypatch.setenv("FIREWORKS_API_KEY", "sk-fireworks-super-secret-value")
    cfg = _provider_call_config("fireworks")
    # api_key is intentionally present in the config dict (needed to build
    # the client) but must never appear in any status/reason string.
    statuses = detect_llm_providers(["fireworks"])
    assert "sk-fireworks-super-secret-value" not in statuses[0].reason
    assert cfg["api_key"] == "sk-fireworks-super-secret-value"


def test_provider_call_config_azure_deployment_and_endpoint_resolution(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-azure-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.delenv("AZURE_OPENAI_CONCURRENCY", raising=False)

    cfg = _provider_call_config("azure")
    assert cfg["model"] == "gpt-4.1-mini"
    assert cfg["base_url"] == "https://example.openai.azure.com/openai/v1"
    assert cfg["api_key"] == "test-azure-key"
    # Default is the empirically-validated, full-scale-tested value (see the
    # Azure latency diagnostic: 210-call burst at concurrency=8 completed in
    # 22.4s with 0 errors, vs. ~151s serial).
    assert cfg["concurrency"] == 8


def test_provider_call_config_azure_concurrency_env_override(monkeypatch):
    """AZURE_OPENAI_CONCURRENCY=1 must be able to reproduce the original
    fully-serial behavior -- the required "configuration switch"."""
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-azure-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_CONCURRENCY", "1")

    cfg = _provider_call_config("azure")
    assert cfg["concurrency"] == 1


def test_get_openai_client_is_cached_and_reused(monkeypatch):
    """Regression test for the Azure latency diagnostic: _call_openai() used
    to construct a brand-new openai.OpenAI() client (fresh TCP+TLS
    connection) on every single pairwise call -- up to 210x per query.
    _get_openai_client() must return the same client instance for the same
    (api_key, base_url), so the underlying HTTP connection pool is reused."""
    import rerankers.llm_pairwise as llm_pairwise

    llm_pairwise._openai_client_cache.clear()

    cfg_a1 = llm_pairwise.PairwiseConfig(api_key="key-a", base_url="https://a.example.com/v1")
    cfg_a2 = llm_pairwise.PairwiseConfig(api_key="key-a", base_url="https://a.example.com/v1")
    cfg_b = llm_pairwise.PairwiseConfig(api_key="key-b", base_url="https://b.example.com/v1")

    client_a1 = llm_pairwise._get_openai_client(cfg_a1)
    client_a2 = llm_pairwise._get_openai_client(cfg_a2)
    client_b = llm_pairwise._get_openai_client(cfg_b)

    assert client_a1 is client_a2, "same (api_key, base_url) must reuse the cached client"
    assert client_a1 is not client_b, "different (api_key, base_url) must get distinct clients"


def test_collect_all_pairs_concurrency_default_is_serial(monkeypatch):
    """concurrency=1 (the default for every provider that doesn't opt in)
    must behave exactly as before: a plain sequential loop, not the
    ThreadPoolExecutor path."""
    import rerankers.llm_pairwise as llm_pairwise

    call_order = []

    def fake_call_llm(prompt, config):
        call_order.append(prompt)
        return "A", None

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)

    config = llm_pairwise.PairwiseConfig(dry_run=False, debias_position=False, concurrency=1)
    candidates = [("d0", "text0"), ("d1", "text1"), ("d2", "text2")]
    pairs, metadata = llm_pairwise.collect_all_pairs("q1", "query text", candidates, config=config)

    assert len(pairs) == 3  # C(3,2)
    assert len(call_order) == 3


def test_collect_all_pairs_concurrency_produces_all_pairs_thread_safely(monkeypatch):
    """concurrency>1 must produce the same complete, uncorrupted set of pair
    outcomes as the serial path -- exercises the _mutation_lock guarding
    stats/budget/detail_sink/cache across threads."""
    import rerankers.llm_pairwise as llm_pairwise

    def fake_call_llm(prompt, config):
        # Deterministic: "A" always wins so we can verify every pair
        # produced a sane, uncorrupted result regardless of thread interleaving.
        return "A", None

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)

    config = llm_pairwise.PairwiseConfig(dry_run=False, debias_position=True, concurrency=6)
    candidates = [(f"d{i}", f"text {i}") for i in range(8)]  # C(8,2) = 28 pairs
    stats = llm_pairwise.LLMCallStats()
    detail_sink: list[dict] = []
    pairs, metadata = llm_pairwise.collect_all_pairs(
        "q1", "query text", candidates, config=config, stats=stats, detail_sink=detail_sink
    )

    assert len(pairs) == 28
    assert all(p is not None for p in pairs)
    # Every pair recorded exactly 2 calls (A-B + B-A debias) with no lost or
    # duplicated stats/detail_sink entries under concurrency.
    assert stats.api_calls == 28 * 2
    assert len(detail_sink) == 28 * 2


def test_collect_all_pairs_concurrency_matches_serial_pair_set(monkeypatch):
    """The *set* of (winner, loser) outcomes must be identical whether run
    serially or concurrently for the same deterministic mock -- concurrency
    must not change which pairs are compared or lose any of them."""
    import rerankers.llm_pairwise as llm_pairwise

    def fake_call_llm(prompt, config):
        return "A", None

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)
    candidates = [(f"d{i}", f"text {i}") for i in range(6)]

    serial_cfg = llm_pairwise.PairwiseConfig(dry_run=False, debias_position=True, concurrency=1)
    serial_pairs, _ = llm_pairwise.collect_all_pairs("q1", "query text", candidates, config=serial_cfg)

    concurrent_cfg = llm_pairwise.PairwiseConfig(dry_run=False, debias_position=True, concurrency=4)
    concurrent_pairs, _ = llm_pairwise.collect_all_pairs("q1", "query text", candidates, config=concurrent_cfg)

    assert sorted(serial_pairs) == sorted(concurrent_pairs)


def test_azure_no_secret_leakage_in_config(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config, detect_llm_providers

    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-azure-super-secret-value")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1")

    cfg = _provider_call_config("azure")
    statuses = detect_llm_providers(["azure"])
    assert "sk-azure-super-secret-value" not in statuses[0].reason
    assert cfg["api_key"] == "sk-azure-super-secret-value"


def test_provider_call_config_cohere_model_and_endpoint_resolution(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key")
    monkeypatch.delenv("COHERE_MODEL", raising=False)
    monkeypatch.delenv("COHERE_BASE_URL", raising=False)
    monkeypatch.delenv("COHERE_CONCURRENCY", raising=False)

    cfg = _provider_call_config("cohere")
    assert cfg["family"] == "openai"
    assert cfg["model"] == "command-r-plus-08-2024"
    assert cfg["base_url"] == "https://api.cohere.ai/compatibility/v1"
    assert cfg["api_key"] == "test-cohere-key"


def test_provider_call_config_cohere_concurrency_default_is_four(monkeypatch):
    """Regression test for the Cohere latency diagnostic: concurrency=8 (the
    value that was safe for Azure) looked clean in an isolated single burst
    but failed catastrophically under sustained back-to-back load against
    Cohere's real per-minute rate limit (130/210 then 210/210 real 429s in
    two consecutive live full-scale bursts). concurrency=4 was validated
    safe across two consecutive back-to-back bursts and must remain the
    default -- this guards against silently reverting to the unsafe value."""
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key")
    monkeypatch.delenv("COHERE_CONCURRENCY", raising=False)

    cfg = _provider_call_config("cohere")
    assert cfg["concurrency"] == 4


def test_provider_call_config_cohere_concurrency_env_override(monkeypatch):
    """COHERE_CONCURRENCY=1 must be able to reproduce the original fully-
    serial behavior -- the required "configuration switch"."""
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config

    monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key")
    monkeypatch.setenv("COHERE_CONCURRENCY", "1")

    cfg = _provider_call_config("cohere")
    assert cfg["concurrency"] == 1


def test_cohere_no_secret_leakage_in_config(monkeypatch):
    from consistency_ranker.failure_mining.llm_runner import _provider_call_config, detect_llm_providers

    monkeypatch.setenv("COHERE_API_KEY", "sk-cohere-super-secret-value")

    cfg = _provider_call_config("cohere")
    statuses = detect_llm_providers(["cohere"])
    assert "sk-cohere-super-secret-value" not in statuses[0].reason
    assert cfg["api_key"] == "sk-cohere-super-secret-value"


def test_collect_all_pairs_cohere_shaped_full_scale_orchestration(monkeypatch):
    """Full 210-call orchestration (15 candidates, matching real production
    query shape) through collect_all_pairs() at Cohere's validated
    concurrency=4, fully mocked -- verifies the shared client-cache +
    concurrency infrastructure (built for Azure, reused here) produces a
    complete, correct, uncorrupted set of pairwise outcomes for Cohere's
    exact configuration shape."""
    import rerankers.llm_pairwise as llm_pairwise

    call_count = {"n": 0}

    def fake_call_llm(prompt, config):
        call_count["n"] += 1
        return "A", None

    monkeypatch.setattr(llm_pairwise, "_call_llm", fake_call_llm)

    config = llm_pairwise.PairwiseConfig(
        provider="openai",
        model="command-r-plus-08-2024",
        api_key="test-cohere-key",
        base_url="https://api.cohere.ai/compatibility/v1",
        dry_run=False,
        debias_position=True,
        concurrency=4,
    )
    candidates = [(f"d{i}", f"doc text {i}") for i in range(15)]  # C(15,2) = 105 pairs
    stats = llm_pairwise.LLMCallStats()
    pairs, metadata = llm_pairwise.collect_all_pairs(
        "q1", "query text", candidates, config=config, stats=stats
    )

    assert len(pairs) == 105
    assert all(p is not None for p in pairs)
    assert call_count["n"] == 210  # 105 pairs x 2 debias directions
    assert stats.api_calls == 210
    assert metadata["n_pairs"] == 105
    assert metadata["n_candidates"] == 15
