"""
Tests for the dataset registry.
"""

from __future__ import annotations

import pytest

from consistency_ranker.data.dataset_registry import (
    DATASET_NAMES,
    REGISTRY,
    DatasetConfig,
    get_config,
    processed_queries_jsonl,
)


class TestRegistry:
    def test_all_expected_datasets_present(self):
        for name in (
            "scidocs",
            "fiqa",
            "hotpotqa",
            "bright",
            "nfcorpus",
            "msmarco_passage",
            "trec_dl_passage",
            "robust04",
        ):
            assert name in REGISTRY

    def test_dataset_names_list(self):
        assert set(DATASET_NAMES) == set(REGISTRY.keys())

    def test_get_config_returns_datasetconfig(self):
        cfg = get_config("scidocs")
        assert isinstance(cfg, DatasetConfig)

    def test_get_config_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown dataset"):
            get_config("nonexistent_dataset")

    def test_config_fields_are_populated(self):
        for name in DATASET_NAMES:
            cfg = get_config(name)
            assert cfg.name == name
            assert cfg.raw_path is not None
            assert cfg.processed_path is not None
            assert cfg.top_k > 0
            assert cfg.max_queries > 0
            assert cfg.loader_type in (
                "beir",
                "hotpotqa",
                "bright",
                "msmarco_passage",
                "trec_dl_passage",
                "robust04",
            )

    def test_paths_contain_dataset_name(self):
        for name in DATASET_NAMES:
            cfg = get_config(name)
            # Processed and raw paths should contain the dataset name or a parent
            assert cfg.raw_path.is_absolute()
            assert cfg.processed_path.is_absolute()

    def test_beir_configs_have_hf_names(self):
        for name in ("scidocs", "fiqa", "nfcorpus"):
            cfg = get_config(name)
            assert "BeIR" in cfg.hf_corpus_name
            assert "BeIR" in cfg.hf_qrels_name

    def test_trec_dl_depends_on_msmarco_corpus_note(self):
        cfg = get_config("trec_dl_passage")
        assert cfg.corpus_dependency == "msmarco_passage"
        assert cfg.ir_dataset_name is not None

    def test_processed_queries_jsonl(self):
        p = processed_queries_jsonl("nfcorpus")
        assert p.name == "queries.jsonl"
        assert "nfcorpus" in str(p)

    def test_bright_has_notes(self):
        cfg = get_config("bright")
        assert cfg.notes  # non-empty
