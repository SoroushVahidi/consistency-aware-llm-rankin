"""
consistency_ranker.data
=======================
Sub-package for dataset loading, preparation, and schema definitions.

Provides a unified interface for BEIR, HotpotQA, and BRIGHT datasets
and utilities to derive pairwise preferences from relevance labels.
"""

from .schema import (
    CandidateRanking,
    Document,
    PairwisePreference,
    QrelEntry,
    Query,
)

__all__ = [
    "Query",
    "Document",
    "QrelEntry",
    "CandidateRanking",
    "PairwisePreference",
    "schema",
    "dataset_registry",
    "unified_loader",
    "beir_loader",
    "hotpotqa_loader",
    "bright_loader",
]
