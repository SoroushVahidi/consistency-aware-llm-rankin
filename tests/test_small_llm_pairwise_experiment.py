from __future__ import annotations

from pathlib import Path

from consistency_ranker.utils.llm_api_status import ProviderProbeResult
from scripts.run_small_llm_pairwise_experiment import build_parser, main


def test_parser_defaults_small_experiment():
    parser = build_parser()
    args = parser.parse_args([])

    assert args.dataset == "scidocs"
    assert args.provider == "auto"
    assert args.max_queries == 20
    assert args.top_k == 10


def test_main_stops_cleanly_when_no_provider(monkeypatch, tmp_path: Path):
    fake_status = {
        "openai": ProviderProbeResult(
            provider="openai",
            env_present=False,
            import_ok=True,
            probe_ok=False,
            message="OPENAI_API_KEY missing",
            details=None,
        ),
        "gemini": ProviderProbeResult(
            provider="gemini",
            env_present=False,
            import_ok=True,
            probe_ok=False,
            message="GEMINI_API_KEY missing",
            details=None,
        ),
    }

    monkeypatch.setattr(
        "scripts.run_small_llm_pairwise_experiment.detect_providers",
        lambda probe=False: fake_status,
    )

    rc = main(["--provider", "auto", "--output-dir", str(tmp_path)])

    assert rc == 1
    report = (tmp_path / "capability_report.json").read_text(encoding="utf-8")
    assert "selected_provider" in report


def test_capability_report_never_contains_secret_literal(tmp_path: Path):
    secret = "sk-test-1234567890"
    statuses = {
        "openai": ProviderProbeResult(
            provider="openai",
            env_present=True,
            import_ok=True,
            probe_ok=False,
            message="env present, import ok",
            details={"note": "safe"},
        )
    }
    probes = {
        "openai": {
            "model": "gpt-4o-mini",
            "ok": False,
            "message": "auth failed",
        }
    }

    from scripts.run_small_llm_pairwise_experiment import _write_capability_report

    _write_capability_report(tmp_path, statuses, probes, selected=None)

    md = (tmp_path / "capability_report.md").read_text(encoding="utf-8")
    js = (tmp_path / "capability_report.json").read_text(encoding="utf-8")

    assert secret not in md
    assert secret not in js
