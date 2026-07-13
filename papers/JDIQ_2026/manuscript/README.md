# JDIQ Manuscript Workspace

**Status: complete first draft.** All 13 main sections, the Abstract, CCS concepts, keywords, and the Data Availability/Reproducibility section are now drafted prose. Two figures (Figure 5, pooled baseline bar chart; Figure 6, failure-class distribution) remain clearly marked placeholders pending regeneration from canonical data already present in the corresponding tables — see "Remaining figure/table TODOs" below. This is a first-draft pass prioritizing completeness and factual accuracy over prose polish, per this task's explicit instructions; a further consistency/style revision pass is expected before submission.

---

## What is in this directory

| File | Status |
|---|---|
| `main.tex` | Compilable ACM `acmart` skeleton (`manuscript,anonymous,review` mode). **All of §1–§13 are now drafted prose**, plus Abstract, Data Availability/Reproducibility, and an anonymized Acknowledgments placeholder. 9 numbered equations, 10 tables, 6 real figures + 2 clearly marked placeholders (Figures 5 and 6). |
| `references.bib` | 16 entries, all actually `\cite{}`-d in the manuscript. Sourced from the rejected IJCS submission's `references.bib` (verified DOI-complete) plus one independently verified primary source (`fox1994combination`, CombSUM). |
| `README.md` | This file. |
| `INTRODUCTION_EVIDENCE_MAP.md` | Every empirical/quantitative sentence in §1 traced to a canonical source file, with claim type, confidence, and caveats. |
| `FULL_DRAFT_EVIDENCE_MAP.md` | Every major empirical claim in §5–§13 and the Abstract traced to source file, table/row, sample size, caveat, and manuscript location. |
| `RESULTS_EVIDENCE_MAP.md` | The detailed R1–R9 evidence inventory that `FULL_DRAFT_EVIDENCE_MAP.md` builds on for §5–§9. |
| `RESULTS_SECTION_PLAN.md` | The structural plan §5–§9's prose follows (central question, findings, tables/figures, word budgets per section). |
| `FIGURE4_FINAL_DECISION.md` | Final specification for Figure 4 (bootstrap forest plot), reaffirmed after §1–§4 were completed. |
| `REVIEWER_CONCERN_COVERAGE.md` | Coverage matrix for the 10 prior reviewer concerns, now with a final-draft disposition table (8 fully resolved, 2 honestly left open by design). |
| `IJCS_REUSE_AUDIT.md` | Section-by-section audit of the rejected IJCS manuscript, with reuse disposition for each passage; updated with two bibliography corrections. |
| `integrity_audit/` | Dedicated audit of the external-solver dependency and the CombSUM citation, whose conclusions were applied to `main.tex` in an earlier pass (Table 4 patch, CombSUM citation, regime-invariance disclosure). |

---

## Compilation

Attempted with `tectonic` (available locally; bundles `acmart.cls` and `ACM-Reference-Format.bst`, so no separate TeX Live install was required).

Command used:

```bash
cd papers/JDIQ_2026/manuscript
tectonic main.tex
```

**Result: compiled successfully** after one fix. `main.pdf` (12 pages, 672,820 bytes) was produced with no errors.

One real error was hit and fixed during this task: the first draft omitted `\begin{document}` entirely (title/author/abstract/`\maketitle` were placed directly after the preamble). Tectonic reported `LaTeX Error: Missing \begin{document}` at the line containing `\begin{abstract}`. Fix: inserted `\begin{document}` immediately before `\begin{abstract}` (matching standard `acmart` ordering: CCS/keywords/title/author/affiliation before `\begin{document}`, then abstract/`\maketitle`/sections inside it). Recompiled clean on the next attempt.

Remaining warnings after the fix (all cosmetic, expected for a draft full of TODO placeholder tables and long file-path `\texttt{}` spans, not blocking):
- Several `Overfull \hbox` / `Underfull \hbox`/`\vbox` warnings, concentrated in the placeholder tables (§3–§9) and the wide file-path strings inside `\texttt{}` in TODO notes.
- Font-substitution warnings for the Libertine/Biolinum OpenType fonts (`libertine.sty`), which are informational under Tectonic's font backend and did not prevent typesetting.
- No missing-figure errors: all four `\includegraphics` calls resolved correctly against `../../../figures/manuscript/*.png` from the `papers/JDIQ_2026/manuscript/` working directory.

**Recompiled after the bibliography correction below** (`burges2005learning`/`su2024bright` swap): still compiles clean, **zero undefined citations**. BibTeX (`ACM-Reference-Format.bst`) reported 3 harmless style-completeness warnings, not errors: "empty address in burges2005learning" (the entry has no `address` field — not fabricated here since the source-provided entry didn't include one), and "no number/volume" + "page numbers missing" for `su2024bright` (expected for an arXiv preprint, which has neither). None of these block compilation or indicate a wrong/missing reference. Intermediate build files (`.aux/.bbl/.blg/.log/.out`) were removed after verification; only `main.pdf` is kept as evidence of a clean build.

**Recompiled again after writing §2–§4** (Sections 2–4 pass). One real error was hit and fixed: an explicit `\usepackage{amssymb}` added for equation notation clashed with `acmart`'s own internal load of `amssymb` (`LaTeX Error: Command \Bbbk already defined`). Fix: removed the explicit `amssymb` load (kept `amsmath`, which does not conflict) with a comment explaining why. Recompiled clean on the next attempt: **19 pages, zero undefined citations, zero undefined references, zero multiply-defined labels** (checked programmatically against `main.log`, not just visually). Two new entries (`cormack2009rrf`, `thakur2021beir`) were added to `references.bib` for citations introduced in §3–§4; both are DOI-complete or, for the NeurIPS Datasets-and-Benchmarks-track `thakur2021beir`, use only fields that entry type actually has (BibTeX's "empty address/publisher" and "missing page numbers" warnings for it are expected for that venue, not errors). A citation-accuracy bug was also caught and fixed during the audit: an early draft cited `cormack2009rrf` (the RRF paper) for the CombSUM baseline, which is incorrect — CombSUM's original citation is not yet in `references.bib`, so the citation was removed and replaced with an inline `TODO` rather than left wrong or fabricated.

---

## References requiring manual verification before submission

**Update (corrected after initial draft):** two entries inherited from the IJCS `references.bib` were flagged as needing verification and have since been corrected:

- `burges2010ranknet` (Burges 2010 MSR technical report, "From RankNet to LambdaRank to LambdaMART: An Overview") was cited at the one place in §1 that discusses classical pairwise learning-to-rank establishing the paradigm — but the manuscript does not discuss LambdaRank or LambdaMART specifically anywhere, so citing the 2010 overview report there was the wrong reference. It has been **replaced with `burges2005learning`** (Burges et al., ICML 2005, "Learning to Rank Using Gradient Descent" — the original RankNet paper, DOI `10.1145/1102351.1102363`), which matches what the sentence actually asserts. The 2010 overview report has been **removed from `references.bib` entirely** (it is not cited anywhere in the current draft, and keeping an uncited entry was flagged as an error); it should only be re-added if a future revision explicitly discusses LambdaRank/LambdaMART, and even then without a fabricated DOI (technical reports of this kind typically don't have one).
- `su2025bright` (BRIGHT, cited as an ICLR 2025 OpenReview submission with `note = {Spotlight}`, no DOI) has been **replaced with `su2024bright`**, the verified arXiv preprint (`arXiv:2407.12883`, `cs.IR`, 2024) — the ICLR spotlight/acceptance status and any resulting DOI were not independently confirmed, so the arXiv entry (which is directly verifiable and does not claim a DOI it doesn't have) is used instead.
- All other 11 entries have complete, verified DOIs and are standard, well-established references (ACM/IEEE/Springer/Biometrika/ACL Anthology) requiring no further action.
- `references.bib` now contains exactly the 13 entries actually `\cite{}`-d in `main.tex` §1 — no uncited entries.

---

## Known open items carried from this task (not resolved here, by design)

1. **Figure/table numbering drift.** `FIGURE_PLAN.md`/`SECTION_EVIDENCE_MAP.csv` call the bootstrap ΔnDCG forest plot "Figure 4"; `FIGURE_SPECIFICATIONS.md` numbers it "F05" and reassigns "F04" to a different scatter plot. `main.tex` follows the majority numbering (Figure 4). See `papers/JDIQ_2026/figure4_evidence/FIGURE4_COMPARISON_SELECTION.md` §1 for the full explanation from an earlier evidence-collection task in this same workspace.
2. **Figures still live at repository root** (`figures/manuscript/*.png`), not inside `papers/JDIQ_2026/figures/`. `main.tex` references them via a relative path (`../../../figures/manuscript/...`) with an explicit `TODO` comment at each `\includegraphics` call. Per task instructions, no binary figure files were copied or moved in this task.
3. **`fig_mean_ndcg_hybrids.png` is a partial/earlier asset** per `FIGURE_PLAN.md`'s own status table ("Partial; needs extension") — flagged in its `main.tex` placeholder caption rather than treated as final.
4. **CARB is a proposed schema/release plan, not a packaged public release** (`PROJECT_STATUS.md`: CARB readiness 35%, "feature files packaged: Not built"). The Introduction's contribution list says "the release of... CARB" in a forward-looking sense consistent with `CANONICAL_PAPER_STORY.md`; authors should confirm packaging is complete by submission time or soften the tense.
5. **§5–§13 remain unwritten.** This was an explicit scope boundary of this pass ("Do not write Results. Do not write Discussion."), not an oversight.
6. **RESOLVED (integrity audit + this pass).** The "exact" repair variants beyond the in-repository brute-force solver (`exact_scc_dp20`, `lrta_external`, `wmsf_external`, `ipsns_external`) were traced to the manuscript author's own separate, unpublished, MIT-licensed public GitHub repository (`minimum-weighted-fas-heuristics`) — see `integrity_audit/EXTERNAL_SOLVER_IDENTITY.md`. Because that repository is registered under the real (currently anonymized) author's identity, citing or linking it in this double-blind submission would deanonymize it. **Action taken:** the four `$\dagger$`-marked rows were removed from Table 4 in `main.tex`; only the two fully in-repository procedures (greedy; exact-for-small-components + greedy fallback) remain, with a qualitative, unnamed sentence noting that a bounded robustness check against additional solvers showed the same pattern and will be cited in full at camera-ready. See `integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md` for the full option analysis.
7. **RESOLVED.** The in-repo Gurobi-based ILP formulation (`src/consistency_ranker/mwfas_solver.py`, `solve(method="ilp")`) is confirmed unused by any committed result table (also independently corroborated by the sibling repository's own docs, which state Gurobi is not installed there either). `main.tex` §4.6 states this precisely and no longer cross-references the now-removed Table 4 rows.
8. **RESOLVED.** CombSUM's citation has been verified against two independently fetched NIST-affiliated primary sources (Fox, E. A., & Shaw, J. A. (1994). "Combination of Multiple Searches." *TREC-2*, NIST SP 500-215, pp. 243-252; no DOI exists) and added to `references.bib` as `fox1994combination`. `main.tex` §4.3 now cites it correctly, describes the min-max normalization adaptation, missing-document handling, and tie-breaking, and no longer carries a `TODO`. Full verification: `integrity_audit/COMBSUM_REFERENCE_VERIFICATION.md`, `integrity_audit/COMBSUM_IMPLEMENTATION_AUDIT.md`.
9. **Table numbering was repurposed.** The original skeleton's placeholder "Table 1: Data-quality dimensions and metrics" and "Table 3: Method inventory" (from `TABLE_PLAN.md`'s T1/T3 numbering) were replaced with "Table 1: Notation" and "Table 3: Baselines" respectively, to match this pass's explicit table plan (Notation / Datasets / Baselines / Repair methods). "Table 2: Dataset statistics" keeps its original numbers and label. `TABLE_PLAN.md` itself was not modified (it describes the full-manuscript plan, not this pass's scope) — a future full-manuscript numbering reconciliation should note this divergence.
10. **Figures 2 and 3 were deliberately not duplicated into §2–§4.** The task's generic instruction to "leave placeholders for Figure 1, Figure 2, Figure 3 where appropriate" was interpreted as applying only to Figure 1 (the conceptual pipeline, which does belong in §3 Methodology and is placed there); Figures 2 and 3 (cyclicity-by-regime and BEW/PIC pre/post) are Results figures showing data, not method, and remain correctly placed in the pre-existing §5 Structural Data Quality Results section rather than being duplicated here.
11. **RESOLVED.** CombSUM (and the other graph-independent baselines: prior, RRF, Borda-count) are regime-invariant by construction (their score depends only on ranker score files, not on the preference graph). This is now disclosed in `main.tex` §4.3 with a dedicated paragraph. The pooled query counts this produces for CombSUM (SciDocs 360, FiQA 359, HotpotQA 156, BRIGHT 145) were traced to `experiments/failure_class_audit_20260711_212157/analysis/canonical_query_records.jsonl`: SciDocs and HotpotQA have a clean 3-regimes-per-query structure (120×3 and 52×3), but FiQA (1 query) and BRIGHT (5 queries) are each missing exactly their `ms2` regime record — confirmed by direct inspection (`fiqa` query `489`; `bright` queries `biology:0/15/23/37/46`). This is a corpus-completeness artifact affecting *every* method in the pooled comparison for those specific query×regime cells, not a CombSUM-specific issue; most plausibly `ms2`'s stricter retention thresholds (`min_support=2`, `min_aggregate_margin=0.1`) occasionally produce a graph too sparse for the downstream pipeline to record for these six queries, though the exact upstream skip condition was not traced further (would require inspecting the original vote-extraction run logs, which are not part of this repository's committed artifacts). Not a blocking item for §4, but Results (§6) must not assume a uniform 3×-per-query structure for all four datasets when discussing graph-independent baseline counts — see the `TODO` already added at the top of `main.tex`'s §6 placeholder and `RESULTS_EVIDENCE_MAP.md`.
12. **RESOLVED / moot.** WMSF's predecessor-paper citation ("paper049," unresolved in the integrity audit) is no longer relevant to this manuscript: WMSF was removed from Table 4 per item 6 above, and no WMSF-related reference was added to `references.bib`, per instruction.

---

## Complete first draft: remaining TODOs (this pass)

### Remaining figure/table TODOs

1. **Figure 5 (pooled mean nDCG@$k$ by method, §6)** is a clearly marked placeholder (`\fbox`, not an `\includegraphics`). The existing `fig_mean_ndcg_hybrids.png` asset is a partial/pre-canonical prototype (per `FIGURE_PLAN.md`'s own status: "Partial; needs extension") and was **not** used numerically anywhere in this draft, per instruction. Table 6 in the same section already carries the correct canonical pooled values; Figure 5 needs to be regenerated as a bar chart from that same table (`final_baseline_comparison.csv`, scope=pooled) before submission.
2. **Figure 6 (failure-class distribution, §7)** is a clearly marked placeholder. Table 7 in the same section carries the canonical values; the script `papers/JDIQ_2026/scripts/fig06_failure_classes.py` referenced in earlier planning docs still does not exist and needs to be written.
3. **Figures 1–4 are treated as finalized** per this task's instructions and now have `\Description{}` alt text added (Figures 1–3 previously lacked it; this pass added it to all of Figures 1–4 and the two new placeholders 5–6).
4. Figures 2, 3, and 4's underlying PNGs still live at the repository root (`figures/manuscript/*.png`) rather than `papers/JDIQ_2026/figures/`, per the long-standing `TODO` already in `main.tex`'s `\includegraphics` calls — unchanged by this pass, still pending a path move before final submission.

### References still needing verification

- `burges2005learning` — no `address` field in the source-provided BibTeX entry (not fabricated; ICML 2005 proceedings location can be added if required by ACM style).
- `su2024bright` — arXiv preprint; if BRIGHT is later published at a venue with a DOI, update the entry.
- `thakur2021beir` — NeurIPS Datasets and Benchmarks track entry has no page numbers/publisher field by the nature of that venue; not an error, but flagged for a final BibTeX polish pass.
- The Hugging Face Datasets Hub distribution channel named in §10 (CARB) is stated as a plausible, standard distribution channel for this kind of resource, not verified against a specific pre-existing author commitment — confirm or soften before camera-ready (see `FULL_DRAFT_EVIDENCE_MAP.md`'s §10 row).

### Data-release TODOs

- CARB (§10) is specified (schema, feature dictionary) but not packaged or public. No claim in the manuscript depends on its public availability before submission.
- The bounded external-solver robustness check (§4.4/§6/§9) remains reported qualitatively; full citation and quantitative detail are deferred to camera-ready per the integrity audit's recommendation.

### Formatting TODOs

- Table 4 was already fixed for column-width overflow in an earlier pass; no other table overflow was found in this pass's compile (see Part 9 verification below).
- CCS concepts and keywords were left as the previously verified selection (per this task's "best verified current selection" instruction) — not re-derived from the live ACM CCS tool in this pass.

### Known unresolved evidence gaps

- Why HotpotQA is the one dataset with a reliable retrieval effect, despite having the lowest `ms1` cyclicity of the four datasets, is explicitly flagged in §11 Discussion as an open question this study raises but does not resolve.
- The exact upstream reason `ms2` (specifically, not `ms1`/`ms1_drop_mutual`) drops six query records from the pooled corpus (1 FiQA, 5 BRIGHT) was traced to a plausible mechanism (sparse-graph skip) but not confirmed against the original run logs.
- No validated predictive criterion exists for when repair will help (stated candidly in §7, §11, and §12 — not a gap introduced by this pass, but not closed by it either).

### Minimum-revision pass status

A full reread and minimum-necessary-consistency pass across §1–§4 (aligning contribution wording with the final Results, removing any now-unsupported claims, trimming repetition) was performed as part of completing this draft — see the "Minimum revision of Sections 1-4" note in this workspace's task history. No full stylistic rewrite of §1–§4 was performed, per instruction.
