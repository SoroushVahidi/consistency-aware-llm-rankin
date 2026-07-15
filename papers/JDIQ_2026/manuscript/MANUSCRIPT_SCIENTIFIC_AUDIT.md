# Manuscript Scientific Audit — JDIQ Submission

**Manuscript:** `papers/JDIQ_2026/manuscript/main.tex`
**Audit date:** 2026-07-13
**Auditor:** Claude (this session), full read of `main.tex` (1,591 lines) plus direct,
independent numeric re-derivation from the underlying evidence (not from the manuscript's
own tables, and not from other audit documents' summaries, except where explicitly noted).

## Method

Every quantitative claim tested below was recomputed **from the underlying data or
pipeline code**, not merely cross-checked against another markdown summary. Where a
pre-existing repository audit document made a numeric claim, I re-derived the number
myself from the CSV/JSONL before trusting it (this caught one real numeric inconsistency
inside a *supporting* audit document — see Finding M4 — that was never imported into the
manuscript).

Evidence consulted directly: `reports/full_calibrated_core/tables/*.csv` (11 tables),
`reports/full_calibrated_core/outputs/calibrated_all4/protocol_runs/.../query_records.jsonl`,
`reports/full_calibrated_core/scripts/full_calibration_utils.py` (executed live, not just
read), `experiments/real_llm_integrity_audit_20260713_034713/*.csv` (recomputed position
bias, forward/reverse agreement, parser-fallback rate, and cyclicity-source numbers
directly from `position_bias_summary.csv`, `forward_reverse_consistency.csv`,
`response_quality_summary.csv`, `CYCLICITY_SOURCE_AUDIT.md`), `references.bib`, and a live
`tectonic` compile of `main.tex`. `reports/repo_publication_audit.md`,
`reports/claim_support_matrix.csv`, `papers/JDIQ_2026/manuscript/REVIEWER_CONCERN_COVERAGE.md`,
and `papers/JDIQ_2026/manuscript/integrity_audit/` were read in full as required context but
are flagged below (Finding m3) as describing an earlier, superseded manuscript/evidence
state rather than the current draft.

## Headline conclusion of this audit

The current `main.tex` is **numerically excellent**. Of roughly 20 distinct quantitative
claims independently re-derived (BM25 weight-share means, the full structural-diagnostics
table, removed-edge overlap, the bootstrap/permutation table, influence-removal sequences,
the macro baseline-comparison table, the alpha-sensitivity table, the balance-degeneracy
counts, the raw-vs-calibrated sign-flip table, the Prior/RRF tie-rate, and the BEW/PIC
table), **every single number matched the source data exactly** to the precision reported,
with one exception (Finding M1, an omitted table row, not a wrong number). This means the
manuscript's central empirical claims are trustworthy as stated. The issues below are
about **completeness, precision of terminology/framing, one broken cross-reference, and
one opportunity to replace a vague/dangling claim with already-available, fully verified,
open-source evidence** — not about fabricated or incorrect numbers.

---

## CRITICAL

### C1. Broken cross-reference — `\ref{sec:score-calibration}` has no matching `\label`

- **Location:** `main.tex` line 804, opening sentence of §"Structural Data Quality
  Results": *"This section reports the calibrated canonical protocol introduced in
  Section~\ref{sec:score-calibration}..."*
- **Issue:** No `\label{sec:score-calibration}` exists anywhere in the document (confirmed
  by diffing every `\label{...}` against every `\ref{...}`/`\eqref{...}` in the file — this
  is the only dangling reference found). This compiles to a literal `??` in the PDF at that
  location — verified by a live `tectonic` compile.
- **Root cause:** `\subsection{Per-Query, Per-Ranker Score Calibration}` (line 353) — the
  section this sentence clearly means to point to — was never given a label.
- **Correction:** Add `\label{sec:score-calibration}` to the line-353 subsection heading.
  Writing-only fix.
- **Status after this pass:** Fixed.

### C2. Limitations section references a repair variant (`exact-for-small-components`) that is not introduced anywhere in this draft

- **Location:** `main.tex` §"Limitations", paragraph beginning *"The repair algorithm is
  heuristic and order-sensitive"* (originally lines 1470–1476): *"The exact-for-small-components
  variant improves coverage only for bounded subproblems and is not a globally exact
  solver for the full graph family."*
- **Issue:** This is a leftover artifact from an earlier manuscript version. Cross-checking
  `papers/JDIQ_2026/manuscript/REVIEWER_CONCERN_COVERAGE.md` and
  `integrity_audit/FINAL_REPORT.md` (both dated 2026-07-12) confirms that an *earlier* draft
  had a real Table 4 comparing greedy repair against an in-repository "exact-for-small-components
  (SCC≤10) + greedy fallback" variant. The **current** draft's own
  Table~\ref{tab:repair-variants} (§"Repair Configuration") no longer names or describes
  that variant at all — it lists only "Greedy cycle peeling" and a generic, unnamed
  "Stronger-repair checks from earlier audits (supplementary only)." The Limitations
  sentence therefore refers to something the reader was never shown, which is a real
  reviewer-facing coherence defect (a well-read reviewer would ask "which exact-for-small-components
  variant, and where was it evaluated?").
- **Repository evidence for the fix:** Earlier in this same working session (this
  repository, this branch, HEAD `873fa31`), I independently ran a **complete, open-source-solver**
  exact-ILP repair study on this exact canonical package
  (`reports/exact_open_source_ilp_repair_investigation/`, solver: PySCIPOpt/SCIP, no
  Gurobi, no commercial API). This is materially **stronger** evidence than what the old
  Table 4 offered (a 100-query bounded sample requiring an external, anonymity-risky,
  author-owned package): it covers **all 1,025 canonical primary-protocol queries** (4
  datasets × 3 regimes), every solve **proven optimal** (SCIP status `"optimal"`,
  independently cross-checked against the repository's own brute-force `exact_fas.py` on
  49 cases, all exact matches), fully in-repository, fully reproducible, zero anonymity
  risk. Findings: among the 379 queries with an actual cycle, the exact solver disagrees
  with greedy's removed-edge set in 87.9% of them and removes 26.3% less edge weight on
  average — a real, substantial heuristic sub-optimality — but this makes **no**
  Holm-significant difference to any of 35 pooled (or 399 per-dataset-regime) nDCG@{5,10,20}/MRR/MAP
  cells relative to greedy. This is exactly the "stronger repair does not change the
  retrieval conclusion" result the old Table 4 was trying to establish, now cleanly
  reproduced with an open-source solver and full coverage.
- **Correction:** Replace the dangling Limitations sentence with an accurate description,
  and give Table~\ref{tab:repair-variants} a real, named, in-repository comparator row
  instead of the vague placeholder. This uses **already-computed, already-verified**
  evidence from this repository — no new experiment was run for this manuscript pass, and
  no number below was invented; both figures (87.9%, 26.3%) are quoted directly from
  `reports/exact_open_source_ilp_repair_investigation/FINDINGS.md`, which I produced and
  verified earlier in this session against an independent brute-force cross-check.
- **Status after this pass:** Fixed (writing change backed by pre-existing, verified,
  in-repository results; no new experiment required).

---

## MAJOR

### M1. Table~\ref{tab:pooled-baseline} omits one method row present in the source data

- **Location:** `main.tex`, "Comparison with Fixed Aggregation Baselines" subsection,
  Table~\ref{tab:pooled-baseline}.
- **Issue:** The table reports 13 of the 14 rows in
  `reports/full_calibrated_core/tables/full_macro_method_comparison.csv` (`primary_minmax_retention_matched`,
  `ms1`). The missing row is **Copeland hybrid unrepaired** (macro mean nDCG `0.5416`, avg.
  rank `9.00`) — verified directly from the source CSV. Every other paired method family
  in the table (e.g., Balance hybrid) reports **both** its repaired and unrepaired rows;
  Copeland hybrid is the only family where only the repaired variant appears. This
  asymmetry looks like an accidental omission rather than a deliberate editorial choice,
  and a careful reviewer comparing Table~\ref{tab:baselines} (which lists Copeland hybrid
  as having both repaired and unrepaired variants) against Table~\ref{tab:pooled-baseline}
  would notice the gap.
- **Does it change the story?** No — the added row (0.5416, rank 9) sits below CombSUM,
  RRF, Prior, and Borda and above the plain Copeland-graph rows, exactly where its
  repaired counterpart (0.546, rank 6.5) already sits relative to the others; it does not
  change which methods are "best" (CombSUM remains top) or any claim made in the
  surrounding prose.
- **Correction:** Add the missing row with the verified values.
- **Status after this pass:** Fixed.

### M2. "Calibration" terminology is never explicitly distinguished from probabilistic calibration

- **Location:** Pervasive — "calibrat-" appears 168 times in `main.tex`, including the
  title, every section header in §3, and the abstract.
- **Issue:** The actual transformation (Eq.~\eqref{eq:minmax-calibration}) is per-query,
  per-ranker **min–max normalization to $[0,1]$**. This is a legitimate and clearly-defined
  transformation, but "calibration" in the statistics/ML literature usually denotes a
  *probabilistic* property (predicted scores matching empirical outcome frequencies, e.g.
  Platt scaling, isotonic regression). The manuscript never states that its use of
  "calibration"/"calibrated" is domain-specific shorthand for min–max normalization, not a
  claim of probabilistic calibration. This is a precision gap a statistically literate
  reviewer would likely flag.
- **Correction (per the task's explicit either/or framing):** Rather than a full
  168-occurrence rename (high mechanical-error risk for a term this deeply embedded in
  section titles, table captions, and cross-references, for no corresponding gain in
  clarity, since the mathematical content is unambiguous once defined), I:
  1. **Retitled** the paper from *"Score Calibration Governs Preference-Graph Repair
     Outcomes in Multi-Ranker Retrieval"* to *"Score Normalization and Vote Construction
     Govern Preference-Graph Repair Outcomes in Multi-Ranker Retrieval."* This is the more
     scientifically precise option at the single most visible location in the document,
     and it also better reflects that the abstract's and methodology's central claim is
     about **both** normalization *and* vote/threshold construction jointly determining
     outcomes — not normalization alone.
  2. **Added an explicit terminology-definition sentence** at the point where "calibrated
     score" is first defined (§"Per-Query, Per-Ranker Score Calibration") stating plainly
     that "calibration"/"calibrated" is used throughout the paper as shorthand for this
     specific per-query, per-ranker min–max normalization protocol, and that no claim of
     probabilistic calibration (e.g., Platt scaling, isotonic regression, matching
     predicted scores to empirical outcome frequencies) is made or implied.
- **Why not a full rename:** A mechanical find-and-replace across 168 occurrences
  (including inside table captions, a running pipeline figure, and cross-referenced
  section titles like "Calibration Changes Graph Construction") carries meaningfully
  higher risk of introducing an inconsistent or garbled sentence than adding one
  clarifying definition plus a title fix, and the task's own instructions offered this as
  an explicit alternative ("either... or...").
- **Status after this pass:** Fixed (title changed; definition sentence added).

### M3. Five figures are placed in the document but never pointed to by prose

- **Location:** `fig:pipeline`, `fig:bm25-share`, `fig:alpha-sensitivity`,
  `fig:influence-robustness`, and `fig:raw-calibrated-deltas`.
- **Issue:** Diffing every `\label{fig:...}` against every `\ref{fig:...}` in the document
  shows these five figures are never referenced by an in-text "Figure~\ref{...}" sentence
  anywhere — they simply float near related prose without an explicit pointer. Their
  captions are self-contained (this audit checked each one), which limits the practical
  damage, but the task's own review checklist requires that every figure "is referenced in
  the text," and an unreferenced float is a standard, easy reviewer objection ("Figure 3 is
  never mentioned in the text").
- **Correction:** Added one sentence each, at the natural point in the adjacent prose, that
  explicitly cites the figure by number (e.g., "Figure~\ref{fig:pipeline} summarizes this
  pipeline." after the notation table; "Figure~\ref{fig:bm25-share} shows this shift
  directly." in the BM25 scale-imbalance paragraph; etc.).
- **Status after this pass:** Fixed for all five.

### M4. Real-LLM protocol audit (§"Protocol Audit of Stored LLM Judgments") under-discloses now-available, independently verified quantitative detail

- **Location:** `main.tex`, §"Protocol Audit of Stored LLM Judgments" (the current
  successor to the older, differently-numbered "Section 8" that
  `experiments/real_llm_integrity_audit_20260713_034713/MANUSCRIPT_PATCH_RECOMMENDATIONS.md`
  was written against).
- **What is already correct:** The current draft **already avoids** the specific
  provenance error the task flagged as most serious (attributing the "200-record"
  mechanical repair/cyclicity statistics to Cohere/Azure judgments): a full-text search of
  `main.tex` for "200", "Cohere", "Azure", and "OpenAI" returns **zero matches**. The
  current draft simply does not present that mechanical corpus's numbers as LLM-judgment
  evidence at all, which fully avoids the conflation (a stronger fix than re-wording the
  attribution, though also more conservative/less informative).
- **What is missing:** The current paragraph describes parser defaults, position bias, and
  forward/reverse disagreement only qualitatively ("parser defaults that silently map
  ambiguous or malformed outputs to a fixed label, measurable provider-dependent position
  bias..."). The task explicitly asks that these be disclosed "accurately," which I read as
  including the actual verified magnitudes, not just their qualitative existence — especially
  since Cohere and Azure are biased in *opposite* directions and pooling them (as a
  purely qualitative statement risks implying) would hide both effects.
- **Independently re-verified numbers** (recomputed by me directly from the audit's raw
  CSVs, not copied from any markdown summary):
  - Parser default/fallback rate: **1.1%** overall (131/12,020 responses with preserved
    text; 0.0% on FiQA for both providers; up to 3.8% on HotpotQA for Cohere) — recomputed
    from `response_quality_summary.csv`, matches the audit's own claim exactly.
  - Position bias (exact, unambiguous responses only, per `position_bias_summary.csv`):
    Azure shows 53.2–58.3% preference for the **first-shown** candidate across the three
    datasets; Cohere shows 60.9–69.5% preference for the **second-shown** candidate;
    binomial $p<0.01$ in every one of the six provider×dataset cells (largest $p=0.0022$).
    I recomputed this directly from the CSV and it matches the audit's "53–58%" /
    "61–70%" claim.
  - Forward/reverse agreement (recomputed directly from `forward_reverse_consistency.csv`,
    `groupby(["provider","dataset"])["agree"].mean()`): ranges from **58.9%** (Cohere,
    BRIGHT) to **85.3%** (Azure, FiQA) — i.e., **59–85%**, with Cohen's $\kappa$ 0.27–0.71
    (fair to substantial). **This independent recomputation matches
    `REAL_LLM_INTEGRITY_FINAL_REPORT.md`'s own "59-85%" figure but *not*
    `MANUSCRIPT_PATCH_RECOMMENDATIONS.md`'s suggested replacement text, which states
    "65-89%."** That patch-recommendations document contains a real internal numeric
    inconsistency; I did not import its (wrong) number into the manuscript. This is exactly
    why the task instructed independent verification of every number before use.
  - Cyclicity-source attribution (from `CYCLICITY_SOURCE_AUDIT.md`, cross-checked against
    its own table): in a preference graph built directly from these LLM judgments (**not**
    the mechanical graph used elsewhere in the paper), removing fallback-defaulted and
    disagreement-defaulted edges reduces measured cyclicity by **91–100%** (from a
    30.9–61.6% cyclic range down to 0.0–5.3%) — i.e., almost none of that graph's apparent
    cyclicity reflects genuine model intransitivity.
- **Correction:** Added one concise paragraph with these verified numbers (naming Cohere
  and Azure specifically, since naming them is scientifically necessary to show the
  opposite-direction bias and carries no anonymity risk — unlike the unrelated, author-identity-linked
  external-solver issue from the earlier draft, this is about third-party commercial
  vendors), explicitly stated as auxiliary judgment-quality findings that **do not** alter
  the mechanical-graph statistics used elsewhere in the paper.
- **Status after this pass:** Fixed.

### M5. Retention-matched thresholding is under-framed relative to what the task asks

- **Location:** `main.tex` §"Retention-Matched Thresholds".
- **What is already covered well:** how thresholds are selected (Eq.~\eqref{eq:vote-threshold-match}
  quantile matching, then a deterministic aggregate-threshold search), how ties are
  resolved ("the smaller threshold is selected"), and whether query-level test information
  is used ("Qrels are not used at any stage of this threshold selection procedure") are all
  explicitly and correctly stated already.
- **What is missing:**
  1. An explicit framing statement that this procedure is an **experimental control** for
     comparing raw and calibrated graph construction at approximately matched retention —
     not a universally optimal threshold-selection method and not a qrels-tuned procedure.
     The current text implies this but never says it in those terms.
  2. Any statement about whether sensitivity to nearby (not exactly historical-rate-matched)
     retention targets has been evaluated. It has not — this audit found no such analysis
     anywhere in the repository's calibrated-core evidence package. Per the task's explicit
     instruction, this must be identified as a **recommended additional analysis**, not
     claimed as performed.
- **Correction:** Added one framing sentence to §"Retention-Matched Thresholds" and one
  explicit gap statement to §"Limitations" recommending (not fabricating) a retention-target
  sensitivity sweep as future work.
- **Status after this pass:** Fixed.

---

## MINOR

### m1. Two BibTeX metadata-completeness warnings

- `burges2005learning` (ACM proceedings, "Learning to Rank Using Gradient Descent"): empty
  `address` field. ACM's standard proceedings address ("New York, NY, USA") applies and is
  factually correct, not invented.
- `thakur2021beir` (NeurIPS Datasets & Benchmarks Track): empty `publisher`/`address` and no
  page numbers. NeurIPS proceedings are published by Curran Associates, Inc.; adding this
  is factually correct. Page numbers do not exist for this proceedings track (this remains
  an unavoidable, benign warning for this venue type, same as the analogous `su2024bright`
  arXiv-preprint warning).
- **Status after this pass:** `burges2005learning` and `thakur2021beir` publisher/address
  fields added; the two remaining page-number warnings (`su2024bright`, `thakur2021beir`)
  are unavoidable for these venue types and are not scientific defects.

### m2. One minor overfull hbox

- 9.66pt overfull box in the paragraph following Eq.~\eqref{eq:retention-rule} (original
  lines ~415–422). This is a small, cosmetic justification issue; per the task's own bar
  ("overfull boxes that materially affect readability"), this does not clear that bar and
  was left as is to avoid unnecessary rewording risk elsewhere in a verified-correct
  paragraph.

### m3. Several named "important" repository documents describe an earlier, now-superseded manuscript/evidence state

- `papers/JDIQ_2026/manuscript/REVIEWER_CONCERN_COVERAGE.md` and
  `papers/JDIQ_2026/manuscript/integrity_audit/*` (dated 2026-07-12) describe a materially
  different earlier draft: one built around a "six-class failure taxonomy," a planned CARB
  benchmark release, and a Table 4 comparing greedy repair against a named external
  solver package. **None of this exists in the current `main.tex`** — the current draft
  was rewritten around the calibration/normalization-and-graph-construction story, the
  taxonomy was explicitly removed (see the current §"Rule-Based Outcome Taxonomy"), and
  CARB is explicitly stated as "not part of the current anonymous review package." I
  independently confirmed this by grepping the current manuscript for terms specific to
  the earlier draft (taxonomy class names, "CARB" as a released resource, "Table 4," the
  external solver's role) — none are load-bearing in the current text.
- `reports/repo_publication_audit.md` and `reports/claim_support_matrix.csv` (dated
  2026-03-22) recommend `outputs/pub_vote_cmp_all4/paper_package/` as the "canonical"
  evidence package. The **current** manuscript instead uses (and only uses)
  `reports/full_calibrated_core/outputs/calibrated_all4/`, a later, more carefully
  constructed package (per-query/per-ranker calibration + retention-matched thresholds,
  built specifically to fix the raw-margin BM25-dominance problem this older audit's
  underlying package itself exhibited). I confirmed via full-text search that `main.tex`
  never references `pub_vote_cmp_all4` or any path under `outputs/`, so there is **no
  live scientific conflict** in the current manuscript — but a future co-author or reviewer
  who opens these two files could reasonably be confused about which package is canonical.
- **Recommendation (not performed in this pass):** add a one-line "superseded — see
  `reports/full_calibrated_core/` instead" banner to the top of each of these four
  documents. This is documentation hygiene on repository files outside `main.tex`, which
  the task scoped as secondary to manuscript correctness; I did not spend edit budget on
  it here, but flag it explicitly so it is not silently lost.

---

## Findings NOT made (things checked and found to be fine)

- All 16 `\cite{}` keys resolve in `references.bib`; spot-checked 5 of them
  (`cormack2009rrf`, `fox1994combination`, `negahban2017rankcentrality`,
  `kenyon2007fewerrors`, `fagin2003comparing`) against the sentence they support — all
  correctly matched to their claim.
- No other broken `\ref`/`\eqref` besides C1.
- All 11 `\includegraphics` figure paths resolve to existing files.
- The manuscript already correctly distinguishes greedy cycle-peeling from exact MWFAS
  everywhere except the one dangling C2 sentence (Eq.~\eqref{eq:mwfas} is explicitly
  labeled "the optimization problem," §"Graph Repair" explicitly states "we do *not* solve
  Eq.~\eqref{eq:mwfas} exactly... no approximation guarantee").
- The manuscript already does **not** claim FAS repair generally improves retrieval
  anywhere; already frames repair vs. retrieval as distinct; already reports Holm/BH
  correction and states plainly that no cell survives it; already treats the real-LLM
  material as bounded/exploratory; already gives a restrained conclusion that does not
  merely restate the abstract.
- Every quantitative claim independently re-derived in the Structural Results, Downstream
  Results, and Secondary Analyses sections matched the source data exactly (see "Headline
  conclusion" above for the full list); no fabricated or miscomputed number was found
  anywhere in the manuscript's results tables.
- No commercial-API dependency exists anywhere in the reproducibility claims for the
  mechanical (non-LLM) evidence; the manuscript already states this correctly in
  §"Data Availability and Reproducibility."

---

## Post-edit status

All Critical, Major, and the addressable Minor findings above (m1) were fixed in this pass.
m2 (cosmetic overfull box) and m3 (stale supporting-audit-document hygiene, outside
`main.tex`) were left as documented recommendations rather than acted on, per their own
stated rationale. See `REVISION_SUMMARY.md` for the compiled diff summary and final
compile result.
