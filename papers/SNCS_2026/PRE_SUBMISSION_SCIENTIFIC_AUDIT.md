# Pre-Submission Scientific Audit

Date: 2026-08-01
Branch: `papers/sncs-2026-foundation`
Manuscript: `manuscript/main.tex`

Scope: independent read of the manuscript text as a submission reviewer would see it. Prior planning files were not used to decide whether a statement was acceptable; repository evidence was consulted only after a possible factual or evidentiary issue was identified.

## Summary

Overall status: PASS after correction of one factual presentation error.

The manuscript's central scientific conclusion remains unchanged: preference-graph repair is structurally active, but no repaired-versus-unrepaired nDCG comparison survives Holm correction in the canonical, larger-pool, or exact-repair comparison families. No new experiments were run and no canonical numerical result was changed except for a stale displayed "smallest Holm-adjusted p" detail that does not affect any rejection count or conclusion.

## Issues and Resolutions

| Severity | Location | Issue | Resolution |
|---|---|---|---|
| Critical | None | No unsupported central conclusion, fabricated result, missing primary evidence, or contradiction between Results and Conclusion was found. | Acceptable. The central null conclusion is supported by the Results tables and explicitly bounded in Discussion and Limitations. |
| Major | Results, Table `tab:retrieval-holm` and adjacent prose | The displayed smallest Holm-adjusted p-value for the active and full canonical greedy-repair families was stale. Recomputing from `table_primary_bootstrap_permutation.csv` with `consistency_ranker.statistical_inference.holm_adjust` gives 0.240 for the active canonical family and 0.720 for the full canonical family, not 0.384 for both. The Holm-rejected counts remain 0/20 and 0/60. | Fixed in `main.tex`, `result_claims.yaml`, and `RESULTS_CROSS_CHECK.md`. This is a factual correction only; it does not alter any conclusion. |
| Major | Introduction, Discussion, Conclusion | Risk that the null result could be read as "repair never helps retrieval." | Acceptable after audit. The manuscript repeatedly states the narrower claim: no statistically supported general improvement in this evidence, with small or dataset-specific effects still possible. |
| Major | Supporting LLM Evidence | Six-query LLM pilot could be overread as confirmatory. | Acceptable. The manuscript states cluster-level n=6, calls it directional/supporting only, and says it does not extend the main conclusion by itself. |
| Major | Exact repair framing | Exact SCIP repair could be mistaken for a production scalability claim. | Acceptable. The paper consistently frames exact repair as a diagnostic control on heuristic suboptimality and limits scalability claims. |
| Minor | Related Work | Two sentences contained citation clusters with more than four cited works. | Fixed by splitting the literature claims into separate sentences. |
| Minor | Journal language/style | Heading used British "Acknowledgements" while the paper otherwise follows American English and the journal page uses "Acknowledgments." | Fixed in `main.tex` and active workspace notes. |
| Minor | Active workspace notes | `README.md` and `GENERATIVE_AI_DISCLOSURE.md` retained resolved placeholder-style notes from earlier stages. | Fixed to reflect final-stage state and remove unresolved author-confirmation text. |
| Editorial | Section transitions | The manuscript repeats the structural-vs-retrieval distinction in several places. | Acceptable. Repetition is purposeful because it prevents over-interpretation; redundant phrasings were not found severe enough to justify cutting evidence-bearing caveats. |

## Section-by-Section Scientific Judgment

| Section | Evidence support | Reviewer risk | Judgment |
|---|---|---|---|
| Abstract | Matches Results after p-value correction indirectly; no unsupported numbers or citations. | Could be too broad if "repair removed non-trivial contradictory edge weight" were not bounded. | Acceptable because it says "in this evidence" and reports only central findings. |
| Introduction | Defines the gap and scope accurately. | Skeptical reviewer may ask why score-derived graphs are relevant to LLM ranking. | Acceptable because the manuscript labels the main evidence as score-derived and keeps the LLM pilot bounded. |
| Related Work | Claims are supported by cited literature categories. | Citation density and self-preprint positioning. | Citation density fixed. Self-preprint is clearly identified as a preprint and as superseded by the current protocol. |
| Background | Mathematical objects are defined before use. | MWFAS MIP equivalence may invite algorithmic-detail questions. | Acceptable for a CS audience; exact solver is not claimed as a new formulation. |
| Methodology | Protocol, datasets, rankers, repair methods, extraction rules, and statistics are specified. | Candidate-pool choice and alpha choice could be challenged. | Acceptable because robustness checks and limitations discuss both. |
| Results | Tables and figures support each RQ. | Stale p-value detail. | Corrected. Rejected-cell counts and conclusions remain supported. |
| Discussion | Separates results from plausible mechanisms. | Mechanistic explanations could be read causally. | Acceptable because the text explicitly says mechanisms are consistent with, not demonstrated by, the design. |
| Limitations | Covers internal, construct, external, statistical, and computational validity. | Could be viewed as long. | Acceptable; the scope is complex and the cautions reduce overclaiming. |
| Conclusion | Answers RQ1-RQ4 and preserves the null-result boundary. | None after audit. | Acceptable. |

## Final Scientific Status

Submission-ready after the p-value display correction. No new analyses, experiments, or scientific claims were introduced.
