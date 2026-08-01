# Submission Checklist

Date: 2026-08-01

## Files

| Item | Status | Path |
|---|---|---|
| Final manuscript source | PASS | `manuscript/main.tex` |
| Final PDF | PASS | `manuscript/main.pdf` |
| Bibliography | PASS | `manuscript/references.bib` |
| Figure files | PASS | `figures/f1_pipeline.pdf` through `figures/f5_exact_vs_greedy_gap.pdf` |
| Springer class and bibliography style | PASS | `template/sn-jnl.cls`, `template/bst/sn-basic.bst` |
| Cover letter | PASS | `COVER_LETTER.md` |
| Reviewer suggestions | PASS | `REVIEWER_SUGGESTIONS.md` |
| Keywords/running title | PASS | `KEYWORDS_RUNNING_TITLE.md` |
| Optional highlights | PASS | `HIGHLIGHTS.md` |
| Scientific audit | PASS | `PRE_SUBMISSION_SCIENTIFIC_AUDIT.md` |
| Simulated reviews | PASS | `SIMULATED_REVIEWS.md` |
| Reproducibility audit | PASS | `REPRODUCIBILITY_AUDIT.md` |
| Journal compliance checklist | PASS | `JOURNAL_COMPLIANCE_CHECKLIST.md` |

## Final QA Commands

The final command results are recorded in `FINAL_CHANGELOG.md` after compile and commit preparation.

Required checks before submission:

- Compile with Tectonic.
- `git diff --check`.
- Scan manuscript/package files for development markers and unresolved author notes.
- Verify citation keys and labels.
- Verify no duplicate BibTeX keys.
- Verify no stale auxiliary files are staged.
- Run repository secret scan.

## Submission Caveats

- Do not submit raw provider request/response payloads.
- Do not cite internal Gurobi validation artifacts as manuscript evidence.
- Do not open a pull request for this final-stage branch unless separately requested.
- Do not submit the manuscript from this repository audit process.
