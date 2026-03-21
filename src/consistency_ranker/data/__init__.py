"""
consistency_ranker.data
=======================
Sub-package for dataset loading, preparation, and schema definitions.

Provides a unified interface for BEIR, HotpotQA, and BRIGHT datasets
and utilities to derive pairwise preferences from relevance labels.
"""

from . import beir_loader as beir_loader
from . import bright_loader as bright_loader
from . import dataset_registry as dataset_registry
from . import hotpotqa_loader as hotpotqa_loader
from . import schema as schema
from . import unified_loader as unified_loader
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
