# Manuscript Evidence Map (Stage 1)

Every planned claim, table, and figure below is mapped to the exact
repository artifact that backs it. This is the SN Computer Science
manuscript's own scoped view of `docs/claim_evidence_registry.yaml` --
consult that file for the machine-readable, repository-wide version and
for the full mutual-exclusion rules (`canonical` claims never overlap with
`internal_validation` or `superseded` ones).

All paths below were confirmed to exist on disk during this Stage-1 pass
(directory-existence checks only; no experiments were re-run). Numbers
quoted are copied verbatim from `papers/JDIQ_2026/manuscript/main.tex`
(the most current, already-checked source) or `docs/claim_evidence_registry.yaml`,
not recomputed.

## Planned main-paper claims

| # | Planned claim (bounded) | Registry ID | Evidence path(s) | Generating script | Statistical unit / correction |
|---|---|---|---|---|---|
| 1 | Raw heterogeneous score margins are scale-dominated (BM25 conditional edge-weight share 0.988 raw vs. 0.512 normalized); normalization materially changes retained votes, cyclicity, and removed edges. | REPAIR-01 (supporting) | `reports/full_calibrated_core/`, `reports/normalization_protocol_audit_20260714/` | `reports/full_calibrated_core/scripts/full_calibration_utils.py` | descriptive; no significance test claimed |
| 2 | Vote-construction regime (`ms1`/`ms2`/`ms1_drop_mutual`) is the dominant determinant of graph cyclicity; e.g. HotpotQA drops from 63.5% to 1.9% cyclic queries under `ms1_drop_mutual`, FiQA from 98.3% to 30.8%. SciDocs post-mutual `ms1` (10.8%) and `ms1_drop_mutual` cyclic (11.7%) are related but **not** identical (see `CORRECTNESS_METHODS_FIX_CHANGELOG.md`). | REPAIR-01 (supporting) | `reports/full_calibrated_core/` | same | descriptive |
| 3 | Repair is structurally active under normalized `ms1` graphs (removed weight 0.029-0.080 of total graph weight); `ms2` is acyclic by construction. | REPAIR-01 | `reports/full_calibrated_core/` | same | descriptive |
| 4 | **Central null result:** no repaired-vs-unrepaired nDCG cell survives Holm correction -- 0/20 active canonical `ms1` cells, 0/60 full canonical cells. | REPAIR-01 | `reports/full_calibrated_core/` | same | query; Holm |
| 5 | Larger-pool (`P>k`) study: repair changes top-$k$ membership (mean rate 10.6%, **pooled across all three vote-construction regimes** -- not `ms1`-only, which gives 26.2% -- vs. 0% at `P=k`, confirmed 2026-07-31) but still 0/110 active larger-pool cells survive Holm correction. | REPAIR-01 | `reports/final_revision_task1_pool_cutoff_20260715/` | `reports/final_revision_task1_pool_cutoff_20260715/scripts/run_pool_cutoff_study.py` | query; Holm |
| 6 | **Headline reviewer-facing result:** of $1{,}026$ nominal query–regime combinations, one BRIGHT/`ms2`/`biology:0` empty-edge graph is excluded; exact SCIP repair reaches proven optimality on the remaining $1{,}025/1{,}025$ graphs and, on the $n=379$ queries whose graph is cyclic (**pooled across all three vote-construction regimes**, confirmed 2026-07-31; restricting to `ms1` alone gives only $n=316$), removes *less* edge weight than greedy, yet 0/36 canonical and 0/56 larger-pool exact-vs-unrepaired cells, and 0/35 pooled + 0/399 finer exact-vs-greedy retrieval cells, survive Holm correction -- a gain of the detectable scale is not explained by greedy under-repair. | REPAIR-02 | `reports/exact_open_source_ilp_repair_investigation/`, `reports/final_revision_task4_exact_baseline_fairness_20260715/` | `reports/exact_open_source_ilp_repair_investigation/scripts/run_exact_open_ilp_study.py` | query; Holm |
| 7 | Simple graph-free baselines remain competitive: CombSUM dataset-macro mean nDCG 0.554; RRF and the repaired Copeland hybrid have the same reported dataset-macro mean to three decimal places (0.546). | REPAIR-01 (supporting) | `reports/full_calibrated_core/` | same | descriptive |
| 8 | Power/MDE: median observed \|delta\| 0.0036 vs. Holm-adjusted median 80%-power MDE **0.0201** (superseded value 0.0207 does not reproduce from the current canonical `mde_per_cell.csv`; see `RESULTS_CROSS_CHECK.md` and `result_claims.yaml`) in the active larger-pool family; narrow equivalence (13/110 at +/-0.005, 32/110 at +/-0.010). | REPAIR-01 (supporting) | `reports/final_revision_task2_statistical_power_20260715/` | same | query; Holm-adjusted MDE |

**Stage-3 clarification on claim #4 vs. claim #6's method-family scope**
(added during Methodology drafting, since this determines exactly which
extraction methods the Methodology section must define): claim #4's 0/20
and 0/60 canonical cells (`reports/full_calibrated_core/`, **greedy**
repair) use only the five original graph-dependent method pairs
(Copeland, Balance, Markov, Copeland-hybrid, Balance-hybrid) plus the four
graph-free baselines (Prior, RRF, CombSUM, Borda) --
`reports/full_calibrated_core/scripts/run_full_calibrated_core.py`'s
`LEGACY_PAIR_NAMES`. Claim #6's 0/36 canonical and 0/56 larger-pool cells
(`reports/final_revision_task4_exact_baseline_fairness_20260715/`,
**exact** repair vs. unrepaired) use an *expanded* nine-pair family: the
same five plus PageRank, Rank Centrality, a Markov-hybrid, and
Bradley-Terry (`NEW_BASELINE_PAIR_NAMES` in the same script, added per
`reports/candidate_pool_conditional_audit_20260714/AUDIT.md` Section 3;
9 pairs x 4 datasets = 36 canonical cells). A separate, earlier exact-repair
study, `reports/exact_open_source_ilp_repair_investigation/` (exact
**vs. greedy**, not vs. unrepaired -- the source of the "1,025/1,025
proven-optimal, removes less weight than greedy" figures in claim #6),
uses yet another method family: the five original methods plus
topological and priority-topological ranking (repaired-graph-only
methods with no unrepaired variant), evaluated on nDCG@5/10/20, MRR, and
MAP pooled across 1,025 queries (35 or, at finer granularity, 399
metric-method cells, both 0 Holm-significant). These three studies are
evidence for the same REPAIR-01/REPAIR-02 claims but are not
method-for-method identical; `MANUSCRIPT_PLAN.md` Section 7's C9/C10 row
("PageRank, Rank Centrality, and Bradley-Terry are already implemented
and evaluated") is correct and refers to the second (Task 4) family --
this was mistakenly flagged as a possible error in
`STAGE2_CHANGELOG.md` Open Question 4 before this closer read; see that
file's Stage-3 amendment.

## Planned appendix / supplementary claims

| # | Planned claim (bounded) | Registry ID | Evidence path(s) | Boundary statement required |
|---|---|---|---|---|
| A1 | A six-query real-LLM multi-provider pairwise-judgment pilot shows directionally consistent structural patterns, presented only as a bounded addendum. | LLM-01 | `reports/multi_provider_repair_pilot_20260729T032348Z/` | Must state n=6, not a confirmatory study; must not claim generalization. |
| A2 | Cluster-aware (query-level, n=6) re-analysis is the only valid inference basis for any statistic derived from the real-LLM pilot's ~120 replicated rows. | LLM-02 | `reports/real_llm_clustered_reanalysis_20260730T023745Z/` | Must explicitly reject any row-level (n=120) significance claim as invalid; this is itself a documented prior error (see `docs/CONTRIBUTIONS.md` S1.2). |
| A3 (optional) | Independent commercial-solver (Gurobi) cross-validation confirms the SCIP exact-repair result on all 1,025 instances (0 mismatches); solver scaling data (SCIP intractable ~n=40, both solvers fail ~n=50). | SOLVER-01, SCALE-01 | `reports/gurobi_vs_scip_solver_cross_validation_20260731T162314Z/`, `reports/exact_solver_scaling_study_20260731T162314Z/` | `manuscript_applicable: false` in the registry -- include only as a footnote/appendix robustness note if at all, never as a numbered contribution; does not change any conclusion; see Section 6 of `MANUSCRIPT_PLAN.md` for why this is still excluded even though SN Computer Science is single-blind. |

## Planned tables

| Table | Content | Source table/data | Reuse basis |
|---|---|---|---|
| T1 | Vote-construction regimes (`ms2`/`ms1`/`ms1_drop_mutual`): min support, min margin, rule, analytical role | `reports/full_calibrated_core/` construction config | Adapt IJCS draft `tab:vote_construction_regimes` / `tab:preference_construction_regimes`, reconciled with JDIQ's regime naming (identical regime names confirmed used in both) |
| T2 | Datasets and prespecified evaluation settings (stored IDs, usable, depth, evaluated cells) | `reports/full_calibrated_core/`, `reports/final_revision_task1_pool_cutoff_20260715/` | Reuse JDIQ `tab:setup` verbatim (already precise and current) |
| T3 | Primary empirical findings (Holm-rejected cell counts, exact-repair confirmation) | `reports/full_calibrated_core/`, `reports/exact_open_source_ilp_repair_investigation/` | Reuse/extend JDIQ `tab:primary-findings`; elevate the exact-vs-greedy row per the reviewer lesson (do not present as a footnote) |
| T4 | Robustness and interpretation summary (exact repair, protocol families, pool robustness, baseline fairness, power/MDE, equivalence) | `reports/final_revision_task1_pool_cutoff_20260715/`, `reports/exact_open_source_ilp_repair_investigation/` | Reuse JDIQ `tab:robustness` verbatim |

## Planned figures

| Figure | Content | Source artifact | Reuse basis |
|---|---|---|---|
| F1 | Pipeline/audit schematic (construction -> repair -> extraction -> evaluation) | conceptual, redrawn | Adapt JDIQ `figure1.png` concept; simplify audit-taxonomy framing per reviewer lesson (must not read as decorative) |
| F2 | Conditional BM25 edge-weight share, raw vs. normalized, across datasets/regimes | `reports/full_calibrated_core/` | Reuse JDIQ `figures_v2/fig2_bm25_share.pdf` if license/authorship allows regeneration from the same underlying CSVs; else regenerate from source tables |
| F3 | Cyclic-query percentage before/after mutual-pair deletion, by dataset | `reports/full_calibrated_core/` | Reuse JDIQ `figure5.png` concept |
| F4 | Repaired-minus-unrepaired paired bootstrap $\Delta$nDCG forest plot (active `ms1` regime) | `reports/full_calibrated_core/` | Reuse JDIQ `figures_v2/fig7_bootstrap_forest.pdf` concept |
| F5 (appendix, new) | Exact-vs-greedy structural gap (removed weight comparison) | `reports/exact_open_source_ilp_repair_investigation/tables/structural_summary_greedy_vs_ilp.csv` | New figure -- not present in either prior manuscript; directly supports the elevated exact-repair contribution |

## Explicitly excluded repository studies (not evidence for this manuscript)

See `MANUSCRIPT_PLAN.md` Section 6 for the full rationale per item. Registry
IDs for completeness: `HEADROOM-01` (repository-scale oracle headroom,
NO-GO), `POLICY-01` (Outcome F / production policy selection),
`PIVOT-01`/`PIVOT-02`/`PIVOT-03` (consistency-aware active-acquisition
pivot), `DOC-01` (superseded `outputs/pub_vote_cmp_*` packages).

## Verification performed this stage

- Confirmed all ten evidence directories referenced above exist on disk
  (`ls -d`/`test -d`, not re-run).
- Confirmed `reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`
  contains the "1,025" optimality figure quoted above (`grep`).
- Cross-checked every number quoted in the "Planned main-paper claims"
  table against `papers/JDIQ_2026/manuscript/main.tex` verbatim (copied,
  not independently recomputed -- that manuscript's numbers were already
  extensively audited in prior repository-hygiene sessions and are the
  submitted, frozen record).
- No pytest run, no script executed to regenerate any statistic.

## Correctness-methods fix (2026-08-01)

See `CORRECTNESS_METHODS_FIX_CHANGELOG.md` for full traces of:

- SciDocs 10.8% (post-mutual `ms1` diagnostic) vs 11.7% (`ms1_drop_mutual`
  cyclic) — equality claim withdrawn;
- 1,026 nominal combinations → 1,025 exact instances (excluded:
  BRIGHT/`ms2`/`biology:0`, empty edge set).
