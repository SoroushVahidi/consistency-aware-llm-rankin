"""Tests for scripts/check_active_portability.py."""

from __future__ import annotations

from pathlib import Path

import scripts.check_active_portability as cap


def test_detects_user_specific_path_in_supplied_file(tmp_path: Path) -> None:
    path = tmp_path / "script.py"
    pattern = "/home/" + "soroush"
    path.write_text(f'ROOT = "{pattern}/project"\n', encoding="utf-8")

    findings = cap.scan_active_files([path])

    assert findings == [(path, 1, pattern)]


def test_current_active_files_are_portable() -> None:
    assert cap.scan_active_files() == []
