# Full Draft Evidence Map

**Prepared:** 2026-07-12
**Scope:** Every major empirical claim in the now-complete `main.tex` Sections 5–13 and the Abstract, mapped to source file, table/row, sample size, caveat, and manuscript location. Sections 5–9 restate (rather than duplicate in full) the claim IDs already fully traced in `RESULTS_EVIDENCE_MAP.md` (R1–R9); this document adds the claims first introduced in Sections 10–13, the Data Availability section, and the Abstract, which `RESULTS_EVIDENCE_MAP.md` does not cover since it predates those sections being written.

---

## Sections 5–9 (restated pointer, full detail in `RESULTS_EVIDENCE_MAP.md`)

| Manuscript location | Claim summary | Evidence-map reference |
|---|---|---|
| §5 Structural Data Quality Results | Cyclicity/SCC by regime (Table 4); BEW/PIC pre/post repair (Table "BEW-PIC") | R1-C1, R2-C1 |
| §6 Downstream Quality Results | Bootstrap Δ nDCG by cell (Table 5, Figure 4); pooled baseline comparison (Table 6); stronger-repair comparison (Table 4/repair-variants) | R3-C1, R4-C1, R4-C2, R5-C1 |
| §7 Failure Taxonomy | Six-class taxonomy (Table 7); fusion suppression rate (14.7%) | R6-C1, R7-C1 |
| §8 Bounded Real-LLM Validation | Three-dataset real-LLM summary (Table "real-llm-summary") | R8-C1 |
| §9 Efficiency and Practical Considerations | Greedy vs. exact-for-small-components runtime/memory | R9-C1 |

All source files, exact table/row/field references, sample sizes, point estimates, confidence intervals, and caveats for the above are in `RESULTS_EVIDENCE_MAP.md` and are unchanged by the prose-drafting pass — no new computation was performed when converting that evidence map into Sections 5–9's prose.

---

## §10 CARB Benchmark

| Claim | Source file | Table/field | Sample size | Caveat | Location |
|---|---|---|---|---|---|
| 440 independent queries; 1,020 query×regime records; 366 methods per record; 14+ feature groups | `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_DATASET_SCHEMA.md`; `phase6/global_feature_dictionary.csv`; `phase9/dataset_contribution_scorecard.csv` | Table 10 (`tab:carb-stats`) | N/A (resource description, not a statistical claim) | These are **planned** release statistics for a schema that has been specified but not yet packaged (`PROJECT_STATUS.md`: CARB readiness 35%, "feature files packaged: Not built") — main.tex uses future/planned tense throughout §10, consistent with this status | §10, Table 10 |
| CARB is feature-only, not raw-text redistribution | `experiments/created_data_audit_20260711_232004/phase10/PROPOSED_RELEASE_STRUCTURE.md` | N/A | N/A | Release plan is proposed, not executed; no public URL exists yet | §10 |
| Planned Hugging Face Datasets Hub + archival distribution | Not independently verified against a specific committed plan document — this is a standard, low-risk distribution channel for feature-based ML/IR resources, stated here as a stated intention consistent with "future or submission-time language," not a claim of an already-arranged agreement | N/A | N/A | **Flag for authors:** verify this specific distribution channel against any actual author intention before camera-ready; if no such plan exists, soften to "a public archival release" without naming a specific platform | §10 |

---

## §11 Discussion

Discussion synthesizes findings already evidenced in §5–§9 and does not introduce new empirical claims; each interpretive statement is traceable to a specific earlier result rather than a new data source.

| Claim | Traces to | Location |
|---|---|---|
| "Repair can succeed mathematically but fail operationally" (mechanism) | R2-C1 (structural improvement) + R3-C1 (retrieval null) + R6-C1 (failure taxonomy mechanisms) | §11 ¶2 |
| Balance hybrid is uniformly repair-invariant; Copeland is not | R3-C1 (24-row bootstrap table: all 12 balance cells are exactly $[0,0]$) | §11 ¶3 |
| Fusion suppression rate 14.7% (repeated from §7 for the discussion of fusion's dual role) | R7-C1 | §11 ¶4 |
| HotpotQA is the least-cyclic dataset yet the one with a reliable effect | R1-C1 (cyclicity table) + R3-C1 (bootstrap table) | §11 ¶5 |
| "We do not have a confirmed explanation for why HotpotQA behaves this way" | No source — explicitly flagged as an open, unresolved question, not a claim requiring evidence | §11 ¶5 |
| Exact-for-small-components does not change the retrieval conclusion despite optimizing the structural objective more thoroughly | R5-C1 | §11 ¶6 |
| "Our attempts... find only modest, non-decisive signal" (predictive criterion) | `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`, claim `selector_predicts_repair = exploratory_only` | §11 ¶6 |

---

## §12 Limitations

| Claim | Source | Caveat already stated at first use | Location |
|---|---|---|---|
| Real-LLM scale (10–50 queries, single provider, no BRIGHT) | `outputs/openai_real_llm_cross_dataset_summary.md` | Yes, §8 | §12 ¶2 |
| No validated predictive selector | `final_claim_support_matrix.csv` (`selector_predicts_repair = exploratory_only`) | Yes, §7/§11 | §12 ¶3 |
| Protocol differences (vote-suite vs. pooled failure-mining corpus) | `main.tex` §4.3's protocol-separation paragraph | Yes, §4.3 | §12 ¶4 |
| HotpotQA $n=52$ | Table 2 (`tab:dataset-stats`), Table 5 | Yes, §6/§11 | §12 ¶5 |
| BEW/PIC qrels circularity | Defined at Eq.~(2)/(3) in §3.3, repeated §5 | Yes, §3.3/§5 | §12 ¶6 |
| Incomplete memory benchmarking | `experiments/failure_class_audit_20260711_212157/phase_reports/EFFICIENCY_EVIDENCE_AUDIT.md` ("no committed comparable memory benchmark package") | Yes, §4.6/§9 | §12 ¶7 |
| Bounded exact-solver coverage (external package, fixed sample) | `integrity_audit/EXTERNAL_SOLVER_EXECUTION_TRACE.md` | Yes, §4.4 | §12 ¶8 |
| Derived-data licensing constraints (CARB feature-only) | `PROPOSED_RELEASE_STRUCTURE.md` | Yes, §10 | §12 ¶9 |
| No claim of universal external validity | N/A — a scope statement, not an empirical claim | N/A | §12 ¶10 |

No new empirical claim is introduced in Limitations; every item restates a caveat already disclosed at its first point of relevance earlier in the manuscript, per the "state candidly" instruction.

---

## §13 Conclusion

Restates, at summary level, R1–R7 findings already fully evidenced above (cyclicity/regime dominance, structural improvement, retrieval decoupling, baseline competitiveness, failure taxonomy, bounded real-LLM corroboration, planned CARB release). No new empirical claim is introduced. One phrase requiring a standing check: "twenty of twenty-four... show no retrieval effect" appears in §6 prose, not verbatim in §13 (§13 uses the softer "the large majority... show no retrieval effect whatsoever" — consistent in direction, not a new number).

---

## Data Availability and Reproducibility section

| Claim | Source | Caveat | Location |
|---|---|---|---|
| Four source datasets are publicly available under their own licenses | Standard fact about SciDocs/FiQA/HotpotQA/BRIGHT, citations already in `references.bib` | None needed | Data Availability ¶1 |
| CARB not yet public as of this draft | `PROJECT_STATUS.md` (CARB readiness 35%) | Consistent with §10's future-tense framing | Data Availability ¶1 |
| Repository identity withheld for double-blind review | `JDIQ_GUIDELINE_SUMMARY.md` §5 anonymization checklist | This is a stated editorial practice, not an empirical claim | Data Availability ¶2 |
| Bootstrap procedure fully specified with fixed parameters ($B=2{,}000$) | Eq.~\eqref{eq:bootstrap-ci}, §4.5 | Already defined in Methodology/Experimental Setup | Data Availability ¶3 |
| Bounded external-solver check reported qualitatively, not reproducible from this repo alone | `integrity_audit/FINAL_REPORT.md` | Already disclosed §4.4 | Data Availability ¶3 |

---

## Abstract

| Sentence | Traces to | Verified? |
|---|---|---|
| "vote construction, not repair, is the dominant driver of graph inconsistency" | R1-C1 | Yes |
| "repair reliably improves graph-level consistency whenever inconsistency is present" | R2-C1 | Yes |
| "translates into a measurable ranking-quality gain in only one of twelve dataset-and-regime combinations tested" | R3-C1 (1 of 12 Copeland cells: HotpotQA/`ms1`) | Yes — note the Abstract deliberately counts only the 12 Copeland cells (the pair with any non-degenerate cells at all), not all 24 Copeland+balance cells, since "one of twelve" is the more precise and defensible framing than "one of twenty-four" (balance contributes no cells with any activity at all, so including it would understate the active-cell denominator in a way that could read as making the one positive result seem rarer than it is among cells where repair is even active) |
| "simple score-fusion baselines... remain competitive with, or better than, every graph-repair method evaluated" | R4-C1 | Yes |
| "a manual failure-class analysis identifies why repair is usually inactive, occasionally neutral, and rarely harmful" | R6-C1 | Yes |
| "we release a companion benchmark" | §10 (planned, not yet released) | Consistent with future-tense framing used throughout §10 |
| No acronym used without expansion | nDCG is avoided entirely in the Abstract (referred to as "a standard graded-relevance retrieval metric") per the "no unexplained acronyms" requirement | Verified by construction |
| No citations, no repository paths | Verified by construction (Abstract text contains no `\cite` or `\texttt` commands) | Verified |

---

## Overall coverage statement

Every empirical, numeric claim introduced for the first time in Sections 10–13, Data Availability, and the Abstract is either (a) a restatement of a claim already fully traced in `RESULTS_EVIDENCE_MAP.md` (R1–R9), or (b) an explicitly forward-looking / planned statement about CARB's release status, clearly marked as such and not presented as an already-completed fact. No claim in Sections 5–13 or the Abstract required new computation, a new source file, or a number not already verified in an earlier pass of this workspace.
