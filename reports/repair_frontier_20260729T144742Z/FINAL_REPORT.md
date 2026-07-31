# Repair-Frontier Program -- Final Report

Runtime: 16.4s. Queries with relevance labels evaluated: 120.

## 1. Does the richer repair frontier contain beneficial rankings the previous single repair method did not?

Frontier oracle headroom (mean of best-candidate-nDCG minus incumbent-nDCG per query): **0.005369** (one-sided 95% CI [0.002911, 0.008411]). Beneficial/neutral/harmful query counts: 33/87/0. Best/median/worst per-query delta: 0.106293/0.000000/0.000000. Decision: **NO_MEANINGFUL_HEADROOM**. Yes, in the narrow sense that 33/120 query-graphs had at least one candidate beat the incumbent (vs. 0 in the original single-method pilot); the oracle-best-method attribution below shows WHICH methods account for this.

Oracle-best-method attribution (which method family won the per-query oracle race, aggregated over all 120 query-graphs): {"incumbent (no benefit found)": 87, "alt_extraction": 30, "whole_graph": 2, "scc_local (unprotected)": 1}.

## 2. Does SCC-local repair produce more headroom than whole-graph repair?

SCC-local-only headroom (0.004507) exceeds whole-graph-only headroom (0.001690) restricted to the same candidate pool. See `sensitivity/SENSITIVITY_TABLES.csv` rows with `dimension=repair_scope` for the full comparison (restricted to the main pass's own already-generated candidates for a like-for-like comparison).

## 3. Does incumbent protection reduce harmful changes?

Harmful changes (delta < 0) are 0 by construction across the whole frontier (the incumbent is always itself a candidate, so no candidate can score below it in this oracle-discovery framing) -- protection's effect is therefore visible in `scc_decisions.jsonl`'s `protected_edge_violations` (how often a protected edge had to be touched anyway to break a cycle) and `acceptance_by_mode` (how often each acceptance mode would have deployed vs. abstained), not in a harmful-fraction reduction that has no headroom to begin with.

## 4. Which protection rules preserve quality without eliminating all repair activity?

No protected-candidate family ever won the oracle-best race in this dataset (see the attribution above), so varying protection-rule threshold/margin left discovery headroom completely unchanged across the confidence_threshold_tau, margin_threshold_tau, and conservative_acceptance_margin sweeps in `sensitivity/SENSITIVITY_TABLES.csv` -- protection strictness is not the limiting factor on this data; see `scc_decisions.jsonl` for per-rule abstention/violation rates.

## 5. Can any observable rule select beneficial candidates on held-out queries?

Selection status: **SUPPORTED**. At least one selector (fixed or predictive) beats always-preserve on this data.

## 6. If not, is the limiting factor candidate generation or candidate selection?

Generation found no meaningful oracle headroom (candidate-generation-limited); selection was not meaningfully evaluated beyond this.

## Localization

Of 33 queries where the oracle-best candidate beat the incumbent, 3 involved an SCC modification and 0 involved a top-k membership change.

## Bottom line

**No positive contribution claimed** on this data -- either the frontier's oracle headroom does not clear the pre-registered gate, or no evaluated selector (fixed or predictive) beats always-preserve on held-out queries. See sections 1-6 above for which.

## Files in this directory

- `RUN_CONFIG.json`, `checkpoint/{frontier_results.jsonl,progress.json}`
- `scc_decisions.jsonl`, `feature_rows.jsonl`, `failures.jsonl`
- `discovery/{FRONTIER_ORACLE_HEADROOM.json,oracle_best_method_per_query.jsonl}`
- `selection/STAGE_SELECTION.json`, `sensitivity/SENSITIVITY_TABLES.csv`
- `runtime_stats.json`, `ENVIRONMENT_pip_freeze.txt`
- `FINAL_SUMMARY.json` (this report's machine-readable twin)
