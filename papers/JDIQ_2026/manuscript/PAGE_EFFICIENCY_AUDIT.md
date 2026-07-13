# Page-Efficiency Audit

**Prepared:** 2026-07-12
**Scope:** Identify safe length reductions in the 26-page draft; apply only reductions that improve or preserve clarity; do not aggressively compress. Report the resulting page count.

---

## Per-section word counts (prose only, tables/figures excluded)

| Section | Words |
|---|---|
| Introduction | 1,558 |
| Background | 646 |
| Methodology | 1,345 |
| Experimental Setup | 1,644 |
| Structural Data Quality Results | 327 |
| Downstream Quality Results | 764 |
| Failure Taxonomy | 583 |
| Bounded Real-LLM Validation | 277 |
| Efficiency and Practical Considerations | 292 |
| CARB Benchmark | 326 |
| Discussion | 810 |
| Limitations | 480 |
| Conclusion | 299 (post-edit) |
| Data Availability | 242 |
| **Total prose** | **~9,600** |

Introduction (1,558) and Experimental Setup (1,644) are the two longest sections, as expected for a methods-heavy data-quality study; neither is disproportionate relative to its content (Introduction carries the full motivation, gap statement, and five-item contribution list required for a JDIQ submission; Experimental Setup specifies datasets, rankers, baselines, repair variants, the bootstrap procedure, and implementation details, each of which needs to be independently reproducible from the text).

---

## Candidates examined and their disposition

### 1. Table 5 (bootstrap deltas) + Figure 4 (bootstrap forest plot) — considered as duplicative, **not cut**

These present the same 24-cell data in two forms. This is deliberate and is the standard treatment for a paper's single central quantitative claim (Section~6, the structural/retrieval decoupling result): the table gives exact, citable numbers; the figure gives the pattern (20 of 24 null, 1 reliable) at a glance. Cutting either would weaken the paper's central evidentiary presentation for a page saving of under half a page. **Not cut.**

### 2. Table 6 (pooled baseline comparison) + planned Figure 5 — considered, **not cut**

Same reasoning as above; this is the paper's second-most-important quantitative claim (CombSUM/RRF beat every graph-based method). Figure 5 is currently a placeholder, so there is no present duplication in the compiled page count to reduce. **Not cut.**

### 3. Table 4b (BEW/PIC, `tab:bew-pic`) merge into Table 4 (`tab:structural-results`) — considered, **not merged**

Table 4 has 12 rows (all datasets $\times$ all regimes); Table "BEW-PIC" has 4 rows (`ms1` only, since BEW/PIC pre/post is degenerate elsewhere by construction). Merging would force 8 additional rows of "N/A" or "0" cells into a single wide table, which would reduce rather than improve clarity — the two tables answer different-grained questions (cyclicity/SCC by regime vs. BEW/PIC change where cyclicity is present) and are already cross-referenced from the same paragraph. **Not merged**, per the instruction to apply only reductions that improve clarity.

### 4. Repeated dataset descriptions — checked, **none found**

Domain descriptions (scientific/financial/multi-hop/reasoning-intensive retrieval) appear exactly once, in Section 4.1. No other section re-describes dataset domains. **No reduction needed.**

### 5. Regime definitions re-explained outside Methodology — checked, **none found**

Only Section 3.2 gives the formal `ms2`/`ms1`/`ms1_drop_mutual` threshold definitions; all later mentions (Sections 4, 5, 6) refer to "the vote-retention rule" or similar without re-deriving the mechanism. **No reduction needed.**

### 6. Section 4.7 (Real-LLM Evidence: Scope and Role) vs. Section 8 (full Real-LLM Validation) — checked, **not cut**

Section 4.7 is a ~130-word scope-flag that explicitly defers full treatment to Section 8 rather than restating it; this is the intended, minimal cross-referencing pattern, not padding. **Not cut.**

### 7. Table 4 (`tab:repair-variants`) caption duplicating its lead-in sentence — found and fixed. **[APPLIED]**

The paragraph immediately before Table 4 states the procedures are "both fully reproducible from this repository alone," and the table's own caption repeated the identical clause verbatim. Shortened the caption to "Repair procedures compared (see text for reproducibility notes)." This is the one genuine, safe, page-neutral-to-positive textual redundancy found in this audit.

### 8. Moving tables to a supplementary appendix — considered, **not implemented**

The manuscript does not yet have a supplementary-appendix section (all content is currently in the single main-text file); several tables are natural supplement candidates in the eventual full paper package (e.g., a per-dataset breakdown of Table 6, already planned as Supplementary Figure SF01 in `FIGURE_SPECIFICATIONS.md`), but none of the *currently included* main-text tables (Tables 1–10) are redundant enough with each other to justify demoting one to a supplement without first building the supplement infrastructure — a structural change beyond a "safe reduction," and out of scope for this pass per its instruction not to aggressively compress. **Recommended for a future pass**, not applied now.

---

## Net effect

One concrete, safe redundancy was found and removed (Table 4's caption). No section was substantially shortened, no table was merged or removed, and no content was relocated to a supplement, because this audit did not find reductions that would both save meaningful space and preserve or improve clarity — the manuscript's cross-referencing discipline (established from the first drafting pass and reinforced in the repetition audit) already keeps most sections close to their necessary minimum length for independent reproducibility and journal-appropriate completeness.

**Page count after this pass: 26 pages (unchanged from before this audit).** This is within the JDIQ target range described in `JDIQ_GUIDELINE_SUMMARY.md` (~20–25 pages for a research paper, "up to 23 pages" cited for some special issues) but at or slightly above its upper end. The largest available future reduction, if the page budget must be brought down further, is to build the supplementary-appendix infrastructure item 8 above recommends and move 2–3 secondary tables (e.g., a future per-dataset baseline breakdown, or the full 24-row Table 5 if a 4-row `ms1`-only summary is judged sufficient for the main text) there — this was deliberately not done in this pass since it changes the paper's structure, not just its wording, and the task instructed against aggressive compression.
