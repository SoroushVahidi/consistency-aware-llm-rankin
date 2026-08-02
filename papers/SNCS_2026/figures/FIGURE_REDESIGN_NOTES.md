# Figure redesign notes (F1 pipeline + structural inconsistency)

Date: 2026-08-01

## Scope
Visual redesign only. No numerical values or scientific claims changed.

## Figure 1 (`f1_pipeline`)
- Earlier redesign regenerated a vector PDF via `generate_f1_pipeline.py`.
- **Canonical manuscript asset (2026-08-02):** author-uploaded PNG
  `f1_pipeline.png` (SHA-256
  `4feeac61a348f526f79393be017734a7dba45f6502004c8d557c93379bfe5af2`;
  source commit `3de82709c5af4c44951c2d57285aa914896cc85a`). The unused
  redesigned PDF was removed from the tree so extension fallback cannot
  select it.

## Structural inconsistency (`f3_cycle_decomposition` + table)
- Option A: booktabs table above + compact paired-bar chart below in one float
  (`fig:structural-outcomes`).
- Chart values identical to prior ms1 Cyclic / Post-mutual rates.
- Table values unchanged; headers shortened (Cyclic %, After mutual %, FAS wt.).
- Blue/gray paired bars for print-safe before/after contrast.
- Old separate `tab:structural-outcomes` + `fig:cycle-decomposition` merged.

## Before/after previews
See `figures/_redesign_compare/`.
