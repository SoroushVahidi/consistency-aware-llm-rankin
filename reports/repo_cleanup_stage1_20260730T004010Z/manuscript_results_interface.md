# Manuscript-Results Generated Interface — Stage 1 Demonstration

## Problem

`papers/JDIQ_2026/manuscript/main.tex` contained **zero** `\input{}` statements pulling in any generated `.tex` fragment — every cited statistic was a hand-typed literal (verified: `grep -c "\\input{" main.tex` returned 0 before this stage). Nothing prevented the prose from silently drifting away from the tables that back it.

## What was built

- **`scripts/generate_manuscript_macros.py`** — reads the canonical source tables directly (never a second-hand copy) and writes `papers/JDIQ_2026/manuscript/generated_macros.tex`, a flat list of `\newcommand` macros, each with a `% SOURCE: ...` comment naming the exact file it came from. Deterministic (pure function of tracked CSV/JSONL inputs, no randomness, no network). Every reader function asserts the expected shape (row counts, dataset sets, method-key presence, metric sets) and raises `AssertionError` if the source data no longer matches what was hand-verified — it fails loudly rather than silently emitting a wrong number.
- **`scripts/check_manuscript_macro_drift.py`** (+ `tests/test_manuscript_macro_drift.py`) — regenerates the macros in-memory and diffs against the committed `generated_macros.tex`; also spot-checks that `main.tex` still `\input`s the file and no longer contains the specific hand-typed literals this migration replaced. Exit code 1 on any drift. Verified to actually catch drift (tampered the committed file, confirmed the check fails; restored it, confirmed the check passes again).
- **Six representative macro categories wired into `main.tex`**, replacing the equivalent hand-typed literals in place (no new prose added):

| Category (from the task brief) | Macro(s) | Source | Wired into main.tex? |
|---|---|---|---|
| Number of datasets and queries | `\NDatasets`, `\NQueriesSciDocs/FiQA/HotpotQA/Bright` | `full_calibrated_core/table_primary_graph_structure.csv` | **Yes** — Table~\ref{tab:setup}'s "Usable" column and the Limitations-section "four benchmarks" sentence |
| Baseline ranking / CombSUM comparison | `\CombSumNDCGTen`, `\RRFNDCGTen` | `full_calibrated_core/table_primary_macro_method_comparison.csv` | **Yes** — the "CombSUM has the best dataset-macro mean nDCG..." sentence (3 occurrences) |
| Cutoff-robust significance counts | `\LargerPoolActiveCells`, `\LargerPoolHolmSignificant` | `final_revision_task1_pool_cutoff_20260715/tables/pool_cutoff_statistics.csv` | **Yes** — both the prose sentence and Table~\ref{tab:primary-findings}'s row |
| Exact-vs-greedy effect bounds | `\ExactVsGreedyMaxAbsDelta` | `exact_open_source_ilp_repair_investigation/tables/retrieval_metric_paired_per_query.csv` | **No, deliberately** — see "Not yet migrated" below |
| Structure–utility correlation | `\StructureUtilityPooledR`, `\StructureUtilityPooledN` | `ir_evidence_audit_20260729T182949Z/structure_utility_associations.csv` | **No, deliberately** |
| Real-LLM unique-query count and query-graph count | `\RealLLMQueryGraphs`, `\RealLLMUniqueQueries` | `extraction_study_20260729T151610Z/extraction_results.jsonl` | **No, deliberately** |

## Why three of the six are generated but not wired into prose

`main.tex` is the already-submitted, frozen JDIQ_2026 manuscript. It predates this session's evidence audit and does not currently discuss the exact-vs-greedy metric-family bound, the structure-utility correlation, or the real-LLM exploratory studies at all — there is no existing sentence to migrate. Wiring these three in would mean **adding new scientific prose**, which this stage's brief explicitly excludes ("do not rewrite the manuscript's scientific narrative yet"). Instead:
- The macros are generated and verified correct (values confirmed against the meta-audit's independent spot-checks in `reports/ir_evidence_audit_review_20260729T235053Z/`).
- `check_manuscript_macro_drift.py` prints their current values every run (see its "not-yet-migrated" section) so a future author adding this prose has an already-correct, already-tested macro to cite immediately instead of hand-copying a number again.

## Non-destructive guarantees verified

- `generated_macros.tex` is a **new** file; no existing file was overwritten by the generator itself.
- The six macro substitutions in `main.tex` were **manual, reviewed edits** (via `Edit`, not a scripted find-replace), each checked against the exact surrounding sentence before and after.
- Existing numerical values did not change: `0.554`/`0.546`/`120`/`52`/`50`/`110`/`0` are exactly what the macros now render as — verified by generating `generated_macros.tex` and confirming its values match what was already in the prose before migration (no discrepancy was found or silently "corrected").
- Brace-balance check on the full `main.tex` passes (`depth == 0` at EOF).
- Every macro used in `main.tex` is defined exactly once in `generated_macros.tex`, and every macro defined is either used or explicitly documented as not-yet-migrated (checked via `comm`/`grep`, see `validation_results.md`).

## Manuscript compilation status

**Not fully verified — no LaTeX engine (`pdflatex`/`xelatex`/`lualatex`) is installed in this environment; only a `latexmk` shim is present, which reports "no .tex file found" and cannot actually typeset.** Do not read the checks above as a substitute for a real compile. What *was* verified without a LaTeX engine:
- Brace balance across the full `main.tex`.
- `\input{generated_macros}` path resolves correctly relative to `main.tex`'s own directory (both files are in `papers/JDIQ_2026/manuscript/`), which is how LaTeX's `\input` resolves paths by default.
- No duplicate `\newcommand` definitions, no undefined-macro usages (see `validation_results.md` for the exact commands run).

**Recommended follow-up**: run `latexmk -pdf main.tex` in an environment with a real TeX Live/MiKTeX install before treating this migration as final; this stage could not do so.

## Migration plan (for later stages, not this one)

1. Once the real-LLM findings and the new evidence audit are incorporated into `main.tex`'s scientific narrative (a separate, larger editorial task), wire `\ExactVsGreedyMaxAbsDelta`, `\StructureUtilityPooledR`/`\StructureUtilityPooledN`, and `\RealLLMQueryGraphs`/`\RealLLMUniqueQueries` into that new prose as it is written, rather than retrofitting them.
2. Extend `generate_manuscript_macros.py` incrementally, one macro at a time, each backed by the same fail-loudly assertion pattern already established — do not batch-migrate the remaining ~40+ hand-typed numbers in one pass; each migration should be an individually reviewable diff.
3. Add `python scripts/check_manuscript_macro_drift.py` (or the `pytest` wrapper) to CI once this pattern is trusted, so future table regenerations that change a cited number are caught automatically.
4. Consider a real LaTeX-compile CI job (or a local pre-submission checklist step) now that `\input` is in use, since a missing/misnamed macro is a hard compile error, not a silent one — this is a feature, not a gap, but should be exercised at least once in an environment with a working TeX toolchain before the next submission.
