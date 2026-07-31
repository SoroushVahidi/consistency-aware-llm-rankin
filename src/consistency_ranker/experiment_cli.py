"""Shared CLI helpers for offline-safe experiment drivers.

These utilities standardize output-directory safety, provenance manifests, and
live-provider gating. They do not encode scientific policy defaults.

**Compatibility note (repo hygiene Stage 5, 2026-07-30):** this module's
``resolve_git_commit``/``file_sha256`` used to duplicate independent
implementations of the same two low-level primitives now defined once in
:mod:`consistency_ranker.provenance` (the canonical module for provenance
primitives). Both functions below are now thin wrappers that delegate the
actual git-subprocess call / hashlib loop to ``provenance``, while preserving
this module's own pre-existing call contracts byte-for-byte (return types,
``None``-for-missing/``"skipped:size=N"``-for-oversized semantics) so that
none of this module's existing callers need to change. ``ensure_output_dir``,
``write_run_manifest``, and ``assert_offline_or_allowed`` have no equivalent
in ``provenance`` and remain fully independent implementations here -- see
each function's own docstring for how it differs from its nearest
``provenance`` counterpart.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from consistency_ranker.provenance import file_sha256 as _canonical_file_sha256
from consistency_ranker.provenance import git_commit_info


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_git_commit(repo_root: Path) -> str | None:
    """Return HEAD SHA when available; None if not a git checkout.

    Compatibility wrapper over :func:`consistency_ranker.provenance.git_commit_info`,
    which performs the actual ``git rev-parse HEAD`` subprocess call. This
    function keeps its own pre-existing ``str | None`` contract (rather than
    ``git_commit_info``'s richer ``{"commit": ..., "dirty": ...}`` dict)
    since callers here only ever wanted the bare commit hash.
    """
    commit = git_commit_info(repo_root)["commit"]
    return commit if commit and commit != "UNKNOWN" else None


def file_sha256(path: Path, *, max_bytes: int | None = 32_000_000) -> str | None:
    """Hash a file for provenance; return None if missing or too large.

    Compatibility wrapper over :func:`consistency_ranker.provenance.file_sha256`,
    which performs the actual hashing. This function adds the size-cap and
    missing-file safety behavior its existing callers depend on -- the
    canonical function has no such cap (it is only ever called internally on
    paths already confirmed to exist via :func:`~consistency_ranker.provenance.hash_paths`),
    so that behavior lives here rather than in the shared primitive.
    """
    if not path.is_file():
        return None
    size = path.stat().st_size
    if max_bytes is not None and size > max_bytes:
        return f"skipped:size={size}"
    return _canonical_file_sha256(path)


def ensure_output_dir(path: Path, *, overwrite: bool = False) -> Path:
    """Create *path* for a fresh run; refuse non-empty existing dirs by default.

    Empty directories are allowed (e.g. caller mkdir then abort). Non-empty
    directories require ``overwrite=True``.

    **Not the same function as**
    ``consistency_ranker.provenance.protect_canonical_output``: this function
    *creates* the directory (``mkdir``), for a script starting a brand-new
    experiment run that should own a fresh output directory. The
    ``provenance`` function never creates anything -- it only guards a
    reproduction workflow against silently overwriting a path that may
    already hold committed canonical evidence. Use this function for a new
    run's output directory; use ``protect_canonical_output`` when
    re-running a reproduction against a path that might already be a
    committed ``reports/...`` directory.
    """
    path = path.resolve()
    if path.exists():
        if not path.is_dir():
            raise FileExistsError(f"Output path exists and is not a directory: {path}")
        contents = list(path.iterdir())
        if contents and not overwrite:
            raise FileExistsError(
                f"Refusing to overwrite non-empty output directory: {path}. "
                "Pass --overwrite to allow this, or choose a new --output-dir."
            )
    else:
        path.mkdir(parents=True, exist_ok=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_run_manifest(
    out_dir: Path,
    *,
    script: str,
    config: Mapping[str, Any],
    repo_root: Path | None = None,
    argv: Sequence[str] | None = None,
    input_hashes: Mapping[str, str | None] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Write ``run_manifest.json`` with config, git commit, and argv."""
    root = repo_root or Path.cwd()
    payload: dict[str, Any] = {
        "script": script,
        "created_utc": utc_stamp(),
        "git_commit": resolve_git_commit(root),
        "argv": list(argv if argv is not None else sys.argv),
        "config": dict(config),
        "input_hashes": dict(input_hashes or {}),
        "python": sys.version.split()[0],
    }
    if extra:
        payload["extra"] = dict(extra)
    out = out_dir / "run_manifest.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return out


def assert_offline_or_allowed(
    *,
    allow_provider_calls: bool,
    dry_run: bool = False,
    cache_only: bool = False,
) -> str:
    """Fail closed unless an explicit offline or live mode is selected.

    Returns the effective mode: ``live``, ``dry_run``, or ``cache_only``.
    """
    if allow_provider_calls:
        if dry_run or cache_only:
            raise SystemExit(
                "Invalid mode combination: --allow-provider-calls cannot be "
                "combined with --dry-run or --cache-only."
            )
        return "live"
    if dry_run:
        return "dry_run"
    if cache_only:
        return "cache_only"
    raise SystemExit(
        "Refusing to run without an explicit mode. Pass one of:\n"
        "  --cache-only              # inventory / analyze existing caches only\n"
        "  --dry-run                 # simulate provider calls (no network)\n"
        "  --allow-provider-calls    # live billed/unbilled provider traffic\n"
    )
