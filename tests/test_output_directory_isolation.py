"""
Tests that different preference sources never share the same output directory.

Regression test for the bug where `qrels` and `qrels_flip` outputs were written
to the same ``outputs/<dataset>/`` directory, causing the later run to silently
overwrite the earlier run.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.run_all_real_experiments import _experiment_output_exists, _run_experiment


# ---------------------------------------------------------------------------
# _experiment_output_exists — directory isolation
# ---------------------------------------------------------------------------


def test_experiment_output_exists_uses_source_subdir(tmp_path: Path):
    """Each source should be looked up in its own sub-directory."""
    name = "scidocs"
    source_a = "qrels"
    source_b = "qrels_flip"

    # Create the sentinel file only for source_a
    sentinel_dir = tmp_path / name / source_a
    sentinel_dir.mkdir(parents=True)
    (sentinel_dir / f"{name}_experiment_summary.json").write_text("{}")

    assert _experiment_output_exists(name, source_a, tmp_path) is True
    assert _experiment_output_exists(name, source_b, tmp_path) is False


def test_experiment_output_exists_different_sources_are_independent(tmp_path: Path):
    """Writing a summary for one source must not affect the other source's check."""
    name = "fiqa"

    for source in ("qrels", "qrels_flip", "score_file", "votes_file"):
        d = tmp_path / name / source
        d.mkdir(parents=True)
        (d / f"{name}_experiment_summary.json").write_text(json.dumps({"source": source}))

    # All four sources are now independently present
    for source in ("qrels", "qrels_flip", "score_file", "votes_file"):
        assert _experiment_output_exists(name, source, tmp_path) is True


def test_experiment_output_not_found_without_source_dir(tmp_path: Path):
    """If only the dataset dir (no source sub-dir) exists, the check returns False."""
    name = "hotpotqa"
    dataset_dir = tmp_path / name
    dataset_dir.mkdir(parents=True)
    # Place the file at the old (buggy) location — flat dataset dir
    (dataset_dir / f"{name}_experiment_summary.json").write_text("{}")

    # Under the new scheme the file is NOT found because it's not in a source subdir
    assert _experiment_output_exists(name, "qrels", tmp_path) is False
    assert _experiment_output_exists(name, "qrels_flip", tmp_path) is False


# ---------------------------------------------------------------------------
# _run_experiment — subprocess receives source-specific output directory
# ---------------------------------------------------------------------------


def test_run_experiment_passes_source_subdir_to_subprocess(tmp_path: Path):
    """The subprocess command must include the source-specific output directory."""
    name = "scidocs"
    source = "qrels_flip"

    captured_cmd: list[list[str]] = []

    def fake_run(cmd: list[str], *, label: str) -> int:
        captured_cmd.append(cmd)
        return 0

    with patch("scripts.run_all_real_experiments._run", side_effect=fake_run):
        result = _run_experiment(
            name,
            source=source,
            top_k=10,
            max_queries=5,
            flip_prob=0.15,
            seed=42,
            output_dir=tmp_path,
            force=True,  # force=True bypasses the "already exists" guard
            save_timings=False,
            profile=False,
        )

    assert result is True
    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]

    # Locate the --output-dir argument
    output_dir_idx = cmd.index("--output-dir")
    actual_output_dir = Path(cmd[output_dir_idx + 1])

    expected_output_dir = tmp_path / name / source
    assert actual_output_dir == expected_output_dir, (
        f"Expected output dir {expected_output_dir} but got {actual_output_dir}"
    )


def test_run_experiment_qrels_and_qrels_flip_use_different_dirs(tmp_path: Path):
    """Running qrels and qrels_flip must yield two distinct output directories."""
    name = "scidocs"
    collected_dirs: list[Path] = []

    def fake_run(cmd: list[str], *, label: str) -> int:
        idx = cmd.index("--output-dir")
        collected_dirs.append(Path(cmd[idx + 1]))
        return 0

    with patch("scripts.run_all_real_experiments._run", side_effect=fake_run):
        for source in ("qrels", "qrels_flip"):
            _run_experiment(
                name,
                source=source,
                top_k=10,
                max_queries=None,
                flip_prob=0.15,
                seed=42,
                output_dir=tmp_path,
                force=True,
                save_timings=False,
                profile=False,
            )

    assert len(collected_dirs) == 2
    assert collected_dirs[0] != collected_dirs[1], (
        "qrels and qrels_flip must write to different output directories"
    )
