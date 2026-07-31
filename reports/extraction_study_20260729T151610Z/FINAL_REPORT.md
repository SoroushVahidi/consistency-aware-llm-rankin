# Extraction-vs-Repair Study -- Final Report

Runtime: 1.0s. Query-graphs evaluated: 120 (identical set used by the repair-frontier program).

## Predeclared decision

**NO_MEANINGFUL_EXTRACTION_GAIN**

Neither a fixed extractor (best: 'hodge_rank' at 0.00407), a selector, nor the oracle (0.00576) clears the 0.01 threshold -- extraction method choice does not meaningfully change ranking quality on this data.

## Per-extractor results (mean delta vs. incumbent, bootstrap 95% CI, win/tie/loss, downside risk)

```
Extractors ranked by mean delta vs. incumbent:
- hodge_rank: mean_delta=0.00407 (CI [0.00201, 0.00667]), win/tie/loss=29/87/4, downside_q05=0.00000, 16.2% of its mean from the single largest delta
- rank_centrality: mean_delta=0.00221 (CI [-0.00024, 0.00532]), win/tie/loss=14/95/11, downside_q05=-0.00723, 39.5% of its mean from the single largest delta
- fas_balance_prior_fusion: mean_delta=0.00075 (CI [0.00011, 0.00150]), win/tie/loss=10/107/3, downside_q05=0.00000, 27.6% of its mean from the single largest delta
- hybrid_rrf_prior_fusion: mean_delta=0.00051 (CI [-0.00052, 0.00158]), win/tie/loss=16/94/10, downside_q05=-0.00926, 40.6% of its mean from the single largest delta
- balance_score: mean_delta=0.00024 (CI [-0.00018, 0.00096]), win/tie/loss=1/117/2, downside_q05=0.00000, 134.2% of its mean from the single largest delta
- copeland: mean_delta=0.00000 (CI [0.00000, 0.00000]), win/tie/loss=0/120/0, downside_q05=0.00000
- pagerank: mean_delta=-0.00076 (CI [-0.00327, 0.00146]), win/tie/loss=22/83/15, downside_q05=-0.01815, -49.1% of its mean from the single largest delta
- borda: mean_delta=-0.00795 (CI [-0.01392, -0.00329]), win/tie/loss=19/74/27, downside_q05=-0.05723, -2.9% of its mean from the single largest delta
```

## Is the gain from one consistently superior extractor, or dataset/provider-specific, cyclic-only, prior-fusion, or outlier-driven?

See `tables/BREAKDOWN_TABLES.csv` for the full by-dataset/by-provider/by-pool_size/by-cyclicity breakdown per extractor, and the per-extractor `fraction_of_mean_from_top_n` figure above for outlier sensitivity (drops the single largest positive delta and recomputes the mean).

## Selective vs. deployable selection

Selection status: **SUPPORTED**. At least one selector (fixed single extractor or predictive) beats always-incumbent.

Comparison (mean nDCG): always_incumbent=0.888692, always_best_single_extractor (hodge_rank)=0.892767, oracle_extractor_selection=0.894450.

## Should extraction, not repair, become the paper's central contribution?

No: neither a fixed extractor, a selector, nor the oracle shows a meaningful gain on this data. The repair-frontier program's apparent 'extraction, not repair' signal does not survive a systematic, bootstrap-CI'd comparison across the full extractor family -- extraction should NOT become the paper's central contribution based on this evidence.

## Files in this directory

- `RUN_CONFIG.json`, `extraction_results.jsonl`, `failures.jsonl`
- `tables/EXTRACTOR_SUMMARY.csv`, `tables/BREAKDOWN_TABLES.csv`
- `FINAL_SUMMARY.json` (this report's machine-readable twin)
