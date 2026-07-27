"""Shared CLI helpers for offline-safe experiment drivers.

These utilities standardize output-directory safety, provenance manifests, and
live-provider gating. They do not encode scientific policy defaults.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_git_commit(repo_root: Path) -> str | None:
    """Return HEAD SHA when available; None if not a git checkout."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.strip() or None


def file_sha256(path: Path, *, max_bytes: int | None = 32_000_000) -> str | None:
    """Hash a file for provenance; return None if missing or too large."""
    if not path.is_file():
        return None
    size = path.stat().st_size
    if max_bytes is not None and size > max_bytes:
        return f"skipped:size={size}"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_output_dir(path: Path, *, overwrite: bool = False) -> Path:
    """Create *path* for a fresh run; refuse non-empty existing dirs by default.

    Empty directories are allowed (e.g. caller mkdir then abort). Non-empty
    directories require ``overwrite=True``.
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
