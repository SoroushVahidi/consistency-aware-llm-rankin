"""Tests for consistency_ranker.provenance (repo Stage 4, 2026-07-30):
the shared provenance-metadata collector and canonical-output overwrite
guard used by scripts/run_ir_evidence_audit.py and
scripts/run_real_llm_clustered_reanalysis.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from consistency_ranker.provenance import (
    _REPO_ROOT,
    CanonicalOutputExistsError,
    collect_provenance,
    dependency_versions,
    file_sha256,
    git_commit_info,
    hash_paths,
    protect_canonical_output,
    solver_version,
)


def test_git_commit_info_returns_commit_and_dirty_flag():
    info = git_commit_info()
    assert info["commit"] != "UNKNOWN"
    assert len(info["commit"]) == 40
    assert isinstance(info["dirty"], bool)


def test_git_commit_info_handles_non_repo_gracefully(tmp_path):
    info = git_commit_info(repo_root=tmp_path)
    assert info == {"commit": "UNKNOWN", "dirty": None}


def test_dependency_versions_reports_installed_and_missing():
    versions = dependency_versions(["numpy", "this-package-does-not-exist-xyz"])
    assert versions["numpy"] != "NOT_INSTALLED"
    assert versions["this-package-does-not-exist-xyz"] == "NOT_INSTALLED"


def test_solver_version_never_raises():
    version = solver_version()
    assert isinstance(version, str)
    assert version != ""


def test_file_sha256_is_deterministic_and_content_sensitive(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello")
    f2.write_text("hello")
    f3 = tmp_path / "c.txt"
    f3.write_text("world")

    assert file_sha256(f1) == file_sha256(f2)
    assert file_sha256(f1) != file_sha256(f3)
    assert file_sha256(f1) == file_sha256(f1)


def test_hash_paths_expands_directories_to_per_file_entries(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    (d / "x.csv").write_text("1,2,3")
    (d / "y.csv").write_text("4,5,6")
    single = tmp_path / "solo.txt"
    single.write_text("solo")

    hashes = hash_paths([d, single])
    assert str(d / "x.csv") in hashes
    assert str(d / "y.csv") in hashes
    assert str(single) in hashes
    assert len(hashes) == 3


def test_hash_paths_returns_repo_relative_keys_for_paths_inside_repo():
    """Regression test for the bug where scripts/run_real_llm_clustered_reanalysis.py
    passed already-absolute paths (built from a module-level ``_REPO_ROOT``
    constant) as ``input_paths``, while its ``output_paths`` were built as
    repo-relative paths -- producing a committed manifest with this
    machine's home directory baked into every input key but not every
    output key. Any real, tracked, in-repo file must hash to a
    repo-relative POSIX-style key, never an absolute filesystem path, so a
    committed manifest reads the same on any clone/machine.
    """
    target = _REPO_ROOT / "tests" / "test_provenance.py"
    hashes = hash_paths([target])
    assert len(hashes) == 1
    key = next(iter(hashes))
    assert key == "tests/test_provenance.py"
    assert not Path(key).is_absolute()
    assert str(_REPO_ROOT) not in key


def test_hash_paths_normalizes_absolute_input_paths_under_repo_root():
    """Same guarantee as above, but explicitly passing an absolute Path (as
    scripts/run_real_llm_clustered_reanalysis.py's population.FRONTIER_DIR
    etc. do) -- normalization must happen regardless of whether the caller
    passed a relative or an already-resolved absolute path.
    """
    absolute_target = (_REPO_ROOT / "tests" / "test_provenance.py").resolve()
    assert absolute_target.is_absolute()
    hashes = hash_paths([absolute_target])
    assert list(hashes) == ["tests/test_provenance.py"]


def test_hash_paths_falls_back_to_absolute_for_paths_outside_repo(tmp_path):
    """A path with no repo-relative form (e.g. a pytest tmp_path fixture,
    or any file outside this repository) has nothing to be relative to --
    it must fall back to its resolved absolute path rather than raising.
    """
    external = tmp_path / "outside.txt"
    external.write_text("x")
    hashes = hash_paths([external])
    assert str(external.resolve()) in hashes


def test_collect_provenance_manifest_has_no_absolute_repo_or_home_paths():
    """End-to-end portability check on real in-repo files (not tmp_path):
    a manifest produced by collect_provenance() must not contain this
    machine's absolute repository path, or any '/home/<user>/...'-shaped
    path, anywhere in its serialized form -- the exact defect that shipped
    in reports/real_llm_clustered_reanalysis_20260730T023745Z/reproducibility_manifest.json
    before this fix.
    """
    real_file = _REPO_ROOT / "tests" / "test_provenance.py"
    record = collect_provenance(
        generator_script="tests/test_provenance.py",
        input_paths=[real_file],
        output_paths=[real_file],
    )
    serialized = json.dumps(record, default=str)
    assert str(_REPO_ROOT) not in serialized
    assert "/home/" not in serialized


def test_collect_provenance_has_expected_schema(tmp_path):
    input_file = tmp_path / "in.csv"
    input_file.write_text("a,b\n1,2\n")
    output_file = tmp_path / "out.csv"
    output_file.write_text("a,b\n1,2\n")

    record = collect_provenance(
        generator_script="tests/test_provenance.py",
        seeds={"seed": 42},
        independence_cluster_count=6,
        input_paths=[input_file],
        config={"alpha": 0.05},
        output_paths=[output_file],
    )

    assert record["schema_version"] == "1.0"
    assert record["generator_script"] == "tests/test_provenance.py"
    assert record["seeds"] == {"seed": 42}
    assert record["independence_cluster_count"] == 6
    assert record["config"] == {"alpha": 0.05}
    assert str(input_file) in record["input_file_hashes"]
    assert str(output_file) in record["output_file_hashes"]
    assert "commit" in record["git"]
    assert "numpy" in record["dependency_versions"]
    # Must be JSON-serializable end to end (this is what every canonical
    # workflow actually writes to reproducibility_manifest.json).
    json.dumps(record, default=str)


def test_collect_provenance_defaults_are_empty_not_missing():
    record = collect_provenance(generator_script="tests/test_provenance.py")
    assert record["seeds"] == {}
    assert record["config"] == {}
    assert record["input_file_hashes"] == {}
    assert record["output_file_hashes"] == {}
    assert record["independence_cluster_count"] is None


def test_protect_canonical_output_allows_nonexistent_path(tmp_path):
    target = tmp_path / "does_not_exist_yet"
    protect_canonical_output(target)  # must not raise


def test_protect_canonical_output_allows_empty_directory(tmp_path):
    target = tmp_path / "empty_dir"
    target.mkdir()
    protect_canonical_output(target)  # must not raise


def test_protect_canonical_output_refuses_nonempty_directory_by_default(tmp_path):
    target = tmp_path / "nonempty_dir"
    target.mkdir()
    (target / "existing.csv").write_text("x")

    with pytest.raises(CanonicalOutputExistsError):
        protect_canonical_output(target)


def test_protect_canonical_output_allows_nonempty_directory_when_opted_in(tmp_path):
    target = tmp_path / "nonempty_dir"
    target.mkdir()
    (target / "existing.csv").write_text("x")

    protect_canonical_output(target, allow_overwrite=True)  # must not raise


def test_protect_canonical_output_refuses_existing_file_by_default(tmp_path):
    target = tmp_path / "existing_file.json"
    target.write_text("{}")

    with pytest.raises(CanonicalOutputExistsError):
        protect_canonical_output(target)

    protect_canonical_output(target, allow_overwrite=True)  # must not raise
