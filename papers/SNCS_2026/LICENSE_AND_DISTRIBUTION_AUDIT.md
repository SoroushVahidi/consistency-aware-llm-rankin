# License and Distribution Audit

**Date:** 2026-08-01  
**Scope:** repository license, datasets, vendored template, figures, model
outputs, solver implications, and source-ZIP contents.  
**Disclaimer:** this is an inventory against available license texts and project
policy documents — **not legal advice**. Uncertainty is flagged explicitly.

## Summary table

| Concern | Classification | Notes |
|---|---|---|
| Repository code (`LICENSE`, MIT) | Clear | Copyright (c) 2026 Soroush Vahidi; MIT terms apply to Software |
| `pyproject.toml` license field | Clear | Declares MIT |
| Benchmark datasets (BEIR/FiQA/HotpotQA/SciDocs/BRIGHT, etc.) | Attribution required / Redistribution restricted | Cite originals; do **not** redistribute raw corpora in a release archive unless each upstream license is checked and permits it |
| Stored derived score files / fixed query lists in reports | Author confirmation required for bulk redistribution | Treated as project-processed artifacts for reproducibility; still avoid shipping upstream document text dumps |
| Springer Nature `sn-jnl.cls` + `sn-basic.bst` in source ZIP | Attribution required | Official author template vendored for submission/compilation; redistributing inside the journal source ZIP is standard author practice; broader packaging should retain provenance note in `papers/SNCS_2026/README.md` |
| Official sample PDFs / `sn-user-manual.pdf` under `template/` | Exclude from release if unused | Reference-only; not required in the submission ZIP (already excluded from `SNCS_2026_latex_source.zip`) |
| Manuscript figures F1–F5 | Clear (author-generated / canonical-data plots) | F2–F4 copied from JDIQ figure set of the same author evidence; not third-party copyrighted art |
| Copied/adapted third-party figures | Clear (none identified) | No external publisher figures embedded |
| Compact parsed LLM judgments in reports | Redistribution restricted (policy) | Allowed in compact form per artifact policy; **raw** transcripts excluded |
| Raw provider request/response payloads | Exclude from release | May contain prompts/completions and operational detail |
| SCIP / PySCIPOpt usage | Clear for dependency use | Open-source exact solver path; distribute code that *calls* SCIP, not a redistributed proprietary binary |
| Gurobi | Redistribution restricted / optional | Academic license terms are personal/site-specific; never ship `gurobi.lic` or claim Gurobi as required |
| API keys / `.env` / cloud credentials | Exclude from release | Must never appear in tag, ZIP, or portal upload |
| Internal audit Markdown in `papers/SNCS_2026/` | Exclude from journal upload | Fine to keep in git; not part of manuscript source ZIP |
| `papers/_archive/` rejected-venue materials | Author confirmation required / usually exclude from DOI archive | Historical; not needed for SNCS reproduction |
| Model-output redistribution constraints (provider ToS) | Author confirmation required / Redistribution restricted | Compact aggregates are used; re-publishing raw completions may conflict with provider terms — raw already excluded |

## Repository license

- File: `LICENSE` — MIT License.
- Classification: **Clear** for the software and associated documentation files as defined by MIT.
- Manuscript PDF/text copyright for journal publication is a separate publishing agreement at acceptance; MIT on the repo does not by itself settle Springer copyright transfer/open-choice questions (**Author confirmation required** at acceptance time).

## Datasets

| Dataset family | How used | Classification |
|---|---|---|
| SciDocs, FiQA, HotpotQA, BRIGHT (and related BEIR-style sources) | Public benchmarks, cited in manuscript | **Attribution required**; raw redistrib. **restricted** pending per-dataset license check |
| qrels / judgments | Evaluation truth | Same as upstream dataset terms |
| Provider LLM outputs | Pilot only | Compact OK under project policy; raw **Exclude from release** |

## Vendored template files

- Provenance recorded in `papers/SNCS_2026/README.md` (Springer Nature LaTeX author-support package, sn-jnl v3.1 Dec 2024).
- Included in `SNCS_2026_latex_source.zip` because compilation requires `sn-jnl.cls` and `sn-basic.bst`.
- Classification: **Attribution required** for provenance; **Clear** for inclusion in the submission source archive as author tooling. Uncertainty remains if redistributing the full official sample kit beyond what Springer expects authors to upload — mitigated by shipping only cls/bst used here.

## Figures

- All five manuscript figures are project-generated PDFs.
- Classification: **Clear** for submission and repo distribution under the author’s control.
- PNG previews are convenience copies; optional to exclude from archives (**Optional / Exclude from release** for minimal ZIPs — already excluded from source ZIP).

## Solver licensing implications

- Manuscript exact repair uses SCIP via PySCIPOpt — **Clear** for open reproduction instructions.
- Gurobi remains optional internal validation — **Redistribution restricted** for license files; do not make Gurobi a reviewer dependency.

## Source ZIP contents review

Current ZIP members: `main.tex`, `references.bib`, five figure PDFs, `sn-jnl.cls`, `sn-basic.bst`.

| Member | OK to redistribute in submission ZIP? |
|---|---|
| Author tex/bib/figures | Yes — **Clear** |
| sn-jnl.cls / sn-basic.bst | Yes for submission — **Attribution required** |
| Secrets / raw transcripts / personal files | Not present — **Clear** |

## Residual uncertainties (not legal conclusions)

1. Whether every processed intermediate under `reports/` embeds upstream document text that would require redaction for a DOI-scale public archive.
2. Provider Terms of Service nuances for any future decision to publish additional LLM generations.
3. Springer open-choice / copyright forms after acceptance.

Flag these as **Author confirmation required** before creating a public DOI-backed archive (not required for the journal portal PDF+source upload itself).
