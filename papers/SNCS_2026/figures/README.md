Manuscript figures for SN Computer Science (`papers/SNCS_2026/`).

Generators (run from repo root with project venv):

```bash
python papers/SNCS_2026/figures/generate_f1_pipeline.py
python papers/SNCS_2026/figures/generate_f3_cycle_decomposition.py
python papers/SNCS_2026/figures/generate_f5_exact_vs_greedy_gap.py
```

- `f1_pipeline` — dual greedy/exact repair pipeline schematic (vector).
- `f2_bm25_share` — BM25 edge-weight share (from JDIQ `figures_v2`).
- `f3_cycle_decomposition` — ms1 cyclic before/after mutual deletion (vector).
- `f4_bootstrap_forest` — bootstrap forest (from JDIQ `figures_v2`).
- `f5_exact_vs_greedy_gap` — exact vs greedy FAS weight (vector).

See `FIGURE_REDESIGN_NOTES.md` for the 2026-08-01 F1/structural redesign.
`style.py` sets sn-jnl single-column width (~5.10in) and embedded Type-42 fonts.
