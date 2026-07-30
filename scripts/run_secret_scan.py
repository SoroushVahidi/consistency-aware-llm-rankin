"""
run_secret_scan.py
=====================
Repo Stage 4 (2026-07-30): a lightweight, dependency-free secret scanner
for CI and local use (`make secret-scan`). Scans every git-tracked file
plus any currently-staged file (so a file about to be committed for the
first time is covered too) for a small set of well-known secret-shaped
patterns (cloud provider keys, private key headers, common LLM-provider API
key formats, generic quoted-literal key/token/secret assignments).

This is a pattern-matching heuristic, not a guarantee: it can produce false
positives (a synthetic test fixture that happens to look key-shaped) and
cannot catch secrets in a format it doesn't recognize. Treat a PASS as "no
obvious committed secret found," not "this repository has no secrets."
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# (pattern_name, compiled regex). Patterns require the matched span to look
# like a real credential (fixed prefix + long random-looking suffix, or a
# quoted literal assigned to a key/secret/token/password-named variable) --
# bare environment-variable *names* like `OPENAI_API_KEY` used without a
# literal value are deliberately not flagged.
_PATTERNS = [
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_header", re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    (
        "generic_quoted_secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*"
            r"['\"]([A-Za-z0-9_\-]{20,})['\"]"
        ),
    ),
]

# Files/directories never worth scanning (large binary/data, or this
# script's own pattern definitions, which would trivially self-match).
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".npy", ".npz", ".pyc",
    ".parquet", ".ipynb",
}
_SKIP_PATHS = {
    "scripts/run_secret_scan.py",
    # This scanner's own test fixtures are synthetic secret-shaped strings
    # (a fake AWS key, a fake generic API-key assignment) written directly
    # into the test file's source to prove scan_file() detects them --
    # scanning tests/test_secret_scan.py itself would self-match those
    # fixtures and fail the whole-repo PASS assertion, exactly analogous to
    # why this module's own pattern definitions above are excluded.
    "tests/test_secret_scan.py",
}


def _git_tracked_and_staged_files() -> list[str]:
    tracked = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    staged = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return sorted(set(tracked) | set(staged))


def scan_file(rel_path: str) -> list[dict]:
    path = _REPO_ROOT / rel_path
    if not path.exists() or path.suffix.lower() in _SKIP_SUFFIXES or rel_path in _SKIP_PATHS:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable; not a text-secret risk in the patterns above

    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append({
                    "file": rel_path,
                    "line": line_no,
                    "pattern": pattern_name,
                })
    return findings


def run() -> dict:
    files = _git_tracked_and_staged_files()
    all_findings = []
    for rel_path in files:
        all_findings.extend(scan_file(rel_path))

    return {
        "overall_status": "PASS" if not all_findings else "FAIL",
        "n_files_scanned": len(files),
        "n_findings": len(all_findings),
        "findings": all_findings,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall_status"] == "PASS" else 1)
