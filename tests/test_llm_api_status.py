from __future__ import annotations

from consistency_ranker.utils.llm_api_status import (
    check_gemini,
    check_openai,
    detect_providers,
)


def test_check_openai_without_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

    res = check_openai(probe=False)

    assert res.provider == "openai"
    assert res.env_present is False
    assert res.probe_ok is False


def test_check_gemini_without_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    res = check_gemini(probe=False)

    assert res.provider == "gemini"
    assert res.env_present is False
    assert res.probe_ok is False


def test_detect_providers_returns_both(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    res = detect_providers(probe=False)

    assert set(res.keys()) == {"openai", "gemini"}
    assert all(r.provider in {"openai", "gemini"} for r in res.values())
