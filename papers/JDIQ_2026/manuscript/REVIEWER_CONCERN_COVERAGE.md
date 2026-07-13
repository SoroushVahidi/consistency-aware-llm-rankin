# Reviewer Concern Coverage Matrix

**Prepared:** 2026-07-12
**Source of the 10 concerns:** the task prompt, which condenses the 15 reconstructed criticisms in `experiments/reviewer_response_state_audit_20260711_214959/reviewer_criticism_inventory.csv` (R1–R10 map 1:1 onto that file's R1–R10; R11–R15 are related but not directly requested — noted where relevant below). All 15 are labeled `reconstructed_summary` in the source file: **no verbatim rejection letter or reviewer report was found in the repository**, so "prior reviewer concerns" throughout this document means the reconstructed summary, not quoted text.

Candor note per task instructions: where evidence is not yet sufficient to fully resolve a concern, this is stated plainly below rather than implied to be resolved.

---

## 1. "The old conclusion looked natural or insufficiently novel." (R1)

- **How the Introduction addresses it:** Reframes the contribution as diagnostic/curatorial data-quality measurement rather than an algorithmic result (five-item contribution list: regime-stratified structural measurement, bootstrap-quantified decoupling account, six-class failure taxonomy, pooled baseline comparison, CARB release). Explicitly states the paper does **not** claim FAS repair is a generally superior reranking strategy — the novelty claim is repositioned around *diagnosis*, not *improvement*.
- **Section that fully addresses it:** §7 Failure Taxonomy (not yet written) is where the mechanistic "why" — the actual novel empirical content beyond IJCS — lives; §9 CARB Benchmark is the second novelty anchor.
- **Is current evidence sufficient?** Yes. The failure taxonomy (6 classes, 1,020 records) and pooled baseline grid did not exist in the IJCS submission (confirmed in `IJCS_REUSE_AUDIT.md`) and constitute genuinely new empirical material satisfying JDIQ's ≥30%-new-material overlap policy (`JDIQ_GUIDELINE_SUMMARY.md` §6).
- **Wording to avoid:** "novel algorithm," "state-of-the-art," "outperforms prior work" — none of these are supported and all are explicitly listed as prohibited in `CANONICAL_PAPER_STORY.md`'s "What must NOT be claimed" table.
- **Unresolved limitation:** Whether JDIQ reviewers will accept "diagnostic/negative-result" framing as sufficiently novel is inherently a reviewer judgment call this document cannot pre-resolve; the mitigation is venue selection itself (JDIQ explicitly values negative/null results per `JDIQ_GUIDELINE_SUMMARY.md` §13 item 3), not additional evidence.

---

## 2. "There was no actionable account of when repair helps." (R2)

- **How the Introduction addresses it:** States plainly that null/mixed outcomes are treated "as part of the contribution, not as a shortfall to be explained away," and that identifying when a DQ intervention does *not* transfer to task-level utility "is itself the actionable finding."
- **Section that fully addresses it:** §7 Failure Taxonomy (six interpretable classes with mean ΔnDCG per class) and §10 Discussion subsection 10.1–10.3 ("when repair is a DQ win / retrieval-neutral / harmful," per `MANUSCRIPT_OUTLINE.md` §10).
- **Is current evidence sufficient?** Partially. The failure taxonomy is a genuine, evidence-backed advance over IJCS (which had no taxonomy at all). However, per the claim-support matrix (`final_claim_support_matrix.csv`), `selector_predicts_repair` is classified `exploratory_only` ("modest signal; no decisive win") — there is **no validated predictive selector**, only a post-hoc taxonomy of why past repairs succeeded or failed. This is weaker than a genuinely predictive/actionable *decision rule*, which is what R2 most literally asks for.
- **Wording to avoid:** "a selector reliably decides when to repair" (explicitly prohibited in `CANONICAL_PAPER_STORY.md`); "predicts retrieval improvement."
- **Unresolved limitation:** The actionable guidance is retrospective/diagnostic ("here is why repair failed in these classes of cases"), not a forward-looking predictive policy with held-out validation. This gap should be stated explicitly in §10 and §11, not minimized.

---

## 3. "The preference sources were too classical." (R3)

- **How the Introduction addresses it:** States the study "additionally test[s] a bounded, cross-dataset sample of real large-language-model pairwise, pointwise, and listwise judgments to check whether the same regime-conditional pattern persists under genuine LLM preferences."
- **Section that fully addresses it:** §8 Bounded Real-LLM Validation.
- **Is current evidence sufficient?** Partially. The addition of real-LLM pilots is genuine new evidence beyond the three-ranker (BM25/TF-IDF/MiniLM) main suite, and beyond the IJCS submission's own framing (which already flagged this as a limitation without a full remedy). But the pilots remain small (SciDocs 50q, HotpotQA 20q, FiQA 10 processed queries — `docs/related_work_positioning_note.md` §1) and single-provider (OpenAI, plus a 2-query Gemini pilot not treated as evidence).
- **Wording to avoid:** "results generalize to LLM-generated preferences" (explicitly listed as unsupported in `docs/SAFE_CLAIMS_FOR_PAPER.md` US-4, and consistent with `CANONICAL_PAPER_STORY.md`'s prohibition on "broad LLM generality").
- **Unresolved limitation:** The core ranker family (BM25/TF-IDF/MiniLM) remains the primary evidence base; this concern is mitigated, not resolved. §11 Threats to Validity must state this directly (per `docs/THREATS_TO_VALIDITY.md` item 4, "external validity limits").

---

## 4. "Real-LLM evaluation was too small." (R4)

- **How the Introduction addresses it:** Explicitly calls the LLM evidence "bounded... a supporting check rather than a confirmatory result in its own right" — pre-empting the concern by scoping the claim down rather than overselling it.
- **Section that fully addresses it:** §8, with a "mandatory limitations paragraph" per `MANUSCRIPT_OUTLINE.md` §8 stating N ≤ 50 per dataset, single provider, not confirmatory.
- **Is current evidence sufficient?** No — and the Introduction does not pretend otherwise. This concern is fundamentally about sample size, and no new LLM queries were run (nor should they be, per this task's "no new experiments, no API calls" constraint and `MISSING_COMPONENTS.md` O3, which explicitly marks "larger LLM campaign" as **not needed for the JDIQ story** and requiring paid API reruns).
- **Wording to avoid:** "real-LLM results confirm generalization" (prohibited in `CANONICAL_PAPER_STORY.md`); any framing of the LLM pilots as a second independent confirmatory experiment rather than a bounded check.
- **Unresolved limitation:** **Open.** This is honestly not fully resolved and should not be presented as resolved. The manuscript's position is that the bounded pilot is *sufficient for its narrow claimed purpose* (checking regime-sensitivity persists directionally) but *insufficient* for any generalization claim — and the Introduction, evidence map, and this document all say so consistently.

---

## 5. "Hybrid fusion may suppress repair effects." (R5)

- **How the Introduction addresses it:** **Fixed during this review pass.** An initial draft omitted this concern; a clause was added to the paragraph enumerating study-design safeguards, stating the study "examine[s] directly whether that fusion step itself can mask a graph-level change, so that a null retrieval result is not silently misattributed to repair being unhelpful." See `INTRODUCTION_EVIDENCE_MAP.md` row I-13b.
- **Section that fully addresses it:** §7 Failure Taxonomy — the `metric_neutral_ranking_change` and `extraction_insensitivity` classes, and specifically Supplementary Figure SF02 ("Fusion Suppression Rates for Hybrid Methods," `FIGURE_SPECIFICATIONS.md`), plus `experiments/final_method_gap_audit_20260711_221113/task1/extraction_fusion_complete.csv`. `RESULTS_EVIDENCE_MAP.md` (R7) now gives a precise, code-verified metric: for the Copeland/RRF combination matching the main paper's $\alpha=0.3$ hybrid, fusion suppresses the graph-level ranking change (repair changed the raw graph ranking, but the fused hybrid ranking did not) in 14.7% of query-method comparisons.
- **Is current evidence sufficient?** Yes, now with an exact figure, not only a qualitative diagnosis. The claim-support matrix classifies `fusion_suppresses_repair` as `safe_with_qualification` ("supported diagnostically, not as universal law") — the 14.7% figure is real evidence of the mechanism's frequency, not proof it is *the* explanation for every null result (the six-class taxonomy in §7 shows five other classes). The Introduction's clause and the Results plan's wording are both calibrated to this qualification.
- **Wording to avoid:** "fusion suppression fully explains the null results" (overclaims a single causal mechanism where the taxonomy shows six distinct classes).
- **Unresolved limitation:** None remaining at the Introduction level. §7/§10 must still present the `extraction_fusion_complete.csv` evidence with the same qualification, not a stronger claim.

---

## 6. "Greedy FAS lacked stronger comparisons." (R6)

- **How the Introduction addresses it:** States directly that "the greedy feedback-arc-set heuristic used in the main experiments is compared against stronger exact and near-exact repair variants, which improve the graph-internal structural objective further but do not change the retrieval conclusion."
- **Section that fully addresses it:** §4.4 (Repair Variants Compared, Table 4) now gives this comparison in full, and it is now **fully reproducible from this repository alone**. Following a dedicated integrity audit (`integrity_audit/EXTERNAL_SOLVER_IDENTITY.md`, `EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`) and the patch applied in this pass, Table 4 reports exactly two procedures: greedy (all 1,020 queries) and exact-for-small-components (exact on SCCs $\le10$ nodes, greedy fallback above, also all 1,020 queries) — both in-repository, both full-coverage, neither a bounded sample.
- **Is current evidence sufficient?** Yes, and more cleanly than before this pass. The audit found that four additional variants (an SCC-bounded exact solver and three metaheuristics) depend on a separate, author-maintained software package that is genuinely public but registered under the manuscript's real (anonymized) author identity — citing it by name during double-blind review would deanonymize the submission. Because the pooled "stronger repair does not change the retrieval conclusion" claim was already carried entirely by the in-repository `exact_small_greedy_hybrid` comparison (confirmed via `REPAIR_COMPARISON_FINAL_REPORT.md`: "Best stronger repair selected for Task 3: `exact_small_greedy_hybrid`"), removing the four external-dependent rows costs nothing scientifically. Their existence and bounded-sample outcome (same qualitative pattern) is retained as one anonymized, unnamed sentence in §4.4, with full disclosure deferred to camera-ready.
- **Wording to avoid:** "exact repair confirms greedy is optimal" (not tested — only that it doesn't change the retrieval conclusion, which is a narrower claim); naming or linking the withheld external package anywhere in the anonymous manuscript.
- **Unresolved limitation:** None remaining for the main-paper claim. If the four external-dependent variants are ever presented quantitatively (camera-ready or supplement only), the same "bounded 100-query sample, seed=42" caveat from `EXTERNAL_SOLVER_EXECUTION_TRACE.md` must be preserved.

---

## 7. "Dataset breadth and protocol consistency were weak." (R7)

- **How the Introduction addresses it:** States the four-dataset, three-regime scope explicitly and says all structural/retrieval outcomes are reported "broken out by regime rather than pooled" specifically so that protocol differences are not conflated.
- **Section that fully addresses it:** §4 Data and Experimental Protocol, with the explicit warning box already planned in `MANUSCRIPT_OUTLINE.md` §4 distinguishing the vote-suite protocol from the failure-mining pooled protocol.
- **Is current evidence sufficient?** Yes, substantially. The four-dataset `pub_vote_cmp_all4` package is a direct, documented expansion beyond IJCS's own two-dataset canonical package status at various points in its history (the IJCS text itself already reports all four datasets, per `IJCS_REUSE_AUDIT.md`, so this concern may in fact already be resolved relative to whatever version R7 was reacting to — but the *reconstructed* criticism predates certainty about which draft state R7 refers to).
- **Wording to avoid:** Blurring the vote-suite protocol (`pub_vote_cmp_all4`) with the failure-mining pooled protocol (`final_baseline_comparison.csv`) as if they were the same evaluation — `MANUSCRIPT_OUTLINE.md` explicitly requires a "warning box" separating these.
- **Unresolved limitation:** None major; residual risk is only that reviewers may still consider four datasets narrow relative to broad IR benchmark suites (`docs/THREATS_TO_VALIDITY.md` item 1 acknowledges domain coverage is "still narrower than a typical broad IR benchmark suite").

---

## 8. "Too few aggregation baselines were evaluated." (R8)

- **How the Introduction addresses it:** States the study "evaluate[s] the repaired hybrid rankings against a broad grid of fixed aggregation baselines, including reciprocal rank fusion and CombSUM."
- **Section that fully addresses it:** §6 Downstream Quality Results (Table 6, pooled baseline comparison) — 12 methods total (`prior_only, borda, rrf, combsum, score_sum, copeland_unrepaired/repaired, markov_unrepaired/repaired, balance, proposed_hybrid, best_stronger_repair`).
- **Is current evidence sufficient?** Yes. This is a clear, direct, and fully new addition relative to the IJCS submission, which had no comparable pooled baseline grid (confirmed in `IJCS_REUSE_AUDIT.md` §4 disposition).
- **Wording to avoid:** Presenting `proposed_hybrid`'s pooled mean nDCG (0.4549) as competitive without noting CombSUM (0.4622) and RRF (0.4587) both exceed it — the claim matrix (`combsum_rrf_beat_repaired_copeland = safe`) requires this ordering be stated plainly, not softened.
- **Unresolved limitation:** None for this specific concern.

---

## 9. "The manuscript overclaimed." (R9)

- **How the Introduction addresses it:** Every empirical sentence in the Introduction is deliberately hedged to match its actual evidentiary strength (see `INTRODUCTION_EVIDENCE_MAP.md`, in particular I-3, I-9, I-10, I-11, I-16, each of which was written or adjusted specifically to avoid overclaiming relative to `CANONICAL_PAPER_STORY.md`'s "What must NOT be claimed" table).
- **Section that fully addresses it:** This concern is addressed continuously throughout the manuscript, not in one section; the discipline mechanism is `experiments/publication_readiness_audit_20260711_233629/final_claim_support_matrix.csv`, which should be checked against every claim before submission (per `JDIQ_GUIDELINE_SUMMARY.md` §13 item 6, "pre-register claims using final_claim_support_matrix.csv discipline").
- **Is current evidence sufficient?** Yes, as a discipline mechanism. The claim matrix exists and is comprehensive (15 claims classified safe/contradicted/unsupported/exploratory_only). The risk is one of *process* (every future section must be checked against it), not of missing evidence.
- **Wording to avoid:** All entries in `CANONICAL_PAPER_STORY.md`'s "What must NOT be claimed" table verbatim, and their paraphrases: "our method improves retrieval," "repair uniformly improves nDCG," "structural consistency predicts retrieval quality," "production-ready," "a selector reliably decides," "real-LLM results confirm generalization," "memory is practical," "strict SciDocs harm with CI < 0." **Added this pass:** naming, linking, or otherwise identifying the withheld external solver package (`integrity_audit/EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`) anywhere in the anonymous manuscript — this is now an anonymity-integrity rule, not only a claim-discipline one.
- **Unresolved limitation:** None in the Introduction as drafted; §2 and §5–§13 remain to be written and must be checked against the same matrix when drafted. §4 (now complete) has been checked and patched this pass (CombSUM citation, external-solver disclosure, regime-invariance transparency).

---

## 10. "The paper was repetitive and unfocused." (R10)

- **How the Introduction addresses it:** The five contributions are stated once, each covering a distinct evidentiary axis (structural measurement / bootstrap decoupling / failure taxonomy / baseline comparison / CARB release) with no restatement; `INTRODUCTION_EVIDENCE_MAP.md`'s "sentences intentionally NOT mapped" section confirms the contributions list restates already-established claims rather than introducing new unsupported ones, which keeps it tight rather than repetitive.
- **Section that fully addresses it:** Overall manuscript structure (`MANUSCRIPT_OUTLINE.md`'s section-by-section page budget, ~22–25 pages total) is designed with one primary purpose per section and no duplicated content across sections (e.g., bootstrap results live only in §6, not restated in §7 beyond what's needed to explain failure classes).
- **Is current evidence sufficient?** N/A — this is a writing-quality concern, not an evidentiary one. The mitigation is structural discipline during drafting, which this task's Introduction attempts (1,448 words, within the 1,200–1,700 target; no paragraph restates another paragraph's central claim).
- **Wording to avoid:** N/A (writing-quality, not claim-wording).
- **Unresolved limitation:** Cannot be fully assessed until the full manuscript (§2–§13) is drafted; the Introduction alone cannot guarantee the whole paper avoids repetition, only that it does not itself repeat.

---

## Related but not directly requested (R11–R15, for completeness)

| Reviewer | Concern | Status relative to this Introduction |
|---|---|---|
| R11 | Missing prior-only/never-repair bootstrap comparisons | Not addressed in the Introduction; `MISSING_COMPONENTS.md` O1 flags this as optional/only-if-reviewer-demands, requiring possible new computation from existing per-query CSVs — **out of scope for this task** (no new experiments) |
| R12 | BEW/PIC self-referential (same qrels as evaluation) | Directly addressed via I-17 in the Introduction (forward reference to Threats to Validity) |
| R13 | `ms1_drop_mutual` is ad hoc | Not addressed in the Introduction; flagged in `IJCS_REUSE_AUDIT.md` §6 Limitations disposition as a gap the future Threats to Validity section must close |
| R14 | HotpotQA underpowered (n=52) | Not addressed in the Introduction; I-10's "single dataset shows a reliable positive effect" should be paired with an explicit n=52 caveat in §6/§11, not yet drafted |
| R15 | Missing modern/LLM baselines | Partially addressed via I-11 (real-LLM pilots); `outputs/final_modern_baselines/` exists but is flagged `do_not_mix` / "different protocol" in `MASTER_EVIDENCE_INVENTORY.csv`, so it is not pulled into the main comparison |

---

## Overall candor summary

Of the 10 requested concerns: **7 are substantially addressed** by the Introduction plus already-existing canonical evidence (R1/1, R5/5 (fixed during this pass), R6/6 (fully resolved as of the post-integrity-audit patch pass — see the dedicated update section below), R7/7, R8/8, R9/9, R10/10); **2 are honestly partial** (R2/2 — diagnostic but not predictive; R3/3 — bounded LLM evidence added but classical rankers remain primary); **1 is explicitly and deliberately left open rather than glossed over** (R4/4 — real-LLM scale is a genuine, acknowledged limitation, not a solved problem).

---

## Update: how Sections 2-4 (Background, Methodology, Experimental Setup) improve coverage

Writing the full technical content of §2–§4 — rather than only asserting scope in the Introduction — moved several concerns from "claimed in prose" to "operationalized in the protocol itself." This update records what changed, per concern.

| Concern | What §2-4 add beyond the Introduction | New status |
|---|---|---|
| R3 — ranker set too narrow | §4.2 (Rankers and Candidate Pooling) states explicitly, as a methodological fact rather than a caveat: "We do not vary the ranker family across regimes or datasets... any difference between regimes reflects the vote-retention rule, not a change in evidence source," and forward-references §11 Threats. The narrowness is now a stated design property of the protocol, not only an acknowledged limitation. | Still **partial** (the ranker family is still narrow) but the framing is now precise about *what* is and isn't varied, which is a more defensible position than a bare caveat. |
| R5 — fusion suppression | §3.6 (Ranking Extraction, Eq.~\eqref{eq:hybrid}) makes the mechanism concrete: the hybrid score is $\hat s_{\mathrm{prior}} + \alpha \hat s_{\mathrm{comp}}$ with both terms min–max normalized, so the algebraic channel through which fusion could mask a graph-level change (a small $\alpha$ relative to the normalized prior) is now visible in the formula itself, not just asserted in prose. | **Improved** — the Introduction's claim now has a formal object (Eq. 7) a reader can inspect. |
| R6 — greedy FAS lacked stronger comparisons | §4.4 (Repair Variants Compared) and Table 4 now report **only** the two fully in-repository procedures (greedy; exact-for-small-components + greedy fallback), both covering the complete 1,020-query canonical package. A prior drafting pass had disclosed four additional external-package-dependent variants with a $\dagger$ marker; a dedicated integrity audit (`integrity_audit/`) traced that package to the author's own separate, unpublished, public-but-identity-revealing GitHub repository and determined the pooled stronger-repair claim never depended on it. Those four rows were removed from the main-paper table this pass; their existence and outcome are retained as one anonymized, unnamed sentence. | **Fully resolved and more honest still** — the comparison is now both scientifically complete *and* free of any anonymity risk, rather than merely "named instead of glossed over" as an interim pass had left it. |
| R7 — dataset breadth / protocol consistency | §4.3 explicitly separates the canonical four-dataset vote-suite protocol from the pooled failure-mining protocol ("We keep this pooled comparison clearly labeled as a distinct protocol throughout the paper rather than merging its numbers... reporting them as though they were one evaluation would overstate the evidence either provides alone"), fulfilling the "warning box" `MANUSCRIPT_OUTLINE.md` §4 called for. | **Fulfilled** — the warning box is now written, not just planned. |
| R8 — too few baselines | Table 3 gives the full baseline list (prior, RRF, CombSUM, Borda, Markov, plus the two hybrid families) with one-line, code-verified descriptions of each. | **Fulfilled** for the canonical four-dataset package; the broader 12-method pooled grid remains a §6 (Results) matter, out of scope here. |
| R9 — overclaiming | §3-4's hedging is now load-bearing, not decorative: "no approximation guarantee," "not a claim of optimality" (§3.4); "a coarse before/after snapshot, not instrumented peak-memory tracking" (§4.6); "a single, unbenchmarked local development machine" (§4.6); "one to two orders of magnitude smaller... not... independent confirmatory evidence" (§4.7). Each hedge is attached to a specific, verifiable methodological fact rather than a general disclaimer. | **Reinforced** with concrete, checkable qualifications. |
| R12 (related) — BEW/PIC circularity | §3.3 states the circularity in the same paragraph that defines BEW/PIC (Eqs.~\eqref{eq:bew}–\eqref{eq:pic}): "when the reference ranking is derived from the same relevance judgments used to compute nDCG, this introduces a circularity that we flag explicitly rather than treat as an independent validation of structural repair." | **Moved earlier** — the caveat now appears at the metric's definition, not only in the eventual Threats section. |

No concern regressed. R2 (no actionable predictive criterion) and R4 (real-LLM scale) are unchanged by this pass — both remain honestly partial/open, as before, since resolving them would require new modeling or new experiments respectively, neither of which is in scope.

---

## Update: post-integrity-audit patch pass (this task)

Following the dedicated integrity audit (`integrity_audit/FINAL_REPORT.md`) and its go/no-go recommendation, this pass applied the required patches and re-verified coverage.

| Concern | What changed this pass | New status |
|---|---|---|
| R6 — greedy FAS lacked stronger comparisons | Table 4 patched to remove the four external-package-dependent rows; an anonymized qualitative sentence retained in their place. See the updated row 6 above (superseding the earlier addendum entry, which described the *discovery* of the anonymity risk, not yet its resolution). | **Fully resolved** |
| R8 — too few aggregation baselines | CombSUM is now correctly cited (`fox1994combination`, verified against two independent NIST-affiliated primary sources) and its implementation (min-max per-(query,ranker) normalization, missing-document handling, tie-breaking) is described precisely in §4.3, replacing an inline `TODO` and a previously wrong citation (`cormack2009rrf`, the RRF paper). | **Fulfilled**, now with correct provenance, not only a complete method list |
| R9 — overclaiming | Graph-independent baselines (prior, RRF, CombSUM, Borda-count) are now explicitly disclosed as regime-invariant by construction, with a dedicated paragraph in §4.3 stating that repeated regime-labeled rows for these methods "reflect the same underlying score fused once... not independent reruns or additional evidence." A forward-looking `TODO` was added to the §6 (Downstream Results) placeholder so this transparency carries through to Results' win/tie/loss accounting rather than being forgotten once §4 is out of view. | **Reinforced** — a subtle statistical-accounting risk (triple-counting graph-independent baselines' effective sample size) is now flagged before it could appear silently in Results |
| Anonymity (cross-cutting, not one of R1–R15 but elevated to a first-class concern by the integrity audit) | The withheld-package disclosure in §4.4 was checked and confirmed not to name, link, or otherwise identify the external repository or its real-name-bearing GitHub account anywhere in `main.tex`. | **Resolved and verified this pass** — see Part 9 compile/verify checklist |

`RESULTS_EVIDENCE_MAP.md` and `RESULTS_SECTION_PLAN.md` (new this pass, not yet written as manuscript prose) confirm that the eventual Results section has a fully in-repository, fully reproducible evidentiary basis for every claim in R1–R9's evidence inventory, with no claim depending on the withheld package. This directly answers the standing instruction that "Results will include strong baseline comparison and failure analysis": both are planned in detail (§6/Table 6 for baselines, §7/Table 7 for the failure taxonomy), sourced from canonical, already-verified CSVs, with no new experiments required.

**Still candidly partial, unchanged by this pass:** R2 (diagnostic, not predictive) and R4 (real-LLM scale) remain open for the same reasons as before — both would require new modeling or new experiments to close, neither of which is in scope for this or the prior pass.

---

## Final status: complete first draft (this pass)

With Sections 5–13, the Abstract, and the Data Availability section now drafted, every one of the 10 requested concerns has a concrete manuscript location, not only a planned one. Final disposition:

| # | Concern | Where addressed in the complete draft | Status |
|---|---|---|---|
| R1 | Main conclusion too natural / insufficiently novel | §7 (failure taxonomy, new relative to IJCS), §10 (CARB), §11 (discussion frames the decoupling as the paper's central, non-obvious finding, not an apology for a null result) | **Fully resolved** |
| R2 | No actionable criterion for when repair helps | §7 (taxonomy) + §11 (explicit statement that a predictive criterion would require identifying an observable pre-repair signal, and that attempts so far give only modest, non-decisive signal) + §12 (restated as a limitation) | **Partially resolved, honestly** — diagnostic, not predictive; stated plainly in three places rather than glossed over |
| R3 | Preference sources too classical | §4.2 (explicit design statement) + §8 (bounded real-LLM check) | **Partially resolved** — classical rankers remain primary; real-LLM check is bounded, not a full remedy |
| R4 | Real-LLM evaluation too small | §8 (explicit query counts, single provider, no BRIGHT coverage) + §12 (restated as a limitation) | **Left open, honestly** — stated as a genuine, unclosed limitation, not implied to be resolved |
| R5 | Fusion may suppress repair effects | §7 (14.7\% suppression rate, precisely defined) + §11 (fusion framed as "both a stabilizer and a suppressor") | **Fully resolved** — quantified, not just hypothesized |
| R6 | Greedy FAS lacked stronger comparisons | §6 (exact-for-small-components comparison, full 1,020-query coverage, fully in-repository) + §9 (cost without retrieval benefit) | **Fully resolved** |
| R7 | Dataset breadth / protocol consistency weak | §4.3 (protocol-separation statement, repeated at each point of use in §6/§7) | **Fully resolved** for the four-dataset scope; four datasets remain narrower than a broad IR benchmark suite (stated in §12) |
| R8 | Too few aggregation baselines | §6 (12-method pooled comparison, Table 6, correct CombSUM citation) | **Fully resolved** |
| R9 | Manuscript overclaimed | Consistent hedging throughout §5–§13 (e.g., "exact-for-small-components," not "exact"; "bounded away from negative," not "excludes zero"; explicit "we do not claim" statements in the Abstract, §11, and §13) | **Fully resolved as a discipline**, verified against `final_claim_support_matrix.csv` at each section |
| R10 | Manuscript repetitive/unfocused | Each of §5–§13 has one central question and does not restate another section's finding as its own (see `RESULTS_SECTION_PLAN.md`'s cross-cutting rule 1); Discussion (§11) explicitly does not restate Results, per its own opening sentence | **Fully resolved**, pending the final consistency pass across §1–§4 (next task) |

**Two concerns remain honestly open by design, not by oversight:** R2 and R4. Both are stated candidly at three separate points in the manuscript (their originating section, §11 Discussion, and §12 Limitations) rather than mentioned once and left for the reader to notice was never revisited.
