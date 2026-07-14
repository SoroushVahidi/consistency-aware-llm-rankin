# Count Reconciliation: 1,025 vs. 1,026 and Related Totals

Status: **1,025 is correct as reported. It is not a typo.** It is the number
of query-regime preference graphs that retain at least one edge, out of the
1,026 nominal query-regime graphs defined by the primary protocol. The
manuscript previously stated "1,025" in four places without explaining the
gap from the naively expected `342 x 3 = 1,026`; this document traces the
gap to its exact source and lists every manuscript location that was edited
to state the exclusion rule explicitly. No numeric result was changed.

Verified 2026-07-14 against the repository state at commit `8395255`
(`git log -1`), using only artifacts already present in the repository
(no code was re-run; all figures below are read directly from existing
output files and cross-checked by independent recomputation from the
per-query CSVs where noted).

## 1. The core reconciliation: 1,026 nominal graphs, 1,025 used

### 1.1 Eligible / usable queries per dataset (authoritative source: Table 2 / `tab:dataset-stats`)

| Dataset | Stored IDs | Usable queries |
|---|---|---|
| SciDocs | 120 | 120 |
| FiQA | 120 | 120 |
| HotpotQA | 70 | 52 |
| BRIGHT | 50 | 50 |
| **Total** | | **342** |

Source: `reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/<dataset>/<regime>/query_records.jsonl`
(one JSON record per usable query; line counts match the table above in
every regime directory, confirmed by direct count, see 1.2).

### 1.2 Regimes per query: 3 (`ms1`, `ms1_drop_mutual`, `ms2`)

`342 usable queries x 3 regimes = 1,026` nominal query-regime graphs. This
is the number implied by Table 2 alone and is **not** the number of graphs
compared in the exact-vs-greedy repair robustness check (Section 4.4 /
`sec:repair-variants`, Table 4).

### 1.3 Where the missing graph is

Authoritative source: `reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv`
(1,025 data rows; independently re-counted below).

```
$ python3 -c "
import csv
from collections import Counter
c = Counter()
with open('tables/structural_per_query.csv') as f:
    for row in csv.DictReader(f):
        c[(row['dataset'], row['regime'])] += 1
for k, v in sorted(c.items()):
    print(k, v)
print('total', sum(c.values()))
"
('bright', 'ms1') 50
('bright', 'ms1_drop_mutual') 50
('bright', 'ms2') 49          <-- one short
('fiqa', 'ms1') 120
('fiqa', 'ms1_drop_mutual') 120
('fiqa', 'ms2') 120
('hotpotqa', 'ms1') 52
('hotpotqa', 'ms1_drop_mutual') 52
('hotpotqa', 'ms2') 52
('scidocs', 'ms1') 120
('scidocs', 'ms1_drop_mutual') 120
('scidocs', 'ms2') 120
total 1025
```

Every dataset/regime cell has exactly `usable_queries` rows **except**
`bright / ms2`, which has 49 instead of 50. Diffing query IDs:

```
in bright/ms1 but not bright/ms2:               {'biology:0'}
in bright/ms1_drop_mutual but not bright/ms2:   {'biology:0'}
```

The single excluded query-regime graph is **BRIGHT, regime `ms2`, query
`biology:0`**.

### 1.4 Why `biology:0` is missing from `ms2`

Authoritative source (canonical primary-protocol output, not the ILP side
study): `reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/bright/ms2/query_records.jsonl`.
The record for `biology:0` exists there (the canonical primary-protocol
package evaluates all 342 x 3 = 1,026 cells, including this one) and shows:

```json
"graph_stats": {
  "n_edges": 0,
  "n_mutual_pairs": 0,
  "is_cyclic": false,
  "is_dag": true,
  "total_edge_weight": 0,
  "voter_edge_counts": {}
}
```

Cross-checked against every other query-regime cell in the primary
protocol (`reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/primary_minmax_retention_matched/*/*/query_records.jsonl`,
1,026 records total): `biology:0` / `bright` / `ms2` is the **only** record
with `n_edges == 0` anywhere in the primary-protocol grid. Under `ms2`
(minimum support kappa_r = 2, retention-matched aggregate threshold), no
pairwise margin for this query cleared the threshold for any candidate
pair, so zero votes survived and the preference graph has 20 isolated
nodes and no edges. This is a natural, reproducible consequence of the
regime-specific thresholding rule (Eq. 5-6 in the manuscript), not a bug
or missing-data problem: the query is present and scored under every
protocol and regime; only its `ms2` preference graph happens to be empty.

### 1.5 The exclusion rule used by the exact-vs-greedy study

Authoritative source: `reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py`, lines 228-238:

```python
for item in ds_inputs["per_query_inputs"]:
    qid = item["query_id"]
    artifacts = fc.build_query_vote_artifacts(...)
    if not artifacts["rows"]:
        continue          # <-- exactly one query-regime cell hits this: bright/ms2/biology:0
```

`artifacts["rows"]` is empty exactly when no ranker's pairwise margin
survives the regime's vote threshold, i.e. when the resulting preference
graph would have zero edges. A graph with zero edges has an empty
feedback arc set by construction: greedy and exact repair both trivially
remove nothing, so the comparison this study exists to make (does the
exact solver disagree with greedy on which edges to remove?) is vacuous
for that cell. The rule is therefore:

> **A query-regime graph is included in the exact-vs-greedy repair
> comparison if and only if it retains at least one edge.**

This rule is deterministic, applies uniformly to all 1,026 cells, and
happens to exclude exactly one of them (Section 1.3-1.4). It does not
change Table 2's usable-query counts (which count query eligibility, not
retained edges) and it does not affect the primary repaired-vs-unrepaired
retrieval results reported in Sections 5-6, which evaluate all 1,026
cells (the empty-graph cell simply contributes a zero/no-op repair there,
identically for every graph-dependent method).

**Conclusion: 1,025 is correct. Table 2 is correct. Neither needed to
change.** What was missing was the manuscript sentence stating the
exclusion rule; that sentence has now been added (Section 4, "manuscript
locations changed" below).

## 2. Cyclic / acyclic breakdown (the "379 cyclic queries" figure)

Authoritative source: `reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv`, column `is_cyclic_pre_repair`, re-counted directly:

| Dataset | Cyclic (any regime) |
|---|---|
| bright | 57 |
| fiqa | 155 |
| hotpotqa | 34 |
| scidocs | 133 |
| **Total** | **379** |

Breakdown by regime (all cyclic queries come from `ms1` or
`ms1_drop_mutual`; `ms2` contributes zero cyclic queries in every
dataset, consistent with Table 5's "Cyclic% = 0.0" row for `ms2`):

| Dataset | ms1 | ms1_drop_mutual | ms2 |
|---|---|---|---|
| bright | 46 | 11 | 0 |
| fiqa | 118 | 37 | 0 |
| hotpotqa | 33 | 1 | 0 |
| scidocs | 119 | 14 | 0 |

`379 + 646 = 1,025` (the 1,025-query scope of the exact-vs-greedy study;
646 of those queries are already acyclic pre-repair, so repair is a
no-op for them under either greedy or exact). Within the 1,025-query
scope used for this check, zero queries have `n_edges_pre_repair == 0`
(the one such case was already excluded per Section 1), confirming the
exclusion rule was applied consistently.

`87.9%` and `26.3%`: from `manifests/study_summary.json`
(`n_queries_different_removed_edge_set = 333`) and `FINDINGS.md`
(mean weight removed: greedy 6.24, exact 4.60, on the 379 cyclic
queries). `333 / 379 = 0.8786 -> 87.9%`. `(6.24 - 4.60) / 6.24 = 0.2628
-> 26.3%`. Both match the manuscript exactly.

## 3. The 216-of-6,156 Prior-vs-RRF figure

This is a **different** count from the exact-vs-greedy study above: it
comes from the full canonical calibration script
(`reports/full_calibrated_core/scripts/run_full_calibrated_core.py`),
which evaluates **6 protocol variants**, not just the primary protocol:

| Protocol key | Label |
|---|---|
| `primary_minmax_retention_matched` | minmax + retention-matched (primary) |
| `ablation_raw_fixed` | raw + fixed (the manuscript's raw-margin ablation) |
| `ablation_minmax_fixed` | minmax + fixed |
| `ablation_unit_vote_retention` | unit vote + retention-matched |
| `robustness_zscore_retention` | z-score + retention-matched |
| `robustness_rank_percentile_retention` | rank-percentile + retention-matched |

Source: `PROTOCOL_SPECS` dict, `run_full_calibrated_core.py` lines 83-117
(6 keys, confirmed by direct count).

Each protocol variant evaluates the same 342 usable queries x 3 regimes =
1,026 query-regime cells (Prior and RRF are graph-independent baselines
computed from stored ranker scores directly, so — unlike the exact-vs-
greedy repair study — they are defined even for the one empty-graph cell;
no exclusion applies here). `6 x 1,026 = 6,156`, matching exactly.

The exact-match count itself (`exact_match_count = 216`) is computed at
lines 1487-1493 of the same script by comparing, for every one of the
6,156 cells, whether `prior_only`'s output ranking equals `rrf`'s output
ranking, and is materialized in
`reports/full_calibrated_core/tables/rrf_implementation_used_in_full_run.csv`
(row `rrf_baseline`, `notes` column: `"Prior-vs-RRF exact match rate in
this run: 216/6156."`). This is a stored result of a deterministic
computation (both rankings are deterministic given fixed inputs); it was
not re-run for this reconciliation, since the full per-query ranking
lists needed to recompute it are not persisted outside that run (only
aggregate metrics are persisted in `query_records.jsonl`), but the
denominator identity `342 x 3 x 6 = 6,156` was independently re-derived
from Table 2's usable-query counts and the `PROTOCOL_SPECS` dict, and it
matches exactly.

## 4. The 35-pooled / 399-per-dataset-regime exact-minus-greedy cells

See the rewritten Section 4.4 in `main.tex` for the full derivation
(method list, metric list, HotpotQA's `nDCG@20` exclusion, and the Holm/BH
correction-family structure). Independently re-verified here from
`reports/exact_open_source_ilp_repair_investigation/tables/retrieval_metric_paired_summary_pooled.csv`
(35 data rows: 7 methods x 5 metrics, `n_queries = 1025` in every row) and
`.../tables/retrieval_metric_paired_summary.csv` (399 data rows):

```
9 dataset-regime cells (bright, fiqa, scidocs x ms1, ms1_drop_mutual, ms2) x 35 = 315
3 dataset-regime cells (hotpotqa x ms1, ms1_drop_mutual, ms2)              x 28 = 84
315 + 84 = 399
```

(HotpotQA's cutoff-28 rows are 7 methods x 4 metrics, `nDCG@20` being
undefined because HotpotQA's candidate pool is `|D_q| = 10` per Table 2.)

The 7 methods (`method_key` values in the pooled/per-dataset CSVs):
`copeland_graph_repaired`, `balance_graph_repaired`, `markov_graph_repaired`,
`hybrid_repaired_copeland_a0p3_minmax`, `hybrid_repaired_balance_a0p3_minmax`,
`topological_repaired`, `priority_topological_repaired`. The last two are
computed by the canonical pipeline (`reports/full_calibrated_core/scripts/full_calibration_utils.py`,
`add_method` calls for `topological_repaired` / `priority_topological_repaired`)
but have no unrepaired counterpart (topological sort requires an acyclic
graph) and so are not part of the primary repaired-vs-unrepaired method
family in Table 3; they are included here only because this check
compares two repaired variants of the same method (exact vs. greedy),
which both extraction rules support.

Holm/BH correction is applied twice in
`run_exact_open_ilp_study.py`: once over the 35 pooled rows as one joint
family (line ~440), and once over the 399 per-dataset-regime rows as a
separate joint family (line ~471) — not per metric, not per dataset, and
not as one combined 434-cell family.

## 5. The 49 brute-force cross-check graphs

Authoritative source: `reports/exact_open_source_ilp_repair_investigation/tables/scip_vs_bruteforce_validation.json`.

```json
{"n_cases": 49, "all_objectives_match": true, "all_scip_proven_optimal": true}
```

Breakdown by `label` prefix: 34 `synthetic_*` cases (4 node-count values x
3 edge-density values x random seeds) + 15 `hotpotqa_ms1_query*` cases
(real HotpotQA `ms1` graphs, n=10 candidates each) = 49. All 49 SCIP
objective values matched the independent brute-force (`n!` permutation)
enumeration exactly, and SCIP reported proven-optimal status in all 49.

## 6. Manuscript locations changed

All edits are explanatory additions or precision fixes; **no numeric
value anywhere in the manuscript was changed.**

- `main.tex`, Section 3.8 (`sec:repair` / graph repair, ILP paragraph):
  clarified that the never-reached 300s safety limit applies to "any of
  the 1,025 query-regime graphs in this check" and forward-referenced
  Section 4.4 for why this is one fewer than `342 x 3 = 1,026`.
- `main.tex`, Section 4.3 (`sec:baselines`, Prior-vs-RRF tie-breaking
  paragraph): added the `342 x 3 x 6 = 6,156` derivation inline.
- `main.tex`, Section 4.4 (`sec:repair-variants`, "Repair Configuration"):
  rewritten into three labeled parts (Scope, Structural comparison,
  Retrieval comparison); the Scope paragraph now states the exact
  exclusion rule (Section 1.5 above), names the excluded query
  (`biology:0`, BRIGHT, `ms2`), and gives the exact 35/399 cell-count
  derivations including the HotpotQA `nDCG@20` exclusion and the
  two-family Holm/BH correction structure.
- `main.tex`, Section 6.4 (`sec:downstream-results`, fixed-aggregation
  baselines paragraph): simplified to cross-reference Section 4.3 instead
  of repeating the 6,156 derivation a second time.
- `main.tex`, Limitations (`sec:threats`, repair-algorithm-is-heuristic
  paragraph): replaced "the complete 1,025-query primary analysis" (which
  incorrectly implied 1,025 was the size of the *primary* nDCG analysis,
  which in fact covers all 1,026 cells) with "all 1,025 query-regime
  graphs with at least one retained edge (Section 4.4)".

Table 2 (`tab:dataset-stats`), Table 4 (`tab:repair-variants`), and every
numeric result in Sections 5-6 are unchanged.
