"""
Tests for scripts/check_repo_ready.py
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Import helper checks
# ---------------------------------------------------------------------------


def test_check_repo_ready_imports():
    """The module can be imported without errors."""
    import scripts.check_repo_ready as crr  # noqa: F401


def test_ok_warn_fail_accumulate():
    """_ok / _warn / _fail append entries to _results."""
    import scripts.check_repo_ready as crr

    # Reset shared state before testing
    original = crr._results[:]
    crr._results.clear()

    crr._ok("cat_a", "all good")
    crr._warn("cat_b", "mild concern")
    crr._fail("cat_c", "broken")

    assert ("OK", "cat_a", "all good") in crr._results
    assert ("WARN", "cat_b", "mild concern") in crr._results
    assert ("FAIL", "cat_c", "broken") in crr._results

    # Restore
    crr._results.clear()
    crr._results.extend(original)


def test_check_package_import_succeeds():
    """check_package_import records at least one OK for consistency_ranker."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()

    crr.check_package_import()

    statuses = {r[0] for r in crr._results}
    assert "OK" in statuses, "Expected at least one OK from package import check"

    crr._results.clear()
    crr._results.extend(original)


def test_check_key_source_files_no_failures():
    """check_key_source_files should record no failures in a correctly installed repo."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()

    crr.check_key_source_files()

    failures = [r for r in crr._results if r[0] == "FAIL"]
    assert failures == [], f"Unexpected source file failures: {failures}"

    crr._results.clear()
    crr._results.extend(original)


def test_check_committed_tables_reads_real_data():
    """check_committed_tables should find and read the committed result tables."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()

    crr.check_committed_tables()

    failures = [r for r in crr._results if r[0] == "FAIL"]
    assert failures == [], f"Unexpected committed table failures: {failures}"

    ok_entries = [r for r in crr._results if r[0] == "OK"]
    # At least the pre-committed paper_package tables should be found
    assert len(ok_entries) > 0, "Expected at least one OK for committed tables"

    crr._results.clear()
    crr._results.extend(original)


def test_check_output_directories_creates_missing(tmp_path: Path, monkeypatch):
    """check_output_directories should create a missing directory without error."""
    import scripts.check_repo_ready as crr

    # Patch REPO_ROOT to a tmp directory so we don't create dirs in the real repo
    monkeypatch.setattr(crr, "REPO_ROOT", tmp_path)

    original = crr._results[:]
    crr._results.clear()

    crr.check_output_directories()

    failures = [r for r in crr._results if r[0] == "FAIL"]
    assert failures == [], f"Unexpected directory failures: {failures}"

    crr._results.clear()
    crr._results.extend(original)


def test_print_report_exit_code_on_failure():
    """print_report returns 1 when there are FAIL entries."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()
    crr._results.append(("FAIL", "test", "something broke"))

    rc = crr.print_report(strict=False)
    assert rc == 1

    crr._results.clear()
    crr._results.extend(original)


def test_print_report_exit_code_ok():
    """print_report returns 0 when there are only OK entries."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()
    crr._results.append(("OK", "test", "everything fine"))

    rc = crr.print_report(strict=False)
    assert rc == 0

    crr._results.clear()
    crr._results.extend(original)


def test_print_report_strict_warns_become_failures():
    """print_report returns 1 in strict mode when there are only WARN entries."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()
    crr._results.append(("WARN", "test", "mild concern"))

    rc = crr.print_report(strict=True)
    assert rc == 1

    crr._results.clear()
    crr._results.extend(original)


def test_main_returns_zero():
    """main() returns 0 in the correctly installed repo (warnings are not failures)."""
    import scripts.check_repo_ready as crr

    original = crr._results[:]
    crr._results.clear()

    rc = crr.main([])
    assert rc == 0, f"check_repo_ready.main() returned {rc} (expected 0)"

    crr._results.clear()
    crr._results.extend(original)
