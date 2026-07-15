# Methods And Protocol

- Stored canonical score files, query IDs, qrels, candidate pools, top-k values, repair code, and evaluation code were reused unchanged.
- Only downstream calibration, vote extraction, graph construction, repair, and evaluation were rerun.

## Protocols

- `primary_minmax_retention_matched`: calibration `minmax_query_ranker`, threshold mode `retention_matched`, role `primary`.
- `ablation_raw_fixed`: calibration `raw`, threshold mode `fixed_numeric`, role `ablation`.
- `ablation_minmax_fixed`: calibration `minmax_query_ranker`, threshold mode `fixed_numeric`, role `ablation`.
- `ablation_unit_vote_retention`: calibration `unit_vote`, threshold mode `retention_matched`, role `ablation`.
- `robustness_zscore_retention`: calibration `zscore_query_ranker`, threshold mode `retention_matched`, role `robustness`.
- `robustness_rank_percentile_retention`: calibration `rank_percentile`, threshold mode `retention_matched`, role `robustness`.

## Threshold Matching

- `retention_matched` uses per-ranker vote-threshold matching to raw retained-vote rates and a regime-specific aggregate threshold selected to minimize retained-edge-count deviation from raw.
- Support rules remain canonical: `ms2` requires support `2` and aggregate threshold default `0.1`; `ms1` and `ms1_drop_mutual` require support `1` with the canonical or matched aggregate threshold.

## Methods

- Graph-independent: Prior, RRF, CombSUM, Borda fusion.
- Graph-dependent: Copeland, Balance, Markov; each evaluated unrepaired and repaired.
- Hybrids: Copeland and Balance unrepaired/repaired hybrids at alpha=0.3, plus a primary-protocol alpha sweep over {0.1, 0.3, 0.5, 1.0}.
