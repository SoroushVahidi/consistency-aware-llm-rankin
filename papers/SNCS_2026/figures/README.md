Manuscript figures for SN Computer Science (`papers/SNCS_2026/`).

Canonical manuscript assets:

- `f1_pipeline.png` — author-uploaded pipeline schematic (required by
  `manuscript/main.tex`; SHA-256
  `4feeac61a348f526f79393be017734a7dba45f6502004c8d557c93379bfe5af2`;
  source commit `3de82709c5af4c44951c2d57285aa914896cc85a`).
- `f2_bm25_share.pdf` — BM25 edge-weight share (from JDIQ `figures_v2`).
- `f3_cycle_decomposition.pdf` — ms1 cyclic before/after mutual deletion.
- `f4_bootstrap_forest.pdf` — bootstrap forest (from JDIQ `figures_v2`).
- `f5_exact_vs_greedy_gap.pdf` — exact vs greedy FAS weight.

Optional regenerators for Figures 3 and 5 (do **not** overwrite Figure 1):

```bash
python papers/SNCS_2026/figures/generate_f3_cycle_decomposition.py
python papers/SNCS_2026/figures/generate_f5_exact_vs_greedy_gap.py
```

`generate_f1_pipeline.py` is retained only as historical tooling; the manuscript
does not use its output. See `FIGURE_REDESIGN_NOTES.md`.
`style.py` sets sn-jnl single-column width (~5.10in) and embedded Type-42 fonts.
