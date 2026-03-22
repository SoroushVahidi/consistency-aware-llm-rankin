from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_real_experiment import _validate_run_configuration
from scripts.run_synthetic import run_experiment as run_synthetic_experiment


def test_real_experiment_validation_requires_existing_pairwise_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        _validate_run_configuration(
            max_queries=10,
            top_k=20,
            preference_source="votes_file",
            flip_prob=0.15,
            pairwise_file=tmp_path / "missing_votes.jsonl",
            score_file=None,
            score_prior_files=None,
            query_id_file=None,
            output_dir=tmp_path / "out",
            save_timings=False,
            overwrite_existing=False,
            dataset="scidocs",
        )


def test_real_experiment_validation_blocks_overwrite(tmp_path: Path):
    out_dir = tmp_path / "scidocs" / "qrels"
    out_dir.mkdir(parents=True)
    (out_dir / "scidocs_per_query.csv").write_text("dataset,query_id\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _validate_run_configuration(
            max_queries=10,
            top_k=20,
            preference_source="qrels",
            flip_prob=0.15,
            pairwise_file=None,
            score_file=None,
            score_prior_files=None,
            query_id_file=None,
            output_dir=out_dir,
            save_timings=False,
            overwrite_existing=False,
            dataset="scidocs",
        )


def test_real_experiment_validation_allows_overwrite_when_enabled(tmp_path: Path):
    out_dir = tmp_path / "scidocs" / "qrels"
    out_dir.mkdir(parents=True)
    (out_dir / "scidocs_per_query.csv").write_text("dataset,query_id\n", encoding="utf-8")

    _validate_run_configuration(
        max_queries=10,
        top_k=20,
        preference_source="qrels",
        flip_prob=0.15,
        pairwise_file=None,
        score_file=None,
        score_prior_files=None,
        query_id_file=None,
        output_dir=out_dir,
        save_timings=False,
        overwrite_existing=True,
        dataset="scidocs",
    )


def test_synthetic_validation_rejects_invalid_noise(tmp_path: Path):
    with pytest.raises(ValueError):
        run_synthetic_experiment(
            n_items=10,
            noise=1.2,
            seed=42,
            output_dir=tmp_path / "out",
        )


def test_synthetic_validation_blocks_overwrite(tmp_path: Path):
    out_dir = tmp_path / "synthetic"
    out_dir.mkdir(parents=True)
    (out_dir / "synthetic_results.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError):
        run_synthetic_experiment(
            n_items=8,
            noise=0.2,
            seed=42,
            output_dir=out_dir,
            overwrite_existing=False,
        )

