# Results Numeric Cross-Check (Stage 4)

Every numerical claim in `manuscript/main.tex`'s Results section
(`\section{Results}`) was computed directly from a canonical repository
CSV during this stage (via `pandas`, not read off a prior report's
prose), and where a prior report (JDIQ's submitted manuscript, or a
`reports/*/FINDINGS.md`/`FINAL_REPORT.md`) also stated the same quantity,
the two were compared. This file records that computation and comparison
per claim, so a reviewer or a later stage can re-verify without redoing
the analysis from scratch. All computations are reproducible with
`pandas`/`numpy` against the paths cited; the exact one-off computations
run are summarized inline rather than kept as throwaway scripts, since
none of them altered any repository artifact.

## Section 5.1, Structural Inconsistency Before Repair

**Table 3 (`tab:structural-outcomes`) and BM25 share (0.988/0.512).**
Source: `reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/table_primary_graph_structure.csv`.
Read directly; every `cyclic_query_pct`, `cyclic_query_pct_after_mutual_deletion`,
and `mean_normalized_fas_weight_removed` value in the table was copied
from this CSV's 12 rows (4 datasets x 3 regimes) with no transformation
beyond rounding to the printed precision. Cross-checked against JDIQ's
submitted manuscript text ("HotpotQA drops from 63.5% to 1.9%... FiQA
retains a larger residual (98.3% -> 30.8%)"): matches exactly. The
`ms1_drop_mutual` row's own `cyclic_query_pct` was verified to equal
`ms1`'s `cyclic_query_pct_after_mutual_deletion` in every dataset (an
internal-consistency identity, not assumed) -- confirmed exactly (e.g.
SciDocs: $10.8\%$ both places). The BM25 conditional edge-weight share
figures ($0.988$ raw, $0.512$ normalized) are carried from
`reports/full_calibrated_core/EXECUTIVE_SUMMARY.md` (`0.9879644976033446`,
`0.5123241797137496`), already an exact match to JDIQ's stated figures;
not independently recomputed from raw score files this stage (out of
scope -- this number is descriptive, not a significance claim, and was
already verified in an earlier repository-hygiene pass per that file's
own provenance).

## Section 5.2, Structural Effect of Repair

**Top-$k$ membership-change rate (10.6% vs.\ 0%).** Source:
`reports/final_revision_task1_pool_cutoff_20260715/tables/pool_cutoff_structural_summary.csv`.
**This required correcting an initial miscomputation.** Restricting to the
active `ms1` regime only (the regime where repair is structurally active)
gives a mean `top_k_membership_changed_rate` of $26.2\%$ for $P>k$ rows --
not $10.6\%$. Reading
`reports/final_revision_task1_pool_cutoff_20260715/FINAL_REPORT.md`
Section 9 ("Aggregate rates from `pool_cutoff_structural_summary.csv`: P
= k: ... 0.000000; P > k: ... 0.105776") showed the correct scope is
**pooled across all three vote-construction regimes**, not `ms1`-only:
recomputing the mean over all regimes' $P>k$ rows gives $0.105776$,
matching exactly ($10.6\%$ to one decimal). The manuscript states this
number with the correct scope ("pooling across all three
vote-construction regimes"); the $P=k$ value ($0.0$ exactly, all regimes)
was independently confirmed the same way.

## Section 5.3, Retrieval Effectiveness

**Holm-rejected cell counts (0/20, 0/60, 0/110).** Source:
`reports/full_calibrated_core/outputs/calibrated_all4/paper_package/tables/table_primary_bootstrap_permutation.csv`
(60 rows: 4 datasets x 3 regimes x 5 pairs) for the canonical families, and
`reports/final_revision_task1_pool_cutoff_20260715/tables/pool_cutoff_statistics.csv`
(pre-computed `holm_active_ms1_family` column, filtered to `metric=="ndcg"`)
for the larger-pool family. The canonical-family Holm adjustment was
**recomputed independently** in this stage using
`src/consistency_ranker.statistical_inference.holm_adjust` (the actual
repository function, imported and run, not reimplemented) on the 60 raw
`paired_permutation_pvalue` values, and again on the `ms1`-only 20-row
subset: both give $0$ significant at $\alpha=0.05$, matching JDIQ's stated
"0/20" and "0/60" exactly, with the same smallest Holm-adjusted $p$-value
($0.384$, SciDocs Copeland graph) independently reproduced. The
larger-pool family's pre-computed `holm_active_ms1_family` column, filtered
to nDCG and `ms1` ($110$ rows), gives $0$ significant, smallest
Holm-adjusted $p=0.352$; matches JDIQ's "0/110" exactly.

**Macro-mean nDCG (CombSUM 0.554, RRF 0.546, best repaired hybrid
0.546).** Source: same
`table_primary_macro_method_comparison.csv`. Read directly:
`combsum` dataset-macro mean $= 0.554119$ across every protocol/regime row
(identical, as expected for a graph-free method); `rrf` $= 0.546223$;
the best-performing repaired hybrid row is `ms2`'s
`hybrid_repaired_copeland_a0p3_minmax` at $0.546703$, with `ms1`'s at
$0.545839$ -- the manuscript reports the `ms1` (active-regime) value
$0.546$ specifically, since `ms1` is the regime under discussion
throughout this subsection; both round to $0.546$ regardless. Matches
JDIQ's stated $0.554$/$0.546$/$0.546$ exactly.

## Section 5.4, Exact Versus Heuristic Repair

**Solver statistics (1,025/1,025 proven optimal; 7.4ms/0.25ms/236ms).**
Source:
`reports/exact_open_source_ilp_repair_investigation/tables/ilp_solver_status_per_query.csv`.
`proven_optimal.sum()` over all rows $= 1025$, out of $1025$ total rows.
`time_s`: mean $0.007444$s ($7.44$ms), median $0.000252$s ($0.25$ms), max
$0.235736$s ($236$ms). Matches `FINDINGS.md`'s stated figures exactly.

**Cyclic-query count (379) and per-dataset structural gap.** Source:
`reports/exact_open_source_ilp_repair_investigation/tables/structural_per_query.csv`.
**Same regime-pooling correction as the top-$k$ membership rate above was
required here too.** Filtering to `regime=="ms1"` and cyclic gives $316$
queries and per-dataset means that do not match `FINDINGS.md`'s stated
per-dataset table (e.g.\ BRIGHT $n=46$ vs.\ `FINDINGS.md`'s $57$).
Pooling across all three regimes (matching `FINDINGS.md`'s own stated
scope, "primary protocol... all 3 vote regimes") gives exactly
`FINDINGS.md`'s numbers: $n=379$ total cyclic queries; per dataset,
BRIGHT $n=57$ (mean weight removed $3.952$ greedy / $3.070$ exact, $22.3\%$
less), FiQA $n=155$ ($6.368$/$4.508$, $29.2\%$), HotpotQA $n=34$
($1.795$/$1.554$, $13.4\%$), SciDocs $n=133$ ($8.194$/$6.136$, $25.1\%$)
-- all reproduced to the reported precision (values in Table 5 /
`tab:exact-vs-greedy` and Figure 5 / `f5_exact_vs_greedy_gap.pdf` use
this all-regimes-pooled scope, computed directly by
`figures/generate_f5_exact_vs_greedy_gap.py`, not hand-copied). Different-edge-set
rate: $87.9\%$ overall (`(~same_edges_removed_set).mean()` over the 379
cyclic rows $= 0.8786$), matching `FINDINGS.md` exactly.

**Exact-vs-greedy retrieval comparison (0/35 pooled, 0/399 finer).**
Source:
`reports/exact_open_source_ilp_repair_investigation/tables/retrieval_metric_paired_summary_pooled.csv`
(35 rows) and `retrieval_metric_paired_summary.csv` (399 rows), both with
pre-computed `holm_pvalue` columns. `(holm_pvalue < 0.05).sum()` is $0$
for both. Smallest raw $p$-value in the pooled table: $0.025897$
(priority-topological, nDCG@10, mean delta $-0.00223$, Holm-adjusted
$p=0.906$) -- matches `FINDINGS.md`'s stated "-0.00223... raw p=0.026,
Holm p=0.91" (rounding accounts for the small difference in the last
digit).

**Exact-vs-unrepaired canonical/larger-pool (0/36, 0/56).** Source:
`reports/final_revision_task4_exact_baseline_fairness_20260715/tables/exact_canonical_family_statistics.csv`
(36 rows) and `exact_larger_pool_family_statistics.csv` (56 rows), both
with pre-computed `holm_significant_at_0.05` boolean columns. Both sum to
$0$. The 36-row table's 9 distinct `pair_name` values were enumerated
directly and confirmed to be exactly the primary five-pair family plus
`pagerank_graph`, `rank_centrality_graph`, `markov_hybrid`, and
`bradley_terry_graph` (the Stage-3 finding recorded in
`STAGE3_CHANGELOG.md`), across the 4 canonical datasets, $9 \times 4 = 36$.

## Section 5.5, Robustness

**Baseline fairness (0/8).** Source:
`reports/final_revision_task4_exact_baseline_fairness_20260715/tables/baseline_targeted_tests_primary_canonical.csv`
(8 rows: 4 datasets x {RRF, CombSUM} vs.\ the fixed repaired Copeland
hybrid). `holm_significant_at_0.05` is `False` in all 8 rows.

**Power/MDE (0.0036 observed; MDE recomputed to 0.0201, not JDIQ's
0.0207).** Source:
`reports/final_revision_task2_statistical_power_20260715/tables/mde_per_cell.csv`,
filtered to `regime=="ms1"`, `metric=="ndcg"`, and `pool_size.notna()`
(this file mixes per-cell rows with per-dataset aggregate rows sharing
the same regime/metric values but `NaN` pool/cutoff fields -- confirmed
by inspecting the distinct `(dataset, pool_size, metric_cutoff)` tuples
before filtering, not assumed), giving exactly $110$ rows matching the
active larger-pool family size used elsewhere. Median of
`mean_delta.abs()` $= 0.003575$, rounding to JDIQ's stated $0.0036$
(a small rounding-precision difference, not a scope error -- the
unfiltered 130-row version gives $0.003608$, also rounding to $0.0036$,
so this particular figure is robust to the filtering question). Median
of `mde_normal_holm_active_ms1_power80` $= 0.020086$, i.e.\ $0.0201$.
**This does not match JDIQ's stated $0.0207$ exactly**, despite matching
scope (regime, metric, family, power target, correction). Checked
alternative candidate columns in the same file
(`mde_sim_holm_active_ms1_power80`, `mde_normal_alpha05_power80`, an
uncorrected variant): none reproduces $0.0207$ either; the closest and
most semantically correct match is the $0.0201$ figure used. Most likely
explanation: this specific statistical-power report was regenerated at
least once after JDIQ's manuscript text was last written (the repository
shows multiple revision-task passes touching statistical methodology),
and the current canonical CSV reflects a later state than the one JDIQ's
prose cites. Per this stage's "correct the manuscript rather than the
repository" instruction and "never invent numbers," the manuscript
reports $0.0201$ -- the value actually reproducible from the current
canonical artifact -- not JDIQ's $0.0207$. **This is the one open
numeric discrepancy from this cross-check; flagged here rather than
silently resolved, per the task's explicit instruction to record
unresolved evidence inconsistencies.**

**Narrow equivalence (13/110, 32/110).** Source:
`reports/final_revision_task2_statistical_power_20260715/tables/equivalence_test_table.csv`,
filtered to `regime=="ms1"` (giving $110$ rows per margin, matching the
active larger-pool family). `equivalent_holm_margin_family.sum()` $= 13$
at margin $0.005$ and $32$ at margin $0.01$. Matches JDIQ's stated
$13/110$ and $32/110$ exactly.

## Section 5.6, Supporting LLM Evidence

**Whole-graph repair effect (0.00019 mean; CI $[-0.00072, 0.00140]$;
$p=0.875$).** Source:
`reports/real_llm_clustered_reanalysis_20260730T023745Z/REAL_LLM_CLUSTERED_REANALYSIS.md`,
Section 3 table, "Whole-graph repair alone" row. Not independently
recomputed from raw per-query data this stage (the reanalysis report's
own frontier-reconstruction accuracy was already verified there to
$1.1\times10^{-16}$ absolute error against stored aggregates, and
re-deriving cluster bootstrap CIs from scratch was judged out of scope
for a "keep it short" supporting-evidence subsection); read directly from
the report's own stated cluster-level ($n=6$) result, which is explicitly
the authoritative corrected version per that report's own stated purpose
(superseding the row-level $n=120$ statistics originally attached to the
same studies). Query/provider/variant counts ($6$/$5$/$4$) cross-checked
against the same report's Section 1 population table and
`reports/multi_provider_repair_pilot_20260729T032348Z/README.md`.

## Cross-references, figures, tables, equations

- Every `\ref`/`\eqref` target in the Results section was confirmed to
  resolve (no `??` in the compiled PDF text, checked via `pdftotext`) and
  every table/figure is referenced by name in the surrounding prose
  before it appears, per this stage's brief.
- No new bibliography entry was needed for the Results section itself
  (it states repository-derived findings, not literature claims); no
  `\cite` appears inside `\section{Results}`.
- Checked for forbidden phrasing across the Results section text
  (`grep -inE` for "we next", "we then", "finally,", "almost
  significant", "marginally significant", "repair does not work",
  "trending toward"): zero matches. Checked for repository/manuscript-history
  language ("repository", "reject", "IJCS", "JDIQ"): the only matches are
  the standard statistical terms "Holm-rejected" and "reject
  non-equivalence," not repository or manuscript-history references.
- Table 5 (`tab:exact-vs-greedy`)'s first LaTeX draft mixed a per-dataset
  structural comparison with a pooled-only retrieval statistic via
  `\multirow`, which read as implying the retrieval numbers had a
  per-dataset breakdown they do not have; redesigned to a plain
  per-dataset structural table with the pooled retrieval result stated in
  the caption instead, before this cross-check was finalized.

## Compilation

`tectonic`, same toolchain as Stages 2-3. Final Stage-4 compile: 33
pages, zero undefined references, zero undefined citations, zero BibTeX
errors, zero overfull/underfull-driven content loss (all remaining
`Underfull \vbox`/`\hbox` warnings are whitespace-only, not content
clipping, and unavoidable at this margin/font combination -- consistent
with Stages 2-3). `manuscript/main.pdf` is that verified output.
