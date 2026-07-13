# Final Report — Pre-Results Integrity Investigation

**Prepared:** 2026-07-12
**Scope:** External solver trace (Part A) + CombSUM citation/implementation (Part B) + manuscript cross-check (Part C). No Results were written, no canonical outputs were modified, no expensive runs were launched, no citations were fabricated. Internet access was available and used successfully for all primary-source verification steps.

---

## The ten questions, answered plainly

### 1. What exactly is the external solver package?

`minimum-weighted-fas-heuristics` — the same author's (Soroush Vahidi's) own separate research repository for a different, currently-unpublished manuscript on feedback-arc-set heuristics (declined once at *Computational Optimization and Applications*; currently being retargeted to *SN Computer Science*, not yet submitted). It is not a third-party package. Full identity trace: `EXTERNAL_SOLVER_IDENTITY.md`.

### 2. Is it public?

Yes — verified live via an unauthenticated call to the GitHub API (`"private": false`), not merely inferred from local git configuration. MIT-licensed. But "public" here cuts against the manuscript, not for it: the repository is registered under the account `SoroushVahidi`, the real name of this JDIQ submission's (currently anonymized) author. Naming or linking it in the anonymous-review manuscript would deanonymize the submission. This is the single most important fact this investigation surfaced.

### 3. Which results depend on it?

Four rows in `experiments/final_method_gap_audit_20260711_221113/task2/repair_comparison_real.csv`, each computed on a fixed, seeded (seed=42), capped sample of 100 cyclic queries with a 10-second per-query timeout: `exact_scc_dp20`, `lrta_external`, `wmsf_external`, `ipsns_external`. All four runs completed with zero recorded failures — this is a genuine, complete result, not a broken one. Full dependency map: `external_solver_result_dependency.csv`; full execution trace including exact function calls, parameters, and completeness verification: `EXTERNAL_SOLVER_EXECUTION_TRACE.md`.

### 4. Can those results be reproduced?

Not by a third party, and not by the author either without the sibling repository present at the exact hardcoded path `/home/soroush/minimum-weighted-fas-heuristics`. This repository's own `.venv` does not have `mwfas` pip-installed (verified this session), and this repository does not vendor a copy of it.

### 5. Do they change the paper's conclusions?

No. The central "stronger/exact repair does not improve retrieval" claim is carried entirely by `exact_small_greedy_hybrid` — an **in-repository, no-external-dependency** method (exact brute-force on SCCs ≤10, greedy fallback above) that is explicitly named in `REPAIR_COMPARISON_FINAL_REPORT.md` as "Best stronger repair selected for Task 3," i.e., as the method actually feeding the pooled Table 6 comparison. The four external-dependent methods are a secondary, bounded robustness check that shows the *same* qualitative pattern (if anything, a more negative nDCG delta), not a different one.

### 6. Should we keep, replace, move, or remove them?

**Remove the four rows from the main-paper Table 4** (Option E for the main paper), because (a) they are not needed for any conclusion, and (b) they cannot be disclosed by name without a real anonymity risk. This is not a blanket "delete because it's external" reflex — Options A-E were scored individually in `EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`, and removal wins specifically because the scientific value is low-to-medium while the anonymity risk of any disclosure that names the package is severe. A fallback (Option B, anonymized disclosure with a withheld-citation footnote) is documented if the authors prefer to keep the four-algorithm robustness angle explicit.

### 7. What should Table 4 contain after the decision?

Two rows only, both fully in-repository and both already covering the complete 1,020-query canonical package (not a 100-query bounded sample):

| Procedure | Scope |
|---|---|
| Greedy (cycle-peeling) | All queries; canonical repair used throughout |
| Exact (brute-force, SCCs ≤ 10) + greedy fallback | All queries |

A short qualitative sentence (given verbatim in `EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`) should replace the four removed rows, reporting that a bounded robustness check against additional solvers showed the same pattern, without naming the solvers, with a commitment to full disclosure at camera-ready.

### 8. What is the verified CombSUM citation?

Fox, E. A., & Shaw, J. A. (1994). "Combination of Multiple Searches." *The Second Text REtrieval Conference (TREC-2)*, NIST Special Publication 500-215 (D. K. Harman, ed.), pp. 243-252. No DOI exists (confirmed explicitly absent on the NIST catalog page, not merely unlisted). Verified directly from two independently fetched NIST-affiliated sources (the primary source paper itself, and the NIST publications catalog record) — full BibTeX in `COMBSUM_MANUSCRIPT_PATCH.md`.

### 9. What exact CombSUM variant did we implement?

Fox & Shaw's original sum-of-scores fusion rule, unmodified, but with per-(query, ranker) min-max normalization to $[0,1]$ applied before summation — an adaptation necessary because this study fuses heterogeneous ranker scales (BM25, TF-IDF, a neural cross-encoder), which is not addressed in the 1994 original. Missing documents contribute 0; ties are broken deterministically by best original rank, then document id. Full formula trace: `COMBSUM_IMPLEMENTATION_AUDIT.md`. Recommendation: keep the name "CombSUM" (the adaptation is to the input normalization, not the fusion rule itself), with one disclosure sentence in Methodology.

### 10. What manuscript patches are required before Results?

See the file-by-file plan immediately below.

---

## File-by-file patch plan

| File | Change | Priority |
|---|---|---|
| `main.tex` §4.4 (Table 4 + disclosure paragraph) | Remove the four `$\dagger$`-marked rows and their disclosure paragraph; replace with the anonymized qualitative sentence given in `EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md` | **Critical — resolve before any further drafting that might get shared/reviewed** |
| `main.tex` §4.6 (Implementation paragraph) | Remove the now-dangling cross-reference to "the external package described in Section 4.4" once Table 4 is patched | High (follows directly from the above) |
| `main.tex` §4.3 (CombSUM sentence + Table 3 context) | Add `\cite{fox1994combination}`; add the one-sentence normalization-adaptation disclosure; remove the `TODO` comment | Medium |
| `references.bib` | Add the verified `fox1994combination` BibTeX entry | Medium (blocks the above) |
| `README.md` | Update "Known open items" #6 to name the anonymity conflict specifically (not just "cite properly" as if that were freely available); update #8 to point to the now-verified citation | Low (documentation hygiene) |
| `REVIEWER_CONCERN_COVERAGE.md` | Update the R6 rows to reference the anonymity finding, not only the "bounded diagnostic slice" completeness caveat | Low (documentation hygiene) |
| Future Results section (§6, not yet drafted) | When written, incorporate the CombSUM regime-invariance / effective-sample-size caveat and the FiQA (n=359) / BRIGHT (n=145) non-exact-multiple-of-3 note | Deferred (no action needed until Results is drafted) |

No patches were applied to `main.tex` or `references.bib` in this task, per instructions.

---

## Future rerun commands (specified, not executed)

**Only needed if Option D (new in-repository bitmask-DP exact solver for SCCs 11-20) is pursued** to fully close the external dependency rather than simply removing the four rows:

1. Implement a new function, e.g. `src/consistency_ranker/exact_fas_dp.py::exact_min_fas_dp`, following the documented recurrence in the external package's own `mwfas/exact.py` docstring (`dp[S] = max over v in S of dp[S\{v}] + inc(v, S\{v})`), for `n <= 20`.
2. Verify it against the existing brute-force `exact_fas.py` on the same toy instances used in this session's lightweight check (`EXTERNAL_SOLVER_EXECUTION_TRACE.md`'s equivalence check already confirms the external DP and the in-repo brute-force agree on a 4-node example; a new in-repo DP implementation should be checked against both).
3. Rerun only the `exact_scc_dp20`-equivalent branch of `experiments/final_method_gap_audit_20260711_221113/run_final_method_gap_audit.py` task2, using the same `EXTERNAL_CYCLIC_CAP=100`, `seed=42` sampling, replacing the `_apply_external_repair(graph, "exact_scc_dp20")` call with the new in-repo function.

**Estimated cost:** implementation, small (single self-contained function, well-understood algorithm; no new experimental design). Rerun cost: same order as the original run (task2 alone took ~10.5 minutes wall-clock for all six methods combined on 1,020+100×4 query-method evaluations; the new DP-only rerun on 100 queries would be a small fraction of that, likely under 2 minutes). No paid API calls, no GPU, no new dataset access required. **Not launched in this session**, per task instructions ("do not launch a large experiment yet").

**LR-TA / WMSF / IPSNS have no proposed rerun command** — there is no in-repository substitute for these three specific algorithms; the only paths are (a) anonymized disclosure of the existing bounded results, or (b) omission, both of which require no rerun.

---

## Files created in this task

All under `papers/JDIQ_2026/manuscript/integrity_audit/`:

1. `EXTERNAL_SOLVER_IDENTITY.md`
2. `external_solver_result_dependency.csv`
3. `EXTERNAL_SOLVER_EXECUTION_TRACE.md`
4. `external_solver_replacement_options.csv`
5. `EXTERNAL_SOLVER_MANUSCRIPT_DECISION.md`
6. `COMBSUM_REFERENCE_VERIFICATION.md`
7. `COMBSUM_IMPLEMENTATION_AUDIT.md`
8. `combsum_protocol_alignment.csv`
9. `COMBSUM_MANUSCRIPT_PATCH.md`
10. `CURRENT_MANUSCRIPT_ISSUES.csv`
11. `FINAL_REPORT.md` (this file)

## Internet verification status

**Succeeded for every step that needed it.** Confirmed live via direct queries in this session:
- GitHub API (`api.github.com/repos/SoroushVahidi/minimum-weighted-fas-heuristics`) — unauthenticated `curl`, HTTP 200, `"private": false`.
- NIST TREC primary source (`trec.nist.gov/pubs/trec2/papers/txt/23.txt`) — fetched and read in full.
- NIST publications catalog (`nist.gov/publications/second-text-retrieval-conference-trec-2`) — fetched and read in full.

No source-verification step was left unresolved due to lack of internet access.

## What remains genuinely unresolved

1. **"paper049"** — the internal reference code for WMSF's predecessor work in the sibling repository — was not resolved to a citable title/author/venue. Not needed for the JDIQ manuscript's own citations (WMSF is recommended for removal from the main paper anyway), but flagged for completeness.
2. **Root cause of FiQA (n=359) and BRIGHT (n=145) not being exact multiples of 3** in the pooled CombSUM comparison was not traced in this session (time-boxed). Does not block any recommendation above; flagged for whoever drafts Results.
3. **The discrepancy between `CITATION.cff` ("not yet published") and `README.md` ("declined / closed")** inside the sibling repository was noted but not further investigated — irrelevant to the JDIQ manuscript's decision either way, since neither status permits citing an accepted publication.

---

## Go/no-go recommendation for drafting Results

**Conditional go.** The scientific evidence behind every claim this investigation touched is sound — the pooled "stronger repair doesn't help" conclusion does not depend on the problematic external package, and the CombSUM baseline is correctly implemented and now properly citable. **Do not proceed to drafting Results, however, until the Table 4 patch (removing or anonymizing the four external-dependent rows) is applied** — leaving the current disclosure in place risks an anonymity breach that has nothing to do with the science and everything to do with a process detail (a hardcoded path to a sibling repo) that this investigation was specifically tasked to catch. Once that one patch is made (and the CombSUM citation patch, which is lower-stakes but should be bundled in the same pass), Results can proceed on a clean, honest, and fully defensible evidentiary base.
