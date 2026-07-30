"""Tests for scripts/run_secret_scan.py (repo Stage 4, 2026-07-30): the
lightweight tracked+staged-file secret scanner wired into `make secret-scan`
and `make repo-ready`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.run_secret_scan import scan_file  # noqa: E402


def test_repository_currently_has_no_flagged_secrets():
    from scripts.run_secret_scan import run

    result = run()
    assert result["overall_status"] == "PASS", result["findings"]
    assert result["n_files_scanned"] > 100


def test_detects_aws_access_key(tmp_path, monkeypatch):
    import scripts.run_secret_scan as module

    f = tmp_path / "leak.txt"
    f.write_text("aws_key = AKIAABCDEFGHIJKLMNOP")
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    findings = scan_file("leak.txt")
    assert any(fnd["pattern"] == "aws_access_key_id" for fnd in findings)


def test_detects_private_key_header(tmp_path, monkeypatch):
    import scripts.run_secret_scan as module

    f = tmp_path / "key.pem"
    f.write_text("-----BEGIN PRIVATE KEY-----\nMIIBogIBAAJ...\n")
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    findings = scan_file("key.pem")
    assert any(fnd["pattern"] == "private_key_header" for fnd in findings)


def test_detects_generic_quoted_secret_assignment(tmp_path, monkeypatch):
    import scripts.run_secret_scan as module

    f = tmp_path / "config.py"
    f.write_text('api_key = "abcdefghijklmnopqrstuvwxyz123456"\n')
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    findings = scan_file("config.py")
    assert any(fnd["pattern"] == "generic_quoted_secret_assignment" for fnd in findings)


def test_bare_env_var_name_reference_is_not_flagged(tmp_path, monkeypatch):
    import scripts.run_secret_scan as module

    f = tmp_path / "config.py"
    f.write_text('api_key = os.environ["OPENAI_API_KEY"]\n')
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    findings = scan_file("config.py")
    assert findings == []


def test_skipped_binary_suffix_is_never_scanned(tmp_path, monkeypatch):
    import scripts.run_secret_scan as module

    f = tmp_path / "image.png"
    f.write_bytes(b"AKIAABCDEFGHIJKLMNOP")
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    findings = scan_file("image.png")
    assert findings == []
