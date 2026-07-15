# Anonymous Submission Package

This is the double-anonymous artifact package for "Score Normalization and
Vote Construction Govern Preference-Graph Repair Outcomes in Multi-Ranker
Retrieval," submitted to the ACM Journal of Data and Information Quality
(JDIQ).

## Contents

- `manuscript/` — LaTeX source (`main.tex`, `references.bib`), the compiled
  PDF (`main.pdf`), and every figure the manuscript includes: the three
  preserved figures (`figure1.png`, `figure3.png`, `figure5.png`) and the
  seven generated figures under `figures_v2/` (`fig2`, `fig4`, `fig6`–`fig10`),
  plus the script (`generate_figures.py`) and shared style module
  (`style.py`) that produced them.
- `supplemental/` — everything needed to verify or reproduce the mechanical
  results without rerunning upstream retrieval or any paid API:
  - `REPRODUCIBILITY.md` — environment, commands, and the table-to-command
    map.
  - `DATA_AVAILABILITY.md` — dataset sourcing and artifact-availability
    statement, matching Section "Data Availability and Reproducibility" in
    `main.tex`.
  - `FIGURE_INVENTORY.md` — every figure's source script/CSV and status.
  - `FIGURE_DATA_VERIFICATION_REPORT.md` — 13 independent checks confirming
    every plotted value matches its source table.
  - `SUBMISSION_FREEZE_MANIFEST.json` — git commit, checksums for every
    canonical table, and the full protocol/pool/method registries this
    submission was frozen against.
  - `tables/` — every aggregate CSV table cited in the manuscript, grouped
    by the report directory that produced it.
  - `scripts/` — the driver and analysis scripts that produced those
    tables, and the verification scripts used to check them.

## What is deliberately not included

Per-query raw output (`manifest.json` / `query_records.jsonl`, 204 cells,
~1.2 GB total) is excluded: it duplicates what the aggregate tables already
report and its `manifest.json` files record local absolute filesystem paths
from the private working repository. The aggregate tables in
`supplemental/tables/` are sufficient to verify every number in the
manuscript; see `REPRODUCIBILITY.md` for how to regenerate the per-query
detail yourself from the stored score files if needed.

## Anonymity

No author name, institution, email, username, hostname, or
identity-revealing repository URL appears anywhere in this package
(verified by full-text scan as part of the submission's final audit).
