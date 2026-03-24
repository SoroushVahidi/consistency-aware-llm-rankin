# LLM Pairwise Pilot Comparison — SciDocs

## Experiment Configuration

- **Dataset**: scidocs
- **Queries**: 50 (sampled from 1000 eligible)
- **Top-k candidates**: 20
- **Seed**: 42
- **LLM mode**: dry_run (deterministic mock judgments via MD5 hashing)
- **Position debiasing**: disabled
- **Judgment caching**: disk-backed (outputs/llm_scidocs_pilot_comparison/judgment_cache)
- **Total pairwise comparisons**: 9500

## Method Categories

| Category | Methods |
|----------|---------|
| LLM Pairwise Baseline | llm_pairwise_copeland |
| Tournament Aggregation | bt_from_llm, win_rate_from_llm, markov_from_llm, tournament_sort_from_llm |
| FAS-Repaired Graph | greedy_fas_topological, greedy_fas_weighted_balance, greedy_fas_copeland |
| Hybrid Repaired | hybrid_rrf_repaired_copeland_a03, hybrid_rrf_repaired_balance_a03 |
| Hybrid Unrepaired | hybrid_rrf_unrepaired_copeland_a03, hybrid_rrf_unrepaired_balance_a03 |

## Pilot Comparison Table

All methods consume the **same LLM pairwise judgments** (deterministic mock, seed=42).

| Method | nDCG@20 | MAP@20 | P@20 | R@20 | BEW↓ | PIC↓ |
|--------|---------|---------|-------|-------|------|------|
| llm_pairwise_copeland | 0.5525 | 0.3088 | 0.2470 | 1.0000 | 69.34 | 69.34 |
| bt_from_llm | 0.5511 | 0.3071 | 0.2470 | 1.0000 | 68.90 | 68.90 |
| win_rate_from_llm | 0.5525 | 0.3088 | 0.2470 | 1.0000 | 69.34 | 69.34 |
| markov_from_llm | **0.5644** | 0.3179 | 0.2470 | 1.0000 | 72.34 | 72.34 |
| tournament_sort_from_llm | 0.5631 | 0.3195 | 0.2470 | 1.0000 | 66.06 | 66.06 |
| greedy_fas_topological | 0.4005 | 0.1612 | 0.2470 | 1.0000 | 79.00 | 79.00 |
| greedy_fas_weighted_balance | 0.4007 | 0.1617 | 0.2470 | 1.0000 | 84.52 | 84.52 |
| greedy_fas_copeland | 0.4007 | 0.1617 | 0.2470 | 1.0000 | 84.52 | 84.52 |
| hybrid_rrf_repaired_copeland_a03 | 0.4858 | 0.2377 | 0.2470 | 1.0000 | 70.60 | 70.60 |
| hybrid_rrf_unrepaired_copeland_a03 | 0.5525 | 0.3088 | 0.2470 | 1.0000 | 69.34 | 69.34 |
| hybrid_rrf_repaired_balance_a03 | 0.4858 | 0.2377 | 0.2470 | 1.0000 | 70.60 | 70.60 |
| hybrid_rrf_unrepaired_balance_a03 | 0.5525 | 0.3088 | 0.2470 | 1.0000 | 69.34 | 69.34 |

## Repaired vs Unrepaired Deltas

Positive Δ means repaired is *better* (higher nDCG / lower BEW).

| Component | nDCG Δ | BEW Δ | PIC Δ |
|-----------|--------|-------|-------|
| copeland | -0.0667 | -1.26 | -1.26 |
| balance | -0.0667 | -1.26 | -1.26 |

## Graph Repair Statistics

- Cyclic preference graphs: 50/50 (100.0%)
- Average FAS edges removed: 90.8

## Files

- Per-query results: `outputs/llm_scidocs_pilot_comparison/pilot_per_query.csv`
- Summary CSV: `outputs/llm_scidocs_pilot_comparison/pilot_summary.csv`
- LLM pairwise judgments: `outputs/llm_scidocs_pilot_comparison/llm_pairwise_judgments.jsonl`
- Judgment cache: `outputs/llm_scidocs_pilot_comparison/judgment_cache`
