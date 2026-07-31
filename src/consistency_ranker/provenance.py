"""
Reusable provenance-metadata collection and canonical-output protection.

Repo Stage 4 (2026-07-30): every canonical analysis workflow in this
repository (the IR evidence audit, the real-LLM clustered re-analysis) wrote
its own ad-hoc, partial reproducibility manifest, if it wrote one at all.
This module factors out one canonical schema (see
``reports/repo_reproducibility_stage4_20260730T031306Z/provenance_metadata_schema.md``
for the human-readable description) plus a guard against silently
overwriting a committed canonical output directory.

**This module is the canonical home for the repository's low-level
provenance primitives** (:func:`file_sha256`, :func:`git_commit_info`,
:func:`hash_paths`). :mod:`consistency_ranker.experiment_cli` -- an older,
still-supported sibling module used by earlier experiment scripts --
delegates its equivalent ``file_sha256``/``resolve_git_commit`` helpers to
the primitives here (added in repo hygiene Stage 5, 2026-07-30) rather than
duplicating the hashing/subprocess logic a second time; see that module's
docstring for the compatibility-wrapper details. The two modules'
higher-level manifest functions (:func:`collect_provenance` here vs.
``write_run_manifest`` there) intentionally keep their own distinct, already
call-site-committed schemas -- neither is "more canonical" than the other at
that level, only the shared low-level primitives were unified.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class CanonicalOutputExistsError(RuntimeError):
    """Raised by :func:`protect_canonical_output` when a target path already
    has content and the caller did not opt in to overwriting it."""


def git_commit_info(repo_root: Path = _REPO_ROOT) -> dict[str, Any]:
    """Return the current git commit hash and dirty-worktree state.

    Returns ``{"commit": "UNKNOWN", "dirty": None}`` if ``repo_root`` is not
    inside a git repository (e.g. a source archive with no ``.git``) rather
    than raising, since provenance collection must not itself become a new
    failure mode for reproduction.
    """
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        return {"commit": commit, "dirty": bool(status.strip())}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": "UNKNOWN", "dirty": None}


def dependency_versions(package_names: list[str]) -> dict[str, str]:
    """Return installed version strings for the given distribution names.

    Missing packages are reported as ``"NOT_INSTALLED"`` rather than raising,
    since some canonical workflows depend on optional extras (e.g.
    ``PySCIPOpt``) that are legitimately absent in a minimal environment.
    """
    versions: dict[str, str] = {}
    for name in package_names:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def solver_version() -> str:
    """Return the installed PySCIPOpt version, or ``"NOT_INSTALLED"``.

    Never raises: provenance collection must succeed even for workflows that
    do not use the exact-repair solver at all.
    """
    from consistency_ranker.mwfas_solver import verify_canonical_solver_version

    try:
        return verify_canonical_solver_version(allow_mismatch=True)
    except Exception:
        return "NOT_INSTALLED"


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's contents."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_key(path: Path) -> str:
    """Return a stable, portable manifest key for ``path``.

    Repo Stage 4A (2026-07-30): a caller (scripts/run_real_llm_clustered_reanalysis.py)
    passed already-absolute ``Path`` objects (built from a module-level
    ``_REPO_ROOT``) as ``input_paths``, while its ``output_paths`` were
    built as repo-relative ``Path`` objects -- ``hash_paths()`` just did
    ``str(f)`` on whatever it was given, so the committed manifest ended up
    with this machine's home directory baked into every input key while
    output keys stayed relative. Normalizing here, once, for every caller,
    is more robust than fixing each call site: any path that resolves to
    somewhere inside this repository is always keyed by its POSIX-style
    path relative to the repo root, regardless of whether the caller passed
    a relative or absolute ``Path`` -- so committed manifests stay portable
    across clones and machines. A path resolving to outside the repository
    (e.g. a pytest ``tmp_path`` fixture) falls back to its resolved absolute
    form, since no repo-relative form exists for it.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def hash_paths(paths: list[Path]) -> dict[str, str]:
    """Return ``{manifest_key: sha256_hex}`` for each input (see :func:`_manifest_key`).

    Directories are hashed by walking their files in sorted order and hashing
    each file individually (keyed by its own path), so a manifest entry for a
    directory expands to one entry per contained file rather than a single
    combined digest -- this keeps individual-file provenance inspectable.
    """
    hashes: dict[str, str] = {}
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    hashes[_manifest_key(f)] = file_sha256(f)
        elif p.is_file():
            hashes[_manifest_key(p)] = file_sha256(p)
    return hashes


def collect_provenance(
    *,
    generator_script: str,
    seeds: dict[str, int] | None = None,
    independence_cluster_count: int | None = None,
    input_paths: list[Path] | None = None,
    config: dict[str, Any] | None = None,
    output_paths: list[Path] | None = None,
    dependency_names: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect one canonical provenance record for a reproducible workflow.

    ``output_paths`` are only meaningfully hashed if they already exist at
    call time (e.g. when re-collecting provenance for a completed run, or
    diffing against a prior run) -- for a fresh run in progress, pass
    ``output_paths=None`` and hash the outputs in a second pass after they
    are written.
    """
    default_deps = [
        "numpy", "scipy", "pandas", "scikit-learn", "networkx",
    ]
    dep_names = dependency_names if dependency_names is not None else default_deps

    return {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator_script": generator_script,
        "git": git_commit_info(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "dependency_versions": dependency_versions(dep_names),
        "solver_version": solver_version(),
        "seeds": seeds or {},
        "independence_cluster_count": independence_cluster_count,
        "config": config or {},
        "input_file_hashes": hash_paths(input_paths) if input_paths else {},
        "output_file_hashes": hash_paths(output_paths) if output_paths else {},
        "extra": extra or {},
    }


def protect_canonical_output(path: Path, *, allow_overwrite: bool = False) -> None:
    """Refuse to silently clobber an existing canonical output directory/file.

    A reproduction command should write to a fresh or explicitly
    caller-chosen location by default; overwriting a committed canonical
    ``reports/...`` directory must always be an explicit, opt-in action.

    Raises :class:`CanonicalOutputExistsError` if ``path`` exists and already
    has content (a non-empty directory, or any file) and ``allow_overwrite``
    is ``False``. Does nothing if ``path`` does not exist, or is an empty
    directory (a location the caller has already reserved but not written
    into).

    **Not the same function as** ``consistency_ranker.experiment_cli.ensure_output_dir``:
    that function *creates* a fresh output directory for a new experiment
    run (and also refuses a non-empty existing one). This function never
    creates anything -- it is a pure guard for reproduction workflows that
    write into a path that may already hold committed canonical evidence,
    where directory creation is either unnecessary (the path already exists)
    or the caller's own responsibility. Use ``ensure_output_dir`` when
    starting a brand-new run that should own its output directory; use this
    function when re-running a reproduction against a path that might
    already be a committed, canonical ``reports/...`` directory.
    """
    if not path.exists():
        return
    if path.is_dir():
        if any(path.iterdir()):
            if not allow_overwrite:
                raise CanonicalOutputExistsError(
                    f"Refusing to write into non-empty canonical output directory "
                    f"'{path}' -- pass allow_overwrite=True (or the corresponding "
                    f"--allow-overwrite CLI flag) if you intend to replace its "
                    f"contents, or choose a new output directory to avoid clobbering "
                    f"committed canonical evidence."
                )
    else:
        if not allow_overwrite:
            raise CanonicalOutputExistsError(
                f"Refusing to overwrite existing canonical output file '{path}' -- "
                f"pass allow_overwrite=True (or the corresponding --allow-overwrite "
                f"CLI flag) if you intend to replace it, or choose a new output path."
            )
