"""Tests for the Stage 4 offline-validation tooling: the canonical-evidence
manifest validator, the report-link validator, and the orchestrating
offline validation workflow script. These wrap real repository state
(the actual canonical_evidence_inventory.csv and reports/README.md etc.)
so a real regression (a moved file, a renamed script, a broken link) would
fail these tests, not just synthetic fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts import (  # noqa: E402
    validate_canonical_evidence_manifest,
    validate_report_links,
)
from scripts.validate_canonical_evidence_manifest import (  # noqa: E402
    extract_path_candidates,
)


def test_extract_path_candidates_finds_prefixed_paths():
    assert extract_path_candidates("scripts/foo.py") == ["scripts/foo.py"]


def test_extract_path_candidates_strips_parenthetical_prose():
    candidates = extract_path_candidates("scripts/foo.py (does the thing)")
    assert candidates == ["scripts/foo.py"]


def test_extract_path_candidates_handles_semicolon_lists():
    candidates = extract_path_candidates("scripts/a.py; scripts/b.py")
    assert candidates == ["scripts/a.py", "scripts/b.py"]


def test_extract_path_candidates_expands_braces():
    candidates = extract_path_candidates("reports/x/{a,b}.csv")
    assert candidates == ["reports/x/a.csv", "reports/x/b.csv"]


def test_extract_path_candidates_returns_empty_for_pure_prose():
    assert extract_path_candidates("(see that report's own scripts directory)") == []


def test_extract_path_candidates_resolves_known_alias():
    assert extract_path_candidates("main.tex Sec.4.1") == [
        "papers/JDIQ_2026/manuscript/main.tex"
    ]


def test_canonical_evidence_manifest_currently_passes():
    result = validate_canonical_evidence_manifest.run()
    assert result["overall_status"] == "PASS", result
    assert result["n_rows_checked"] >= 17
    assert result["n_rows_with_missing_paths"] == 0


def test_report_links_currently_all_resolve():
    result = validate_report_links.run(validate_report_links.DEFAULT_FILES)
    assert result["overall_status"] == "PASS", result
    assert result["n_files_with_issues"] == 0


def test_report_link_extraction_ignores_external_and_anchor_links():
    text = (
        "[real](reports/README.md) "
        "[external](https://example.com/x) "
        "[anchor](#section) "
        "[mailto](mailto:a@b.com)"
    )
    links = validate_report_links.extract_local_links(text)
    assert links == ["reports/README.md"]


def test_report_link_check_file_detects_broken_link(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("[broken](does/not/exist.csv)")
    result = validate_report_links.check_file(doc)
    assert result["status"] == "BROKEN_LINKS"
    assert result["n_broken"] == 1


def test_claim_evidence_registry_currently_passes(capsys):
    from scripts import validate_claim_evidence_registry

    exit_code = validate_claim_evidence_registry.main()
    captured = capsys.readouterr()
    assert exit_code == 0, captured.out
    assert "OK:" in captured.out
