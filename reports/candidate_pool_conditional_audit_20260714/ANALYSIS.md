# Candidate-Pool, Conditional-Analysis, and Baseline Robustness: Consolidated Findings

Consolidates results from `run_pool_robustness.py`,
`run_conditional_and_failure_analysis.py`, and `run_baseline_comparison.py`,
all reading/writing only under
`reports/candidate_pool_conditional_audit_20260714/` and the (newly
extended) canonical `reports/full_calibrated_core/` engine. No manuscript
figures were touched to produce any of this.

## 1. Candidate-pool robustness (task steps 2-3)

Five pools evaluated under the primary protocol (minmax calibration,
retention-matched thresholds), 4 datasets x 3 regimes: the canonical
RRF-fused top-k union, plus four independently-defined alternatives
(equal-depth union, neutral round-robin union, BM25-only, CombSUM-fused
union). 60 cells, 0 exclusions, ~110s wall time.

**Pool overlap with the canonical pool** (mean Jaccard, `ms1`, averaged
over datasets — verified directly from
`pool_overlap_vs_canonical.csv`): equal-depth union 0.438, round-robin
0.521, BM25-only 0.532, CombSUM 0.640. Moderate, not high, agreement —
consistent with the already-known confound documented in the prior,
uncommitted `reports/rrf_pool_investigation/` (which found comparable
overlap figures for a related-but-not-identical set of pool policies). An
earlier draft of this section reported different (higher) numbers for this
paragraph, transcribed from memory rather than read back from the CSV; they
have been corrected here and in `main.tex` to the values actually in
`pool_overlap_vs_canonical.csv` / `pool_removed_edge_overlap_vs_canonical.csv`.

**Removed-edge overlap with canonical**: 1.0 under `ms2` (both sides have
essentially no removed edges regardless of pool, since `ms2`'s strict
aggregate threshold keeps every pool policy near-acyclic — not evidence of
pool-invariance, just a floor effect from the regime itself), 0.403-0.606
under `ms1` (verified from `pool_removed_edge_overlap_vs_canonical.csv`).
Meaningful divergence: roughly 39-60% of removed edges differ depending on
pool policy, similar in magnitude to Task 2's finding for
normalization/threshold policy.

**Repaired-ranking agreement among documents common to both pools**:
0.955-0.962 under `ms1` (verified from
`pool_repaired_ranking_overlap_vs_canonical.csv`; Kendall-style pairwise
concordance rate, computed only over the intersection of the two pools'
candidate sets). This is the most important new finding of the
pool-robustness work: even though pool *membership* and *which edges get
removed* are meaningfully pool-dependent, the **relative order of whichever
documents happen to be eligible under both pools is highly stable and
essentially constant across pool policies**. Pool choice changes the
competition, not how already-common competitors are ordered against each
other.

**Retrieval-metric robustness under a joint multiplicity family**: pooling
all 4 alternative-pool cells jointly (4 pools x 4 datasets x 3 regimes x 5
pairs = 240 tests, one Holm/BH correction), **zero cells are significant**
(`pool_robustness_multiplicity_adjusted.csv`). Extending to all 5 pools
jointly (300 tests) is still zero. The paper's null retrieval-robustness
conclusion, already shown in Task 2 to generalize across independently-
defined normalization/threshold protocols, now also generalizes across
independently-defined candidate-pool constructions.

## 2. Conditional analysis (task step 4)

Computed for the primary protocol under the canonical pool — the
manuscript's actual reported setting — across 4 datasets x 3 regimes x 5
method pairs x 6 subsets = 360 rows
(`conditional_analysis_primary_protocol.csv`).

The clearest illustration is HotpotQA `ms1` Copeland-hybrid, which
reproduces the manuscript's already-published headline number exactly
(mean delta over all 52 queries: +0.01227, matching the reported +0.0123)
and then decomposes it:

| subset | n | mean delta nDCG |
|---|---:|---:|
| all queries | 52 | +0.0123 |
| has a cycle / repair active | 33 | +0.0193 |
| repaired ranking differs from unrepaired | 22 | +0.0290 |
| top-k document *set* changes | 0 | (undefined — never happens) |
| relevance-order (pairwise accuracy) changes | 3 | +0.2126 |

Two things follow, and both matter for how the manuscript should describe
this cell. First, conditioning on activation does not "hide a larger
effect" in the sense of revealing new evidence of a robust benefit — it
mechanically raises the mean because it removes queries contributing
exact zeros, exactly as expected, and the effect is still not close to
significant once the corresponding multiplicity family is considered
(Section 1 above and Task 2's existing correction both already show the
uncorrected local minimum p-values do not survive). Second, and more
informative for interpretation: **the top-k document set never changes for
this cell** (0/52) — every nDCG@k change comes from reordering documents
that were already in the top-k, not from swapping documents in or out of
it — while the small residual effect concentrates almost entirely in 3
queries where the relevance ordering itself changes, with a very large
per-query effect (+0.21) in exactly those 3. This is fully consistent with,
and gives a mechanistic explanation for, the manuscript's existing
influence-removal finding that this same cell's mean collapses to exactly
zero once the top 3 influential queries are removed
(Section~\ref{sec:multiplicity-robustness} of `main.tex`, already
published) — the conditional-subset analysis now shows *why*: those are
almost exactly the queries where relevance ordering changes at all.

The same pattern (activation roughly doubles or more the point estimate,
topk-set changes are rare-to-absent, and effects concentrate in a handful
of relevance-order-changed queries) recurs across most dataset/regime/pair
cells in the full table; magnitudes vary by cell, and this is a *within-
cell decomposition*, not a new significance claim — no subset-level test is
computed here (subsets are too small in most cells for a separate
multiplicity-corrected test to be meaningful), and the manuscript must not
present subset means as a new positive finding.

## 3. Failure decomposition (task step 5)

Five mutually-exclusive, exhaustive categories per query (`no_cycle`,
`cycle_but_repair_inactive`, `repair_inactive_on_ranking`,
`ranking_changed_metric_stable`, `metric_changed`), computed two ways:

- **By protocol** (canonical pool, the 4 canonical Task-2 protocols x 4
  datasets x 3 regimes x 5 pairs, 240 rows,
  `failure_decomposition_by_protocol.csv`).
- **By pool** (primary protocol x all 5 pools x 4 datasets x 3 regimes x 5
  pairs, 300 rows, `failure_decomposition_by_pool.csv`).

`cycle_but_repair_inactive` is 0 in every single row of both tables — the
repair procedure never leaves a detected cycle untouched, which is the
expected/required behavior of a correct FAS repair (it always returns a
DAG) and is reassuring as an implementation-correctness check, not a new
finding. The dominant category under `ms2` is `no_cycle` (consistent with
Section 1's near-total acyclicity under that regime, for every pool and
protocol); under `ms1`, most queries fall into `repair_inactive_on_ranking`
or `ranking_changed_metric_stable` rather than `metric_changed` — i.e. most
of the time, even when repair actively changes the graph and the specific
ranking method's output, nDCG@k does not move. This is the same "structural
repair activity substantially exceeds retrieval-metric activity" pattern
the manuscript already reports for the primary protocol/canonical pool,
now shown to hold across the four canonical protocols and across pool
choice as well, not only in the single previously-reported setting.

## 4. Stronger baselines (task steps 6-7)

Per `AUDIT.md` section 3: `pagerank_graph`, `rank_centrality_graph`,
`markov_hybrid`, and `bradley_terry_graph` were wired into the canonical
`evaluate_query()` (all four reuse pre-existing, already-tested ranking
code — `src/consistency_ranker/baseline_ranking.py`'s
`pagerank_ranking`/`rank_centrality_ranking`, the existing hybrid-fusion
helper for the Markov component, and `src/rerankers/tournament_agg.py`'s
`bradley_terry_ranking` — no new ranking algorithm was implemented).
HodgeRank, Elo, and TrueSkill were deliberately not implemented (no
existing code, and building HodgeRank's Helmholtz decomposition from
scratch is not "reasonable effort using existing infrastructure").

**Fairness verification** (`baseline_fairness_verification.csv`): for
every one of the 12 dataset/regime cells (1,026 queries total = 342 usable
queries x 3 regimes), every
method's output ranking — old and new alike — was confirmed to be a subset
of that query's single, already-fixed candidate pool; 0 violations. This
holds by construction (`evaluate_query` computes `candidate_nodes` once and
passes it to every `add_method` call) and was verified empirically rather
than only asserted.

**Retrieval robustness**: `new_baseline_statistics.csv`
(4 pairs x 4 datasets x 3 regimes = 48 cells) shows small, mixed-sign point
estimates for all four new baselines. Jointly Holm/BH-corrected across all
48 tests (`new_baseline_multiplicity_adjusted.csv`): **zero cells
significant.** The paper's null-effect conclusion extends to these four
additional, previously-excluded graph-ranking baselines as well.

## 5. Cross-cutting summary

Across every independent axis examined in Task 2 and Task 3 combined —
normalization calibration, threshold policy, candidate-pool construction,
and choice of graph-ranking baseline — jointly-corrected multiplicity
testing finds **zero** repaired-versus-unrepaired nDCG cells that survive
correction. This is now a substantially broader evidence base for the
manuscript's central negative retrieval-robustness claim than the
single-protocol/single-pool result it started from. At the same time,
structural quantities (which edges get removed, which documents are
eligible, cyclicity/mutual-pair prevalence) are confirmed, again, to be
meaningfully sensitive to these same construction choices — the paper's
"structural sensitivity, retrieval-conclusion robust" framing (already
adopted after Task 2) is the correct one for candidate-pool choice too, not
only for normalization/threshold policy.
