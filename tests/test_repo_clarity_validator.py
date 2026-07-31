"""Tests for scripts/validate_repo_clarity.py.

Includes regression tests for two false positives found while building the
validator (documented in the source): a "historical" adjective used mid-
paragraph inside an unrelated blockquote (docs/REPRODUCTION_Q1.md), and a
negated CI-status claim ("do not claim GitHub CI is green" is not a claim
that CI is green).
"""

from __future__ import annotations

import scripts.validate_repo_clarity as clarity


def test_module_imports():
    import scripts.validate_repo_clarity  # noqa: F401


def test_required_docs_currently_all_exist():
    assert clarity.check_required_docs_exist() == []


def test_readme_currently_links_to_all_required_docs():
    assert clarity.check_readme_links_to_required_docs() == []


def test_project_status_files_currently_cross_reference():
    assert clarity.check_project_status_cross_reference() == []


def test_superseded_banners_currently_all_name_a_replacement():
    assert clarity.check_superseded_docs_name_a_replacement() == []


def test_no_ci_green_claims_currently():
    assert clarity.check_no_ci_green_claims() == []


def test_cloud_validation_tiers_currently_match_cli():
    assert clarity.check_cloud_validation_tiers_match_cli() == []


def test_main_returns_zero_when_all_checks_pass():
    assert clarity.main() == 0


def test_banner_marker_does_not_match_mid_paragraph_historical_adjective():
    """Regression test for the docs/REPRODUCTION_Q1.md false positive: a
    blockquote block that uses '**historical**' as a plain adjective
    mid-paragraph (not opening a new banner paragraph) must not match."""
    text = (
        "> **Purpose:** Exact commands to reproduce results.\n"
        "> Canonical evidence lives elsewhere. This guide rebuilds the\n"
        "> **historical** Q1 journal bundle from an earlier package.\n"
    )
    assert list(clarity._BANNER_MARKER.finditer(text)) == []


def test_banner_marker_matches_a_real_opening_banner():
    text = "\n\n> **SUPERSEDED (as of 2026-07-28).** See docs/CONTRIBUTIONS.md.\n"
    matches = list(clarity._BANNER_MARKER.finditer(text))
    assert len(matches) == 1


def test_ci_green_check_ignores_negated_claims(tmp_path, monkeypatch):
    """Regression test for the docs/EXPERIMENTS.md false positive: 'do not
    claim GitHub CI is green' must not be flagged as claiming it is green."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "EXAMPLE.md").write_text(
        "Do not read a red/absent check as a code signal, and do not claim "
        "GitHub CI is green -- it currently cannot run at all."
    )
    monkeypatch.setattr(clarity, "_REPO_ROOT", tmp_path)
    assert clarity.check_no_ci_green_claims() == []


def test_ci_green_check_flags_an_actual_unqualified_claim(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "EXAMPLE.md").write_text("Great news: GitHub Actions is green across the board.")
    monkeypatch.setattr(clarity, "_REPO_ROOT", tmp_path)
    errors = clarity.check_no_ci_green_claims()
    assert len(errors) == 1
    assert "EXAMPLE.md" in errors[0]


def test_tier_mismatch_is_detected(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_cloud_validation.py").write_text(
        'parser.add_argument("--tier", choices=["core", "solver", "real-data", "all"], '
        'default="core")\n'
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "EXAMPLE.md").write_text(
        "Run `python scripts/run_cloud_validation.py --tier basic`."
    )
    monkeypatch.setattr(clarity, "_REPO_ROOT", tmp_path)
    errors = clarity.check_cloud_validation_tiers_match_cli()
    assert len(errors) == 1
    assert "basic" in errors[0]
