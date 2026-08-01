# Repetition Reduction Changelog (SNCS 2026)

**Date:** 2026-08-01  
**Branch:** `papers/sncs-2026-foundation`  
**Companion audit:** [`REPETITION_AUDIT.md`](REPETITION_AUDIT.md)

No experiments were run. No canonical numerical results were changed.
No new scientific claims were introduced.

---

## Before / after metrics

| Metric | Before | After | Change |
|---|---|---|---|
| PDF pages (`pdfinfo`) | 42 | **39** | −3 pages |
| Detex body words (Abstract → Statements, excl. bib) | 15,112 | **13,419** | −1,693 (−11.2%) |
| Exact duplicate sentences resolved | 0 exact found | — | N/A (near-duplicates targeted) |
| Near-duplicate / conceptual issues addressed | 14 near-dup pairs + 11 multi-section concepts flagged | **12 resolved or substantially reduced**; **~12 necessary patterns retained** | See below |
| Potentially redundant figures/tables removed | — | **0** (none were removal candidates) | Caption trim only |

Method: detex word count on `main.tex` from `\abstract` through `\bibliography`; page count via `pdfinfo` after `tectonic` compile. PDF rebuilt with the repository’s documented tectonic workflow.

---

## Edits applied (safe reductions only)

### Exact / near-exact consolidation

1. **Methodology §Repair Methods** — Removed near-duplicate greedy algorithm walkthrough and full “diagnostic control” paragraph already stated in Background §MWFAS; kept SCIP version, proven-optimality gate, time limit, brute-force cross-check, and Eades–Lin–Smyth non-attribution.
2. **Methodology §Extraction** — Replaced restated “evaluate on \(G_q\) and \(\widetilde{G}_q\)” paragraph with cross-ref + unique α-masking point.
3. **Methodology §Metrics** — Replaced full three-quantity restatement with short operational pointer to Background §Extraction.
4. **Related Work §Utility close** — Shortened contribution restatement to point at Introduction’s controlled-separation framing.
5. **Declarations §Data availability** — Replaced duplicated URL/payload paragraph with cross-ref to §Data Availability.

### Discussion / Conclusion densification

6. **Introduction finding paragraph** — Compressed overlap with contribution #3; deferred full thesis wording to Discussion.
7. **Discussion §Main Findings** — Replaced Results re-narration with interpretive synthesis + scope denials (kept non-significance caveats).
8. **Discussion §Mechanism** — Dropped formal re-proof of MWFAS≠nDCG already in Background; kept mechanism list in condensed form.
9. **Discussion §Exact Repair** — Cut Results re-argument to a short methodological reading + cross-refs.
10. **Discussion §Literature** — Removed second full preprint paragraph and duplicated “controlled separation” contribution sentence; kept literature contrast + short preprint cross-ref.
11. **Discussion §LLM** — Condensed six-query restatement to one paragraph pointing at Results.
12. **Limitations §External / Statistical / Computational** — Removed repeated power numbers, second LLM essay, and diagnostic-control essay; kept threat framing + cross-refs.
13. **Conclusion** — Replaced RQ1–RQ4 walkthrough and second practical bullet list with compact synthesis + future work.

### Results / visual

14. **Results §Retrieval** — Reduced line-by-line re-enumeration of Holm families already in `tab:retrieval-holm`; kept headline $p$ and forest-plot reading.
15. **`tab:exact-vs-greedy` caption** — Removed retrieval Holm dump duplicated in prose; structural columns unchanged.

### Intentionally retained (necessary repetition)

- Structured Abstract (self-contained).
- Introduction scope denials and numbered contributions.
- Background formal definitions (primary home).
- Methods statistical protocol definition (primary home for Holm).
- Discussion §Practical Implications bullet list (primary home for recommendations).
- Full LLM pilot description in Results §LLM.
- Acknowledgments + Funding dual grant list (Springer dual placement).
  **Superseded 2026-08-01:** API/cloud computational credits are Funding-only;
  Acknowledgments are personal/non-funding only (`FUNDING_ACK_CHANGELOG.md`).
- Brief cross-references that preserve section readability.

---

## Issues resolved vs retained

| Severity (from audit) | Resolved / reduced | Intentionally retained |
|---|---|---|
| Critical (3) | All 3 addressed (diagnostic dual paragraph; preprint dual essay; thesis cascade) | — |
| Major (8) | 7 addressed; 1 partially (Background/Methods still share some extraction vocabulary by necessity) | Formal defs in Background |
| Moderate / Minor | Caption + table-narration + declarations data | Captions kept partly self-contained; funding dual placement |

**Repetition issues resolved (count):** 12 substantive consolidations above.  
**Intentionally retained as necessary:** 12 patterns listed in the audit’s Necessary / retain set (Abstract self-containment, formal defs, stats protocol, practical bullets, Results LLM full statement, funding dual placement, etc.).

---

## Evidence-document updates

- `RESULTS_CROSS_CHECK.md` — amended note that `tab:exact-vs-greedy` caption no longer embeds retrieval Holm counts (numbers remain in `sec:results-exact` prose).
- `EVIDENCE_MAP.md` — **unchanged** (claim→evidence paths and labels unchanged).
- `result_claims.yaml` — **unchanged** (`manuscript_location` labels and values unchanged).

---

## Final reviewer test (post-edit)

| Question | Answer |
|---|---|
| Central conclusion repeated too often? | **No longer** — full statement in Abstract + Discussion; brief recalls elsewhere |
| Distinct section purposes? | **Yes** — Discussion interprets; Conclusion synthesizes; Methods instantiates |
| Discussion adds interpretation beyond Results? | **Yes** — Mechanism and Practical remain; Main Findings/Exact no longer re-list cells |
| Conclusion adds synthesis rather than repetition? | **Yes** |
| Limitations stated once clearly? | **Mostly yes** — LLM/power/exact-role no longer fully restated in three places |
| Still feel like 42 pages of necessary content? | **No** — now 39; remaining length is mostly evidence + formal setup |
| Could an editor call it verbose? | **Less likely** — residual verbosity is methodological precision, not thesis looping |

### Final repetition verdict

**Acceptable repetition**

(Previously: Noticeable repetition. Remaining repetition is mostly necessary self-containment, cross-references, and dual funding/data declarations.)
