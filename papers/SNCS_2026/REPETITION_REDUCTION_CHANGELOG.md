# Repetition Reduction Changelog (SNCS 2026)

**Date:** 2026-08-02  
**Branch:** `papers/sncs-2026-foundation`  
**Companion audit:** [`REPETITION_AUDIT.md`](REPETITION_AUDIT.md)

No experiments were run. No canonical numerical results were changed.
No new scientific claims were introduced. No paid API calls.

---

## 2026-08-02 editorial consolidation (this pass)

### Before / after metrics

| Metric | Before | After | Change |
|---|---|---|---|
| Body words (Abstract → bibliography; macro-stripped) | 13,368 | **11,279** | −2,089 (−15.6%) |
| PDF pages (`pdfinfo` after clean `tectonic` compile) | 40 | **35** | −5 pages (−12.5%) |

Method: same macro-stripped word counter as prior pass; page count via `pdfinfo` after compiling from `papers/SNCS_2026/manuscript/` with template `sn-jnl.cls` / `sn-basic.bst` copied in then removed.

### Figure 1

- Fetched exact updated figure from `origin/main` commit `3de82709c5af4c44951c2d57285aa914896cc85a`.
- Source path on `main`: `71A559E5-30E7-465F-BDC0-33CF17FC3474.png` (PNG only; no vector PDF uploaded).
- SHA-256: `4feeac61a348f526f79393be017734a7dba45f6502004c8d557c93379bfe5af2`.
- Installed as `papers/SNCS_2026/figures/f1_pipeline.png` (byte-identical).
- `main.tex` now includes `f1_pipeline.png`; caption remains in LaTeX outside the image.
- Older `f1_pipeline.pdf` left on disk but is no longer referenced (not overwritten onto the new asset).

### Section-by-section consolidations

1. **Abstract** — Minor wording tighten; all reported values unchanged.
2. **Introduction** — Single full statement of the four-stage separation, study design, and findings; shorter contributions and scope paragraph; removed repeated “separate claims” restatement.
3. **Related Work** — Compressed pairwise/combinatorial contrast, IR pairwise paragraph, graph-based IR close, MWFAS novelty denial, preprint disclaimer, and utility subsection while retaining citations.
4. **Background §3.4 (MWFAS)** — Kept equations; shortened solver descriptions and diagnostic-control paragraph (primary home remains Intro + this section once).
5. **Background §3.5 (Extraction/Eval)** — Kept nDCG definition; collapsed repeated MWFAS≠nDCG essay to one sentence + cross-refs.
6. **Methodology** — Shortened section opener, RQ scope sentence, pipeline figure caption/follow-on, datasets description, repair-methods diagnostic reminder, metrics proxy sentence.
7. **Results** — Shortened section opener, graph-free comparison close, exact-vs-unrepaired close, and robustness qualification paragraph; all table/figure numbers unchanged.
8. **Discussion §6.1–6.5** — Main findings, mechanism, exact-control, literature, and practical implications rewritten once each without re-proving Background/Results; LLM subsection kept brief.
9. **Limitations** — Internal/construct/external/statistical/computational threats retained with fewer defensive restatements.
10. **Conclusion** — Compact synthesis of the central conclusion without a second practical-bullet essay.

### Intentionally retained (further shortening would weaken precision)

- Structured abstract (self-contained; values preserved).
- Formal MWFAS / linear-ordering equations and SCIP proven-optimality gate.
- Full statistical protocol + Holm family table.
- Robustness table cells (power MDE, TOST counts, fairness).
- Exact-repair coverage counts (`1,025/1,025`, cyclic `n=379`, `87.9%` FAS disagreement).
- Six-query LLM pilot description and cluster-level caveat.
- Practical-implications bullet list (primary home for recommendations).
- Scope denials: non-significance ≠ equivalence; small effects below detectable scale remain possible; exact repair rules out greedy under-repair only for the stated objective/protocol.

### Evidence documents

- `EVIDENCE_MAP.md` / `result_claims.yaml` — **unchanged** (no claim/number edits).
- Scientific code, experiment outputs, and repository-wide non-SNCS files — **unchanged**.

---

## Prior pass (2026-08-01)

Earlier reduction: 42→39 pages, ~15,112→13,419 detex words (−11.2%). See git history of this file for that pass’s detailed item list.
