# Claims and Evidence

*Every claim below cites an exact artifact and, where a number is quoted,
the exact value as computed/verified in this repository. See
`reports/repository_scale_headroom_analysis/evidence_table.csv` and
`manuscript_tables/table_7_claims_and_evidence_status.csv` for the
machine-readable companion to this document.*

---

## Claim 1 — Structural consistency and retrieval effectiveness are different objectives

**Statement:** Graph repair reliably improves structural properties
(acyclicity, feedback-arc-set objective, removed inconsistent weight, SCC
structure) but these improvements do not reliably produce improvements in
downstream retrieval metrics (nDCG, MRR, Recall).

**Evidence:**
- Structural side: `outputs/pub_vote_cmp_all4/paper_package/tables/table_consistency_qrels_bew.csv` — BEW/PIC decrease after repair in every tested condition. Normalized removed weight ranges 0.029–0.080 of total graph weight under `ms1` (`papers/JDIQ_2026/manuscript/main.tex` line 357).
- Downstream side: `papers/JDIQ_2026/manuscript/main.tex` — *"no repaired-versus-unrepaired nDCG cell survives Holm correction in the canonical design, the larger-pool P>k study, or direct exact-repair checks."*
- Status: **Established** (both halves independently verified, not merely asserted — see the JDIQ manuscript's own methodology and this repository's repository-scale meta-analysis, which reuses the same underlying per-query tables).

## Claim 2 — Aggregate whole-graph repair is not reliably beneficial

**Statement:** Across datasets, candidate pools, construction regimes,
repair algorithms, and evaluation settings, beneficial and harmful
query-level effects are nearly symmetric in count, many queries are
exactly unaffected, and corrected significance analyses do not establish
reliable downstream improvement.

**Evidence:**
- JDIQ significance results (cited, not recomputed): 0/20 canonical active `ms1` cells, 0/60 canonical full, 0/110 larger-pool, 0/36 exact-repair canonical, 0/56 exact-repair larger-pool Holm-significant cells (`manuscript_tables/table_2_canonical_downstream_significance.csv`).
- Repository-scale query-level decomposition (this paper's own contribution, `manuscript_tables/table_4_benefit_harm_neutral_decomposition.csv`, `ALL`/`query-level` row): n=419, benefit 28.2% (95% CI [24.1%, 32.7%]), harm 27.2% (95% CI [23.2%, 31.7%]), neutral (exact zero) 44.6% (95% CI [39.9%, 49.4%]) — counts are near-symmetric between benefit and harm.
- **New, more precise finding than previously documented**: benefit and harm are near-symmetric in *count* but **not** in *magnitude* — mean benefit magnitude is +0.0054, mean harm magnitude is −0.0116 (harmed queries lose, on average, about **2.1x** as much as benefited queries gain). This asymmetry is worth reporting precisely rather than rounding away; see §8 (regime decomposition) discussion in `OUTLINE.md`.
- Status: **Established** (query-level, n=419, both count-symmetry and magnitude-asymmetry independently computed from raw data with proper CIs).

## Claim 3 — Oracle selection provides only negligible practical headroom

**Statement:** An oracle that chooses the better of preserve and repair
per query has positive expected headroom, but the effect (0.0025) is far
below the project's own 0.0207 minimum-detectable-effect, heavily
concentrated in the already-known high-cyclicity `ms1` condition, nearly
absent after mutual-edge dropping, and effectively zero in the
near-acyclic `ms2` condition.

**Evidence:**
- `reports/repository_scale_headroom_analysis/summary.json`, `query_level_headroom_RECOMMENDED`: headroom = 0.0025078, 95% CI [0.0020411, 0.0030189], n = 419 distinct queries.
- `reports/final_revision_task2_statistical_power_20260715/` + `papers/JDIQ_2026/manuscript/main.tex` line 429-430: Holm-adjusted 80%-power MDE = 0.0207 ("in the active larger-pool family").
- Ratio: 0.0025 / 0.0207 ≈ **0.121** — the oracle's average per-query advantage is roughly one-eighth of what this research program's own methodology treats as a reliably detectable effect.
- Regime decomposition (`manuscript_tables/table_3_oracle_headroom.csv`): `ms1` headroom 0.0041–0.0084 across datasets; `ms1_drop_mutual` 0.0000–0.0005; `ms2` ≈0.000001–0.000009 in every dataset.

**Required interpretive statements (do not omit any of these three):**
1. *Statistical nonzero does not imply practical importance.* The
   headroom's 95% CI excludes zero (it is a real, reproducible effect,
   not noise), but its magnitude is smaller than the smallest effect this
   same research program's own power analysis considers worth acting on.
   These are two different questions, and the paper must answer both,
   separately, explicitly.
2. *The oracle estimate is an upper bound unavailable to a real policy.*
   No real classifier has access to the ground-truth outcome at decision
   time; the oracle number is a ceiling, not an achievable target.
3. *A learned policy would necessarily recover only a fraction of this
   already tiny headroom.* This paper does **not** manufacture a specific
   "recoverable benefit under X% policy accuracy" number, because no
   defensible accuracy assumption exists for an unbuilt classifier (doing
   so would be exactly the kind of unsupported quantitative claim the
   task instructions prohibit). If a future draft wants such a number, it
   must come from an actually-trained-and-evaluated classifier, not a
   hypothetical accuracy figure.

Status: **Established** (headroom is real and precisely bounded; its
practical insignificance follows directly from comparison to an
independently-established, pre-existing threshold — not a new, ad hoc
bar invented for this paper).

## Claim 4 — Whole-graph repair utility is not predictably encoded in current observables

**Statement:** Existing graph, repair, confidence, and regime covariates
show negligible association with repair effect. Prior learned-selector
attempts also failed to establish practically useful selection.

**Evidence:**
- `manuscript_tables/table_5_feature_association_summary.csv`: repair cost r=0.0184 (p=0.00027, n=39,175), largest-SCC size r=0.0260 (p=4.0e-6, n=31,573), graph density r=0.0395 (p=1.5e-11, n=29,220) — all statistically significant only because of very large n, all practically negligible (r² < 0.2% of variance explained in every case). `is_cyclic` ANOVA: Cohen's d = 0.034 (roughly 6x below the conventional "small effect" threshold of 0.2).
- `manuscript_tables/table_6_previous_selector_attempts.csv` and `RELATED_WORK_POSITIONING.md`'s selector-attempt synthesis: four independent attempts (three prior/informal, one this paper's own rigorous repository-scale pass), none establishing a practically useful selector; the one attempt with real modeling effort found a fixed heuristic threshold beat every learned model.

**Required language (exact phrasing, do not deviate toward a stronger claim):**
- "not predictably encoded in the available pre-repair feature set"
- "no practically useful signal was detected"
- "the evidence does not justify learned whole-graph policy selection"
- **Do not** write "prediction is mathematically impossible," "no
  predictive relationship exists," or any equivalent universal-negative
  claim — the evidence supports a bounded, current-feature-set-scoped
  negative finding, not an impossibility proof.

Status: **Established** (as scoped above — negligible-association claim
is established; the broader "not predictable in principle" claim would be
**unsupported** and must not be made).

## Claim 5 — Cyclicity is a poor surrogate for retrieval harm

**Statement:** The fact that `ms1` has more oracle headroom than `ms2`
does not imply cycles reliably identify *when* repair helps — it is
equally consistent with cyclicity increasing the variance of the repair
effect (both help and harm) rather than its direction.

**Evidence and status — HYPOTHESIS SECTION, distinguish carefully from
established results above:**
- **Established, supports the variance-not-direction framing:** in `ms1`
  (highest headroom), benefit and harm counts are both elevated relative
  to `ms1_drop_mutual`/`ms2` (see per-dataset breakdown,
  `manuscript_tables/table_4_benefit_harm_neutral_decomposition.csv`,
  query-by-regime rows) — i.e., `ms1` has more of *both* outcomes, not
  predominantly more benefit.
- **Hypothesis, not established, must be labeled as such in the
  manuscript:** cycle removal addresses structural contradiction (the
  graph-level objective) without necessarily correcting the *evaluated*
  top-k relevance ordering (the retrieval-level objective) — these are
  different objectives operating on different parts of the ranking, and
  nothing in this repository's artifacts directly measures whether a
  removed edge was relevant to the top-k cutoff specifically versus deep
  in the ranking.
- **Hypothesis, not established:** some topologically-inconsistent edges
  may reflect genuine, context-dependent, non-transitive preference
  information (e.g. two documents are both excellent for different
  sub-aspects of a query) that repair incorrectly treats as noise to be
  removed rather than signal to be preserved. No artifact in this
  repository tests this directly; it is offered as an explanation
  consistent with the observed pattern, not a tested mechanism.
- **Do not claim causality.** All of the above are consistent
  explanations for an observed correlational pattern (higher cyclicity
  regime → higher variance in repair effect), not causally established
  mechanisms. The manuscript must use hedged language throughout this
  section ("consistent with," "one plausible explanation," "not directly
  tested here").

Status: **Partially established** (the variance-not-direction empirical
pattern is established from data; the proposed mechanisms explaining it
are hypotheses requiring future, targeted investigation, not established
results).
