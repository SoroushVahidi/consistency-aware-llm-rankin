# Figure 6 Specification

**Prepared:** 2026-07-12
**Scope:** Canonical plotting package for Figure 6 (failure-class distribution). No image generated in this task.

---

## Source and integrity

All six rows are read directly, this session, from `experiments/failure_class_audit_20260711_212157/phase_reports/manual_failure_summary.csv` — the same canonical source already underlying `main.tex` Table 7 (`tab:failure-taxonomy`). No recomputation was performed; counts and percentages are copied verbatim.

## Percentage sum check

$652 + 210 + 55 + 54 + 26 + 23 = 1{,}020$, matching the corpus size exactly. The six `pct` values in the source file sum to $0.999999999999999\overline{9}$ (i.e., exactly $1.0$ up to floating-point representation error, not a real discrepancy) — verified by direct summation this session. No class was omitted or double-counted.

## Design

- **Type:** Sorted horizontal bar chart, descending by count (already reflected in `plot_order`), consistent with Table 7's existing row order.
- **$x$-axis:** Count (with percentage of 1,020 records as a secondary label on or beside each bar, e.g., "652 (63.9%)").
- **$y$-axis:** Failure-class name (human-readable labels as in the CSV, not the raw `snake_case` category identifiers from the source file).
- **Color:** A single accent color highlighting "Repair-inactive" (the dominant class, 63.9%) is reasonable, but not required; all six classes can share one color family with the sort order alone carrying the visual emphasis.
- **Annotation:** Consider a small secondary annotation of mean $\Delta$nDCG per class (already in Table 7) directly on or beside each bar, since the taxonomy's diagnostic value comes from pairing frequency with effect size — "Wrong-direction repair" is a small bar (5.4%) but the only one with a materially negative mean effect, and this pairing is worth making visible in the figure, not only in the table.
- **Size:** Single-column or 1.5-column width (six short bars do not need double-column space).

## Placement

All six classes belong in the **main text** (`main_text_or_supplement = main_text` for every row), matching Table 7's current placement in §7 (Failure Taxonomy and Diagnostic Analysis) — this taxonomy is one of the paper's central diagnostic contributions (Section 11 Discussion; `REVIEWER_CONCERN_COVERAGE.md` R1/R5), not a supplementary detail. No class is proposed for supplementary-only placement.

## What must not appear in the image

- No recomputed percentages or counts different from the CSV above.
- No merging of classes not already merged in the canonical source (e.g., do not combine "Metric-neutral change" and "Extraction-insensitivity" into one bar — they are analytically distinct per Section 7's prose, even though their counts are close).
