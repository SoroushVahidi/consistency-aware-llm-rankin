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
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    res = check_gemini(probe=False)

    assert res.provider == "gemini"
    assert res.env_present is False
    assert res.probe_ok is False


def test_check_gemini_vertex_mode_detected_without_api_key(monkeypatch):
    """No GEMINI_API_KEY/GOOGLE_API_KEY, but Vertex AI env + ADC are usable."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")

    class _FakeCreds:
        pass

    monkeypatch.setattr(
        "google.auth.default", lambda: (_FakeCreds(), "test-project-123"), raising=False
    )

    res = check_gemini(probe=False)

    assert res.provider == "gemini"
    assert res.env_present is True
    # probe=False never calls the network-dependent branch.
    assert res.probe_ok is False


def test_check_gemini_vertex_mode_missing_project_falls_back_unavailable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("VERTEXAI_PROJECT", raising=False)

    def _raise():
        raise RuntimeError("no ADC available")

    monkeypatch.setattr("google.auth.default", lambda: _raise(), raising=False)

    res = check_gemini(probe=False)

    assert res.env_present is False


def test_check_gemini_no_secret_leakage_in_message(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-super-secret-value-xyz")

    res = check_gemini(probe=False)

    assert "sk-super-secret-value-xyz" not in res.message
    assert res.details is None or "sk-super-secret-value-xyz" not in str(res.details)


def test_detect_providers_returns_both(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    res = detect_providers(probe=False)

    assert set(res.keys()) == {"openai", "gemini"}
    assert all(r.provider in {"openai", "gemini"} for r in res.values())
