# SN Computer Science Manuscript Plan (Stage 1 of 7)

This is a **foundation and scoping document**, not a draft. It establishes
what the manuscript will and will not claim before any prose is written.
Per the task brief for this stage: "This is a final audit and handoff
pass"-equivalent discipline applies here too -- nothing below should be
treated as settled prose to copy verbatim; it is the plan Stage 2 drafting
must follow.

Cross-references: [`EVIDENCE_MAP.md`](EVIDENCE_MAP.md) (claim-to-evidence
table), [`README.md`](README.md) (workspace/template provenance),
`manuscript/main.tex` (the initialized skeleton implementing this plan's
Section 4 outline).

---

## 1. Three possible titles

1. **"Structural Consistency Is Not Retrieval Utility: An Exact-and-Heuristic
   Audit of Preference-Graph Repair for Multi-Ranker Retrieval"**
   (used as the working title in `manuscript/main.tex`). Leads with the
   paper's organizing distinction, appropriate for a general-CS audience
   that may not know feedback-arc-set terminology on sight.

2. **"When Does Repairing a Preference Graph Help Retrieval? Exact and
   Heuristic Feedback-Arc-Set Evidence Across Four Benchmarks"**
   Frames the paper as answering a direct question, which pre-empts the
   Iran JCS "logical necessity" (C1) objection by signaling an empirical
   rather than definitional contribution.

3. **"Exact Minimum-Weight Feedback-Arc-Set Repair Does Not Rescue
   Retrieval Gains: A Construction-Sensitivity Study of Derived Preference
   Graphs"**
   Most specific and most defensive: puts the exact-SCIP finding (the
   strongest answer to the heuristic-artifact objection, C7/C8) in the
   title itself. Best choice if editorial fit review suggests reviewers
   need the null result signaled up front rather than discovered in
   Results.

**Recommendation:** Title 1 for the submission title (broadest, most
natural for a general CS venue); keep Titles 2 and 3 as documented
alternatives in case the handling editor requests a more specific title
during a revise-and-resubmit.

---

## 2. Precise research question

> Does enforcing acyclicity in a derived multi-ranker preference graph --
> via either heuristic (greedy cycle-peeling) or exact (SCIP-based
> minimum-weight feedback-arc-set) repair -- produce a statistically
> reliable improvement in downstream retrieval effectiveness (nDCG) once
> construction choices, paired inference, and multiplicity correction are
> made explicit, and if not, what does that imply about using structural
> graph consistency as a proxy for retrieval utility?

This intentionally does not ask "does repair help" (already rejected by
prior reviewers as inviting a trivial-sounding answer, C1) but asks a
narrower, methodologically loaded question that the four contributions
(Section 3) answer piece by piece. The abstract's four-part structure
(Purpose/Methods/Results/Conclusion, per SN Computer Science's submission
guidelines) should restate this question under "Purpose" without
compressing it into a slogan.

---

## 3. Principal contributions (four, maximum allowed)

1. **Exact-repair confirmation that the null result is not a
   heuristic-repair artifact.** SCIP-based exact MWFAS repair reaches
   proven optimality on 1,025/1,025 canonical query graphs and removes
   *less* total edge weight than greedy repair, yet the retrieval decision
   does not change (0/36 canonical, 0/56 larger-pool Holm-significant
   cells). This is the direct, evidence-based answer to the strongest
   prior-reviewer objection (Iran JCS C7/C8) and should be foregrounded,
   not treated as a robustness-check footnote the way it was in the
   rejected IJCS draft.
2. **A four-benchmark, three-regime empirical demonstration that
   structural repair is genuinely active but not a reliable retrieval
   intervention.** Repair measurably removes cyclic edge mass and, under
   $P>k$ evaluation, changes top-$k$ membership at a 10.6% mean rate
   (**Stage-4/5 clarification, confirmed correct as stated but scope was
   ambiguous here**: this rate is pooled across all three
   vote-construction regimes, not `ms1`-only -- restricting to `ms1`
   alone gives 26.2%, a materially different number; see
   `RESULTS_CROSS_CHECK.md` and `result_claims.yaml`) -- yet no
   repaired-vs-unrepaired nDCG cell family (canonical, larger-pool, or
   exact) survives Holm correction.
3. **A construction-sensitivity finding that vote-construction regime, not
   the repair algorithm, is the dominant driver of graph cyclicity and of
   whether repair has any opportunity to act at all** (e.g. raw BM25
   edge-weight share 0.988 vs. 0.512 normalized; cyclicity swings of
   60-90 percentage points between regimes on the same underlying
   documents).
4. **A restrained, evidence-bounded methodological conclusion and
   practitioner checklist** that explicitly separates structural
   consistency from downstream retrieval utility as two distinct quality
   dimensions, with a narrowly bounded (six-query) real-LLM addendum that
   is never treated as confirmatory.

**Explicitly not a contribution:** a new ranking algorithm, a new fusion
method, a state-of-the-art reranking claim, or a claim that the
seven-dimension audit taxonomy (if retained from JDIQ) is itself a novel
theoretical framework rather than an organizing device for reporting
already-necessary diagnostics.

---

## 4. Section-by-section outline

Matches `manuscript/main.tex`'s section skeleton exactly.

1. **Introduction** -- motivate preference graphs as derived data
   artifacts; state the research question (Section 2); state the <=4
   contributions (Section 3); explicit one-sentence disclaimer that this
   is not a state-of-the-art reranking proposal.
2. **Related Work** -- rank aggregation / feedback-arc-set; probabilistic
   pairwise models (Bradley-Terry, Rank Centrality); graph-free fusion
   (RRF, CombSUM, Borda); LLM-as-judge and pairwise-ranking positional-bias
   literature; brief nod to LLM reranking paradigms (RankGPT-style,
   RankZephyr, Setwise) for a general-CS audience, framed as adjacent, not
   competing, work.
3. **Preference-Graph Construction and Repair** -- formal graph definition;
   the three vote-construction regimes; the MWFAS objective presented with
   **greedy and exact SCIP as co-equal repair methods from the first
   mention**, not exact-as-afterthought; ranking extraction (Copeland,
   balance, graph-free baselines).
4. **Experimental Design** -- four benchmarks; stored score signals;
   canonical vs. larger-pool ($P>k$) cells; Holm-corrected paired nDCG as
   the single primary confirmatory test; every other check (bootstrap,
   exact repair, alternative pools, power analysis) explicitly labeled a
   robustness check, not a separate headline family; explicit boundary
   statement for the six-query real-LLM pilot.
5. **Results** (four subsections, see Section 5 below for exact
   table/figure assignment):
   5.1 Construction dominates graph structure.
   5.2 Repair is structurally active; retrieval gains do not survive Holm
   correction.
   5.3 Exact SCIP repair confirms the null is not a greedy-heuristic
   artifact.
   5.4 Robustness: alternative pools, added baselines, power/MDE, narrow
   equivalence.
6. **Discussion** -- state the restrained thesis in the paper's own words
   (see Section 11); the structural-consistency-vs-retrieval-utility
   distinction as the organizing idea; a short practitioner audit-logic
   list; brief, explicitly bounded real-LLM addendum discussion (2-3
   sentences maximum, not a subsection).
7. **Limitations** -- finite power for small effects; benchmark/ranker
   scope; bounded real-LLM evidence; candidate-pool sensitivity; no
   transfer claim to learned fusion, cross-encoder reranking, or online
   evaluation.
8. **Conclusion** -- one paragraph restating the thesis; one sentence on
   what would be required to overturn it (falsifiability framing), not a
   future-work wish list.
9. **Data Availability and Reproducibility** -- public-benchmark citations;
   repository URL; explicit "no paid API calls required to regenerate
   reported statistics" statement (true for every main-paper number, per
   `EVIDENCE_MAP.md`).
10. **Declarations** (Funding, Conflict of interest, Data and code
    availability) -- required by the template's `\backmatter`.

---

## 5. Planned tables and figures

Full detail with exact source paths is in
[`EVIDENCE_MAP.md`](EVIDENCE_MAP.md#planned-tables) --
summary: **4 tables, 4 main-paper figures, 1 appendix figure.** T1
(vote-construction regimes), T2 (datasets/settings, reused verbatim from
JDIQ), T3 (primary findings, exact-repair row elevated), T4 (robustness
summary, reused verbatim from JDIQ). F1 (pipeline schematic), F2 (BM25
raw-vs-normalized share), F3 (cyclicity by regime), F4 (bootstrap forest
plot), F5-appendix (exact-vs-greedy structural gap, new).

---

## 6. Scope: in main paper, in appendix, excluded entirely

### 6.1 Exact experiments included in the main paper

- `reports/full_calibrated_core/` -- primary four-dataset canonical
  package (construction, repair, retrieval evaluation).
- `reports/normalization_protocol_audit_20260714/` -- raw-vs-normalized
  robustness.
- `reports/candidate_pool_conditional_audit_20260714/` -- candidate-pool
  robustness.
- `reports/final_revision_task1_pool_cutoff_20260715/` -- larger-pool
  ($P>k$) study.
- `reports/exact_open_source_ilp_repair_investigation/` -- exact SCIP
  repair (now a headline result, not a robustness footnote).
- `reports/final_revision_task4_exact_baseline_fairness_20260715/` --
  exact-vs-greedy-vs-unrepaired three-way fairness comparison.

### 6.2 Experiments placed in an appendix / supplement only

- `reports/multi_provider_repair_pilot_20260729T032348Z/` and
  `reports/real_llm_clustered_reanalysis_20260730T023745Z/` -- the
  six-query real-LLM pilot and its mandatory cluster-aware reanalysis.
  Appendix-only, with an explicit boundary statement in both the appendix
  heading and wherever the main text alludes to it.
- Additional independently-defined normalization/threshold protocol
  families beyond the primary one, if the main Results section would
  otherwise exceed a reasonable table count -- move the secondary protocol
  families to a supplement table, keeping only the primary-protocol
  numbers in the main Results tables (mirrors JDIQ's existing supplement
  split).
- Full power/MDE derivation detail and the narrow equivalence-testing
  table, if reviewers or page budget require compressing Table T4 in the
  main text.

### 6.3 Repository studies excluded entirely (not evidence for this paper)

| Study | Registry ID | Why excluded |
|---|---|---|
| Repository-scale oracle-headroom analysis (NO-GO) | HEADROOM-01 | Different research question (predictive modeling of *when* to repair from pre-repair covariates at repository scale); belongs to the separate `papers/negative_result_2026` track; including it would blur this paper's single research question. |
| Production policy selection / "Outcome F" | POLICY-01 | Entirely different research thread (adaptive LLM-judge budget allocation under a fixed acquisition policy), sharing no code path with graph repair. `docs/CONTRIBUTIONS.md` §1.7 and `docs/AGENT_GUIDE.md` both flag this as a common source of confusion because of a **literal naming collision**: the manuscript's own audit-taxonomy dimension "F" (if the taxonomy is retained) and this thread's "Outcome F" are unrelated. If any table in this manuscript uses lettered dimensions, do not reuse the letter "F" as a taxonomy label without an explicit disambiguating footnote, or better, avoid lettered dimensions in favor of named ones. |
| Consistency-aware active-acquisition pivot (offline pair-selection, regularized aggregation, stopping rule) | PIVOT-01, PIVOT-02, PIVOT-03 | A separate research question (adaptive judge/pair acquisition under budget) that reuses the phrase "consistency-aware" for an unrelated concept -- structural graph consistency (this paper) vs. adaptive-acquisition policy consistency (that thread). `README.md` in the main repository already carries an explicit warning about this exact overload; this manuscript must not conflate the two. |
| Counterfactual multi-provider benchmark / Cohere native-transport wiring | n/a (engineering, `docs/PROJECT_STATUS.md` issue #48) | Unfinished engineering work, not a research finding; no claim in this manuscript depends on it. |
| `outputs/pub_vote_cmp_all4/`, `outputs/pub_vote_cmp_v2/`, `outputs/q1_journal_package/` | DOC-01 | Superseded pre-`full_calibrated_core` evidence packages; zero citations in the current JDIQ manuscript; must not resurface here either. |
| The abandoned "CARB" (Consistency-Aware Reranking Benchmark) resource-paper framing | n/a | `papers/JDIQ_2026/CANONICAL_PAPER_STORY.md` (explicitly self-marked superseded) proposed releasing a curated benchmark under this name; that plan was abandoned before the JDIQ pivot and no such benchmark artifact exists in the repository. Do not resurrect the name or the framing. |
| Repair-selector-mining / learned repair-decision gates | n/a (subsumed under POLICY-01 negative result) | No validated real-query selector exists; including this would invite exactly the "actionable criterion" claim (C2/C11) that the evidence does not support. |
| HodgeRank, Plackett-Luce, RankZephyr/RankLLM as *implemented* methods | n/a | Deliberately absent from the codebase (`docs/CONTRIBUTIONS.md`, `reports/final_revision_task9_.../tables/baseline_completeness_decision.md`). Citable in Related Work as literature; must not be implied as evaluated methods. |
| Gurobi cross-validation as a **numbered contribution or headline evidence** | SOLVER-01, SCALE-01 | `manuscript_applicable: false` in the registry. For JDIQ (double-blind) this was excluded for anonymity reasons (a commercial, identity-linkable dependency). SN Computer Science is single-blind, so the anonymity reason does not strictly apply -- **but the exclusion still holds** for a different, still-valid reason: the registry itself states this evidence "confirms an existing result; does not change any conclusion," and it requires a commercial license readers may not have, working against the reproducibility statement in Section 9 of the outline. It may appear as a one-sentence appendix footnote ("independently confirmed with a commercial solver, see repository artifact X") but must never be a contribution, a table, or a figure. |

---

## 7. How this plan addresses the prior reviewer concerns

Source: `docs/historical/REVIEWER_CONCERN_GAP_AUDIT.md` (14 Iran JCS
concerns, audited 2026-07-26). This manuscript is a new venue and a
substantially reframed contribution, not a resubmission, but the
underlying evidence is the same repository and the same concerns would
recur if not addressed structurally.

| Concern | This plan's answer |
|---|---|
| C1 (finding is a "logical necessity") | Research question (Section 2) is framed empirically, not definitionally; Contribution 1 (exact-repair confirmation) is a genuine empirical result no prior reviewer anticipated. |
| C7/C8 (no exact baseline; weak gains may reflect the heuristic) | **Directly resolved.** Contribution 1 and Results 5.3 exist specifically to close this gap; exact SCIP repair is a headline result, not a footnote. |
| C5 (hybrid fusion formula may distort repair effects) | Already substantially addressed in JDIQ via $\alpha$-sweeps and reported graph-only rows (see Method Eq. for $h_q(d)$); reuse that framing, keep $\alpha=0.3$ as the primary value with the sweep noted as a robustness check. |
| C6 (graph-only / alternative fusion undertested) | Graph-only method keys already exist and are reported in the canonical package; Results 5.4 should explicitly include a graph-only row in Table T3 or T4. |
| C9/C10 (Copeland/balance underjustified; PageRank/HodgeRank) | PageRank, Rank Centrality, and Bradley-Terry are already implemented and evaluated; cite them in Related Work / Table T4 context; HodgeRank stays an explicit, justified exclusion (see Section 6.3). |
| C4/C13 (real-LLM evidence too limited; dataset-specific concerns) | Explicitly bounded, not overstated: the six-query pilot is appendix-only with a mandatory cluster-aware-inference caveat (Contribution 4); the four-benchmark main package already spans four distinct domains, stated plainly as the scope, not oversold as universal. |
| C2/C11 (no actionable criterion for when repair helps) | Not claimed to be resolved. The manuscript should state directly that no validated real-query criterion for "should I repair?" exists yet, and that this is future work -- this is honest given `POLICY-01`'s negative result and avoids re-inviting the same objection with a false promise. |
| C12 (gains minimal/statistically uncertain) | This is now the paper's *central, embraced* finding rather than a weakness to explain away -- Holm-corrected null results are reported as the thesis, not hedged. |
| C14 (repetitive / overstates contribution) | Four contributions maximum (Section 3), one restrained thesis statement (Section 11), no repeated null-result restatement across more than the Results + Discussion + Conclusion sections already required by the outline. |
| C3 ("outdated," non-LLM pipeline) | Acknowledge directly in Introduction/Limitations that the main evidence stream is score-derived (BM25/TF-IDF/MiniLM), with the real-LLM pilot as a bounded modern-paradigm check -- do not claim the classical pipeline is state-of-the-art; frame it as the controlled setting that makes the construction-sensitivity analysis (Contribution 3) tractable. |

---

## 8. Prior-manuscript reuse plan

### 8.1 From `papers/_archive/IJCS_early_draft.zip` (rejected IJCS draft)

**Reuse, with reconciliation:**
- Related Work prose on rank aggregation, preference modeling
  (Bradley-Terry, Rank Centrality), and graph-based ranking -- largely
  reusable as-is; refresh citations against the merged `references.bib`
  and add the LLM-reranking-paradigm citations already merged in (RankGPT,
  RankZephyr, Setwise) for a general-CS audience.
- Method section formalism: the $G_q=(V_q,E_q,w_q)$ definition, the
  three-stage framework description (construct -> repair -> extract), and
  Algorithm 1 (preference-graph construction) pseudocode structure.
  **Must reconcile:** Algorithm 2 (repair) currently shows only greedy
  cycle-peeling; add exact SCIP as a co-equal branch, not a caption
  footnote, per Contribution 1.
- Dataset/ranker description table structure (`tab:datasets_and_rankers`)
  -- reuse the table shape, replace all numbers with JDIQ's precise,
  already-verified `tab:setup` values (see Section 8.2).
- Vote-construction-regime definitions and rationale prose (`ms1`/`ms2`/
  `ms1_drop_mutual`) -- directly reusable; regime names and semantics are
  unchanged in JDIQ.

**Do not reuse:**
- Every Results-section table and number (Table `tab:overall_retrieval_performance`,
  `tab:cyclicity_structural_summary`, `tab:repair_effect_delta_ndcg`) --
  these come from an older, less rigorous protocol (no Holm correction
  applied to the headline claims, no larger-pool $P>k$ separation, no
  exact-repair check) and are **superseded** by JDIQ's numbers. Mixing the
  two would silently reintroduce exactly the incomparable-protocol problem
  flagged in Section 10 below.
- The "HotpotQA shows a clearly positive effect" framing and any language
  implying repair "helps in some cyclic settings" without the Holm
  qualifier -- this is the framing that drew reviewer objections and is
  contradicted by the more careful JDIQ analysis of the same underlying
  phenomenon.
- The Conclusions/Future Research framing that treats "comparing greedy
  against exact repair" as future work -- that comparison is now complete
  and is this manuscript's headline contribution.

### 8.2 From `papers/JDIQ_2026/manuscript/main.tex` (current submitted manuscript)

**Reuse, largely as-is:**
- Abstract's core empirical claims (adapted into the new structured
  Purpose/Methods/Results/Conclusion format required by SN Computer
  Science, since JDIQ's abstract is unstructured free prose for ACM
  format).
- All headline numbers: BM25 share (0.988/0.512), cyclicity percentages,
  Holm-rejected cell counts (0/20, 0/60, 0/110, 0/36, 0/56), CombSUM/RRF
  means (0.554/0.546), power/MDE figures (0.0036/0.0207 -- **superseded,
  Stage 4**: the 0.0207 MDE figure does not reproduce from the current
  canonical `mde_per_cell.csv`; the manuscript uses the reproducible
  value 0.0201 instead, see `RESULTS_CROSS_CHECK.md`), equivalence
  counts (13/110, 32/110).
- Table `tab:setup` (datasets and prespecified evaluation settings) --
  reuse verbatim.
- Table `tab:robustness` (compact robustness/interpretation summary) --
  reuse verbatim.
- The Holm-correction / paired-bootstrap / larger-pool-study experimental
  design description (Section 4/"Experimental Design").
- The Limitations section's five bullet points -- reusable near-verbatim,
  since the underlying evidence boundaries have not changed.
- Data Availability and Reproducibility section structure.

**Reuse with expansion, not verbatim:**
- The seven-dimension audit taxonomy (Table `tab:dq-taxonomy`) -- JDIQ
  presents this compactly for a data-quality-focused ACM venue; for a
  general-CS SN Computer Science audience, either (a) keep it but add one
  worked example per dimension so it does not read as "a superficial
  wrapper" (an explicit instruction for this stage), or (b) fold its
  content into ordinary Method/Results prose without the letter-lettered
  table if the taxonomy format itself invites the wrapper objection. Prefer
  (a): expand with concrete per-dimension pointers to the specific
  table/figure that operationalizes it, and drop the letter "F" naming to
  avoid the Outcome-F collision (Section 6.3).
- The Discussion's three practical implications -- reusable in substance,
  should be rewritten as the practitioner audit-logic list (Section 4,
  Discussion) with the exact-repair finding folded in as a fourth item
  ("repair quality and downstream utility must be reported separately,
  and this now includes exact-vs-heuristic repair quality, not only
  structural-vs-retrieval outcome").

### 8.3 From `docs/historical/REVIEWER_CONCERN_GAP_AUDIT.md`

Not prose-reusable (it is an internal audit document, not manuscript
text), but its concern-by-concern evidence inventory (Section 5/6 of that
file) is the authoritative source for exactly which existing artifacts
answer which prior objection -- consulted directly to build Section 7 of
this plan.

---

## 9. Claims that must not be made

1. "Graph repair improves retrieval" or "repair improves retrieval
   quality," stated without the Holm-correction qualifier -- contradicted
   by the central evidence.
2. "Structural consistency predicts / is a reliable proxy for retrieval
   quality" as a general claim -- contradicted; the paper's whole thesis
   is the opposite.
3. Any framing of the method as state-of-the-art reranking, a new ranking
   algorithm, or a production-ready system.
4. Any suggestion that the seven-dimension taxonomy (if retained) is a
   free-standing theoretical contribution rather than an operational
   reporting device tied to specific measured diagnostics.
5. "The null result could still be a weak-heuristic artifact" -- directly
   refuted by the exact-SCIP evidence; do not hedge on this point once
   Contribution 1 is stated.
6. "The six-query real-LLM pilot confirms / validates / generalizes the
   classical findings" -- must be stated as directional-only, bounded,
   appendix-scoped evidence.
7. Treating the real-LLM pilot's ~120 replicated rows as 120 independent
   queries (n should be 6, cluster-level) -- this is a **documented past
   error** (`docs/CONTRIBUTIONS.md` §1.2, corrected by `LLM-02`) and must
   never resurface in any new prose.
8. "A learned or production policy selector successfully decides when to
   repair" -- false; that is a separate, negative-result research thread
   (`POLICY-01`) not part of this manuscript's evidence base at all.
9. Any specific numeric result copied from the IJCS draft's Results tables
   (e.g. mean nDCG 0.3068, $\Delta$nDCG $+0.016713$ for HotpotQA) -- these
   come from a superseded protocol; only JDIQ-sourced numbers may appear.
10. Any claim that depends on Gurobi as evidence, beyond a single bounded
    appendix footnote (Section 6.3) -- never a table, figure, or numbered
    contribution.
11. Reviving the "CARB" benchmark name or claiming a benchmark resource is
    being released -- no such artifact exists; the plan was abandoned.
12. Overclaiming dataset/domain generality beyond the four tested
    benchmarks (SciDocs, FiQA, HotpotQA, BRIGHT) and the tested
    construction regimes -- match JDIQ's existing Limitations language.

---

## 10. Evidence inconsistencies to resolve before drafting

1. **BRIGHT benchmark citation-key mismatch.** The IJCS draft cites the
   published ICLR 2025 spotlight version (`su2025bright`,
   `openreview.net/forum?id=ykuc5q381b`); JDIQ cites the 2024 arXiv
   preprint (`su2024bright`, `arXiv:2407.12883`) of the same paper, same
   authors. Both entries currently coexist in the merged
   `manuscript/references.bib` (seed pool, intentional for Stage 1). **Must
   resolve to exactly one key before drafting** -- recommend the published
   ICLR 2025 version (`su2025bright`) as the more citable, permanent
   record, and delete `su2024bright` plus retarget every `\cite` to the
   surviving key.
2. **IJCS-draft vs. JDIQ result tables are not directly comparable and
   must not be merged or averaged.** The IJCS draft's cyclicity and
   $\Delta$nDCG numbers come from an evaluation design that does not
   separate canonical $P=k$ from larger-pool $P>k$ cells and does not
   apply Holm correction to the headline claim; JDIQ's numbers do both.
   Any apparent discrepancy between the two documents' cyclicity
   percentages for the same dataset (e.g. IJCS's SciDocs `ms1` cyclic
   87.50% vs. JDIQ's own construction-quality numbers) is very likely a
   protocol-scope difference, not a data error -- but this should be
   explicitly re-verified against `reports/full_calibrated_core/`'s
   current tables before either number is quoted, rather than assumed.
3. **The seven-dimension audit taxonomy's letter "F" collides with the
   unrelated "Outcome F" policy-selection thread's own lettering** (see
   Section 6.3, and `docs/CONTRIBUTIONS.md` §1.7's explicit naming-note,
   added during a prior repository-hygiene pass specifically because a
   hostile fresh-reader audit flagged this exact collision). Resolve
   before drafting by either renaming the taxonomy dimensions (named, not
   lettered) or adding an explicit one-sentence disambiguation the first
   time "Dimension F" appears.
4. **Funding/acknowledgment statement not yet confirmed.** The IJCS draft
   states "Not applicable" for funding; verify this is still accurate
   before the Declarations section is finalized (SN Computer Science,
   being single-blind, will show this text to reviewers, unlike JDIQ's
   withheld-for-anonymity acknowledgments).
5. **`sn-basic` vs. another reference style has not been confirmed against
   a live, currently-open SN Computer Science article** (the submission
   guidelines page did not name a specific `.bst` file; `sn-basic` is
   inferred from the "numeric, consecutively numbered" description, which
   matches the template's own description of that style). Recommend
   checking one or two recently published SN Computer Science articles'
   reference formatting directly before final submission.

---

## 11. Scope statement (paper identity before prose drafting)

This will be a **rigorous empirical and computational study**, not an
algorithm paper and not a benchmark-resource paper. Its identity, in one
sentence, matches the thesis given in the task brief:

> Enforcing acyclicity in derived preference graphs produces genuine
> structural changes, but exact and heuristic repair do not yield a
> statistically supported general improvement in information-retrieval
> effectiveness -- structural consistency is therefore not a reliable
> surrogate for downstream retrieval utility.

Everything in Sections 1-10 above exists to keep the eventual manuscript
inside that sentence: four bounded contributions, one primary confirmatory
test (Holm-corrected paired nDCG) with everything else labeled a
robustness check, one appendix-only bounded LLM addendum, and an explicit
exclusion list for every adjacent-but-unrelated repository research
thread. Stage 2 drafting should treat any proposed addition that does not
directly serve this sentence as out of scope by default.

## 12. Readiness checklist for Stage 2

- [x] Repository inspected: canonical source/experiments/results,
      exact-vs-greedy evidence, statistical analyses, real-LLM evidence,
      exploratory/negative-result studies, and status-labeling
      documentation all located and read (this pass).
- [x] Both named prior manuscripts located and read in full (IJCS draft,
      JDIQ current submission); IP&M/JIIS/Iran JCS rejection history
      located and read (`docs/historical/REVIEWER_CONCERN_GAP_AUDIT.md`).
- [x] Official SN Computer Science LaTeX template verified against a live
      Springer Nature source and downloaded fresh; confirmed
      content-identical to the copy already vendored in this repository.
- [x] `papers/SNCS_2026/` workspace initialized with template, skeleton
      `main.tex`, seed `references.bib`, this plan, and the evidence map.
- [x] Claim-to-evidence table built and cross-checked against
      `docs/claim_evidence_registry.yaml`.
- [x] Forbidden-claims list compiled from `docs/CONTRIBUTIONS.md` §3,
      `papers/JDIQ_2026/CANONICAL_PAPER_STORY.md`'s prohibited-claims
      table, and the reviewer-concern audit.
- [ ] **Not done, and correctly deferred to Stage 2+:** any actual prose
      drafting, figure regeneration, or bibliography pruning.
