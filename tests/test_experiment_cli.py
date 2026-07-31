"""Tests for consistency_ranker.experiment_cli (repo hygiene Stage 5, 2026-07-30).

This module's ``resolve_git_commit``/``file_sha256`` are now compatibility
wrappers over the canonical primitives in ``consistency_ranker.provenance``
(``git_commit_info``/``file_sha256``). These tests exist specifically to
prove the consolidation did not change this module's pre-existing public
behavior for its 11 real callers: identical hash values, identical
``str | None`` / ``"skipped:size=N"`` contracts, identical git-metadata
behavior inside and outside a git checkout, and unchanged manifest-writing
and output-directory-safety behavior.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from consistency_ranker import experiment_cli as ec
from consistency_ranker import provenance as pv

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# resolve_git_commit: compatibility wrapper over provenance.git_commit_info
# ---------------------------------------------------------------------------


def test_resolve_git_commit_matches_canonical_git_commit_info_inside_repo():
    """Both the compatibility wrapper and the canonical primitive must agree
    on HEAD's SHA for a real git checkout."""
    wrapped = ec.resolve_git_commit(REPO_ROOT)
    canonical = pv.git_commit_info(REPO_ROOT)["commit"]
    assert wrapped == canonical
    assert wrapped is not None
    assert len(wrapped) == 40


def test_resolve_git_commit_returns_none_outside_a_git_repo(tmp_path):
    """Pre-existing contract: None (not an exception, not 'UNKNOWN') when
    repo_root is not inside a git checkout."""
    assert ec.resolve_git_commit(tmp_path) is None
    # Cross-check against the canonical primitive's own sentinel, to make
    # the relationship between the two explicit rather than just asserting
    # the wrapper's output in isolation.
    assert pv.git_commit_info(tmp_path) == {"commit": "UNKNOWN", "dirty": None}


def test_resolve_git_commit_is_pure_string_never_a_dict():
    """Compatibility guarantee: unlike git_commit_info, this always returns
    a bare string or None -- never the richer {"commit":..., "dirty":...}
    dict, since existing callers only ever destructured a bare string."""
    result = ec.resolve_git_commit(REPO_ROOT)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# file_sha256: compatibility wrapper over provenance.file_sha256
# ---------------------------------------------------------------------------


def test_file_sha256_matches_canonical_hash_for_identical_content(tmp_path):
    """The exact hash value this module returns must be byte-identical to
    the canonical provenance.file_sha256, for any file small enough that
    both would actually hash it (i.e. under the size cap)."""
    f = tmp_path / "content.txt"
    f.write_text("consolidation must not change hash values")

    wrapped = ec.file_sha256(f)
    canonical = pv.file_sha256(f)
    assert wrapped == canonical
    assert wrapped is not None
    assert len(wrapped) == 64  # hex sha256


def test_file_sha256_returns_none_for_missing_file(tmp_path):
    """Pre-existing safety behavior, not present in the canonical primitive
    (which assumes the file exists) -- must still hold after delegation."""
    missing = tmp_path / "does_not_exist.txt"
    assert ec.file_sha256(missing) is None


def test_file_sha256_returns_skip_sentinel_for_oversized_file(tmp_path):
    """Pre-existing safety behavior: a file above max_bytes is not hashed at
    all (avoids reading arbitrarily large files during manifest writing),
    reported via a 'skipped:size=N' sentinel string rather than a hash."""
    f = tmp_path / "big.bin"
    f.write_bytes(b"0" * 2048)
    result = ec.file_sha256(f, max_bytes=1024)
    assert result == "skipped:size=2048"


def test_file_sha256_default_cap_still_hashes_small_files(tmp_path):
    """The default max_bytes (32MB) must not affect ordinary small files."""
    f = tmp_path / "small.txt"
    f.write_text("small")
    assert ec.file_sha256(f) == pv.file_sha256(f)


def test_file_sha256_deterministic_and_content_sensitive(tmp_path):
    f1, f2, f3 = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    f1.write_text("hello")
    f2.write_text("hello")
    f3.write_text("world")
    assert ec.file_sha256(f1) == ec.file_sha256(f2)
    assert ec.file_sha256(f1) != ec.file_sha256(f3)


# ---------------------------------------------------------------------------
# write_run_manifest: unchanged schema, deterministic serialization, no
# machine-specific absolute paths leaking into the written manifest
# ---------------------------------------------------------------------------


def test_write_run_manifest_schema_unchanged(tmp_path):
    """Locks the manifest's field set and types -- this schema predates the
    consolidation and must not silently drift."""
    out = ec.write_run_manifest(
        tmp_path,
        script="tests/test_experiment_cli.py",
        config={"alpha": 0.05},
        repo_root=REPO_ROOT,
        argv=["prog", "--flag"],
        input_hashes={"data": "deadbeef"},
        extra={"note": "x"},
    )
    payload = json.loads(out.read_text())
    assert set(payload) == {
        "script", "created_utc", "git_commit", "argv", "config",
        "input_hashes", "python", "extra",
    }
    assert payload["script"] == "tests/test_experiment_cli.py"
    assert payload["config"] == {"alpha": 0.05}
    assert payload["argv"] == ["prog", "--flag"]
    assert payload["input_hashes"] == {"data": "deadbeef"}
    assert payload["extra"] == {"note": "x"}
    assert payload["git_commit"] == ec.resolve_git_commit(REPO_ROOT)


def test_write_run_manifest_omits_extra_key_when_not_provided(tmp_path):
    """Pre-existing behavior: 'extra' is only present in the payload when
    the caller actually passes something -- must not regress to always
    including an empty 'extra' key."""
    out = ec.write_run_manifest(
        tmp_path, script="s", config={}, repo_root=REPO_ROOT,
    )
    payload = json.loads(out.read_text())
    assert "extra" not in payload


def test_write_run_manifest_serialization_is_deterministic(tmp_path):
    """Two manifests written back-to-back for the same inputs must produce
    byte-identical JSON except for the created_utc timestamp field."""
    kwargs = dict(
        script="s", config={"a": 1, "b": 2}, repo_root=REPO_ROOT,
        argv=["x"], input_hashes={"k": "v"},
    )
    (tmp_path / "run1").mkdir()
    (tmp_path / "run2").mkdir()
    out1 = ec.write_run_manifest(tmp_path / "run1", **kwargs)
    out2 = ec.write_run_manifest(tmp_path / "run2", **kwargs)
    p1, p2 = json.loads(out1.read_text()), json.loads(out2.read_text())
    p1.pop("created_utc")
    p2.pop("created_utc")
    assert p1 == p2


def test_write_run_manifest_contains_no_machine_specific_absolute_path(tmp_path):
    """The manifest's own fields (git_commit, python version, script name)
    must never contain this machine's absolute repo path or home directory
    -- config/argv are caller-controlled and out of scope here, but the
    fields this function itself derives must be portable."""
    out = ec.write_run_manifest(
        tmp_path, script="tests/test_experiment_cli.py", config={},
        repo_root=REPO_ROOT, argv=["prog"],
    )
    payload = json.loads(out.read_text())
    assert "/home/" not in payload["script"]
    assert "/home/" not in (payload["git_commit"] or "")
    assert "/home/" not in payload["python"]


# ---------------------------------------------------------------------------
# ensure_output_dir: collision/overwrite protection (unchanged, independent
# of the provenance-primitive consolidation)
# ---------------------------------------------------------------------------


def test_ensure_output_dir_creates_fresh_directory(tmp_path):
    target = tmp_path / "fresh"
    result = ec.ensure_output_dir(target)
    assert result == target.resolve()
    assert target.is_dir()


def test_ensure_output_dir_allows_pre_existing_empty_directory(tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    ec.ensure_output_dir(target)  # must not raise


def test_ensure_output_dir_refuses_nonempty_directory_by_default(tmp_path):
    target = tmp_path / "nonempty"
    target.mkdir()
    (target / "existing.txt").write_text("x")
    with pytest.raises(FileExistsError):
        ec.ensure_output_dir(target)


def test_ensure_output_dir_allows_nonempty_directory_when_overwrite_true(tmp_path):
    target = tmp_path / "nonempty"
    target.mkdir()
    (target / "existing.txt").write_text("x")
    ec.ensure_output_dir(target, overwrite=True)  # must not raise


def test_ensure_output_dir_refuses_path_that_is_a_file(tmp_path):
    target = tmp_path / "im_a_file"
    target.write_text("x")
    with pytest.raises(FileExistsError):
        ec.ensure_output_dir(target)


# ---------------------------------------------------------------------------
# Fresh-process import check: this module must still import cleanly on its
# own, with no import-order dependency on anything importing it first.
# ---------------------------------------------------------------------------


def test_experiment_cli_imports_cleanly_in_a_fresh_process():
    result = subprocess.run(
        [sys.executable, "-c", "import consistency_ranker.experiment_cli"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
