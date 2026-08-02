# Visual layout correction (2026-08-02)

No scientific numbers changed. Released with the SNCS submission package.

## Figure 1

| Field | Value |
|---|---|
| Source commit (`origin/main`) | `3de82709c5af4c44951c2d57285aa914896cc85a` (“Add files via upload”) |
| Source path | `71A559E5-30E7-465F-BDC0-33CF17FC3474.png` |
| Source SHA-256 | `4feeac61a348f526f79393be017734a7dba45f6502004c8d557c93379bfe5af2` |
| Installed path | `papers/SNCS_2026/figures/f1_pipeline.png` |
| Installed SHA-256 | identical (`4feeac61…5af2`) |
| LaTeX include | `\includegraphics[width=\linewidth]{f1_pipeline.png}` |
| Removed unused asset | `figures/f1_pipeline.pdf` (prior vector redesign; not referenced) |

Compiled manuscript embeds raster **1909×824**, matching the author upload.
Caption remains outside the image in LaTeX.

## Global table typography

- Packages: `booktabs`, `tabularx`, `array`, `ragged2e`
- Shared `\sncstable`: `\footnotesize`, `\arraystretch{1.28}`, `\tabcolsep 3.8pt`,
  raised tolerance / emergencystretch, higher hyphenation penalties
- Column types: `L{width}` and `Y` (ragged-right paragraph cells)
- No vertical rules; `\addlinespace` between dense rows
- No `\scriptsize` tables

## Table-by-table layout changes

| Table | Change |
|---|---|
| 1 `tab:closest-works` | 7 cramped columns → 4; `\mbox` on method names; `\addlinespace` |
| 2 `tab:preprint-comparison` | `tabularx` + ragged columns + `\addlinespace`; content unchanged |
| 3–7, 9–10 | Migrated to `\sncstable` / `tabularx` |
| 8 `tab:retrieval-holm` | Explicit Panel A / Panel B with separation; values unchanged |

## Shortened wording (meaning preserved)

| Location | Original | New |
|---|---|---|
| Table 1, LLM-RankFusion Diff. | `Improves agreement/aggregation; no exact MWFAS diagnostic on retrieval deltas` | `Improves agreement/aggregation; no exact-MWFAS retrieval diagnostic` |

## Status

`VISUAL PRESENTATION READY` — included in the public submission release.
