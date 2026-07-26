"""
consistency_ranker
==================
Consistency-Aware Retrieval and Reasoning in LLM Systems.

Main package exposing the core sub-modules.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("consistency-ranker")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = [
    "data_loader",
    "synthetic_data",
    "pairwise_prefs",
    "graph_construction",
    "cycle_detection",
    "baseline_ranking",
    "dag_linear_extensions",
    "dag_ambiguity",
    "soft_score_ranking",
    "greedy_fas",
    "mwfas_solver",
    "evaluation",
]
