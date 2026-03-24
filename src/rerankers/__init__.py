"""
Modern reranking baselines for the consistency-aware ranking project.

Modules
-------
cross_encoder   : Cross-encoder neural reranking (sentence-transformers)
llm_pointwise   : LLM pointwise relevance scoring
llm_pairwise    : LLM pairwise document comparison
llm_listwise    : LLM listwise (RankGPT-style) reranking
tournament_agg  : Tournament / graph aggregation baselines (Bradley-Terry, etc.)
common          : Shared utilities (caching, judgment I/O, budget tracking)
"""

__all__ = [
    "cross_encoder",
    "llm_pointwise",
    "llm_pairwise",
    "llm_listwise",
    "tournament_agg",
    "common",
]
